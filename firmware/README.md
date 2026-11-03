# Firmware

Hai ứng dụng ESP-IDF độc lập, giao tiếp BM-v1, dùng chung codec C++ thuần.

- [brain](brain/README.md): Xiaozhi, INMP441, OLED I²C, RGB, AP+STA và Web;
  source hoạt động ở nhánh `feat/f03-xiaozhi-ai`, PR #13 draft.
- [motion](motion/README.md): MCU 2, hai UART, vòng hở, lease và gate;
  ESP-IDF 6.1, mặc định khóa driver. PI/PID và cảm biến ở mốc sau.
- [shared](shared/README.md): BM-v1 và Motion–FPGA v2, không phụ thuộc SDK.

Checkout Motion từ main không chứa toàn bộ ứng dụng Brain hoặc RTL v2.
Xem README từng ứng dụng và [bằng chứng Motion](../docs/motion-verification.md)
trước khi build/nạp; hai board có image và dữ liệu NVS riêng.
