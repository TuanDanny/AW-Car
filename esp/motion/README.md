# Motion simplev1

ESP-IDF 6.1, ESP32-S3. AP+STA đang phát triển: AP AW-CAR/123456789 → http://192.168.4.1;
nhập Wi-Fi ngoài trên dashboard để gửi tới Brain và lưu riêng trên Motion.
Đã thử AP/STA và log HTTPS qua router; điều khiển chỉ AP. Chưa có receiver OTA.
`partitions_ota_candidate.csv` là phương án bố trí OTA đang phát triển, chưa kích hoạt,
chưa được phép nạp lên board; `partitions.csv` vẫn là bảng hiện hành.
Không ARM/PIN. Một task control core1 owns SPI2/GPIO10, HTTP task chỉ tiếp nhận.
Manual độc lập Brain. PID mặc định tắt; không dùng encoder một OUT để suy chiều.

Build: `python ../../utils/build_esp.py motion` từ thư mục này hoặc xem root hướng dẫn.
Không nạp cho tới khi VM ngắt, các dây SPI/tháo fixture theo sơ đồ đã được xác nhận.
