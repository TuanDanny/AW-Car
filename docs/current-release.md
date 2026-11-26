> Pinout V4 đang tích hợp: SPI Motion GPIO42/41/40/39, FPGA encoder
> P49/P48 và DRV P51/P35/P31/P32. Bằng chứng trong tài liệu dưới đây
> thuộc mốc prototype trước đó và không xác nhận firmware V4 trong Flash.

# Mốc tích hợp AW-Car ngày 19/11/2026

## Firmware đang chạy

| Board | Firmware | Bằng chứng đối chiếu |
| --- | --- | --- |
| Brain ESP32-S3 | `simplev1-446be7f0109d` | OTA xác nhận build, hash ELF và trạng thái `valid` |
| Motion ESP32-S3 | `simplev1-7c10f8dbd4db` | OTA xác nhận build, hash ELF và trạng thái `valid` |
| Tang Nano9K | UserCode `0x0000A6C1` từ lần nạp trước | Cây RTL và constraints trùng `prototype-v2:fpga`. Motion nhận SPI ACK trên xe. |

Mã build của hai ESP khớp với cây source tích hợp. Hash app, hash ELF và
thông số cấu hình nằm trong [manifest](../data/current-release.json). Khi đối
chiếu Brain, sinh `lang_config.h` theo cấu hình tiếng Trung trong
`esp/brain/main/CMakeLists.txt`. Bitstream Tang lưu từ lần nạp trước còn
khớp hash. Build Gowin lần này tạo cùng payload cấu hình, đạt timing ở 27 MHz
và vượt mô phỏng RTL lẫn netlist. Bằng chứng trên xe gồm ACK SPI hiện tại và
lần xác minh nạp Tang đã lưu. Chưa có lượt đọc từng byte Flash Tang.
Xem [mốc prototype v2](https://github.com/TuanDanny/AW-Car/blob/prototype-v2/docs/current-release.md)
để phục hồi bản cũ.

## Kiểm thử phần mềm

Build ESP-IDF của hai ESP đạt. Kiểm thử host đạt 56 ca. Bộ trình duyệt
chạy riêng trên simulator đạt 34 ca, gồm giữ/nhả, STOP, quy đổi Thanh ga
và nhận ACK. FPGA đạt 4 testbench RTL, mô phỏng netlist và Gowin PnR/STA
với 0 vi phạm setup và hold tại 27 MHz. Chạy lại báo cáo Gowin bằng
`python utils/build_fpga.py --report build/fpga/release-check.json`.
Khi cần tái tạo mốc này, checkout commit chứa bản manifest ngày 19/11/2026
rồi làm theo [hướng dẫn build](build.md).

## Phạm vi hiện tại

- Người dùng xác nhận xe chạy với đề-pa hàm mũ hệ số **1,40** và **150 ms**.
  Thanh ga Web mặc định **20%**, gửi duty mục tiêu **56%**. Dải 1–100% tương
  ứng 45–100% duty mục tiêu, ga 0% gửi duty 0%.
- Web và AI cùng dùng các động tác tiến/lùi, quay tại chỗ, rẽ cong và quay
  quanh một bên. AI dùng cùng thang Thanh ga với Web và mặc định 20% trong
  3 giây. PID đang tắt.
- Laser và MPU đã đọc được trên Motion. Laser có mẫu hợp lệ xen lỗi pha.
  Kênh mép trái đã đổi mức đúng trên Web, có sàn là 1 và hở mép là 0.
  Mốc khoảng 43 mm là kết quả thử với mặt sàn và biến trở hiện tại.
  Firmware hiển thị cảm biến, chức năng tự dừng theo cảm biến đang chờ thử riêng.
- OTA giữ chế độ Manual với PWM hai bên bằng 0 lúc khởi động. Số đo Web,
  FPGA ACK và thời gian xe thực sự dừng là ba phép đo riêng.
- Khi Motion đứng yên, bộ đếm lỗi SPI tăng 112 trong khoảng 8 giây ở một
  đoạn log. Liên kết vẫn có ACK. Cần đo đường SPI trên xe để đánh giá độ
  ổn định trước khi coi phần truyền động đã nghiệm thu đầy đủ.

## Chân cảm biến và phần cứng chờ bổ sung

| Kênh | Chân theo firmware | Trạng thái |
| --- | --- | --- |
| VL53L0X | Motion SDA11 / SCL12 | Đã đọc |
| MPU mã thiết bị `0x74` | Motion SDA6 / SCL7 | Đã đọc tại địa chỉ I²C `0x68` |
| TCRT5000 trái | Motion DO → GPIO8 | Đã thấy đổi mức 1↔0 |
| TCRT5000 phải | Motion DO → GPIO9 | Chờ lắp và đo cực tính |
| Encoder phải | OUT qua chuyển mức → Tang P28 | Đã gắn, đếm một OUT |
| Encoder trái | OUT qua chuyển mức → Tang P27 | Chờ lắp. Xác nhận pull-up của module và cấu hình chân trước khi chạy. |

Đợt KiCad tiếp theo bổ sung kênh encoder trái, TCRT5000 phải và rail
`3V3_PERIPH` từ buck riêng cho các module cần 3,3 V. Dùng GND chung,
giữ hai đầu ra 3,3 V của buck và ESP32 tách riêng. Cần xác nhận điện áp
từng module, rail kéo lên SDA/SCL và trạng thái khi Motion mất nguồn trước
khi chốt mạch. [Đặc tả I²C](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)
· [Datasheet ESP32-S3](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf#page=65)

Lượt tích hợp này dùng source phần mềm đã kiểm chứng. Schematic và PCB
đang chỉnh tay chờ chốt đấu nối theo bảng trên trên
[nhánh KiCad](https://github.com/TuanDanny/AW-Car/pull/18).
