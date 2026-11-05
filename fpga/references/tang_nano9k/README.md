# AW-Car trên Tang Nano 9K

> **Bản tham chiếu, chụp ngày 05/11/2026.** Nguồn: nhánh
> `feat/f01-tang-nano9k-target`, tài liệu tại commit `697c4fa`,
> implementation đã đo tại `17a0ccb`. Thư mục này chỉ lưu tài liệu;
> RTL/constraints/project Gowin của target chưa được ghép vào
> `feat/f01-fpga-drive`. Các lệnh build bên dưới phải chạy tại worktree
> target nêu trên, nơi có `fpga/targets/tang_nano9k/` và tool tương ứng.

Danh tính nguồn và hash bản gốc/bản lưu: [reference-source.json](reference-source.json).

Target chuẩn bị trên nhánh `feat/f01-tang-nano9k-target`, kế thừa RTL `7ab91b2`.
Physical top `aw_car_nano9k` chỉ thêm POR/mask reset, bọc logical top duy nhất
`aw_car_top`. Device `GW1NR-9C`, part `GW1NR-LV9QN88PC6/I5`; clock ngoài27MHz,
không PLL hoặc generated clock. Chưa được phép nạp AW-Car lên board.

`aw_car_nano9k.gprj` mở được bằng Gowin EDA. Chọn top `aw_car_nano9k`, chuẩn
SystemVerilog2017, giữ JTAG/MSPI/SSPI cấu hình mặc định, rồi Synthesize/Place & Route.
CLI được thực hiện bằng `tools/build_tang_nano9k.py` trong worktree target.
File `aw_car_nano9k.cst` là pin contract ứng viên đã đối chiếu schematic3672/3674,
không phải phép cho nối motor. Hai đầu nối LCD phải bỏ trống; không dùng pin1,8V
cho tín hiệu ESP32. Reset dùng nút S2/package3 ở1,8V, không đưa3,3V vào nút này.
Package4/JTAGSEL_N, JTAG5..8, MODE/RECONFIG/flash và SD được giữ riêng.

POR giữ core reset1024clock sau cấu hình/nhả nút; FF init0 được checker kiểm tra
trong netlist Gowin, vẫn cần nghiệm thu power-up thật. Gate default-off và E-stop
độc lập chưa có phần cứng; Motion vẫn LOCKED. Thử sau phê duyệt với VM tách rời.

## Tài liệu và trạng thái

- [Hardware audit, review warnings, CDC, risk register và integration readiness](hardware-audit.md).
- [Pinout đủ17 tín hiệu, package/header/bank/nguồn](pinout.md), dữ liệu checker
  trong [pinout.json](pinout.json).
- [Timing và bằng chứng kiểm thử](timing-report.md).
- [Kế hoạch bring-up không VM, chưa thực hiện](bringup-checklist.md).

## Build CLI từ root

Python3.10+, Gowin Education1.9.11.03 và Icarus/VVP. Không cần thư viện Python
ngoài. Dùng đường dẫn cài trên máy của mình hoặc biến môi trường GOWIN_SH:

```powershell
python tools/build_tang_nano9k.py --audit-only --gw-sh C:/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/bin/gw_sh.exe
python tools/build_tang_nano9k.py --gw-sh C:/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/bin/gw_sh.exe --iverilog D:/Project/AW-Car/build/toolchain/ucrt64/bin/iverilog.exe --vvp D:/Project/AW-Car/build/toolchain/ucrt64/bin/vvp.exe --rtl-tests full --post-map-test
```

Mặc định chạy34 RTL bench full-timing; tùy máy có thể mất nhiều phút. `quick`
chạy bộ mặc định có bài dài scaled, không thay physical STA. `skip` chỉ bỏ lần
chạy RTL đó và được ghi rõ trong JSON; không được trình bày như regression PASS.
`--post-map-test` dùng netlist thật sau PnR và thư viện primitive của chính Gowin
(không chép/commit thư viện hãng). Netlist functional không annotate SDF; STA
route là bằng chứng timing riêng. Test bắt được trường hợp compiler bỏ encoder.
Hai mode mapped kiểm tra cả boot DISARMED/session0 và GPIO recovery/HELLO với
session12345678 ở trạng thái HANDSHAKE, mỗi mode hai frame CRC/sequence/count/
period/age. Logical permit vẫn LOW, không gửi ARM/MOVE trong mapped test này.

Output chỉ ở `build/tang-nano9k/` và `fpga/build/`, đều ignored. JSON ghi commit,
dirty flag, hash từng source/report, constraint state, warning, pad/POR/timing.
LUT/FF/BRAM/Fmax/slack/TNS không lấy từ bài LED. Synthesis/PnR exit0 chưa đủ:
checker từ chối mất pad, missing report, constraint inactive hoặc timing âm.
Không có lệnh Programmer/flash/COM trong flow. File `.fs` chỉ là artifact chuẩn bị.

## Build GUI

1. Mở `aw_car_nano9k.gprj`; kiểm Device GW1NR-9C, part LV9QN88PC6/I5.
2. Đặt top `aw_car_nano9k`, language SystemVerilog2017. GPRJ chứa đúng RTL,
   physical shell, CST/SDC; không thêm testbench hoặc nguồn từ project LED.
3. Project Configuration: không bật use_jtag_as_gpio/use_mspi_as_gpio/
   use_sspi_as_gpio. Bật text timing report, IO CST, post-PnR Verilog netlist và
   show INIT. CLI build.tcl là nguồn options chuẩn để đối chiếu.
4. Run Synthesize rồi Place & Route. So pin report và9 constraint active,
   setup/hold/recovery/removal, warning và netlist encoder. Mở báo cáo `.tr`,
   `.rpt.txt` trong `impl/pnr`. GUI output tại `impl` được ignore.
5. Chạy CLI/checker và mapped test để nghiệm thu tái lập. Chưa mở Programmer
   hoặc tự chọn cổng USB/JTAG để nạp AW-Car.
