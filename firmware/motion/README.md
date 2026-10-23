# Motion - MCU 2

Nhận số đếm encoder từ FPGA, đọc cảm biến, chạy PID từng motor, điều khiển servo
và quyết định dừng an toàn độc lập với Brain, Web và Internet. Gửi duty/chiều
quay có hạn dùng cho FPGA; PWM của 2 motor sau do FPGA phát.

Phải có đường khóa driver phần cứng ngoài UART FPGA. Mất phản hồi FPGA, dữ liệu
encoder quá hạn hoặc hết lease Brain thì bỏ arm; không phát lại duty cũ để giữ
watchdog. Cần thực hiện GPIO recovery/STATUS xác nhận ARM và stale snapshot
30+1ms theo [hợp đồng Motion–FPGA](../shared/fpga-safety.md).
Xem [phân tải và an toàn](../../docs/fpga-drive-plan.md).

Trạng thái: chưa có firmware. Cần kiểm thử boot/reset, mất lệnh, lỗi cảm biến,
kẹt bánh và dừng khẩn cấp trước khi nghiệm thu chuyển động.
