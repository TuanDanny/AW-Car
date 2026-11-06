# AW-Car KiCad — bản nháp schematic để review

Cập nhật07/11/2026. Nhánh `feat/f01-tang-nano9k-target`; làm schematic trước,
PCB sau khi chốt thành phần theo chủ dự án. Các board/module phải tháo rút
được. Không có footprint module, file PCB, Gerber hoặc phê duyệt lắp công suất.

## Mở project

Mở [aw_car.kicad_pro](aw_car.kicad_pro), sau đó schematic cùng tên. Tám trang:

| Trang | File | Phạm vi |
| --- | --- | --- |
| 1 | `aw_car.kicad_sch` | Mục lục và các điều kiện còn mở |
| 2 | `controllers.kicad_sch` | Brain–Motion–Tang, UART và GPIO đã gán trong source |
| 3 | `audio_oled.kicad_sch` | OLED, INMP441, MAX98357A và loa BTL |
| 4 | `drivers.kicad_sch` | Hai DRV, bốn cầu H/motor độc lập |
| 5 | `safety_contract.kicad_sch` | Giao diện gate cần có; **chưa phải mạch gate hoàn chỉnh** |
| 6 | `stby_clamps.kicad_sch` | Tầng kẹp STBY ứng viên bằng transistor, cần prototype |
| 7 | `sensors.kicad_sch` | Encoder, buffer ứng viên, đầu nối cảm biến/GPIO còn chờ |
| 8 | `power_review.kicad_sch` | Pack đã bảo vệ, cầu chì/công tắc TBD, DSN6000AUD |

[Đầu vào và contract](design-inputs.json) đối chiếu source Brain, Motion4af21b8
và pinout Tang hiện tại. Số `GPIO17`/`P25` trên symbol MCU/FPGA là **ID logic/
package**, không phải vị trí chân header hoặc pad của module. Không cập nhật
PCB từ các symbol logic này. Thứ tự chân các jack ngoại vi là đề xuất cho
harness; phải đối chiếu silk từng module khi làm cáp.

## Mô phỏng trong KiCad

Mở riêng [stby_simulation.kicad_pro](stby_simulation.kicad_pro), rồi schematic
cùng tên. Nó dùng lại **chính trang stby_clamps**, thêm nguồn và tải thử, không
vẽ lại một mạch độc lập. Vào Inspect → Simulator, chạy `.tran` được ghi trên
schematic, chọn `GATE_ALLOW`, `STBY_L`, `STBY_R` để xem. KiCad dùng ngspice
đi kèm. Library [generic-clamp.lib](generic-clamp.lib) là mô hình NPN/tải
**generic**, không phải model hãng đã được chứng thực cho2N3904/DRV8833.
Các nguồn/tải R201/C201/D201 trong bench chỉ phục vụ mô phỏng, không phải BOM
linh kiện carrier. Không nhập bench này vào PCB xe.

Phép quét batch lấy kết nối R/Q từ XML do KiCad xuất;180 ca DC với VM5,5–8,4V,
ALLOW thả nổi/LOW/HIGH, beta40/100/300 và pull-up module20k/47k/75k đã đạt
trong phạm vi mô hình. Ba phép transient quét điện dung đầu vào10p/100p/1n
đạt ở các cửa sổ đã ổn định. Bench SPICE xuất trực tiếp từ KiCad cũng chạy
ngspice thành công. Đây **không** phải mô phỏng đầy đủ gate/E-stop/watchdog,
converter DSN6000AUD, pin/BMS, motor, nhiệt hoặc hành vi khởi động của silicon.
Không khẳng định fail-safe khi đứt dây STBY hoặc miễn glitch từ phép thử này.

Tầng STBY dùng hai NPN mỗi driver: VM tự bias transistor kẹp về LOW khi
ALLOW mất/thả nổi; ALLOW chỉ điều khiển transistor nhả kẹp. VM/STBY không nối
trực tiếp tới GPIO. Phải xác minh STBY thực sự là nSLEEP, cách kéo lên và
điện áp thực của module trước khi chọn mạch cuối. Nếu STBY nối thẳng VM,
không được áp dụng mạch này. Wake-up phải được đánh giá từ ngưỡng HIGH thật
của nSLEEP và so với firmware; mô hình không bảo đảm margin1ms hiện tại.

## Đã chốt và còn mở

- Pin18650, phương án2S cấp thẳng VM; DSN6000AUD có sẵn để tạo5V logic/audio.
  Cầu chì/công tắc ghi TBD, không tự lấy thông số3A của listing làm tải liên tục.
  Cell cụ thể, cách đóng pack, BMS và sạc chưa chốt. J30 chỉ nhận đầu ra pack
  đã được bảo vệ; không phải đầu nối cho hai cell rời chưa có BMS.
- E-stop chỉ ngắt lực motor, giữ Brain/OLED/Web; nhả nút không tự chạy lại.
  Mạch chốt lỗi, giám sát nguồn và watchdog độc lập mất clock **chưa triển khai**.
  Permit mức HIGH tĩnh không được coi là bằng chứng FPGA còn chạy.
- Cần debug USB khi dùng pin; chưa chốt RUN/DEBUG bằng jumper hay chuyển nguồn
  tự động. Bốn rail5V tới board/amp cố ý chưa được nối chung. ERC hiện0error,
  **4warning isolated labels tại bốn nguồn chờ này**; không suppress để gọi PASS.
- Cắm rút module đã chốt; carrier hay bo nguồn/gate rời, kiểu đế/jack, phương
  án hàn và ngân sách đang chờ câu trả lời. Footprint/lỗ gá/USB/anten chờ đo.
- Đủ OLED, INMP441, MAX98357A/loa, MPU6050, VL53L0X, hai encoder một OUT và hai
  TCRT5000. Motion GPIO17/18 hỏng để trống. GPIO I2C/TCRT mới chưa gán vào MCU.
- SN74LVC2G17 là ứng viên buffer3V3 có input5V tolerant, không phải BOM đã mua.
  Nguồn/pull-up của MPU/ToF và actual module encoder/TCRT vẫn cần xác minh.

[verification.json](verification.json) ghi đúng phạm vi test, cảnh báo ERC,
hash source/log và các blocker. Kiểm netlist không chứng minh cơ khí, dòng,
nhiệt hoặc an toàn thực. Motion vẫn LOCKED; không đổi firmware/nạp/reset board.

## Lặp lại kiểm tra

Từ root repo, dùng KiCad CLI thực, Python3.13 với ngspice DLL trên máy:

```powershell
& D:/APP/KiCad/bin/kicad-cli.exe sch export netlist --format kicadxml -o build/awcar-review.xml hardware/pcb/kicad/aw_car.kicad_sch
python tools/check_awcar_schematic.py build/awcar-review.xml
& D:/APP/KiCad/bin/kicad-cli.exe sch erc --format json --severity-all --exit-code-violations -o build/awcar-erc.json hardware/pcb/kicad/aw_car.kicad_sch
python tools/simulate_awcar_clamps.py build/awcar-review.xml --output build/awcar-clamp-sim
& D:/APP/KiCad/bin/kicad-cli.exe sch export netlist --format spice -o build/awcar-clamp.cir hardware/pcb/kicad/stby_simulation.kicad_sch
python -m unittest discover -s tests -p test_awcar_schematic.py
```

ERC hiện trả code5 do4warning còn mở, đúng là **chưa sign-off**, không phải
lỗi chạy CLI. Không bỏ kiểm tra warning hoặc tự nối chung USB/buck để hết báo.
`generate_awcar_schematic.py` chỉ tái tạo bản sinh ban đầu; mặc định từ chối
đè file đã có. Chỉ dùng `--overwrite` sau review chỉnh tay; source trước đó
được sao lưu vào build. Thay đổi trong KiCad phải được giữ khi phát triển tiếp.

## Nguồn đối chiếu

- [KiCad10 schematic/simulation](https://docs.kicad.org/10.0/en/eeschema/eeschema.html),
  [CLI/ERC/netlist](https://docs.kicad.org/10.0/en/cli/cli.html).
- [TI DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf): nSLEEP, wake,
  giới hạn chân và bypass; chưa xác nhận IC thực trên module đang sở hữu.
- [TI SN74LVC2G17](https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf): pinout,
  input5,5V, Ioff và điều kiện nguồn/đầu ra.
- [onsemi2N3903/2N3904](https://www.onsemi.com/pdf/datasheet/2n3903-d.pdf): E/B/C,
  giới hạn và đặc tính; generic model trong project không lấy từ model hãng.
- [DSN6000AUD tại Hshop](https://hshop.vn/mach-on-ap-dc-dc-automatic-buck-boost-dsn6000aud):
  tên/model do người dùng xác nhận; listing không thay phép đo tải/ripple/nhiệt.

Đồ họa R/C/Fuse/Switch/NPN/nguồn thử lấy từ thư viện symbol KiCad cài trên máy,
nhúng để mở project độc lập. Xem [giấy phép thư viện KiCad và schematic exception](https://www.kicad.org/libraries/license/).
Symbol module chức năng và generator là phần bổ sung AW-Car; không giả làm
footprint chuẩn của nhà sản xuất hoặc pinout PCB đã xác nhận.
