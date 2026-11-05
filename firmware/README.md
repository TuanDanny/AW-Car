# Firmware

Hai ứng dụng ESP-IDF6.1 độc lập dùng BM-v1 và shared source trong cùng repository:

- [brain](brain/README.md): Xiaozhi, AP+STA, Dashboard Manual/AI, mic/loa/OLED,
  WS2812 trạng thái; không cấp PWM trực tiếp hoặc tự ARM sau reconnect.
- [motion](motion/README.md): UART1 BrainTX13/RX14, UART2 FPGA15/16, vòng hở,
  lease/gate; mặc định ENABLE_DRIVER=n/validated=0. PID/cảm biến để mốc sau.
- [shared](shared/README.md): codec BM-v1/FPGA v2 và policy LED C++ thuần.

Mỗi ứng dụng có CMake, sdkconfig.defaults và dependencies.lock riêng. Không dùng
sdkconfig/NVS hoặc binary của board này cho board kia. Baseline RTL trong `fpga/`
vẫn là main cũ; Motion yêu cầu v2 ở peer riêng. Build không chứng minh phần cứng.
Bản tích hợp chỉ chuẩn bị review, không flash/reset/nâng quyền driver. Xem
[MERGE-READINESS](../docs/MERGE-READINESS.md) và README từng ứng dụng.
