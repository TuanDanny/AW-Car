# RTL độc lập hãng

Lõi SystemVerilog (`.sv`), một clock domain, không tạo clock bằng logic.
RTL dùng `logic`, `always_ff` cho thanh ghi, `assign` cho tổ hợp đơn giản và
enum cho FSM. Không dùng khởi tạo biến thay phép gán liên tục.
Top tích hợp **duy nhất cho bản triển khai là `aw_car_top`**, đặt ngay root
và chứa một instance `drive_core`. Lõi không phụ thuộc chân board; module con
phân theo chức năng:

```text
rtl/
  README.md
  drive_core.sv               # lõi chung, tổng hợp riêng để kiểm thử
  aw_car_top.sv               # top triển khai, 2 OUT/v2; bọc drive_core
  common/                     # reset, đồng bộ và lọc input
  encoder/                    # đếm một OUT hoặc giải mã X4, snapshot hai bên
  pwm/                        # PWM cặp và trình tự đổi chiều
  link/                       # UART, CRC, frame và command guard
  safety/                     # FSM, watchdog và phục hồi ARM
```

## Vai trò từng file

Các module là các khối phần cứng hoạt động đồng thời; bảng dưới không phải
thứ tự chạy như các hàm trong chương trình MCU. `drive_core` nối các khối.

| Nhóm | File | Chức năng dễ hiểu |
| --- | --- | --- |
| Core | [drive_core.sv](drive_core.sv) | Nối reset, encoder, UART, an toàn, PWM và adapter DRV8833; chặn đầu ra khi mất quyền chạy. Chưa gán chân board cụ thể. |
| Top | [aw_car_top.sv](aw_car_top.sv) | Wrapper hai OUT/v2, giữ reverse/40 ms và bốn chân driver của lõi. |
| Encoder | [pulse_encoder_pair.sv](encoder/pulse_encoder_pair.sv) | Snapshot nguyên tử count/period/age/status cho hai OUT; không đo chiều. |
| Common | [reset_sync.sv](common/reset_sync.sv) | Đưa reset vào ngay khi tín hiệu reset xuống LOW; chỉ nhả reset sau hai cạnh clock. Top còn dùng khối này để giữ lại sự kiện mất quyền/health LOW. |
| Common | [input_sync_filter.sv](common/input_sync_filter.sv) | Đưa tín hiệu bên ngoài qua hai tầng thanh ghi, rồi chỉ nhận giá trị mới khi ổn định đủ số mẫu cấu hình. |
| Encoder | [quadrature_decoder.sv](encoder/quadrature_decoder.sv) | Đọc pha A/B theo chuỗi Gray, đếm X4 tăng/giảm theo chiều; báo chuyển trạng thái hai bit bất thường. |
| Encoder | [pulse_counter.sv](encoder/pulse_counter.sv) | Đếm cạnh lên của một OUT đã lọc; bỏ mẫu đầu, đếm không dấu cả khi lùi/thả trôi. Không có thông tin chiều quay thực. |
| Encoder | [encoder_pair.sv](encoder/encoder_pair.sv) | Ghép hai bộ đọc encoder; chốt đồng thời số đếm trái/phải, thời gian, số thứ tự và cờ trạng thái để gửi về Motion. |
| PWM | [pwm_pair.sv](pwm/pwm_pair.sv) | Tạo hai PWM cùng chu kỳ; áp dụng cặp duty mới ở ranh giới chu kỳ để tránh cập nhật lệch trái/phải. |
| PWM | [motor_pwm_pair.sv](pwm/motor_pwm_pair.sv) | Bọc quanh `pwm_pair`; khi đổi chiều thì ngắt PWM, đợi khoảng zero, đổi chiều, đợi ổn định rồi nạp duty. |
| PWM | [drv8833_adapter.sv](pwm/drv8833_adapter.sv) | Đổi PWM/chiều thành hai chân IN mỗi bên theo bảng TI; mất quyền/reset đưa về00 (thả trôi), không thêm bộ tạo PWM. |
| Link | [uart_rx.sv](link/uart_rx.sv) | Nhận bit UART thành byte 8N1; báo stop bit sai hoặc đường RX LOW quá lâu. |
| Link | [uart_tx.sv](link/uart_tx.sv) | Gửi từng byte thành start bit, 8 bit dữ liệu và stop bit; báo sẵn sàng/gửi xong. |
| Link | [crc16_byte.sv](link/crc16_byte.sv) | Tính bước CRC16 cho một byte; được cả bộ nhận và bộ gửi khung dùng để kiểm tra lỗi truyền. |
| Link | [frame_rx.sv](link/frame_rx.sv) | Ghép các byte thành khung lệnh; kiểm tra phiên bản, loại, độ dài, timeout và CRC trước khi báo khung hợp lệ. |
| Link | [frame_tx.sv](link/frame_tx.sv) | Đóng gói snapshot và trạng thái thành khung STATUS v2 47 byte (v1 31 byte); giữ nguyên mẫu đang gửi. Nếu đang bận thì báo bỏ mẫu mới. |
| Link | [command_guard.sv](link/command_guard.sv) | Kiểm tra đúng phiên, số thứ tự mới, miền duty/chiều và quyền nhận lệnh; tạo yêu cầu chạy/arm/dừng/xóa lỗi cho lớp sau. |
| Link | [fpga_link.sv](link/fpga_link.sv) | Ghép UART, CRC, nhận/gửi khung và guard thành một cổng giao tiếp Motion–FPGA; xác nhận STATUS sau khi gửi đủ byte cuối. |
| Safety | [safety_fsm.sv](safety/safety_fsm.sv) | Quản lý chưa arm/bắt tay/chờ arm/đang arm/lỗi/xóa lỗi; chỉ cho chạy đúng trình tự và hết hạn lệnh thì thu quyền chạy. |

Trạng thái: có 19 module, có testbench và script tổng hợp generic; chưa có target
board/driver thực hoặc báo cáo timing sau route. Runner tìm đệ quy toàn bộ
`.sv` trong cây này; script tổng hợp ở `fpga/` dùng đường dẫn nhóm tương ứng.
Testbench vẫn ở [tb](../tb/README.md), ngoài cây nguồn RTL.

## Luồng để đọc code

Luồng nhận lệnh:

```text
Motion → uart_rx → frame_rx → command_guard
                                   ├─ yêu cầu arm/dừng/clear → safety_fsm
                                   └─ duty/chiều + quyền từ safety_fsm
                                                → motor_pwm_pair → pwm_pair
                                                → PWM/chiều → drv8833_adapter → bốn IN
```

Luồng phản hồi:

```text
Encoder OUT → input_sync_filter → pulse_counter → encoder_pair
     (A/B → input_sync_filter → quadrature_decoder, khi chọn mode A/B)
    → snapshot + trạng thái safety_fsm → frame_tx → uart_tx → Motion
```

`fpga_link` bọc phần giao tiếp; `drive_core` nối toàn bộ. PID và đổi số đếm
sang m/s nằm ở Motion. Hai kênh PWM đại diện hai bên của TT 4WD; mỗi motor
vẫn cần cầu H phù hợp, không có bốn vòng điều khiển độc lập trong RTL này.

Thứ tự đọc gợi ý: `drive_core` để biết sơ đồ nối, `pwm_pair` để hiểu cách tạo
PWM, `motor_pwm_pair` để hiểu đổi chiều, rồi `safety_fsm`. Sau đó đọc
`fpga_link` và các khối UART/khung lệnh; cuối cùng đọc nhóm encoder.

## Nhận xét rà soát nhẹ — cập nhật 01/11/2026

- Cách chia thư mục hợp lý, tên file khớp module; đã tách phần truyền byte,
  kiểm tra khung, kiểm tra quyền, an toàn và tạo PWM thành các lớp rõ ràng.
  Giữ cấu trúc hiện tại để triển khai bản chạy đầu, chưa cần thêm tầng kiến trúc.
- Top mặc định dùng một OUT mỗi bên; `pulse_counter` đếm một cạnh lên/xung,
  không đo chiều quay. `ENCODER_SINGLE_OUT=0` giữ giải mã A/B X4 theo chuỗi Gray.
- Top đặt `ALLOW_REVERSE=1`, cho phép lùi và xoay hai bên ngược chiều; guard/link
  dùng riêng vẫn mặc định khóa lùi. Khoảng zero khi đổi chiều không chứng minh
  rotor đã dừng; còn phải thử driver/motor và vùng bảo vệ trên bàn.
- `CLK_HZ` chỉ tự ảnh hưởng bộ chia UART; các tham số PWM, snapshot, watchdog
  và timeout đang tính theo số clock riêng. Khi đổi clock phải rà lại cả nhóm.
- Một số cờ như `receive_error`, `command_rejected`, `snapshot_dropped` và
  `interlock_active` mới nằm trong top, chưa được đưa vào STATUS để debug từ MCU.
  Có thể bổ sung chẩn đoán sau khi đường điều khiển cơ bản chạy ổn.
- Đã có adapter chân DRV8833 drive/coast; chưa có wrapper/pinout/constraints Tang Nano 9K.
  Mô phỏng/tổng hợp generic chưa thay phép đo trên board hoặc báo cáo timing.

## Top `drive_core`

Theo quyết định 28/10/2026, hệ thống dùng TT 4WD: hai đầu ra duty/chiều là
hai nhóm trái/phải, mỗi nhóm hai motor qua adapter DRV8833 đã nối RTL; mạch công suất chưa thử.
Hai encoder đo hai bánh đại diện, chưa giám sát riêng bốn motor. Đây là ánh
xạ tích hợp dự kiến, v2 1 OUT đã có RTL/wire format riêng nhưng chưa chứng minh
4WD đã hoạt động. Xem [kiểm kê](../../hardware/components.md).

Nối reset/CDC, encoder, link, FSM và PWM. Input recovery_req/motion_permit/
safety_ok/gate_fault_n; output recovery_ack/fpga_permit/gate_clear, UART và
encoder/PWM/chiều. Cổng state/fault là diagnostic, board wrapper có thể giữ
nội bộ, không tính là GPIO bắt buộc.

Bốn output `drv_left_in1/in2`, `drv_right_in1/in2` là tín hiệu IN tới driver;
PWM/chiều trung gian vẫn có để debug. STBY/nSLEEP và gate ngoài không do
adapter phát. Xem [bảng nối](../../hardware/drv8833-interface.md).

`encoder_left_out/right_out` nối OUT trái/phải khi `ENCODER_SINGLE_OUT=1`.
Đặt tham số bằng 0 để dùng `left_ab/right_ab`; nối các cổng không dùng về 0
trong wrapper. `INVERT_LEFT/RIGHT` chỉ có tác dụng ở mode A/B. Cờ mode được
đóng gói tại STATUS `encoder_status[4]`, không thêm byte vào frame31.

Capture LOW bất đồng bộ và release hai FF cho health/permit; mask PWM/permit
bằng điều kiện raw. Gate-clear bị chặn raw khi reset, live fault, Motion permit
hoặc recovery_req HIGH. Một clock domain không loại bỏ yêu cầu rà CDC/reset.
Thuộc tính ASYNC_REG vẫn phải đối chiếu mapping/constraints theo target.

Mặc định 27 MHz, FILTER_N=3, count/timestamp32, sequence16, snapshot270.000
tick (10 ms), PWM1.350 tick (20 kHz). Watchdog1.350.000, handshake6.750.000,
clear135.000 và hold2.700 tick. Chỉ thay CLK_HZ không tự đổi các timer này.

Reset ngoài phải assert khi khởi động; chưa có POR/pin/clock constraints theo
board hoặc adapter driver. Gate ngoài và Motion stale inhibit là bắt buộc;
RTL mask không bảo vệ lúc chưa cấu hình hay thay mạch E-stop độc lập.
Xem [hợp đồng an toàn](../../firmware/shared/fpga-safety.md),
[wire v1](../../firmware/shared/fpga-protocol.md),
[wire v2](../../firmware/shared/fpga-protocol-v2.md) và
[bằng chứng kiểm thử](../verification.md).
