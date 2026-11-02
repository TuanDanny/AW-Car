# Motion - MCU 2

Nhận số đếm encoder từ FPGA, đọc cảm biến, chạy PID hai bên motor TT 4WD
và quyết định dừng an toàn độc lập với Brain, Web và Internet. Gửi duty/chiều
quay có hạn dùng cho FPGA; PWM hai bên do FPGA phát, xe lái vi sai không servo.
Encoder bản đầu một OUT mỗi bên; kiểm tra STATUS bit4 và lấy delta không dấu
để tính độ lớn tốc độ. Không coi chiều lệnh là chiều đo; A/B X4 là mode tùy chọn.

Phải có đường khóa driver phần cứng ngoài UART FPGA. Mất phản hồi FPGA, dữ liệu
encoder quá hạn hoặc hết lease Brain thì bỏ arm; không phát lại duty cũ để giữ
watchdog. Cần thực hiện GPIO recovery/STATUS xác nhận ARM và stale snapshot
30+1ms theo [hợp đồng Motion–FPGA](../shared/fpga-safety.md).
Xem [phân tải và an toàn](../../docs/fpga-drive-plan.md).

Trạng thái: chưa có firmware. Cần kiểm thử boot/reset, mất lệnh, lỗi cảm biến,
kẹt bánh và dừng khẩn cấp trước khi nghiệm thu chuyển động.

Liên kết Brain dùng [đặc tả Brain–Motion](../shared/brain-motion-protocol.md);
FPGA một OUT mặc định dùng [Motion–FPGA v2](../shared/fpga-protocol-v2.md),
STATUS34 byte/frame47. Cả firmware parser và PID tích hợp vẫn chưa triển khai.
