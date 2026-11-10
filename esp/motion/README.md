# Motion simplev1

ESP-IDF 6.1, ESP32-S3. AP+STA đang phát triển: AP AW-CAR/123456789 → http://192.168.4.1;
nhập Wi-Fi ngoài trên dashboard để gửi tới Brain và lưu riêng trên Motion.
Đã thử AP/STA và log HTTPS qua router; điều khiển chỉ AP. OTA dùng service HTTPS riêng.
`partitions.csv` thêm hai OTA slot, giữ factory/NVS/motioncfg theo `partitions_legacy.csv`.
Board cũ cần migration USB một lần; không flash-all hoặc ghi đè bản factory.
MAINTENANCE hạ GPIO10 và chờ hai ACK của gói PWM0 rồi mới ghi slot không chạy.
MOVE/mode bị từ chối khi bảo trì; kết thúc/lỗi/reboot về Manual0, không phát lại lệnh.
Boot trial phải xác nhận task control và output0, không cần Internet/Xiaozhi.
Không ARM/PIN. Một task control core1 owns SPI2/GPIO10, HTTP task chỉ tiếp nhận.
Manual độc lập Brain. PID mặc định tắt; không dùng encoder một OUT để suy chiều.
Web gửi ngay khi nhấn, lặp20Hz. Socket bận ngắn thì bỏ lần gửi lặp; tắc liên tục
quá150ms thì hủy giữ, không tự phát lại. Nhả/STOP/timeout500ms vẫn về0.
AI bỏ duration hoặc duration0 dùng3giây; thời gian chỉ định riêng giữ100..3000ms.

Build: `python ../../utils/build_esp.py motion` từ thư mục này hoặc xem root hướng dẫn.
Không nạp cho tới khi VM ngắt, các dây SPI/tháo fixture theo sơ đồ đã được xác nhận.
