# FPGA truyền động

Nơi lưu RTL và testbench cho 2 encoder A/B, PWM hai nhóm motor trái/phải,
giao tiếp Motion và watchdog/FSM. Xe dùng TT 4WD, không servo lái; PID và xử lý
cảm biến an toàn nằm ở ESP32 Motion. Mode encoder một OUT còn là kế hoạch.
Toàn bộ nguồn RTL/testbench dùng **SystemVerilog, đuôi `.sv`**; hook/CI chặn
đuôi HDL khác. Runner bật `iverilog -g2012`, script tổng hợp bật `read_verilog -sv`.

Trạng thái: đã có RTL/testbench cho reset, encoder X4 hai bánh, snapshot,
PWM hai kênh, trình tự đổi chiều độc lập driver và UART/parser/CRC/serializer/
command guard, FSM/watchdog và top `drive_core` đã nối link với PWM. Chưa có
adapter driver, wrapper/constraints cho Tang Nano 9K hoặc báo cáo timing. Hợp đồng GPIO phục hồi/ARM
và gate ngoài ở [fpga-safety.md](../firmware/shared/fpga-safety.md). Xem
[vai trò từng file, luồng tín hiệu và rà soát nhẹ RTL](rtl/README.md),
ca thử ở [tb](tb/README.md).

Top logic ở `rtl/drive_core.sv`; module con chia theo `common`, `encoder`,
`pwm`, `link`, `safety`, mỗi nhóm có README. Runner tìm `.sv` đệ quy trong
`rtl/`; bốn script tổng hợp dùng đường dẫn nhóm tương ứng.

Chạy từ root sau khi Icarus/VVP có trong PATH:

```sh
python tools/run_fpga_tests.py
```

Runner nhận `--iverilog` và `--vvp` để dùng đường dẫn cục bộ, `--waves` để lưu
VCD tại `fpga/build/`. Có22 testbench; `--report fpga/build/regression-report.json`
cùng `--require-module-coverage` xuất bằng chứng module -> test và chặn module
chưa tham gia bài PASS. Đây chưa phải coverage dòng/nhánh/toggle hoặc timing
vật lý. CI lưu JSON thành artifact và chạy mô phỏng trên Linux. Viết lõi độc lập hãng;
chỉ thêm thư mục target khi có wrapper/constraints thực tế.

Với bộ Icarus cục bộ đã chuẩn bị trên máy này, không cần đổi PATH hệ thống:

```sh
python tools/run_fpga_tests.py --iverilog build/toolchain/ucrt64/bin/iverilog.exe --vvp build/toolchain/ucrt64/bin/vvp.exe
```

Kết quả chạy và giới hạn được ghi ở [verification.md](verification.md).
Chưa nối motor thật: còn cần driver/gate an toàn bên ngoài, target và thử trên bàn.

Runner mặc định chạy top 2 giây ở clock rút gọn2,7MHz và bài lỗi ở27MHz.
Dùng `--full-timing --timeout 1800` để chạy cả bài2giây ở27MHz; CI dùng chế độ
này. Đây là thời gian mô phỏng, thời gian chạy trên máy có thể lâu hơn nhiều.

`synth_encoder.ys`, `synth_pwm.ys`, `synth_link.ys`, `synth_drive.ys` kiểm tra latch/lỗi cấu trúc và mapping
generic Gowin; chạy từ root sau khi có `fpga/build/` bằng `yosys -s <script>`
hoặc YoWASP-Yosys. Đã chạy Yosys0.70 cục bộ; CI cũng chạy bốn script này, gồm top hoàn chỉnh.
Chưa có pinout/constraints/PnR/STA đúng chip; cell count sơ bộ không kết luận fit.
Luồng đề xuất: Icarus/VVP + GTKWave để mô phỏng, Gowin Education để tổng hợp,
place-and-route và kiểm tra timing đúng chip Tang Nano 9K; không cần Quartus.
Tcd/Tpd min/max, setup/hold và slack được kiểm tra bằng STA sau route ở bước
target, trước khi mua board; xem [tiêu chí timing](../docs/fpga-rtl-design-test-plan.md#5-tổng-hợp-và-điều-kiện-quyết-định-mua-board).
Board mục tiêu **Nano 9K / GW1NR-LV9QN88PC6/I5**, chưa mua hoặc xác nhận
fit/timing/giá. Tối ưu duty và timer vẫn giữ mục tiêu 9K; số liệu trước/sau
ở [verification.md](verification.md). Công cụ kiểm chứng tương đương với bản
trước: `python tools/check_fpga_equivalence.py --base 821cfae --yosys <yosys>`.

Xem [kế hoạch và nghiệm thu toàn hệ thống](../docs/fpga-drive-plan.md).
Chi tiết [thiết kế RTL, kiểm thử và thứ tự triển khai](../docs/fpga-rtl-design-test-plan.md).
Wire format và ranh giới phiên/ARM ở [protocol v1](../firmware/shared/fpga-protocol.md).
