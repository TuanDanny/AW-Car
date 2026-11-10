# Đấu nối simplev1

Schematic KiCad A3 là **tham chiếu đấu nối trên bàn**, chưa PCB/nguồn pin/Gate.
ID GPIO và package giữ đúng tên vật lý, không đoán số pad footprint module.
Các net cùng tên nối chung. Inputs bên trái, outputs bên phải, nguồn trên/GND dưới.

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

## Tháo dây cũ, khi đã tắt nguồn

P48↔Motion6, P51↔Motion7; fixture3V3 qua1k tới P33/P34 và Motion8/9;
dây gate_clear P49 nếu có. Giữ GND chung. Motion17/18 hỏng để trống.
Không nối FPGA reset P3 (bank1.8V) hoặc LED onboard1.8V vào GPIO3.3V ngoài.

Chỉ một encoder hiện gắn kênh phải. Khi thêm encoder trái: OUT→HV1, LV1→P27,
đổi pullP27 thành NONE vì module chuyển mức đã kéo lên; không nối5V trực tiếp Tang.

VM5V chỉ thử không motor. Rút nguồn trước đổi dây; ba rail USB5V riêng, GND chung.
Không coi điện áp DC cầu H thả nổi là số đo duty; dùng tải trở nhỏ khi đo trung bình.
Không cấp motor từ USB laptop. Sơ đồ pin2S/carrier cũ giữ nguyên tại nhánh PCB.
