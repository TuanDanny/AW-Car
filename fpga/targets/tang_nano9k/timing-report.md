# AW-Car Nano9K — timing và kiểm thử

**BUILD/CONSTRAINED STA/SOFTWARE PASS — HARDWARE NOT VERIFIED.**

## Nguồn và công cụ

- Implementation commit: `17a0ccbd26c2e6fe916877c0290ebebc3f3a514d`; branch `feat/f01-tang-nano9k-target`.
- FPGA base: `7ab91b2`; production Motion peer: main`4cea85c` LOCKED.
- Gowin1.9.11.03 Education; GW1NR-9C / GW1NR-LV9QN88PC6/I5.
- Source và report hashes: [timing-evidence.json](timing-evidence.json). Raw artifacts chỉ trong build ignored.
- Mọi kết quả là AW-Car/physical shell, không dùng Fmax hoặc slack bài LED.

## STA sau route

| Chỉ số | Kết quả |
| --- | ---: |
| Clock constraint | 27MHz /37,037037ns |
| Actual Fmax | 35.963MHz |
| Worst setup slack (gồm I/O budget) | +9.230ns |
| Worst hold slack | +0.357ns |
| Worst recovery / removal | +29.294 /+1.906ns |
| TNS setup / hold | 0 /0ns |
| Setup / hold violated endpoints | 0 /0 |
| Paths / endpoints analyzed | 4672 /4487 |
| LUT4 / ALU | 1663 /311 |
| Logic cells | 1974/8640 |
| Logic FF / I/O FF | 1568 /4 |
| BRAM | 0 primitive; không có BSRAM trong netlist |
| Logic / I/O latch | 0 /0 |
| I/O port / buffer | 17/71 /17 |
| Constraint active | 9 |
| First-sampler D pin exceptions | 4, exact names |
| Tổng số unconstrained paths | Tool format không xuất; null, không bịa0 |

Setup model: Slow 1.14V 85C C6/I5; hold model: Fast 1.26V 0C C6/I5.

STA PASS dưới [SDC/audit](hardware-audit.md): guardband0,2ns là giả định kỹ thuật,
I/O propagation budget một clock37,037ns. Không dựng clock chung giả giữa ESP32/
encoder và FPGA. Chỉ cắt bốn first-sampler D pins; stage1→stage2, raw shutdown
và reset distribution vẫn timed. Không có tổng unconstrained để công bố0:
17 cổng và9 constraints đã audit; sign-off CDC/MTBF và giao tiếp ngoài chip còn mở.

## Kiểm thử và mức bằng chứng

| Tầng | Kết quả |
| --- | --- |
| Repository / Python | 56/56PASS, không cần board |
| RTL Icarus | 34/34PASS full-timing; bài core2010,544ms ở27MHz,20/20 module evidence |
| Gowin actual synthesis/PnR/STA | PASS; điện áp/pin sau route khớp contract17 cổng |
| Post-PnR functional | 2 mode PASS, mỗi mode2 STATUS/CRC: DISARMED/session0 và GPIO HELLO/HANDSHAKE/session12345678 |
| Encoder mapped | count3/5, period32, age khác0, bit mode/valid và header/payload sequence đúng |
| POR/reset mapped | Bắt đầu resetHIGH, INIT0/POR và boundary OFF đạt; không gửi ARM/MOVE |
| Production Motion + FPGA v2 co-sim | 6 kịch bản PASS ở27MHz, peer main4cea85c;430000us thời gian mô phỏng |
| Physical AW-Car/gate/E-stop/VM | NOT VERIFIED / không thực hiện |

Mapped functional không annotate SDF; timing sau route là STA riêng. Không dùng
thời gian chạy host/co-sim như độ trễ MCU hoặc xe. Lệnh CLI nghiệm thu dùng
`--rtl-tests skip --post-map-test` vì bộ34 full đã chạy độc lập song song;
hash tất cả nguồn regression và netlist build được đối chiếu cùng nguồn cuối.
Script mặc định `--rtl-tests full` để tái lập toàn bộ trong một lượt.

Lượt full bị người dùng ngắt sau33 bài đã có PASS/$finish, khi bài maneuvers
đang chạy. Chạy lại riêng bài cuối bằng runner gốc; báo cáo tổng hợp kiểm hash
nguồn, compiled VVP và log của33 bài hoàn tất, không lấy PASS từ báo cáo cũ.
Thời gian host từng bài bị ngắt không được lưu nên ghi null, không ước lượng.

## Hai counterexample compiler đã bắt được

1. Trước sửa default payload selection: netlist không có pad encoder; cùng
   test mapped FAIL count0/0. Full-width shift +fixed slice giữ đúng body.
2. Sau sửa body nhưng trước sửa header: parser và active_session đều12345678,
   header TX thành12340000 dù CRC hợp lệ. Fixed header slices khôi phục đủ byte.
   Test HELLO nonzero là điều kiện bắt buộc, không bỏ để xanh build.

Không đổi timer, CRC, wire format, epoch/session policy hoặc điều kiện ARM.
Một lượt build/test bị hủy hoặc FAIL trong chẩn đoán không được tính PASS.
Báo cáo này ghi lượt cuối đã đạt và hash khớp source commit ở trên.

## Giới hạn và bước tiếp theo

Source chỉ chốt ở nhánh riêng; chưa push/merge FPGA vào main. Checkout FPGA/CAD/
LED gốc giữ HEAD7ab91b2;49/50 file baseline còn nguyên hash. Metadata GUI
`led_test.gprj.user` đã đổi và có thêm `impl/led_test_process_config.json`
so với ảnh chụp ban đầu; tác vụ target không ghi checkout đó và giữ nguyên
những thay đổi này, không khôi phục snapshot để làm sạch status.
Không flash/reset/mở COM,
không đổi Motion LOCKED, không cấp VM. Gate/chốt lỗi/E-stop độc lập chưa có.
Bài LED thật do người dùng xác nhận không phải nghiệm thu bitstream AW-Car.

Chỉ tiếp tục [bring-up không VM](bringup-checklist.md) sau phê duyệt riêng;
đo revision/header/điện áp/POR, UART và encoder trước. Không nối tắt safety/gate
để có DISARMED. Trước thử công suất phải đóng các rủi ro trong hardware-audit.
