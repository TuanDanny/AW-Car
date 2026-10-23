# FPGA truyền động

Nơi lưu RTL và testbench cho 2 encoder A/B, PWM 2 motor sau, giao tiếp Motion
và watchdog/FSM. PID, xử lý cảm biến an toàn và servo lái nằm ở ESP32 Motion.

Trạng thái: mới chốt phân tải, chưa có RTL, báo cáo tổng hợp hay board đã chọn.
Viết lõi độc lập hãng; chỉ thêm thư mục RTL/testbench/target khi có file thực tế.
Quartus dùng chip Altera/Intel tham chiếu; Tang Nano phải đánh giá lại bằng
Gowin cho đúng mã chip, gồm place-and-route, timing và cấu hình tự khởi động.

Xem [kế hoạch và nghiệm thu toàn hệ thống](../docs/fpga-drive-plan.md).
