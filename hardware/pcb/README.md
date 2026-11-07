# Schematic và PCB AW-Car

Mở **[aw_car.kicad_pro](aw_car.kicad_pro)** trong KiCad, rồi mở
**[aw_car.kicad_sch](aw_car.kicad_sch)**: sơ đồ đấu nối chung **một trang A1**,
44 linh kiện/module,69 net. Brain, Motion, Tang, audio/OLED, hai driver/bốn
motor, encoder, cảm biến, nguồn và interface gate cùng nằm trên trang này.
Dây tín hiệu nối trực tiếp giữa các chân; các nhãn nguồn cùng tên nối chung.
Module dự kiến cắm rút, không hàn cố định lên carrier.

Thư mục này giữ source KiCad: project, schematic, thư viện symbol cục bộ
`aw_car.kicad_sym`, `sym-lib-table` và model `generic-clamp.lib`. Đã bỏ các
sheet/project tách và hình/script PCB concept cũ khỏi thư mục theo yêu cầu
07/11/2026. Bản phục hồi gồm cả lịch sử chỉnh sửa cũ giữ cục bộ trong
`build/hardware-pcb-before-single-sheet-20261107/pcb` (Git ignore).

**Chưa tạo layout.** Khi schematic và thành phần được chốt, layout native
sẽ đặt ngay đây với tên `aw_car.kicad_pcb`; chưa có footprint/pad/outline
hoặc Gerber được duyệt. GPIO ESP32 và mã package Tang trên symbol là ID
logic để đối chiếu đấu dây, chưa phải số pad header của devboard/module.

Các phần còn mở được ghi trên schematic và trong
[dữ liệu thiết kế](../../docs/awcar-schematic-design-inputs.json): nguồn 5V
khi cắm USB cùng pin, BMS/sạc/cầu chì, GPIO cảm biến, header/footprint, tải
DSN6000AUD và gate/E-stop/watchdog độc lập đầy đủ. J9 là **interface gate
cần triển khai**, chưa phải mạch gate hoàn chỉnh. Nguồn 5V test của DSN chưa
nối vào bốn đầu nguồn board/amp; không nối thêm để làm hết cảnh báo ERC.

## Kiểm tra và mô phỏng

Chạy từ root, cần KiCad CLI trong PATH (máy hiện tại: `D:/APP/KiCad/bin`):

```sh
kicad-cli sch export netlist --format kicadxml -o build/awcar.xml hardware/pcb/aw_car.kicad_sch
python tools/check_awcar_schematic.py build/awcar.xml
kicad-cli sch erc --format json --severity-all --exit-code-violations -o build/awcar-erc.json hardware/pcb/aw_car.kicad_sch
python tools/simulate_awcar_clamps.py build/awcar.xml --output build/awcar-simulation
python -m unittest discover -s tests
```

Tạo `build` trước nếu chưa có. ERC hiện còn **4 warning** `isolated_pin_label`
ở nguồn5V Brain/Motion/Tang/amp, **0 error**; lệnh ERC trả mã khác0 vì cảnh
báo còn tồn tại, không phải đã được miễn trừ. Checker so toàn bộ kết nối
với [manifest](../../docs/awcar-schematic-parts.json), thêm contract firmware.
[Báo cáo kiểm chứng](../../docs/awcar-schematic-verification.json) ghi hash và
phạm vi thực tế.

Batch ngspice đọc R/Q từ netlist của chính schematic chung; không cần project
simulation riêng. 180 ca DC và3 quá độ chỉ kiểm **tầng STBY ứng viên**, dùng
NPN/đầu vào driver generic. Chưa mô phỏng gate hoàn chỉnh, cell/BMS/sạc,
buck-boost, motor, nhiệt hoặc PCB. Không coi PASS này là nghiệm thu phần cứng.

Generator mặc định từ chối ghi đè source đã có. Muốn thử bố cục khác:

```sh
python tools/generate_awcar_schematic.py --output build/kicad-candidate
```

Review trước khi thay source chỉnh tay. `--overwrite` chỉ dùng khi chủ động
regenerate; bản source trước đó sẽ được sao lưu trong `build`.
