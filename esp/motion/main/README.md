# Firmware Motion

`runtime` owns Control/SPI/UART và mailbox. `web` HTTP/WS, snapshot/JSON ngoài
đường deadline. `main` khởi tạo AP+STA; lái xe chỉ AP, không xóa NVS khi init lỗi.
`network_activity.hpp` là predicate C++ thuần dùng chung với host test: intent
Waking/Reversing vẫn bận dù PWM0; giữ kiểm pending/OTA và STA đã online.

`Kconfig.projbuild`: đề-pa mũ thử nghiệm mặc định tắt, gain mặc định100% không
boost. Chỉ cấu hình khi build sau khi đo motor/dòng; Web chỉ quan sát trạng
thái này. Sáu action mới đi qua cùng mailbox/task/timeout với bốn action cũ.

Bản thử VL53L0X dùng I²C 100 kHz trên SDA GPIO11 và SCL GPIO12, địa chỉ
7 bit `0x29`. Task `laser_diag` chạy ưu tiên thấp trên core 0 và đọc
khoảng cách độc lập với đường điều khiển. Giữ VM ngắt khi kiểm trên bàn.

`awcarctl.py info motion` và `logs motion` trả về `tof_ack` cho phản hồi
I²C, `tof_status` cho trạng thái và `tof_mm` cho khoảng cách hợp lệ.
`tof_status` bằng 0 khi có mẫu hợp lệ. Giá trị dương là mã RangeStatus
của ST. Mã âm gồm -1 đang khởi tạo, -2 lỗi bus, -3 chưa ACK, -4 lỗi khởi
tạo sensor và -5 lỗi khi đọc. Khoảng cách là `null` khi mẫu không hợp lệ.
Driver dùng ST API qua [component ESP-IDF](https://github.com/nallyn1972/vl53l0x/tree/108d39933303cbdb68a61e72dceda1e7d6c76b76)
đã khóa revision trong manifest.

Dashboard nhận telemetry trong khung STATUS 10 Hz có sẵn. Một tác vụ I²C
chạy ở core 0, bên ngoài vòng điều khiển. VL53L0X vẫn đo từng lần theo bản
gốc. MPU6050 địa chỉ 0x68 dùng chung SDA11/SCL12, đọc trong các nhịp 100 ms
giữa những lần đo VL53L0X, với thang
±2 g và ±250 °/s. Hai TCRT5000 dùng DO trái GPIO8 và DO phải GPIO9, chỉ
hiển thị mức logic cho đến khi xác nhận cực tính trên xe. Khi cảm biến
không trả mẫu hoặc mẫu quá hạn, Web hiển thị trạng thái thay cho số cũ.
