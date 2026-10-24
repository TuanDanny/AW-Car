# RTL độc lập hãng

Lõi SystemVerilog (`.sv`), một clock domain, không tạo clock bằng logic.
RTL dùng `logic`, `always_ff` cho thanh ghi, `assign` cho tổ hợp đơn giản và
enum cho FSM. Không dùng khởi tạo biến thay phép gán liên tục.
Top tích hợp đặt ngay root; module con phân theo chức năng:

```text
rtl/
  README.md
  drive_core.sv               # top logic toàn lõi
  common/                     # reset, đồng bộ và lọc input
  encoder/                    # giải mã X4 và snapshot hai bánh
  pwm/                        # PWM cặp và trình tự đổi chiều
  link/                       # UART, CRC, frame và command guard
  safety/                     # FSM, watchdog và phục hồi ARM
```

| Nhóm | Module | Tài liệu |
| --- | --- | --- |
| Top | [drive_core](drive_core.sv) | Tích hợp các nhóm dưới |
| Common | reset_sync, input_sync_filter | [common](common/README.md) |
| Encoder | quadrature_decoder, encoder_pair | [encoder](encoder/README.md) |
| PWM | pwm_pair, motor_pwm_pair | [pwm](pwm/README.md) |
| Link | crc16_byte, uart_rx/tx, frame_rx/tx, command_guard, fpga_link | [link](link/README.md) |
| Safety | safety_fsm | [safety](safety/README.md) |

Trạng thái: đủ 15 module, đã có testbench và tổng hợp generic; chưa có target
board/driver thực hoặc báo cáo timing sau route. Runner tìm đệ quy toàn bộ
`.sv` trong cây này; script tổng hợp ở `fpga/` dùng đường dẫn nhóm tương ứng.
Testbench vẫn ở [tb](../tb/README.md), ngoài cây nguồn RTL.

## Top `drive_core`

Nối reset/CDC, encoder, link, FSM và PWM. Input recovery_req/motion_permit/
safety_ok/gate_fault_n; output recovery_ack/fpga_permit/gate_clear, UART và
encoder/PWM/chiều. Cổng state/fault là diagnostic, board wrapper có thể giữ
nội bộ, không tính là GPIO bắt buộc.

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
[wire protocol](../../firmware/shared/fpga-protocol.md) và
[bằng chứng kiểm thử](../verification.md).
