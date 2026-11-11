# Schematic đấu nối prototype v2 — A3

Mở `simplev1.kicad_pro` bằng **KiCad10** rồi vào Schematic Editor. Bản gốc là
[simplev1.kicad_sch](simplev1.kicad_sch), thư viện module cùng thư mục.
[PDF một trang A3 ngang](simplev1.pdf), [ảnh xem trước](simplev1-preview.png) và
[bản draw.io sửa được](simplev1.drawio) dùng cùng model chân/đường dây.

Ba board được tô màu: **Brain tím, Motion xanh dương, FPGA xanh lá**. Các đường
tín hiệu và nguồn nối trực tiếp tới chân, không chỉ có các nhãn rời. GPIO/Pxx
ghi tại đầu chân; đường vuông góc, chấm là nối, giao không chấm không nối.
Input trái/output phải là hướng ưu tiên; nguồn ở trên/GND dưới. Pxx là số chân
package FPGA, không phải thứ tự đếm lỗ header. Số chân module là ID logic,
chưa phải footprint/pad PCB. Khung nét đứt hoặc `[PLAN]/[P]` là nhánh dự kiến.

**Đây là schematic đấu module, chưa phát hành PCB.** Nguồn và cảm biến mới chỉ
được bổ sung vào bản vẽ; không đổi firmware hoặc hướng dẫn tự đấu lại toàn hệ
đang chạy. Các kết nối đã thử của prototype v2 giữ nguyên.

## Giữ dây

| Nguồn → đích | Chức năng |
| --- | --- |
| Brain17 → Motion14; Motion13 → Brain18 | UART460800 |
| Motion15 → TangP25; TangP26 → Motion16 | SPI MOSI/MISO |
| Motion4 → TangP29; Motion5 → TangP30 | SPI SCLK/CS_n, dùng lại dây handshake |
| TangP35/P40 → DRV trái IN1/IN2 | AIN1+BIN1 nhận IN1; AIN2+BIN2 nhận IN2 |
| TangP41/P42 → DRV phải IN1/IN2 | Hai cầu H vẫn có output riêng, không chập AO/BO |
| Motion10 → 1k → STBY trái; Motion10 → 1k → STBY phải | Hai nhánh; GPIO10 không nối vào3V3 |
| EncoderOUT → HV2; LV2 → TangP28 | Encoder phải, 5V→3V3 |
| Tang5V→HV; Tang3V3→LV; GND chung | Chân nguồn chuyển mức không có số |

Giữ dây audio/OLED Brain: mic WS4/BCLK5/SD6, ampli DIN7/BCLK15/LRC16,
OLED SDA41/SCL42. Chân cùng số ở **hai ESP khác nhau** không phải cùng tín hiệu.

## Cảm biến dự kiến

| Thiết bị | Nối vào | Trạng thái |
| --- | --- | --- |
| MPU6050 | Motion SDA11/SCL12; VCC3V3 Motion, AD0→GND, địa chỉ0x68 | Chưa bật trong firmware; XDA/XCL/INT không dùng |
| VL53L0X màu xanh | Cùng I²C Motion SDA11/SCL12, VIN3V3, địa chỉ0x29 | Chưa bật; XSHUT/GPIO1 để NC |
| TCRT5000 mép rơi trái | DO→Motion GPIO8, VCC3V3 Motion, GND chung | Chưa bật; AO không dùng |
| TCRT5000 mép rơi phải | DO→Motion GPIO9, VCC3V3 Motion, GND chung | Chưa bật; AO không dùng |
| Encoder trái bổ sung | OUT→HV1; LV1→TangP27 | Chưa có cảm biến thứ hai; đổi pull P27→NONE trước khi nối |
| Encoder phải hiện có | OUT→HV2; LV2→TangP28 | Giữ kết nối đã kiểm trên bàn |

Bus I²C Motion tách bus OLED Brain. Kiểm tra pull-up SDA/SCL của module phải về
3V3; nếu module chưa có pull-up, cần bổ sung sau khi xác nhận bo thực. Nguồn/
I/O của module cảm biến phải được đo trước khi cắm; không suy ra tương thích
chỉ từ màu PCB. Một OUT chỉ đếm cạnh không dấu, không đo được chiều quay.

## Nguồn 8,4V dự kiến

Nguồn bàn có giới hạn dòng J1 cấp thẳng VM hai DRV và cấp input hai bộ ổn áp:

- U15 DSN6000AUD chỉnh5,0V → `5V_LOGIC` → JP1/JP2/JP3 → ba board.
- U16 buck5V riêng → MAX98357A. Mã buck và khả năng chịu tải còn TBD.
- Ba nguồn3V3 lấy riêng từ từng board; không nối chung các chân3V3 này.
- GND nguồn bàn, hai buck, ba board, driver và cảm biến nối chung.

**J1 tối đa8,4V trong sơ đồ này** vì VM đi thẳng, không đi qua DSN. Việc chủ dự
án đo DSN ra5V khi Vin đổi3,3V→gần30V là phép thử **không tải**, không xác nhận
khả năng nuôi ba board và không cho phép cấp30V vào J1.

JP1–JP3 là jumper rút được cho từng board: RUN đóng jumper khi USB board đó đã
rút; DEBUG mở jumper trước khi cắm USB. Đây là thao tác cách ly thủ công, chưa
có mạch chống cấp ngược tự động. Loa chỉ nối SPK+/SPK− của amp; SPK− không phải
GND. Dòng nguồn, tụ lọc, fuse và bảo vệ công suất cần chốt trước bước PCB/tải.
Không coi ERC0 là bằng chứng nguồn chịu tải hoặc xe đã chạy.

## Tháo dây cũ, khi đã tắt nguồn

P48↔Motion6, P51↔Motion7; fixture3V3 qua1k tới P33/P34 và Motion8/9;
dây gate_clear P49 nếu có. Giữ GND chung. Motion17/18 hỏng để trống.
Không nối FPGA reset P3 (bank1.8V) hoặc LED onboard1.8V vào GPIO3.3V ngoài.

Chỉ một encoder hiện gắn kênh phải. Khi thêm encoder trái: OUT→HV1, LV1→P27,
đổi pullP27 thành NONE vì module chuyển mức đã kéo lên; không nối5V trực tiếp Tang.

Lượt đã nghiệm thu trước dùng VM5V không motor. Không cấp motor từ USB laptop.
Kiểm tra bản này: [schematic-verification.json](../data/schematic-verification.json).
Generator `utils/generate_schematic.py` bảo vệ chỉnh tay mặc định; `--force`
sao lưu trước vào `build/private/schematic-backups`. Nguồn model:
`utils/schematic_model.py`; không regenerate sau chỉnh tay nếu chưa đối chiếu.
