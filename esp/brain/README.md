# Brain Xiaozhi simplev1

Firmware thật ESP-IDF 6.1 cho một ESP32-S3 AW-Car: Xiaozhi tiếng Trung,
INMP441 16 kHz, MAX98357A 24 kHz, SSD1306 128×64 và UART1 tới Motion.
STA-only; Web/AP thuộc Motion. Chi tiết: [docs/brain.md](../../docs/brain.md).

Build từ root: `python utils/build_esp.py brain`. Chỉ build, không nạp.
Nguồn và giấy phép: [UPSTREAM.md](UPSTREAM.md), [LICENSE](LICENSE).
Kết quả build/host không chứng nhận phần cứng hay activation trên image mới.
