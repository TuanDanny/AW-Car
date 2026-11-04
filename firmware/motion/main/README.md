# Mã Motion

`motion_core`: chủ sở hữu trạng thái/quyền/deadline; `fpga_link`: phục hồi và
ARM FPGA; `drive_model`: lái vi sai/kích đề-pa/đảo chiều. Ba phần C++ thuần
được biên dịch trực tiếp trên host. `runtime` nối UART/GPIO/timer/FreeRTOS;
`console` nhận cấu hình khi driver đã khóa. Không có Wi-Fi, PID hoặc driver
cảm biến ở mốc vòng hở. Giao thức nhị phân dùng codec trong `firmware/shared`.

Console `uart` có bộ đếm riêng cho hai peer và baud/chân thực được cấu hình;
đọc qua task console, không log/serialize trong RX/TX control path.
