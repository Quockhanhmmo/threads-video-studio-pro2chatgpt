import os, re, tempfile, subprocess, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import edge_tts

BASE = Path(__file__).resolve().parent.parent
FRONTEND = BASE / "frontend"
app = FastAPI(title="Threads Video Studio PRO", version="1.0.0")

class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = Field(pattern=r"^vi-VN-(HoaiMy|NamMinh)Neural$")

def run_ffmpeg(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Quá thời gian xử lý. Hãy thử video ngắn hơn.")
    if p.returncode != 0:
        detail = (p.stderr or "FFmpeg error")[-1800:]
        raise HTTPException(500, "Không thể kết xuất video. " + detail)

@app.get("/api/health")
def health():
    return {"ok": True, "service": "Threads Video Studio PRO"}

@app.post("/api/tts")
async def tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Kịch bản đang trống.")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "voice.mp3"
        try:
            communicate = edge_tts.Communicate(text, req.voice)
            await communicate.save(str(out))
        except Exception as e:
            raise HTTPException(502, "Dịch vụ giọng đọc hiện không phản hồi. Hãy thử lại sau.")
        if not out.exists() or out.stat().st_size < 1000:
            raise HTTPException(502, "Không nhận được dữ liệu giọng đọc hợp lệ.")
        # The response streams the temporary file before the directory is removed.
        data = out.read_bytes()
    from fastapi.responses import Response
    return Response(content=data, media_type="audio/mpeg", headers={"Content-Disposition": 'inline; filename="voice.mp3"'})

def srt_time(seconds):
    ms = max(0, int(seconds * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(text, duration, path):
    # Approximate subtitle timing by Vietnamese word groups; keep each card readable.
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    groups = [" ".join(words[i:i+8]) for i in range(0, len(words), 8)]
    if not groups: groups = [text]
    total_chars = sum(max(1, len(g)) for g in groups)
    cursor = 0.0
    lines = []
    for i, group in enumerate(groups, 1):
        span = duration * max(1, len(group)) / total_chars
        end = duration if i == len(groups) else min(duration, cursor + span)
        lines += [str(i), f"{srt_time(cursor)} --> {srt_time(end)}", group, ""]
        cursor = end
    path.write_text("\n".join(lines), encoding="utf-8")

@app.post("/api/render")
async def render(
    background: UploadFile = File(...),
    audio: UploadFile = File(...),
    script: str = Form(...),
    ratio: str = Form("9:16"),
    font_size: str = Form("medium"),
    subtitle_position: str = Form("bottom")
):
    if not script.strip() or len(script) > 5000:
        raise HTTPException(400, "Kịch bản phải có từ 1 đến 5.000 ký tự.")
    if ratio not in ("9:16", "1:1", "16:9"):
        raise HTTPException(400, "Tỷ lệ video không hợp lệ.")
    if font_size not in ("small", "medium", "large") or subtitle_position not in ("bottom", "middle"):
        raise HTTPException(400, "Thiết lập phụ đề không hợp lệ.")
    if not (background.filename or "").lower().endswith((".mp4", ".mov", ".webm", ".m4v")):
        raise HTTPException(400, "Video nền phải là MP4, MOV, WebM hoặc M4V.")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bg, au, srt, out = td/"background", td/"voice.mp3", td/"captions.srt", td/"final.mp4"
        bg_data = await background.read()
        au_data = await audio.read()
        if len(bg_data) > 100*1024*1024:
            raise HTTPException(413, "Video nền vượt quá 100 MB.")
        if len(au_data) > 25*1024*1024:
            raise HTTPException(413, "File giọng đọc quá lớn.")
        if len(bg_data) < 1000 or len(au_data) < 1000:
            raise HTTPException(400, "File video hoặc âm thanh không hợp lệ.")
        bg.write_bytes(bg_data); au.write_bytes(au_data)
        probe = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(au)], capture_output=True, text=True)
        try: duration = float(probe.stdout.strip())
        except: raise HTTPException(400, "Không đọc được thời lượng giọng đọc.")
        if duration <= 0 or duration > 180:
            raise HTTPException(400, "Video đầu ra giới hạn tối đa 3 phút.")
        make_srt(script, duration, srt)
        dimensions = {"9:16":(1080,1920), "1:1":(1080,1080), "16:9":(1920,1080)}
        w,h = dimensions[ratio]
        font = {"small":36, "medium":48, "large":60}[font_size]
        y = "h-th-150" if subtitle_position == "bottom" else "(h-th)/2"
        # Escape path for FFmpeg subtitles filter.
        srt_path = str(srt).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},subtitles='{srt_path}':force_style='FontName=DejaVu Sans,FontSize={font},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV={150 if subtitle_position == 'bottom' else h//2}'"
        args = ["ffmpeg","-y","-stream_loop","-1","-i",str(bg),"-i",str(au),"-vf",vf,"-map","0:v:0","-map","1:a:0","-t",str(duration),"-r","30","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",str(out)]
        run_ffmpeg(args)
        payload = out.read_bytes()
    from fastapi.responses import Response
    return Response(content=payload, media_type="video/mp4", headers={"Content-Disposition": 'attachment; filename="threads-video.mp4"'})

app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")

# Public Threads link reader. Threads may block server-side requests or omit replies;
# this endpoint only returns text actually present in public metadata.
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.title = False; self.title_parts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "meta":
            key = attrs.get("property") or attrs.get("name")
            value = attrs.get("content")
            if key and value: self.meta[key.lower()] = value
        elif tag.lower() == "title": self.title = True
    def handle_endtag(self, tag):
        if tag.lower() == "title": self.title = False
    def handle_data(self, data):
        if self.title: self.title_parts.append(data)

class ThreadAnalyzeRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2000)

@app.post("/api/thread/analyze")
def analyze_thread(req: ThreadAnalyzeRequest):
    parsed = urlparse(req.url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ("threads.net", "www.threads.net", "threads.com", "www.threads.com"):
        raise HTTPException(400, "Chỉ chấp nhận link https://threads.net hoặc https://threads.com.")
    if not re.search(r"/(post|t|share)/[A-Za-z0-9_-]+", parsed.path):
        raise HTTPException(400, "Link chưa giống một bài viết Threads. Hãy sao chép link bài đăng, không phải link hồ sơ.")
    req_obj = Request(req.url.strip(), headers={"User-Agent": "Mozilla/5.0 (compatible; ThreadsStudio/2.0; +https://threads.net)"})
    try:
        with urlopen(req_obj, timeout=12) as response:
            final = urlparse(response.geturl())
            if (final.hostname or "").lower() not in ("threads.net", "www.threads.net", "threads.com", "www.threads.com"):
                raise HTTPException(400, "Link chuyển hướng ra ngoài Threads nên đã bị từ chối.")
            raw = response.read(2_500_000).decode("utf-8", "ignore")
        parser = MetaParser(); parser.feed(raw)
        meta = parser.meta
        title = meta.get("og:title", "")
        description = meta.get("og:description", "")
        author = ""
        # Common OG title format contains the account handle and Threads.
        match = re.search(r"@([A-Za-z0-9._]+)", title)
        if match: author = "@" + match.group(1)
        text = description or meta.get("description", "")
        text = re.sub(r"\s+", " ", text).strip()
        # Avoid returning generic page metadata as if it were the post body.
        if text and len(text) < 12: text = ""
        if not text:
            raise HTTPException(424, "Threads không trả nội dung bài viết cho máy chủ. Hãy mở bài viết và sao chép nội dung công khai vào ô bình luận/nội dung thủ công.")
        return {"ok": True, "url": req.url.strip(), "author": author or "Bài viết Threads", "text": text[:5000], "source": "Đọc từ metadata công khai", "comments_available": False}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(424, "Không thể đọc bài viết từ Threads lúc này. Threads có thể chặn truy cập tự động hoặc yêu cầu đăng nhập. Hãy thử lại sau hoặc dán nội dung công khai thủ công.")
