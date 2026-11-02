# Brain - MCU 1

Thu 1 mic INMP441, phát loa, tích hợp Xiaozhi, màn hình OLED 0,96 inch **I²C**
hiển thị biểu cảm/trạng thái và kết nối Web Dashboard.
Gửi yêu cầu chuyển động đã giới hạn tới Motion qua UART.
Liên kết Dashboard được đặc tả ở [Web-v1](../../dashboard/web-brain-protocol.md)
(Wi-Fi/WebSocket/JSON, quyền điều khiển duy nhất, dead-man và timeout); Brain
chuyển lệnh mới hợp lệ sang [BM-v1](../shared/brain-motion-protocol.md), không
chuyển JSON trực tiếp xuống Motion.

Phần cứng đã có: một trong hai ESP32-S3 có Wi-Fi (chủ dự án ghi `R16N8`),
mic, OLED và ampli I²S MAX98357A. Người dùng đã nạp Xiaozhi stock và xác nhận
OLED hiển thị với GPIO 41/42 (source profile: SDA=41, SCL=42). Chưa xác nhận
mã board/bộ nhớ, anten, controller vật lý/độ phân giải OLED hoặc toàn bộ
pinout; không mặc định WROOM-1U hay giao tiếp SPI.
Xem [kiểm kê hiện tại](../../hardware/components.md). Món đang chọn là 1 loa
thụ động 4 Ω 3 W ghép MAX98357A đã có; chưa kiểm thử âm thanh trên phần cứng.
TFT 2,8 inch là phương án cũ; LVGL/GIF/QR cần đánh giá lại theo OLED thực.

Trạng thái đồng bộ02/11/2026: source Brain/Xiaozhi đã phát triển và thử trên
[nhánh AI riêng](https://github.com/TuanDanny/AW-Car/tree/feat/f03-xiaozhi-ai/firmware/brain),
commit112914e; không dùng ghi chú binary ban đầu để kết luận source chưa có.
Xiaozhi v2.5.2 đã build/nạp ESP32-S3 tại0x0000; boot nhận PSRAM8MB,
OLED hoạt động, INMP441 thu được lời nói tiếng Trung. Demo AI gọi tool
bật/tắt/đổi RGB đỏ/xanh lá/xanh dương đã được log và người dùng xác nhận.
Nhấn/nhả BOOT để nghe. Loa chưa gắn/thử; tối ưu độ trễ còn ở bước nghiên cứu.

Bản FPGA này giữ đặc tả ghép nối chung; chưa có firmware UART Brain–Motion
hoặc xe tích hợp được nghiệm thu. Binary gốc và phân tích ngày28/10 ở
[kết quả phân tích](../../docs/xiaozhi-binary-review.md) là tham chiếu lịch sử,
không thay source đã thử trên nhánh AI.
DoA dành cho nâng cấp; không điều khiển PWM motor trực tiếp từ lệnh AI hoặc Web.
