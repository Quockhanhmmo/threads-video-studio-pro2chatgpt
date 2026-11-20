# Threads Studio PRO 2.0 · GenZ Mode

Bản nâng cấp ưu tiên điện thoại Android: giao diện một cột, nhập một link topic, thử đọc metadata công khai, tạo lời thoại Gen Z, TTS và xuất MP4.

## Tính năng
- Giao diện mobile-first một cột; không còn bố cục hai cột bị bóp trên màn hình hẹp.
- Dán một link bài viết Threads (`threads.net` hoặc `threads.com`) và bấm **Phân tích**.
- Backend thử lấy tiêu đề/tác giả/nội dung từ metadata công khai của bài viết.
- Tạo lời thoại tiếng Việt theo các phong cách Gen Z, hài, kể chuyện hoặc trung tính; chọn độ dài 30–45, 45–60 hoặc 60–90 giây.
- Có vùng dán bình luận thủ công khi Threads không cung cấp bình luận cho máy chủ.
- Tạo giọng đọc Edge TTS (Hoài My / Nam Minh), ghép video nền và phụ đề, xuất MP4 H.264.
- PWA có cache shell phiên bản 2.

## Giới hạn quan trọng
- Threads thường chặn yêu cầu tự động hoặc không đưa nội dung bài viết/bình luận vào metadata. Vì vậy link không phải lúc nào cũng đọc được. Khi không lấy được, ứng dụng sẽ báo lỗi rõ ràng thay vì giả vờ đã đọc.
- Endpoint hiện chỉ lấy metadata bài viết công khai; **chưa tự lấy được danh sách bình luận/replies**. Có thể dán những bình luận muốn dùng vào phần tùy chọn. Không tự tạo bình luận giả.
- Bộ tạo kịch bản hiện là bộ dựng lời thoại theo mẫu/heuristic Gen Z, không phải mô hình AI sinh ngôn ngữ kết nối cloud. Có thể thay bằng API AI ở phiên bản sau nếu bổ sung khóa API và xử lý an toàn phía máy chủ.
- Không đăng nhập, không vượt quyền riêng tư, không lấy nội dung riêng tư.
- Phụ đề chia thời gian ước lượng, chưa căn khớp từng từ. Video tối đa 3 phút, nền tối đa 100 MB.
- Edge TTS và FFmpeg cần backend có Internet và tài nguyên phù hợp. Free hosting có thể sleep hoặc giới hạn thời gian/RAM.

## Chạy bằng Docker
```bash
docker build -t threads-studio .
docker run --rm -p 8000:8000 threads-studio
```
Mở `http://localhost:8000`.

## Triển khai Render
1. Đưa toàn bộ thư mục dự án lên một repository GitHub.
2. Trong Render chọn **New → Blueprint** và kết nối repository.
3. Render đọc `render.yaml`, build Docker backend và deploy.
4. Dùng URL HTTPS của Render trên điện thoại. Trên Chrome Android có thể chọn menu ⋮ → **Cài đặt ứng dụng**.

**Lưu ý:** GitHub Pages chỉ host frontend tĩnh, không chạy được `/api/thread/analyze`, `/api/tts` hoặc `/api/render`. Muốn dùng đầy đủ cần backend Render/Docker; không chỉ mở repository trên GitHub Pages.

## Kiểm tra
- `GET /api/health`
- `POST /api/thread/analyze`
- API docs: `/docs`
