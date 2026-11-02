# FPGA truyền động

Nơi lưu RTL và testbench cho 2 encoder một OUT, PWM hai nhóm motor trái/phải,
giao tiếp Motion và watchdog/FSM. Xe dùng TT 4WD, không servo lái; PID và xử lý
cảm biến an toàn nằm ở ESP32 Motion. Giữ encoder A/B X4 là cấu hình tùy chọn.
Toàn bộ nguồn RTL/testbench dùng **SystemVerilog, đuôi `.sv`**; hook/CI chặn
đuôi HDL khác. Runner bật `iverilog -g2012`, script tổng hợp bật `read_verilog -sv`.

Trạng thái: đã có RTL/testbench cho reset, encoder một OUT/A-B hai bên, snapshot,
count/period/age theo protocol v2 mặc định (STATUS 34 byte/frame 47 byte),
PWM hai kênh, trình tự đổi chiều độc lập driver và UART/parser/CRC/serializer/
command guard, FSM/watchdog và lõi `drive_core` đã nối link với PWM/adapter
DRV8833 drive/coast. Chưa có wrapper/constraints cho Tang Nano 9K hoặc báo cáo timing. Hợp đồng GPIO phục hồi/ARM
và gate ngoài ở [fpga-safety.md](../firmware/shared/fpga-safety.md). Xem
[vai trò từng file, luồng tín hiệu và rà soát nhẹ RTL](rtl/README.md),
ca thử ở [tb](tb/README.md).

Top triển khai duy nhất là **`rtl/aw_car_top.sv`**. Top này bọc một instance
`drive_core`, cố định một OUT/v2 và nối các cổng bên ngoài; không thêm thanh ghi.
`drive_core.sv` là lõi độc lập board, vẫn tổng hợp riêng để hồi quy A/B/v1.
Module con chia theo `common`, `encoder`,
`pwm`, `link`, `safety`, mỗi nhóm có README. Runner tìm `.sv` đệ quy trong
`rtl/`; năm script tổng hợp (gồm `synth_aw_car.ys`) dùng đường dẫn nhóm tương ứng.

Chạy từ root sau khi Icarus/VVP có trong PATH:

```sh
python tools/run_fpga_tests.py
```

Runner nhận `--iverilog` và `--vvp` để dùng đường dẫn cục bộ, `--waves` để lưu
VCD tại `fpga/build/`. Có34 testbench; `--report fpga/build/regression-report.json`
cùng `--require-module-coverage` xuất bằng chứng module -> test và chặn module
chưa tham gia bài PASS. Đây chưa phải coverage dòng/nhánh/toggle hoặc timing
vật lý. CI lưu JSON thành artifact và chạy mô phỏng trên Linux. Viết lõi độc lập hãng;
chỉ thêm thư mục target khi có wrapper/constraints thực tế.

Với bộ Icarus cục bộ đã chuẩn bị trên máy này, không cần đổi PATH hệ thống:

```sh
python tools/run_fpga_tests.py --iverilog D:/Project/AW-Car/build/toolchain/ucrt64/bin/iverilog.exe --vvp D:/Project/AW-Car/build/toolchain/ucrt64/bin/vvp.exe
```

Kết quả chạy và giới hạn được ghi ở [verification.md](verification.md).
Chưa nối motor thật: còn cần driver/gate an toàn bên ngoài, target và thử trên bàn.
`drive_core` có bốn đầu ra `drv_left_in1/in2`, `drv_right_in1/in2` để nối IN
hai module DRV8833. Bảng nối một module mỗi bên và yêu cầu STBY ở
[giao tiếp driver](../hardware/drv8833-interface.md); chưa gán số chân board.

Runner mặc định chạy top 2 giây ở clock rút gọn2,7MHz và bài lỗi ở27MHz.
Dùng `--full-timing --timeout 1800` để chạy cả bài2giây ở27MHz; CI dùng chế độ
này. Đây là thời gian mô phỏng, thời gian chạy trên máy có thể lâu hơn nhiều.

`synth_encoder.ys`, `synth_pwm.ys`, `synth_link.ys`, `synth_drive.ys` và
`synth_aw_car.ys` dùng kiểm tra latch/lỗi cấu trúc và mapping
generic Gowin; chạy từ root sau khi có `fpga/build/` bằng `yosys -s <script>`
hoặc YoWASP-Yosys. Đã chạy Yosys0.70 cục bộ; CI cũng chạy năm script này, gồm top hoàn chỉnh.
Script encoder và drive tổng hợp riêng cả mode một OUT mặc định lẫn mode A/B;
artifact có hậu tố `_ab` thuộc mode A/B.
Script PWM còn tổng hợp riêng adapter để kiểm tra ánh xạ tổ hợp không latch.
Chưa có pinout/constraints/PnR/STA đúng chip; cell count sơ bộ không kết luận fit.
Luồng đề xuất: Icarus/VVP + GTKWave để mô phỏng, Gowin Education để tổng hợp,
place-and-route và kiểm tra timing đúng chip Tang Nano 9K; không cần Quartus.
Tcd/Tpd min/max, setup/hold và slack được kiểm tra bằng STA sau route ở bước
target, trước khi mua board; xem [tiêu chí timing](../docs/fpga-rtl-design-test-plan.md#5-tổng-hợp-và-điều-kiện-quyết-định-mua-board).
Board mục tiêu **Nano 9K / GW1NR-LV9QN88PC6/I5**, chưa mua hoặc xác nhận
fit/timing/giá. Tối ưu duty và timer vẫn giữ mục tiêu 9K; số liệu trước/sau
ở [verification.md](verification.md). Công cụ kiểm chứng tương đương với bản
trước: `python tools/check_fpga_equivalence.py --base 821cfae --yosys <yosys>`.
Baseline này phục vụ refactor giữ chức năng; thay đổi thời gian/quy tắc cập
nhật interlock hiện tại là thay đổi chức năng, không dùng bằng chứng cũ để
kết luận tương đương cho phần đó.

Xem [kế hoạch và nghiệm thu toàn hệ thống](../docs/fpga-drive-plan.md).
Chi tiết [thiết kế RTL, kiểm thử và thứ tự triển khai](../docs/fpga-rtl-design-test-plan.md).
Wire format mặc định ở [protocol v2](../firmware/shared/fpga-protocol-v2.md);
[v1](../firmware/shared/fpga-protocol.md) giữ cho tương thích/hồi quy.

## Cấu hình xe hiện tại

`drive_core` mặc định `ALLOW_REVERSE=1`, `ENCODER_SINGLE_OUT=1`,
`PROTOCOL_VERSION=2`; wrapper `aw_car_top` chỉ lộ hai chân OUT
và bốn chân IN driver, dùng cùng thời gian đổi chiều 40 ms.
Mode A/B đặt `ENCODER_SINGLE_OUT=0` (mặc định phiên bản tương ứng là v1).
Cấu hình một OUT v1 cũ cần đặt riêng `PROTOCOL_VERSION=1`, không có period/age.
Hai đầu vào encoder là `encoder_left_out` và `encoder_right_out`; mỗi cảm biến
có VCC/GND/OUT. Cổng `left_ab/right_ab` không dùng ở mode này, wrapper nối 0.
OUT phải có mức điện áp phù hợp bank I/O đã chọn; không nối OUT 5 V trực tiếp
vào GPIO 3,3 V. Chưa có pinout Tang Nano 9K hoặc xác nhận điện trên module thật.

Duty là số tick HIGH trong 1.350 tick, không phải phần trăm. `direction[0]`
là bên trái, `[1]` là bên phải; 0 thuận, 1 ngược theo quy ước lắp motor:

| Chuyển động | direction[1:0] | Duty trái/phải ví dụ |
| --- | --- | --- |
| Tiến | `00` | 675 / 675 |
| Lùi | `11` | 675 / 675 |
| Rẽ trái khi tiến | `00` | 337 / 1012 |
| Rẽ phải khi tiến | `00` | 1080 / 270 |
| Quay trái tại chỗ | `01` | 675 / 675 |
| Quay phải tại chỗ | `10` | 675 / 675 |

Đổi chiều qua khoảng PWM zero1.080.000 tick (40ms) và setup27 tick (1us).
Lệnh cập nhật trong zero không khởi động lại bộ đếm; watchdog50ms không tạm
dừng. Đã có ca so sánh30/40ms, nhưng chưa đo rotor dừng hoặc xe quay đúng góc.
Một OUT chỉ đo độ lớn chuyển động, đếm cả khi thả trôi; Motion đọc cờ mode
STATUS bit4 và lấy delta không dấu modulo32 để tính tốc độ. Chưa thể suy ra
quãng đường có dấu chính xác chỉ từ cảm biến này và chiều lệnh.

## Chọn top và build

Dùng `aw_car_top` trong project triển khai xe; script chính là
`fpga/synth_aw_car.ys`. `synth_drive.ys` kiểm tra riêng lõi và mode A/B,
không phải top thứ hai chạy đồng thời trong bản nạp. Tên cũ
`drive_core_single_out` đã đổi thành `aw_car_top` ngày02/11/2026.
Logical top chưa thay wrapper clock/POR/I/O/constraints đúng Tang Nano9K.


## Kiểm tra khi đang chạy

Top chỉ lộ **17 tín hiệu một bit**:9 input (clk/reset/RX/2 encoder/4 safety),
8 output (TX/4 IN/permit/ack/clear). PWM/DIR/state/fault ở trong lõi, quan sát
qua UART hoặc testbench; không cần gán chân board cho28 bit debug cũ.
Protocol v2 có thêm [runtime diagnostics](../firmware/shared/fpga-protocol-v2.md#6-runtime-diagnostics--extension-02112026).
Không đổi kích thước STATUS. Chưa có constraints/PnR/STA hoặc firmware Motion.
