# FPGA truyền động

Nơi lưu RTL và testbench cho 2 encoder A/B, PWM 2 motor sau, giao tiếp Motion
và watchdog/FSM. PID, xử lý cảm biến an toàn và servo lái nằm ở ESP32 Motion.

Trạng thái: đã có RTL/testbench cho reset, encoder X4 hai bánh, snapshot,
PWM hai kênh và trình tự đổi chiều độc lập driver. Chưa có UART/watchdog,
adapter driver, target board hoặc báo cáo timing. Xem giao diện ở
[rtl](rtl/README.md), ca thử ở [tb](tb/README.md).

Chạy từ root sau khi Icarus/VVP có trong PATH:

```sh
python tools/run_fpga_tests.py
```

Runner nhận `--iverilog` và `--vvp` để dùng đường dẫn cục bộ, `--waves` để lưu
VCD tại `fpga/build/`. CI chạy mô phỏng trên Linux. Viết lõi độc lập hãng;
chỉ thêm thư mục target khi có wrapper/constraints thực tế.

Với bộ Icarus cục bộ đã chuẩn bị trên máy này, không cần đổi PATH hệ thống:

```sh
python tools/run_fpga_tests.py --iverilog build/toolchain/ucrt64/bin/iverilog.exe --vvp build/toolchain/ucrt64/bin/vvp.exe
```

Kết quả chạy và giới hạn được ghi ở [verification.md](verification.md).
Chưa được nối lõi PWM này vào motor: cần FSM/watchdog và gate an toàn bên ngoài.

`synth_encoder.ys` và `synth_pwm.ys` kiểm tra latch/lỗi cấu trúc và mapping
generic Gowin; chạy từ root sau khi có `fpga/build/` bằng `yosys -s <script>`
hoặc YoWASP-Yosys. Đã chạy Yosys0.70 cục bộ; CI cũng chạy hai script này.
Chưa có pinout/constraints/PnR/STA đúng chip; cell count sơ bộ không kết luận fit.
Luồng đề xuất: Icarus/VVP + GTKWave để mô phỏng, Gowin Education để tổng hợp,
place-and-route và kiểm tra timing đúng chip Tang Nano ứng viên; không cần
Quartus. Chưa chứng minh toàn lõi fit trên board 1K.

Xem [kế hoạch và nghiệm thu toàn hệ thống](../docs/fpga-drive-plan.md).
Chi tiết [thiết kế RTL, kiểm thử và thứ tự triển khai](../docs/fpga-rtl-design-test-plan.md).
