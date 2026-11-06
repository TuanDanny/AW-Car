# Mã Motion

`motion_core`: chủ sở hữu trạng thái/quyền/deadline; `fpga_link`: phục hồi và
ARM FPGA; `drive_model`: lái vi sai/kích đề-pa/đảo chiều. Ba phần C++ thuần
được biên dịch trực tiếp trên host. `runtime` nối UART/GPIO/timer/FreeRTOS;
`console` nhận cấu hình khi driver đã khóa. Không có Wi-Fi, PID hoặc driver
cảm biến ở mốc vòng hở. Giao thức nhị phân dùng codec trong `firmware/shared`.

Console `uart` có bộ đếm riêng cho hai peer và baud/chân thực được cấu hình;
đọc qua task console, không log/serialize trong RX/TX control path.

RX chờ event ISR tối đa1tick để vẫn kiểm epoch/generation khi dây im lặng,
rồi đọc ring buffer với timeout0. Không chờ đủ64byte trước khi feed parser.
Frame dở bị hủy khi epoch/generation đổi; lỗi FIFO/parity/framing giữ cách
xử lý và khóa driver. Chẩn đoán FPGA chỉ chép snapshot ngắn khi có reject,
bảo vệ bằng critical section riêng để context không trộn hai lỗi;
`UART_PARSE_DIAG` serialize từ task console, không printf/cấp phát ở RX.

WS2812 GPIO48 (`AWCAR_STATUS_LED_GPIO`) chỉ báo trạng thái. StatsTask100ms
chọn màu bằng policy C++ chung, ghi RMT khi đổi màu, không thêm I/O vào ISR/
control/UART. Fault đỏ; LOCKED/chờ FPGA hoặc gate xanh dương; sẵn sàng cục bộ
xanh lá, không đồng nghĩa ARM. Console status có indicator và số lần ghi/lỗi.
