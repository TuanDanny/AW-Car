# Bằng chứng kiểm thử RTL

## Encoder/snapshot — 23/10/2026

Đã chạy trên Windows với Icarus Verilog/VVP **13.0 stable (v13_0)**, package
MSYS2 UCRT64 `iverilog 1~13.0-2`. Tool/binary ở `build/toolchain/`, không commit.
Máy khác có thể dùng Icarus trong PATH; CI chạy package Ubuntu 24.04 và in version.

```powershell
$env:PATH = (Join-Path (Get-Location) 'build/toolchain/ucrt64/bin') + ';' + $env:PATH
python tools/run_fpga_tests.py
```

| Testbench | Kết quả | Bằng chứng |
| --- | --- | --- |
| tb_encoder_units | PASS | Reset assert/nhả, lọc N=1/3, ngưỡng N-1/N/N+1, 16 chuyển A/B, inversion và count4 wrap |
| tb_encoder_pair | PASS | 10 seed x 10.000 chuyển mỗi bánh; glitch, invalid sticky; snapshot trước cạnh đếm và timer/sequence/timestamp wrap |
| tb_encoder_timing | PASS | Tham số mặc định, 810.000 clock = 3 snapshot10ms, pha khởi động khác zero không tạo count |

Lệnh trả mã 0; compile không có warning. Thêm 3 test runner và 8 test cấu
trúc repo đều đạt. Không có phép đo trên FPGA hoặc xe; chưa có báo cáo tổng
hợp/PnR/timing, chưa chứng minh toàn lõi chứa được trên Nano 1K.

Nguồn phân phối công cụ: [MSYS2 Icarus](https://packages.msys2.org/package/mingw-w64-ucrt-x86_64-iverilog).
Toolchain cục bộ không thay đổi PATH hệ thống hoặc yêu cầu tắt phần mềm bảo vệ.

## PWM/chiều và tổng hợp sơ bộ — 23/10/2026

Cùng Icarus/VVP13.0, ba testbench PWM trả mã0, compile không warning:

| Testbench | Kết quả | Bằng chứng |
| --- | --- | --- |
| tb_pwm_pair | PASS | 10 seed x 1.000 cặp duty, đo số tick HIGH/cạnh và boundary; 0/1/giữa/P-1/P, ngoài miền, latest shadow và disable |
| tb_motor_pwm_pair | PASS | Zero/setup, lệnh mới thay cặp đang chờ, lệnh lỗi, reset/disable từng phase, mask/reset cả khi clock đứng |
| tb_pwm_timing | PASS | Clock27MHz: period1350, HIGH675/1350; zero27000, setup27; tham số nhỏ nhất1/1/1 |

Đã chạy lại regression encoder sau khi thêm PWM: cả sáu testbench PASS.
12 test Python và kiểm tra cấu trúc/diff đạt. Runner cũng được kiểm tra bằng
đường dẫn tool tương đối khi PATH chưa có Icarus; môi trường DLL chỉ truyền
cho subprocess, không sửa PATH hệ thống. Lõi PWM chưa có watchdog/arm;
enable phải đến từ FSM an toàn, không phải một chân MCU raw hoặc E-stop raw.

Tổng hợp sơ bộ bằng **YoWASP-Yosys0.70.0.0.post1259**, Yosys0.70,
git `28ba3cb92`. Các script được commit cùng RTL:

```powershell
build/toolchain/yowasp/Scripts/yowasp-yosys.exe -l fpga/build/encoder-synth.log -s fpga/synth_encoder.ys
build/toolchain/yowasp/Scripts/yowasp-yosys.exe -l fpga/build/pwm-synth.log -s fpga/synth_pwm.ys
```

Mapping generic Gowin/gw1n, `-noiopads -nowidelut`, tham số mặc định của từng
module. `proc` không suy ra latch; `check -assert` báo0 vấn đề ở cả hai khối.
Toolchain, log, netlist và stat JSON nằm trong build đã ignore; nguồn tương
ứng là revision chứa báo cáo này, có thể tái tạo bằng các script trên.

| Khối độc lập | FF primitive | LUT1–4 cell | ALU cell |
| --- | --- | --- | --- |
| encoder_pair | 266 | 108 | 195 |
| motor_pwm_pair | 134 | 303 | 118 |

Đây là **cell count từ Yosys**, chưa là utilization vật lý của Nano1K. ALU và
LUT dùng tài nguyên theo cách pack của chip; không cộng các cột để suy ra số
LUT4 thực. Cũng chưa gồm UART/CRC/parser/FSM/watchdog, reset/target và giao tiếp
giữa các khối. Không coi tổng FF của hai bài độc lập là kết quả fit toàn lõi.
Chưa chạy Gowin, PnR hoặc STA đúng GW1NZ-LV1QN48C6/I5; chưa chọn/mua board.

## Chuyển toàn bộ HDL sang SystemVerilog — 23/10/2026

Đã chuyển cả sáu khối RTL sang `.sv`, dùng `logic`, `always_ff`, `$clog2` có
giới hạn tối thiểu một bit và enum cho FSM đổi chiều. Sáu testbench cũng dùng
`.sv`/`logic`. Runner dùng `-g2012`, hai script Yosys dùng `read_verilog -sv`.
`AGENTS.md` yêu cầu `.sv`; checker được hook/CI gọi chặn đuôi HDL khác, gồm
file untracked và snapshot đã stage, bỏ qua build đã ignore.

Trên cùng Icarus13.0/Yosys0.70 đã nêu ở trên:

- Cả sáu testbench encoder/PWM PASS, biên dịch không warning.
- 15 test Python PASS; có ca từ chối đuôi HDL sai, đổi tên chưa stage và kiểm
  tra runner đưa đủ nguồn `.sv` vào compiler ở chế độ SystemVerilog.
- Tổng hợp hai khối không latch/lỗi cấu trúc. Cell count giữ nguyên bảng trên.
- So sánh tương đương cả sáu module với bản Verilog ở `f9471b3`, tham số mặc
  định: `equiv_status -assert` PASS. Hai phía cùng qua `prep -flatten`,
  `async2sync`, `opt`, rồi `equiv_make`, `equiv_simple`, `equiv_induct -seq 4`.
  Đây là kiểm tra logic sau chuẩn hóa reset; reset bất đồng bộ vẫn được thử
  riêng bằng mô phỏng, không phải bằng chứng metastability/điện áp phần cứng.

Log kiểm tra cục bộ nằm trong `fpga/build/`, không commit. Chưa có kết quả
Gowin/PnR/timing hoặc chạy trên board. Kết quả UART ở mục dưới;
FSM an toàn/watchdog vẫn ở giai đoạn tiếp theo.

## UART/giao thức và command guard — 23/10/2026

Đã có bảy module SystemVerilog mới: uart_rx/tx, crc16_byte, frame_rx/tx,
command_guard, fpga_link. Wire format/CRC/vector chung nằm trong
[protocol v1](../firmware/shared/fpga-protocol.md); STATUS31 byte giữ cả status
encoder. Reference Python dùng `binascii.crc_hqx`, không gọi hàm CRC RTL.

| Testbench mới | Kết quả | Bằng chứng |
| --- | --- | --- |
| tb_uart | PASS | 256 giá trị byte x3 baud danh định/+2%/-2%, pha lệch và back-to-back; false start, stop sai, break một lần, reset giữa byte, TX busy/stop |
| tb_frame_rx | PASS | CRC29B1, 6 vector control và STATUS sai hướng; mutation mọi byte từ version đến CRC; resync/overlap; timeout trước/tại hạn; reset/flush18 vị trí CMD; 10 seed x1.000 trường hợp hỗn hợp |
| tb_frame_tx | PASS | Vector STATUS31 byte; đổi mọi nguồn snapshot lúc stalled; giữ byte/CRC qua backpressure; báo drop; reset/flush31 vị trí và frame phục hồi |
| tb_command_guard | PASS | HELLO không cấp quyền, session/sequence gap/wrap/duplicate/old/32767/32768, reserved/duty/chiều sai, ALLOW_REVERSE0/1, reset và context_load ưu tiên |
| tb_fpga_link | PASS | Tham số27MHz/115200, full-duplex CMD/STATUS, snapshot bất biến, CRC lỗi/duplicate không commit; timeout mặc định2ms/5ms rồi phục hồi |

Đã chạy toàn bộ 11 testbench bằng Icarus/VVP13.0 và 19 test Python; compile
không warning, test/mã thoát đều PASS. Check cấu trúc/đuôi `.sv`, diff và
vector chung đạt. Test link thật dài khoảng21,7ms mô phỏng; chưa phải regression
toàn xe2s hoặc bài watchdog50ms ở kế hoạch safety.

`synth_link.ys` dùng cùng Yosys0.70/generic Gowin như hai bài trước:
`proc` không latch, `check -assert` không lỗi. Riêng `fpga_link` có **544 FF
primitive, 847 LUT1–4 cell và 282 ALU cell**. Không có buffer RX/TX32 byte;
TX giữ một snapshot và RX giữ header/payload nhỏ. Đây chưa phải utilization
vật lý hoặc tổng hợp toàn lõi; không cộng LUT/ALU để kết luận fit. Ngân sách
Nano1K (864 FF) rất hẹp khi còn encoder/PWM và safety; cần đo lại sau tích hợp
và cân nhắc tối ưu/chip khác, chưa xác nhận board1K phù hợp.

Lệnh tái tạo: runner ở README và
`yosys -s fpga/synth_link.ys`; bản Windows dùng
`build/toolchain/yowasp/Scripts/yowasp-yosys.exe -s fpga/synth_link.ys`.
Log/netlist/stat JSON nằm trong build đã ignore. CI chạy cả11 mô phỏng và
ba script tổng hợp.

Link không có PWM/permit và chưa nối PWM hiện có. Quyền phiên/sequence_base/
command_enable do mô hình controller trong test cấp, không đến từ HELLO.
Handshake chống buffer cũ, ARM thực tế, watchdog/FSM và gate độc lập vẫn cần
thiết kế/kiểm thử ở f10. Chưa có firmware Motion, target, PnR/STA hoặc phép đo
đường truyền/motor trên board.

## FSM an toàn và top truyền động — 23/10/2026

Nhánh `feat/f10-fpga-safety`, nền `e3bfb7f`. Thêm `safety_fsm`/`drive_core`,
giữ toàn bộ HDL `.sv`. UART/encoder/PWM đã nối thành top logic; chưa có
wrapper board, adapter driver hoặc firmware Motion. [Hợp đồng safety](../firmware/shared/fpga-safety.md)
chốt GPIO recovery/ACK, STATUS ARM_PENDING, fault và clear gate bên ngoài.

Cùng Icarus/VVP13.0 và YoWASP-Yosys0.70 nêu ở trên. Lệnh tái tạo toàn bộ
hồi quy với bài tích hợp dài ở clock danh định:

```powershell
python tools/run_fpga_tests.py --iverilog build/toolchain/ucrt64/bin/iverilog.exe --vvp build/toolchain/ucrt64/bin/vvp.exe --full-timing --timeout 1800
build/toolchain/yowasp/Scripts/yowasp-yosys.exe -Q -q -l fpga/build/drive-synth.log -s fpga/synth_drive.ys
```

| Testbench | Kết quả | Bằng chứng |
| --- | --- | --- |
| tb_safety_fsm | PASS | Baseline GPIO LOW/stale HIGH, ACK và session; STATUS sai phiên/state, permit quá sớm; CMD trước/tại deadline; traffic khác không gia hạn; mất permit, reconnect, DISABLE, lỗi ngoài/PWM, clear/timeout và reset các pha |
| tb_safety_timing | PASS | Tham số mặc định27MHz: ARM ở zero tại49ms, FAULT đúng tick1.350.000 ở50ms dù có CMD, không phục hồi tại51ms |
| tb_frame_tx | PASS | Giữ toàn vector STATUS cũ và kiểm tra byte_last/session/state đóng băng qua backpressure |
| tb_drive_core --full-timing | PASS | 2.010,444ms tại27MHz/115200/20kHz/50ms; 189 STATUS đúng snapshot; UART/PWM/encoder, reset, E-stop, clock-stop/stale gate |
| tb_drive_defaults | PASS | 225,343ms,11 STATUS; cùng chuỗi lỗi, cả hai duty đúng và encoder thuận/ngược qua STATUS, toàn tham số danh định |

Toàn bộ **15 testbench PASS**, compile không warning; **20 test Python PASS**,
vector chung/kiểm tra repo/nhánh/diff đạt. Bốn script synthesis encoder/PWM/
link/drive đều đạt; chưa phải nghiệm thu phần cứng.

Bài top dùng host UART/CRC/observer riêng; đối chiếu cả payload/session từ
snapshot được chấp nhận, xác nhận metadata completion sau CRC stop bit. Thử
duplicate, sai phiên/CRC/duty, xung E-stop10ns, reset với permit HIGH, mất
clock khi PWM HIGH. Mô hình Motion dùng đồng hồ riêng, không gia hạn bằng
metadata snapshot lặp/cũ, kiểm tra hạ permit trong30+1ms. Gate ngoài ưu tiên
SET, giữ lỗi sau nhả E-stop/nguồn; clock trở lại không cấp lại duty cache.
Đây là model hợp đồng, chưa phải kiểm thử firmware hay sơ đồ điện.

Runner mặc định dùng clock2,7MHz cho bài2s và scale đồng thời timer/PWM,
giữ baud115200; chế độ `--full-timing` đổi bài này sang27MHz. CI bật full-timing.
Không dùng mô phỏng logic để kết luận timing điện hay timing sau route.

Tổng hợp **toàn top `drive_core`**, mặc định27MHz, bằng `synth_drive.ys`:
`proc` không latch, `check -assert` không lỗi. Mapping generic Gowin/gw1n,
`-noiopads -nowidelut`, không phải netlist đúng mã chip9K:

| Khối | FF primitive | LUT1–4 cell | ALU cell |
| --- | --- | --- | --- |
| drive_core, toàn lõi | **1.122** | **1.608** | **662** |
| fpga_link, có completion metadata mới | 587 | 838 | 282 |

Không cộng cell các bài độc lập để thay kết quả top, không cộng LUT/ALU để
báo utilization vật lý. Top xuất43 bit cổng logic, gồm24 bit diagnostic
state/fault có thể giữ nội bộ ở wrapper; giao diện chức năng còn19 bit,
gồm cả clock/reset. Số pin board còn dùng được và điện áp bank chưa kiểm tra.

Mapping hiện tại vượt864FF của Nano1K. Người dùng đồng ý đánh giá **Nano9K**
thay vì cắt CRC/watchdog/độ rộng encoder. Sipeed ghi9K dùng
GW1NR-LV9QN88PC6/I5,8.640LUT4/6.480FF,27MHz; [nguồn chính thức](https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K.html)
đối chiếu23/10/2026. Chưa chốt mua: cần constraints/CDC/reset, Gowin/PnR/STA
đúng chip, pinout/nguồn/giá. Còn driver/gate, Motion/Brain lease/PID/cảm biến,
servo và thử quãng dừng trên xe; FSM/top mô phỏng không thay các bước này.
