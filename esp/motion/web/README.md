# Web Motion simplev1

`index.html` là toàn bộ dashboard tiếng Việt: HTML/CSS/JavaScript nội tuyến,
không dependency, CDN hoặc tài nguyên ngoài. Motion phục vụ ở `/`, WebSocket `/ws`.
Contract nằm tại `docs/protocol.md`; hướng dẫn tại `docs/dashboard.md`.

Giữ nút hoặc W/S/A/D để gửi ngay rồi lặp 50 ms. Nhả nút mới nhất về neutral,
không khôi phục nút trước. Space gửi STOP. Trang chỉ kết nối một lần; sau khi
ngắt phải chọn Kết nối lại. Trạng thái/PWM là dữ liệu Motion trả về, không phải
bằng chứng xe đã dừng hoặc tốc độ đo. Simulator phải bật nhãn mô phỏng.

Kiểm thử trình duyệt: `python test/browser/test_dashboard.py --port 8783` sau
khi simulator C++ của `utils/simulator.py` đã sẵn sàng. Không dùng trang này để
thay deadline hoặc phân xử của Motion.
