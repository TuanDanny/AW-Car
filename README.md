# AW-Car

Xe 4WD hai bên độc lập. **Web → Motion → SPI → Tang Nano9K → DRV8833** là
đường điều khiển trực tiếp. Brain chạy Xiaozhi, mic, loa và OLED, rồi gửi lệnh
AI sang Motion qua UART. Manual hoạt động qua AW-CAR tại `192.168.4.1`.
Wi-Fi router phục vụ Xiaozhi, OTA và log.

[Bản hiện hành, mốc nghiệm thu và phần cứng chờ bổ sung](docs/current-release.md)
ghi mã nguồn và mã firmware của cả ba board. `main` là nhánh chính thức.
`prototype-v1` và `prototype-v2` là hai mốc phục hồi.

| Thư mục | Nội dung |
| --- | --- |
| [esp](esp/README.md) | Firmware Brain, Motion và giao thức C++ dùng chung |
| [fpga](fpga/README.md) | SPI, PWM và encoder SystemVerilog trên Tang Nano9K |
| [schematic](schematic/README.md) | Bản vẽ đấu nối tham chiếu |
| [docs](docs/README.md) | Hướng dẫn, contract và lịch sử kiểm chứng |
| [data](data/README.md) | Vector giao thức và bằng chứng đã lọc |
| [utils](utils/README.md) | Build, kiểm tra, OTA và thu log |
| [test](test/README.md) | Kiểm thử host, trình duyệt và RTL |

Bắt đầu từ [Dashboard](docs/dashboard.md), [OTA và log](docs/ota-usage.md)
hoặc [hướng dẫn build](docs/build.md). Đọc [contract](docs/protocol.md)
trước khi đổi giao thức và [bảng chân đang chạy](docs/current-release.md#chân-cảm-biến-và-phần-cứng-chờ-bổ-sung)
trước khi đi dây.

## Bảng kết nối toàn mạch

Bảng V4 dưới đây đối chiếu với PCB và schematic **candidate** đang chỉnh tại
`schematic/pcb-in/ban-di-day-dang-do` trên máy làm việc ngày 26/11/2026.
PCB này còn đang đi dây và chưa được kiểm chứng hoàn chỉnh.\nPCB chính thức trên máy nằm trong thư mục `schematic/pcb-in/ban-di-day-dang-do`. Số `Pxx` là số
chân package FPGA của Tang Nano 9K, còn `GPIOxx` là GPIO ESP32-S3.

**Trạng thái V4:** source trên nhánh này sử dụng pinout PCB V4 ở SPI
Motion, encoder và các đầu ra DRV. Firmware V4 mới build cần được thử lại
trên đúng ba board trước khi xác nhận trùng với Flash trên xe.

### Nguồn

| Đầu nối hoặc nguồn | Kết nối V4 |
| --- | --- |
| U15 | Chân 1: +5,18 V từ DSN 1 cho Brain và Motion. Chân 2: GND. |
| U16 | Chân 1: +5,10 V từ DSN 2 cho Tang, MAX98357A và tải 5 V AUX. Chân 2: GND. |
| U18 | Chân 1: +3,3 V từ buck ngoại vi. Chân 2: GND. Cấp các module ngoại vi 3,3 V theo bảng dưới. |
| J9 | Chân 1: +VM từ pin 2S qua cầu chì F1 ngoài bo. Chân 2: GND. VM đến cả hai DRV. |
| GND | Âm pin, âm các buck, ba board và ngoại vi nối chung. Hai đầu ra dương 5 V và buck 3,3 V giữ riêng. |

Buck 3,3 V cấp ngoại vi, không cấp vào chân 3V3 hoặc GPIO ESP32-S3.
Ngắt nguồn 5 V ngoài của board trước khi cắm USB board đó.

### Brain và Motion

| Tín hiệu | Nối dây |
| --- | --- |
| Brain TX → Motion RX | Brain GPIO17 → Motion GPIO14 |
| Motion TX → Brain RX | Motion GPIO13 → Brain GPIO18 |
| INMP441 WS / SCK / SD | Brain GPIO4 / GPIO5 / GPIO6 |
| INMP441 VDD / GND / L/R | 3,3 V ngoại vi / GND / GND |
| OLED SDA / SCL | Brain GPIO41 / GPIO42. VCC 3,3 V ngoại vi và GND. |
| MAX98357A DIN / BCLK / LRC | Brain GPIO7 / GPIO15 / GPIO16 |
| MAX98357A VIN / GND | 5 V AUX / GND |
| Loa | Nối hai dây vào SPK+ và SPK− của MAX98357A. |
| VL53L0X SDA / SCL | Motion GPIO11 / GPIO12, VCC 3,3 V ngoại vi và GND |
| MPU SDA / SCL | Motion GPIO6 / GPIO7, VCC 3,3 V ngoại vi và GND |
| Mép trái / phải theo firmware main | Motion GPIO8 / GPIO9. Trên PCB V4 hai chân này đưa ra JXM1. |
| STBY hai DRV | Motion GPIO10 qua hai nhánh điện trở riêng tới STBY trái và phải |

GPIO17/18 của Motion được ghi nhận là hỏng trên board đã dùng. Nút BOOT
Brain là GPIO0, LED onboard Brain là GPIO48.

### SPI Motion → Tang

| Tín hiệu | Motion | Tang |
| --- | --- | --- |
| MOSI | GPIO42 | P25 |
| MISO | GPIO41 | P26 |
| SCLK | GPIO40 | P29 |
| CS | GPIO39 | P30 |

### Tang, DRV và encoder

| Tín hiệu | Chân Tang V4 |
| --- | --- |
| DRV trái IN1 / IN2 | P51 / P35 |
| DRV phải IN1 / IN2 | P31 / P32 |
| Encoder trái / phải qua chuyển mức | P49 / P48 |

Trên PCB V4, IN1 nối đến AIN1 và BIN1 cùng phía, IN2 nối đến AIN2 và BIN2.
Mỗi DRV có hai ngõ ra AO và BO cho hai motor của cùng bên. Mỗi encoder dùng
một OUT, qua bộ chuyển mức từ 5 V encoder sang mức tham chiếu 3,3 V của Tang.
Giắc encoder U10/U17 có thứ tự GND, 5 V AUX, OUT. Xác nhận thứ tự trên module
encoder thực tế trước khi cắm.

### Giắc mở rộng trên PCB V4

| Giắc | Thứ tự chân theo số pad |
| --- | --- |
| JXB1 — Brain 2×5 | 1 GPIO8, 2 GPIO9, 3 GPIO10, 4 GPIO11, 5 GPIO12, 6 GPIO13, 7 GPIO14, 8 GPIO21, 9 GPIO47, 10 GPIO1 |
| JXM1 — Motion 2×6 | 1 GND, 2 3V3 ngoại vi, 3 GPIO8, 4 GPIO9, 5 GPIO38, 6 GPIO5, 7 GND, 8 SDA ToF, 9 SCL ToF, 10 GND, 11 5V AUX, 12 3V3 ngoại vi |
| JXT1 — Tang 2×5 | 1 P27, 2 P28, 3 P33, 4 P34, 5 P40, 6 P41, 7 P42, 8 P53, 9 P54, 10 P56 |

JXB1 gồm 10 chân GPIO, lấy nguồn và GND từ giắc khác. SDA/SCL trên JXM1 dùng
chung bus ToF. Một số chân JXT1 dùng chung chức năng RGB LCD trên board Tang;
cần cấu hình RTL và xem xét thiết bị gắn trên board khi sử dụng.

### Siêu âm dự kiến trên PCB V4

| Vị trí | TRIG từ Motion | ECHO tới Motion |
| --- | --- | --- |
| Trước U19 | GPIO1 | GPIO15 qua chia áp |
| Trái U20 | GPIO2 | GPIO16 qua chia áp |
| Phải U21 | GPIO21 | GPIO4 qua chia áp |

Mỗi giắc có thứ tự 5 V AUX, TRIG, ECHO, GND. Mạch ECHO chia áp trước GPIO
ESP32-S3. Các kênh này là bố trí PCB dự kiến, cần kiểm tra firmware và module
thực tế trước khi sử dụng.
