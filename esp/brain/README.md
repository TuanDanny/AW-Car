# Brain Xiaozhi simplev1

Firmware thật ESP-IDF 6.1 cho một ESP32-S3 AW-Car: Xiaozhi tiếng Trung,
INMP441 16 kHz, MAX98357A I²S 48 kHz, SSD1306 128×64 và UART1 tới Motion.
Audio cloud/OGG được đổi mẫu theo tần số khai báo, giữ cao độ/thời lượng.
Setup giãn150ms trước Wi-Fi, 300ms trước cloud và500ms trước âm báo;
không thêm delay vào đường nghe/nói sau boot. Xem
[nghiên cứu và kiểm chứng](../../docs/brain-startup-power-review.md).
STA-only; Web/AP thuộc Motion. Chi tiết: [docs/brain.md](../../docs/brain.md).

Build từ root: `python utils/build_esp.py brain`. Chỉ build, không nạp.
Nguồn và giấy phép: [UPSTREAM.md](UPSTREAM.md), [LICENSE](LICENSE).
Kết quả build/host không chứng nhận phần cứng hay activation trên image mới.
