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
Gowin/PnR/timing hoặc chạy trên board; UART/FSM an toàn/watchdog vẫn ở giai
đoạn tiếp theo.
