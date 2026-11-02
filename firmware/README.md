# Firmware

Hai ứng dụng ESP-IDF độc lập và phần dùng chung; hiện mới có khung thư mục.

- [brain](brain/README.md): MCU 1, âm thanh, Xiaozhi, OLED I²C và mạng.
- [motion](motion/README.md): MCU 2, truyền động và an toàn cục bộ.
- [shared](shared/README.md): giao thức và kiểu dữ liệu dùng chung.

Đã có 2 ESP32-S3 có Wi-Fi; mã `R16N8` do chủ dự án cung cấp cần đối chiếu
ảnh module, bộ nhớ và pinout trước cấu hình firmware. Đồ đã có và kế hoạch
mua tiếp ở [kiểm kê phần cứng](../hardware/components.md).

Chốt SDK/board trước khi thêm CMake và cấu hình build. Khi có mã nguồn, ghi
lệnh build của từng MCU tại README tương ứng.
