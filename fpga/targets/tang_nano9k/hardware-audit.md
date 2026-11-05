# FPGA hardware audit — Giai đoạn2

Ngày05/11/2026, nhánh `feat/f01-tang-nano9k-target`, worktree riêng từ FPGA
`7ab91b2d6119af211453a1273e3dae978d8af286`. Remote/main mới nhất khi bắt đầu là
`4cea85c9f34a26a2e8e2af793575a82cbcf11132`, tag `v0.1-brain-motion-locked`.
Không dùng trạng thái integration a27a098 như thay thế cho main hiện tại.

## Bằng chứng và phạm vi

Người dùng đã nạp LED SRAM trên GW1NR-9C/id0x1100481B, Programmer Finished
~2,96s và quan sát sáu LED chuyển mỗi0,5s. Đã xác minh đủ bốn source/constraints/
bitstream trong project thực hành `D:/Project/AW-Car/fpga/led_just_test/led_test`.
Không sửa, chép vào Git hoặc dùng timing bài LED cho AW-Car.

Board hiện chỉ dùng USB, chưa có gate/chốt lỗi/E-stop độc lập. AW-Car chưa nạp
Nano9K, chưa kết nối VM. Không mở COM, reset ESP32, erase NVS hoặc thay Motion
LOCKED. Worktree FPGA/CAD gốc được chụp status và hash trước khi làm việc.

## RTL được kế thừa

Giữ logical top `aw_car_top`, lõi `drive_core`, UART/parser/guard/CRC, Safety FSM,
diagnostics, encoder một OUT và PWM/DRV8833 adapter. Các timer, duty, chiều,
watchdog và wire format không đổi. Một OUT đếm cạnh lên không dấu; không suy
chiều vật lý từ lệnh. Protocolv2 có STATUS34/frame47, CRC16, period/age.

| Hạng mục | Giá trị giữ nguyên |
| --- | --- |
| Clock / UART | 27MHz / 1152008N1 |
| PWM / snapshot | 1350tick=20kHz /270000tick=100Hz |
| Watchdog CMD | 1350000tick=50ms |
| GPIO/HELLO recovery window | 6750000tick=250ms |
| WAIT_ZERO / setup | 1080000tick=40ms /27tick=1us |
| CLEAR wait / hold | 135000tick=5ms /2700tick=100us |
| Encoder stale warning | 500ms; không tự coi là fatal |
| Diagnostic reset mask | 0x8800; Safety mask0x00ff; warning còn lại không tự khóa |

Các sửa đổi cần thiết có bằng chứng:

1. Khai báo **cổng module** `input wire logic` thay `input logic`: Gowin yêu
   cầu net type tường minh khi dùng default_nettype none. Function/task vẫn dùng
   tham số logic. Đây không phải thay đổi thuật toán hay giao thức.
2. Gowin1.9.11.03 tối ưu mất payload cone với indexed part-select động trong
   nhánh default của frame_tx.select_byte. Netlist ban đầu không có IBUF cho
   left_out/right_out. Thay đúng phép chọn payload bằng full-width shift và
   fixed slice8bit, giữ mọi byte/CRC. Bản chẩn đoán trước sửa FAIL count0/0;
   netlist sửa PASS count3/5, period32, age, hai frame STATUS/CRC. Đây là lý do
   không chỉ dựa vào build exit0/Fmax hoặc regression RTL.
3. Physical shell `aw_car_nano9k` thêm POR1024clock (~37,93us), FF init0 và
   mask reset ở boundary. Logical core đã đồng bộ nhả reset hai FF. Không thêm
   clock mới, quyền ARM hoặc lệnh motor. Netlist Gowin có INIT0 cho10 FF counter
   và por_ready; kiểm thử mapped bắt đầu resetHIGH để thử cấu hình/POR.

## Clock, reset, CDC và timing

Một miền clock27MHz; không PLL/generated fabric clock. RX, encoder và req là
bất đồng bộ, vào meta_ff rồi sync_ff và filter. Safety/gate/permit assert LOW
bất đồng bộ và nhả qua reset_sync. Raw shutdown vẫn mask trực tiếp ra permit/IN.
POR dùng clock; khi clock đứng, POR/RTL không thể tự chứng minh gate đã tắt.
External default-off gate và E-stop độc lập vẫn bắt buộc.

SDC không dựng quan hệ clock giả giữa ESP32/encoder và FPGA. Ngân sách propagation
cho I/O là một chu kỳ37,037ns, clock guardband0,2ns setup/hold là **giả định kỹ
thuật, không phải jitter đo được**. Lượt thăm dò10ns raw-mask và15ns output
không đạt (raw-mask ~19,685ns); đây là ngân sách thăm dò, không yêu cầu vật lý
đã nghiệm thu. Target chốt ngân sách một chu kỳ27MHz, không thay timer an toàn.

Chỉ bốn D pin của **first sampler** được false-path, tên exact được đối chiếu
netlist: RX, recovery_req, left_out, right_out. Không cắt stage1→stage2, raw-mask,
reset distribution hay toàn bộ I/O. Các đường recovery/removal còn được báo.
Attributes ASYNC_REG thể hiện ý định; không phải báo cáo MTBF hoặc bằng chứng
metastability đã được giải quyết trên board.

Gowin automatic text report không xuất tổng số unconstrained paths. Script ghi
`null`, không bịa thành0. Kiểm kê đủ17 cổng,9 SDC constraints Actived và4 sampler
exceptions; sign-off CDC đầy đủ/độ trễ ngoài chip và measurement vẫn còn mở.
STA PASS trong báo cáo chỉ áp dụng các ràng buộc đã nêu, không phải an toàn xe.

## Review warnings

- EX3791 ở pwm_pair.sv:37: biểu thức next_phase rộng hơn đích. Trong nhánh
  tăng phase, phase<PERIOD_CYCLES-1; với period1350, giá trị tối đa1349 vừa11bit.
  Nhánh boundary gán0. Giữ RTL và hồi quy period16/1350/2048/65535; không xóa
  warning bằng cách nới duty hoặc bỏ range check.
- NL0002: module con inlining/sweep được kiểm tra bằng netlist. Sau sửa serializer,
  cả hai pad encoder, sampler và cone counter đều còn; mapped test bắt buộc.
  Không dùng NL0002 đơn lẻ làm bằng chứng vô hại.
- Script chặn warning mới, pin/standard drift, thiếu sampler/POR INIT, latch,
  constraint không active, timing âm hoặc mất pad. Không sửa allowlist để xanh CI
  khi chưa review nguyên nhân.

## Risk register

| ID | Rủi ro / tình trạng | Điều kiện đóng |
| --- | --- | --- |
| R1 | Gate/E-stop/chốt lỗi chưa có — chặn thử công suất | Thiết kế SET-dominant, default-off không cần MCU/clock; đo mất nguồn/clock |
| R2 | Board revision/điện áp/header chưa đo | Kiểm silk, continuity và bank3/1/2 đúng điện áp trước đấu |
| R3 | Encoder OUT có thể5V | Conditioner đúng mức/hướng, đo HIGH/LOW, tắt nguồn và xung thực |
| R4 | POR/GSR mới kiểm mapped | Đo power-up, SRAM reprogram, nút reset, USB sụt áp; tất cả output khóa |
| R5 | CDC/MTBF/reset async chưa sign-off vật lý đầy đủ | Review placement/synchronizer, đo glitch; không dùng STA thay E-stop |
| R6 | GPIO khi chưa cấu hình/mất nguồn có thể floating/backfeed | Điện trở/gate/level translator có trạng thái mất nguồn được kiểm chứng |
| R7 | Pin shared LCD dù board đang trống | Giữ LCD tháo rời hoặc tạo target pinout khác đã audit |
| R8 | Main còn baseline RTL cũ | Tích hợp sau bằng PR riêng; v2 peer tường minh, không fallback v1 |
| R9 | Công cụ có thể build thành công nhưng đổi chức năng | Mapped test encoder/CRC và checker pad/cone/POR chạy lại mỗi build |
| R10 | Chưa đo drive, stall, rotor coast40ms hoặc dòng nguồn | Giữ Motion LOCKED; nghiệm thu không motor rồi kế hoạch công suất riêng |

## Integration readiness

Contract shared cập nhật từ main4cea85c, chỉ đồng bộ tài liệu cần thiết. GPIO4
motion_permit là logic vào FPGA; GPIO10 driver_permit là đường gate riêng. Đọc
`FpgaLink::Fresh` của Motion: mẫu mới khi age<30000us; mốc30ms phải khóa driver.
ResetRequired mask0x8800, Safety0x00ff; warning/encoder-no-edge không tự thành
fatal. Version/length/CRC/session/sequence và snapshot freshness vẫn kiểm độc lập.

Co-sim dùng production Motion từ worktree peer main4cea85c riêng trong build
ignored, ghép RTL v2 của nhánh này; không dùng RTL v1 của main. Kịch bản gồm
boot/v2 CRC, GPIO ARM_PENDING/wake, duty/PWM vi sai, hai permit khi STOP,
Motion tự cắt khi clock FPGA đứng, fault/CLEAR không tự ARM. Sáu hướng/đổi
chiều và boundary CRC/session/deadline còn được kiểm riêng trong bộ RTL34bench
và host Motion. Số liệu/hash nguồn lưu trong báo cáo test; đây là mô hình gate,
không phải phép đo gate hoặc motor thật.

Kết quả chi tiết: [timing](timing-report.md), [pinout](pinout.md),
[trình tự bring-up](bringup-checklist.md). Mốc phần mềm/timing chưa cho phép
thử driver. **HARDWARE NOT VERIFIED cho bitstream AW-Car.**
