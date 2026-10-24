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

## Phân nhóm thư mục RTL — 24/10/2026

Nhánh `chore/rtl-layout`, nền `6848dbd`. Giữ `drive_core.sv` ở root `rtl/`;
14 module con chuyển vào common/encoder/pwm/link/safety, mỗi nhóm có README.
Git nhận đủ14 rename100%; toàn bộ15 nguồn RTL giữ nguyên nội dung. Runner
tìm `.sv` đệ quy; bốn script Yosys dùng đường dẫn mới, giữ thứ tự nguồn của
top để mapping generic tái tạo được. Quy ước bố trí đã ghi vào AGENTS.md.

Đã chạy Icarus/VVP13.0 với danh sách nguồn mới: **15 testbench PASS**, compile
không warning. Chế độ mặc định: bài top dài **2.001,560ms tại2,7MHz**,188 STATUS;
bài lỗi danh định **225,343ms tại27MHz**,11 STATUS. Không chạy lại bài top2s
ở27MHz cục bộ trong lần phân nhóm này; kết quả full-timing trước đó ở mục trên.

```powershell
python tools/run_fpga_tests.py --iverilog build/toolchain/ucrt64/bin/iverilog.exe --vvp build/toolchain/ucrt64/bin/vvp.exe --timeout 1800
```

YoWASP-Yosys0.70 chạy đủ synth_encoder/pwm/link/drive với nguồn mới: không
latch, `check -assert` đạt, không warning. Cell count từng khối khớp bản trước;
toàn top vẫn **1.122FF,1.608 LUT1–4,662ALU**. Log `layout-*-synth.log` và
netlist/stat nằm trong `fpga/build/` đã ignore. Chưa có PnR/STA đúng chip.

**20 test Python PASS**, gồm hồi quy nguồn root/lồng hai cấp và helper ngoài
RTL; kiểm tra repo/nhánh, đường dẫn nguồn và `git diff --check` đạt. Thay đổi
sơ đồ draw.io đang có được giữ riêng, không thuộc lần phân nhóm này.

## Tối ưu duty và timer, giữ mục tiêu Nano 9K — 24/10/2026

Nhánh `feat/f11-fpga-optimize`, baseline `821cfae`. Không đổi cổng/giao thức,
clock27MHz, độ rộng encoder/timestamp32, CRC/session/sequence hoặc thứ tự
ARM/fault/clear. Target vẫn là **Tang Nano 9K / GW1NR-LV9QN88PC6/I5**, chưa mua.

- Thanh ghi duty trong guard/PWM/motor PWM dùng11bit cho miền0..1350,
  thay vì16bit. Vẫn kiểm tra đủ lệnh16bit trước khi thu hẹp, zero-extend khi
  xuất; dùng clog2(period+1) để biểu diễn cả duty100% khi period là lũy thừa2.
- FSM dùng chung một timer23bit cho các pha recovery/handshake, watchdog và
  clear. Hold clear dùng ngưỡng trên timer đó, thay tổng74bit timer trước.
  Không chia clock/tick, mỗi pha nạp deadline riêng; timeout vẫn ưu tiên.
- Giữ snapshot riêng ở encoder và serializer để không thay hợp đồng đóng
  băng dữ liệu/backpressure. Không bỏ CRC, chống lệnh cũ hoặc đường an toàn.

Cùng Yosys0.70 và bốn script generic Gowin/gw1n như baseline:

| Top | FF trước → sau | LUT1–4 trước → sau | ALU trước → sau |
| --- | --- | --- | --- |
| encoder_pair | 266 → 266 | 108 → 108 | 195 → 195 |
| motor_pwm_pair | 134 → 104 | 303 → 237 | 118 → 108 |
| fpga_link | 587 → 577 | 838 → 820 | 282 → 282 |
| drive_core, toàn lõi | **1.122 → 1.031** | **1.608 → 1.497** | **662 → 604** |

Toàn top giảm91FF (8,1%),111LUT cell (6,9%),58ALU cell (8,8%). Không cộng
các top riêng hoặc cộng LUT/ALU để suy ra utilization vật lý. Bốn synthesis
không warning/latch, `check -assert` đạt; log `fpga/build/opt-*-synth.log`
và `opt-drive-step1.log` đã ignore. Chưa có PnR/STA/fit đúng chip9K.

Icarus/VVP13.0:toàn bộ16 testbench PASS, compile không warning, gồm bài
mới `tb_pwm_widths` với period16/1350/2048/65535, duty0/1/100%, lệnh sai có
bit cao và disable. Bài mới cũng PASS trên baseline: đây là kiểm tra giữ
hành vi khi thu hẹp, không phải bằng chứng sửa một lỗi của bản cũ.
Hai bài top cũng PASS: bài dài **2.010,544ms tại27MHz,189 STATUS**; bài lỗi
danh định **225,343ms,11 STATUS**. Kiểm tra UART/PWM/encoder, reset, E-stop,
clock-stop/stale gate đạt; CI tiếp tục chạy full-timing trước merge. Lệnh tái tạo:

```powershell
python tools/run_fpga_tests.py --iverilog build/toolchain/ucrt64/bin/iverilog.exe --vvp build/toolchain/ucrt64/bin/vvp.exe --full-timing --timeout 1800
python tools/check_fpga_equivalence.py --base 821cfae --yosys build/toolchain/yowasp/Scripts/yowasp-yosys.exe
```

Kiểm chứng tương đương: **14 trường hợp PASS** bằng Yosys SAT temporal
induction, so với nguồn baseline lấy trực tiếp từ Git. Bốn khối sửa đổi được
so sánh đầu ra và quan hệ thanh ghi; invariant state/recovery/session và
miền timer là assertion được chứng minh, không phải assumption. Có duty
power-of-two/full16bit, timer nhỏ, thay đổi pha có timer lớn nhất và
hold<clear/hold=clear/hold>clear. Hai negative control cố ý làm sai duty và
nạp watchdog lệch1tick đều bị proof từ chối trong pha có thể đạt tới.

Nguồn instrument/miter/log ở `fpga/build/equivalence/` đã ignore. Proof dùng
`async2sync`, reset đầu vào ở bước đầu, rồi temporal induction; không chứng
minh metastability, reset điện hoặc timing sau route. Mô phỏng reset/E-stop/
clock-stop, gate ngoài và phép đo phần cứng vẫn bắt buộc như trước.

20 test Python, kiểm tra repo/nhánh và `git diff --check` đạt. Các file sơ đồ
và liên kết README của tác vụ trước được giữ ngoài thay đổi tối ưu này.

## Mở rộng regression và bằng chứng bao phủ module — 24/10/2026

Nhánh `chore/fpga-regression-coverage`, nền `ec20257` (PR tối ưu #10 đã merge).
**Không thay đổi nguồn RTL**; bổ sung sáu testbench SystemVerilog, runner báo
cáo và yêu cầu CI. Cùng Icarus/VVP13.0: **22/22 testbench PASS**, compile không
warning, cả **15/15 module RTL** được elaborate trong bài thành công.

| Bài mới | Phạm vi đã kiểm tra |
| --- | --- |
| tb_common_matrix | Sáu cấu hình (N,WIDTH)=(1,1)/(2,2)/(3,4)/(4,2)/(5,3)/(8,4); scoreboard lịch sử mẫu độc lập; nhiễu N-1/N/N+1, 2.000 thay đổi ngẫu nhiên/cấu hình; reset ở chín pha và khi clock đứng |
| tb_crc16_matrix | 327.680 so sánh bằng chia đa thức24bit độc lập; đủ65.536 CRC trước với bốn byte0/FF/55/AA; đủ256 byte trên256 seed bổ sung, chưa phải toàn bộ2^24 cặp |
| tb_guard_sequence | Toàn65.536 delta sequence modulo,32.767 retry duplicate,16 bit điều khiển sai gồm chiều, duty2049/675/1350 và context_load trùng CMD |
| tb_uart_matrix | Bốn cấu hình divider8/9/16/17, gồm biên làm tròn; đủ256 byte TX/RX mỗi cấu hình; đo từng tick TX/stop/done, busy, reset ở cả10 vị trí ký hiệu và RX phục hồi |
| tb_frame_tx_random | 10 seed x256 STATUS, trường ngẫu nhiên/đủ256 byte state; packing/CRC reference riêng, nguồn đổi khi stall, metadata đóng băng,5.120 drop không tạo hàng đợi cũ |
| tb_safety_matrix | Năm cấu hình (watchdog,handshake,clear,hold)=(8,16,8,1)/(32,16,8,3)/(8,16,32,4)/(8,16,5,5)/(8,16,5,6), thêm watchdog1/handshake1; đủ6 state/8 fault bit, deadline, ưu tiên sự kiện, clear và illegal state |

Quét sequence giữ một base cố định và kiểm tra mọi khoảng cách modulo, không
phải mọi chuỗi traffic dài bất kỳ. FSM kiểm tra sáu trạng thái hợp lệ/tám bit
fault và những sự kiện đồng thời nêu trong test; không tuyên bố mọi tổ hợp
trạng thái/đầu vào đều đã được vét cạn. Illegal state được đưa vào bằng
`$deposit` để kiểm tra nhánh fail-safe, chưa chứng minh chịu SEU trên silicon.

### Ánh xạ toàn bộ RTL sang bằng chứng mô phỏng

Runner lấy tên module khai báo từ nguồn, đối chiếu kiểu module thực trong
file VVP của bài đã PASS, không suy từ tên file hay tên instance. Bảng dưới
liệt kê test chính; JSON còn ghi test tích hợp gián tiếp.

| Module RTL | Testbench chính |
| --- | --- |
| reset_sync | tb_encoder_units, tb_common_matrix |
| input_sync_filter | tb_encoder_units, tb_common_matrix, tb_encoder_pair |
| quadrature_decoder | tb_encoder_units, tb_encoder_pair, tb_encoder_timing |
| encoder_pair | tb_encoder_pair, tb_encoder_timing |
| pwm_pair | tb_pwm_pair, tb_pwm_widths, tb_pwm_timing |
| motor_pwm_pair | tb_motor_pwm_pair, tb_pwm_widths, tb_pwm_timing |
| uart_rx | tb_uart, tb_uart_matrix |
| uart_tx | tb_uart, tb_uart_matrix |
| crc16_byte | tb_crc16_matrix, tb_frame_rx, tb_frame_tx_random |
| frame_rx | tb_frame_rx, tb_fpga_link |
| frame_tx | tb_frame_tx, tb_frame_tx_random |
| command_guard | tb_command_guard, tb_guard_sequence |
| fpga_link | tb_fpga_link |
| safety_fsm | tb_safety_fsm, tb_safety_timing, tb_safety_matrix |
| drive_core | tb_drive_core, tb_drive_defaults |

Chỉ số **15/15 là module được elaborate trong test thành công**, không phải
100% dòng lệnh/nhánh/toggle/FSM transition hay chứng minh đúng mọi trạng thái.
Các metric đó chưa được đo. Ca chức năng có assert/scoreboard và counter
`COVER` riêng; số lượt chạy không tự thay tiêu chí bao phủ yêu cầu.

### Lệnh tái tạo và báo cáo

```powershell
python tools/run_fpga_tests.py --iverilog build/toolchain/ucrt64/bin/iverilog.exe --vvp build/toolchain/ucrt64/bin/vvp.exe --timeout 1800 --report fpga/build/regression-report.json --require-module-coverage
```

Bài tích hợp dài cục bộ PASS **2.001,560ms tại2,7MHz,188 STATUS**; bài lỗi
danh định PASS **225,343ms tại27MHz,11 STATUS**. Các bài encoder/PWM/safety/link
danh định vẫn chạy cấu hình27MHz. Không chạy lại bài top2s tại27MHz cục bộ
trong lần mở rộng này: nguồn RTL giữ nguyên PR#10, đã có bằng chứng full-timing
ở mục tối ưu; CI của PR này chạy lại toàn22 bài với `--full-timing`.

JSON ghi phiên bản compiler, SHA256 từng nguồn RTL/testbench, kết quả/duration,
module -> test và số ca chức năng. Thất bại/thiếu marker PASS không được tính
bằng chứng module. `--require-module-coverage` làm CI fail nếu có module mới
chưa nằm trong bài PASS; đây chỉ là hàng rào tối thiểu, vẫn phải review test
cho hành vi mới. CI lưu artifact `fpga-regression-evidence` kể cả khi lỗi.
Build/VCD/JSON là artifact bị ignore, không commit. Unit test Python kiểm
tra cả báo cáo lỗi, marker, module bị bỏ sót và hash nguồn. **28 test Python
PASS**, kiểm tra cấu trúc/nhánh và `git diff --check` đạt.

### Thử khả năng phát hiện lỗi

Đã tạo sáu bản nguồn sai trong build tạm, không sửa RTL gốc. Mỗi bản compile
thành công, sau đó bị bài tương ứng từ chối bằng `$fatal`; compile lỗi hay
timeout không được tính là phát hiện đúng:

| Sai lệch cố ý | Test phát hiện |
| --- | --- |
| Bộ lọc nhận sớm một mẫu | tb_common_matrix |
| CRC polynomial1021 đổi thành1020 | tb_crc16_matrix |
| Guard chấp nhận sequence lặp | tb_guard_sequence |
| TX rút một bit ngắn đi một tick | tb_uart_matrix |
| STATUS đổi chỗ count hai bánh | tb_frame_tx_random |
| Watchdog nạp deadline sớm một tick | tb_safety_matrix |

Kết quả6/6 bị từ chối; nguồn mutant/log/result cục bộ ở
`fpga/build/coverage-mutations/` bị ignore. Đây là negative control cho sáu
sai lệch cụ thể, không phải mutation score toàn bộ RTL.

### Timing còn phải làm

Chưa có số **Tcd/Tpd ns, setup/hold slack hoặc Fmax sau route**. Yosys generic
và mô phỏng logic/VCD không tạo bằng chứng này. Bước tiếp theo **f12 target9K**
thêm wrapper, pin/I/O/clock constraints và chạy Gowin synthesis/PnR/STA đúng
chip, trước mua board. Clock27MHz có chu kỳ khoảng37,037ns; STA phải kiểm tra
cả đường min/max, clock, FF setup/hold và corner yêu cầu, không chỉ so một
đường logic với chu kỳ. Xem [thời điểm và tiêu chí timing](../docs/fpga-rtl-design-test-plan.md#khi-nào-kiểm-tra-tcdtpd-và-timing).
Chưa thay thử điện/driver/gate/reset/clock-stop trên phần cứng.
