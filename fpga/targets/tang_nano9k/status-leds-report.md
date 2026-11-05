# LED trạng thái Nano9K — kết quả 05/11/2026

Implementation `30d45ed`, nhánh `feat/f01-tang-nano9k-target`. LED chỉ quan sát
state/fault;19 file điều khiển Safety/UART/PWM và drive_core khớp hash nguồn
trước LED. Không có tín hiệu LED đi ngược vào ARM/PWM/watchdog/gate.

| Điều kiện | Hiển thị |
| --- | --- |
| Safety fault, diagnostic0x8800, FAULT/CLEAR_WAIT hoặc state không hợp lệ | Cả6 sáng |
| HANDSHAKE / ARM_PENDING / ARMED, không fault | LED1 sáng liên tục |
| DISARMED, không fault | LED1 sáng500ms / tắt500ms |
| Reset/POR | Cả6 tắt |

FAULT ưu tiên CONNECTED, CONNECTED ưu tiên WAITING. CONNECTED là trạng thái
phiên giao thức, chưa đồng nghĩa cho phép motor. Warning RX/encoder còn lại
không bị đổi thành lỗi nghiêm trọng. Cờ0x88ff gom Safety và hai diagnostic fatal.

Sáu output active-low ở package10/11/13/14/15/16, bank3/LVCMOS18=1,8V,
pull-up, drive4mA. LED1 là leds_n[0]/package10 theo thứ tự firmware. Giữ nguyên
17 tín hiệu chức năng, tổng23 tín hiệu vật lý. Chỉ có clock27MHz; counter24bit
và bit pha, không tạo clock phụ, không thêm FSM hoặc polling MCU.

## Bằng chứng kiểm thử và tài nguyên

- Python57/57 PASS;5 bài RTL chọn lọc PASS,21/21 module được elaborate trong
  bài đạt. Không gọi đây là coverage dòng/nhánh/toggle hoặc tuyên bố chạy lại36/36.
- Miter cùng đầu vào ở27MHz:79.414 chu kỳ so Safety/UART/PWM/permit/ACK/clear
  khớp với drive_core không observer;22.552 chu kỳ có PWM. Có CRC sai, đảo
  chiều, STOP, watchdog và dừng bất đồng bộ. Baud/timer rút ngắn tường minh.
- Unit LED: ba divider HALF1/7/16;256 state x16 bit fault, active-low,
  ưu tiên, cảnh báo, reset và clock-stop.
- Hai test netlist sau route PASS: CRC/session/encoder/POR/default-off và
  LED waiting/connected, all6 FAULT, reset OFF. Không annotate SDF.
- Gowin synth/PnR/STA PASS27MHz: Fmax44,816MHz; worst setup+12,771ns,
  hold+0,358ns; recovery+28,179ns/removal+1,831ns; TNS0, violation0.
- LUT4=1657, ALU311, logic FF1593 +I/O FF4, BRAM0, latch0,23I/O.
  So bản trước: thêm đúng25FF. Chênh LUT/Fmax phụ thuộc mapping và routing;
  không quy toàn bộ chênh lệch đó thành hiệu quả thuật toán LED.
- 9 constraints active; bốn first-sampler exceptions giữ nguyên. Unconstrained
  total vẫn null vì tool không xuất; CDC/giao tiếp ngoài chip còn mở.

## Nạp và quan sát board thật

Đã SRAM Program bằng CLI trên USB Debugger A/0/529, GW1NR-9C ID0x1100481B,
CRC cấu hình ON, SecurityBit ON, không ghi flash. Đọc lại UserCode0x00009EF7
khớp bitstream và status0x0003F020. Người dùng xác nhận cả6 LED sáng liên tục.
Không giả định healthHIGH; board chưa có gate, các health input LOW được xem
là lỗi an toàn theo FSM. Mã fault cụ thể chưa được đọc qua UART.

Waiting/connected chưa quan sát độc lập trên board thật; đã kiểm trong unit,
miter và netlist. Khi chưa cấu hình hoặc mất nguồn, LED không thể báo trạng
thái. Mất clock có thể làm đứng hình. Không dùng LED thay E-stop/mạch gate.
UART header, encoder, công suất và mạch gate/E-stop vẫn chưa nghiệm thu.

## Gate là phần cứng gì?

Gate là mạch khóa driver rời đang chờ thiết kế, chưa có SKU/board mua sẵn được
chốt. Nó nhận driver_permit riêng của Motion, fpga_permit, safety_ok và chốt
lỗi gate_fault_n; chỉ cho phép khi đủ điều kiện. Chốt ưu tiên SET khi E-stop/
nguồn lỗi, default-off khi FPGA chưa cấu hình/mất nguồn và chỉ clear chủ động.
Mạch tác động tới chân cho phép nSLEEP/STBY của hai module sau kiểm tra đúng IC.
[Datasheet TI DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf) mô tả
nSLEEP LOW đưa driver vào sleep. RTL và LED không thay mạch ngoài này.
Không thêm giả lập gate trong bản chạy thật hoặc đổi Motion LOCKED để demo.

[JSON nguồn, hash, kết quả và lệnh nạp](../../../docs/fpga-status-led-evidence.json).
Workspace thực tế: `D:/Project/AW-Car/fpga/IDE-fpga/awcar_project`.
Bản trước LED và log gốc đã sao lưu tại worktree target,
`build/tang-nano9k/workspace-before-led`; không sửa snapshot timing17a0ccb cũ.
