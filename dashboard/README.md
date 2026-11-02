# Web Dashboard

Giao diện điều khiển và xem telemetry: vận tốc, cảm biến, nguồn, lỗi và trạng
thái kết nối. Sau này tích hợp phục vụ giao diện từ Brain.

Trạng thái: chưa chọn framework hay tạo ứng dụng. Cần một phiên điều khiển,
giới hạn lệnh và timeout khi mất kết nối; không để logic Web thay thế an toàn ở Motion.

Đã có [đặc tả Web Dashboard ↔ ESP32-S3 Brain (Web-v1)](web-brain-protocol.md):
WebSocket/JSON; các field MOVE, ACK/STATUS, giá trị/đơn vị và tần suất đề xuất
(MOVE 20 Hz, STATUS 10 Hz, TTL 120 ms, Brain timeout 150 ms).
**Chưa có mã Web server/firmware hoặc số đo độ trễ thực tế.**
