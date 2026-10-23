# FPGA truyền động

Nơi lưu RTL và testbench cho 2 encoder A/B, PWM 2 motor sau, giao tiếp Motion
và watchdog/FSM. PID, xử lý cảm biến an toàn và servo lái nằm ở ESP32 Motion.

Trạng thái: mới chốt phân tải, chưa có RTL, báo cáo tổng hợp hay board đã chọn.
Viết lõi độc lập hãng; chỉ thêm thư mục RTL/testbench/target khi có file thực tế.
Luồng đề xuất: Icarus/VVP + GTKWave để mô phỏng, Gowin Education để tổng hợp,
place-and-route và kiểm tra timing đúng chip Tang Nano ứng viên; không cần
Quartus. Chưa cài/chạy xác minh toolchain, chưa chứng minh fit trên board 1K.

Xem [kế hoạch và nghiệm thu toàn hệ thống](../docs/fpga-drive-plan.md).
Chi tiết [thiết kế RTL, kiểm thử và thứ tự triển khai](../docs/fpga-rtl-design-test-plan.md).
