const $ = id => document.getElementById(id);
let voiceBlob = null, lastObjectUrl = null, topicData = null;
const MAX_VIDEO = 100 * 1024 * 1024;
const setStatus = (id, msg, kind='') => { $(id).textContent = msg; $(id).className = `status ${kind}`; };
const scriptText = () => $('script').value.trim();
const setBusy = busy => { ['analyzeThread','generateScript','makeVoice','render'].forEach(id => $(id).disabled = busy); $('progressWrap').hidden = !busy; };
const progress = n => $('progressBar').style.width = `${Math.max(0,Math.min(100,n))}%`;

$('script').addEventListener('input', () => $('charCount').textContent = `${$('script').value.length} / 5000 ký tự`);
$('background').addEventListener('change', () => { const f=$('background').files[0]; $('bgInfo').textContent=f?`${f.name} · ${(f.size/1048576).toFixed(1)} MB`:'Chưa chọn video nền'; voiceBlob=null; });
$('threadUrl').addEventListener('keydown', e => { if(e.key==='Enter') $('analyzeThread').click(); });

$('analyzeThread').addEventListener('click', async () => {
  const url=$('threadUrl').value.trim();
  if(!url) return setStatus('topicStatus','Bạn chưa dán link Threads.','error');
  setBusy(true); setStatus('topicStatus','Đang thử đọc bài viết Threads…'); progress(12);
  try {
    const r=await fetch('/api/thread/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const data=await r.json(); if(!r.ok) throw new Error(data.detail||'Không đọc được bài viết.');
    topicData=data; $('topicResult').hidden=false; $('topicAuthor').textContent=data.author||'Bài viết Threads'; $('topicStats').textContent=data.source||'Nội dung công khai'; $('topicText').textContent=data.text||'Không tìm thấy phần nội dung văn bản trong bài.'; $('topicOpen').href=data.url;
    const notes=[]; if(data.text) notes.push('Đã lấy được nội dung topic.'); if(!data.comments_available) notes.push('Threads không cung cấp bình luận qua đường truy cập này; bạn có thể dán bình luận chọn lọc ở phần tùy chọn.');
    setStatus('topicStatus',notes.join(' '),'success'); progress(100);
    if(data.text) $('generateScript').disabled=false;
  } catch(e) { topicData=null; setStatus('topicStatus',e.message||'Có lỗi khi đọc link.','error'); }
  finally { setBusy(false); }
});

function buildScript() {
  if(!topicData?.text) throw new Error('Hãy phân tích link Threads trước.');
  const topic=topicData.text.replace(/\s+/g,' ').trim();
  const comments=$('comments').value.split('\n').map(x=>x.trim()).filter(Boolean).slice(0,5);
  const tone=$('tone').value, duration=$('duration').value;
  const openers={genz:'Ê, lướt Threads mà gặp topic này thì phải dừng lại đọc liền nè!',funny:'Ủa alo, Threads hôm nay lại có chuyện gì mà náo nhiệt dữ vậy?',story:'Có một topic trên Threads đang khiến nhiều người phải bàn luận, và đây là chuyện xảy ra.',neutral:'Hôm nay cùng xem một chủ đề đang được chia sẻ trên Threads nhé.'};
  const reactions={genz:'Đọc tới đây mới thấy mỗi người một góc nhìn, đúng là không có chuyện gì đơn giản như mình nghĩ.',funny:'Đọc xong chỉ biết: mạng xã hội đúng là không bao giờ thiếu plot twist.',story:'Điều đáng chú ý là câu chuyện không chỉ nằm ở bài đăng, mà còn ở những góc nhìn phía dưới.',neutral:'Chủ đề này cho thấy có nhiều cách nhìn nhận khác nhau về cùng một vấn đề.'};
  const intro= openers[tone];
  const summary=topic.length>700?topic.slice(0,697).replace(/\s+\S*$/,'')+'…':topic;
  let middle=`Topic được đăng trên Threads chia sẻ rằng: ${summary}`;
  if(comments.length) middle+=`\n\nMột vài bình luận đáng chú ý:\n${comments.map((c,i)=>`Ý kiến ${i+1}: ${c}`).join('\n')}`;
  else middle+='\n\nHiện chưa lấy được bình luận tự động từ Threads, nên phần lời dẫn sẽ tập trung vào nội dung topic, không tự tạo bình luận giả.';
  let outro=tone==='funny'?'Còn bạn đứng về góc nhìn nào? Thả ý kiến xuống dưới, cùng hóng phần tiếp theo!':tone==='neutral'?'Bạn nghĩ sao về chủ đề này? Hãy chia sẻ góc nhìn của mình nhé.':'Còn bạn thấy sao? Comment góc nhìn của mình xuống dưới nha, biết đâu lại có thêm một góc nhìn cực cuốn!';
  let result=`${intro}\n\n${middle}\n\n${reactions[tone]}\n\n${outro}`;
  if(duration==='short') result=result.slice(0,1700);
  if(duration==='medium' && result.length<450) result+='\n\nVà đó là topic hôm nay. Nếu thấy thú vị thì gửi video này cho người cũng muốn bàn về chủ đề này nhé!';
  if(duration==='long') result+='\n\nThử nhìn rộng hơn một chút, điều quan trọng là mình nên lắng nghe các ý kiến khác nhau, kiểm chứng thông tin và tự đưa ra quan điểm của mình.';
  return result.slice(0,5000);
}
$('generateScript').addEventListener('click',()=>{try{$('script').value=buildScript();$('script').dispatchEvent(new Event('input'));setStatus('status','Đã tạo lời thoại Gen Z. Bạn có thể chỉnh sửa trước khi tạo giọng đọc.','success');$('scriptPanel').scrollIntoView({behavior:'smooth',block:'start'});}catch(e){setStatus('topicStatus',e.message,'error');}});
$('cleanText').addEventListener('click',()=>{$('script').value=$('script').value.replace(/https?:\/\/\S+/g,'').replace(/[ \t]+/g,' ').replace(/\n{3,}/g,'\n\n').trim();$('script').dispatchEvent(new Event('input'));});
async function requestVoice(){const text=scriptText();if(!text)throw new Error('Bạn chưa có kịch bản.');const r=await fetch('/api/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,voice:$('voice').value})});if(!r.ok){let j={};try{j=await r.json()}catch{}throw new Error(j.detail||'Không tạo được giọng đọc.')}return r.blob();}
$('makeVoice').addEventListener('click',async()=>{setBusy(true);setStatus('status','Đang tạo giọng đọc…');progress(20);try{voiceBlob=await requestVoice();if(lastObjectUrl)URL.revokeObjectURL(lastObjectUrl);lastObjectUrl=URL.createObjectURL(voiceBlob);$('voicePreview').src=lastObjectUrl;$('voicePreview').hidden=false;progress(100);setStatus('status','Đã tạo giọng đọc. Hãy nghe thử nhé.','success');}catch(e){setStatus('status',e.message,'error')}finally{setBusy(false)}});
$('render').addEventListener('click',async()=>{const text=scriptText(),bg=$('background').files[0];if(!text)return setStatus('status','Hãy tạo hoặc nhập kịch bản trước.','error');if(!bg)return setStatus('status','Hãy chọn video nền trước khi xuất.','error');if(bg.size>MAX_VIDEO)return setStatus('status','Video nền vượt quá 100 MB.','error');setBusy(true);$('download').hidden=true;progress(8);try{if(!voiceBlob)voiceBlob=await requestVoice();progress(35);setStatus('status','Đang ghép video, giọng đọc và phụ đề…');const form=new FormData();form.append('background',bg,bg.name);form.append('audio',voiceBlob,'voice.mp3');form.append('script',text);form.append('ratio',$('ratio').value);form.append('font_size',$('fontSize').value);form.append('subtitle_position',$('subtitlePosition').value);const r=await fetch('/api/render',{method:'POST',body:form});if(!r.ok){let j={};try{j=await r.json()}catch{}throw new Error(j.detail||'Xuất video thất bại.')}const video=await r.blob();if(!video.size)throw new Error('Video đầu ra trống.');if(lastObjectUrl)URL.revokeObjectURL(lastObjectUrl);lastObjectUrl=URL.createObjectURL(video);$('download').href=lastObjectUrl;$('download').download=`threads-video-${new Date().toISOString().slice(0,10)}.mp4`;$('download').hidden=false;progress(100);setStatus('status',`Hoàn tất! Video ${(video.size/1048576).toFixed(1)} MB đã sẵn sàng.`,'success');}catch(e){setStatus('status',e.message,'error')}finally{setBusy(false)}});
if('serviceWorker'in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));
