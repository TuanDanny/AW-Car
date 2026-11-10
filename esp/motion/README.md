# Motion simplev1

ESP-IDF 6.1, ESP32-S3. AP-only AW-CAR/123456789 → http://192.168.4.1.
Không ARM/PIN. Một task control core1 owns SPI2/GPIO10, HTTP task chỉ tiếp nhận.
Manual độc lập Brain. PID mặc định tắt; không dùng encoder một OUT để suy chiều.

Build: `python ../../utils/build_esp.py motion` từ thư mục này hoặc xem root hướng dẫn.
Không nạp cho tới khi VM ngắt, các dây SPI/tháo fixture theo sơ đồ đã được xác nhận.
