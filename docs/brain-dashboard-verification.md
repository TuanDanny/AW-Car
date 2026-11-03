# Brain/dashboard — bằng chứng ngày 03/11/2026

Nhánh `feat/f03-xiaozhi-ai`, phát triển từ baseline `112914e`. Mốc này kiểm
chứng Brain/dashboard với PC Motion test peer. Không có firmware Motion/PID,
FPGA hoặc motor thật trong vòng kiểm thử. Không nạp ESP32 trong mốc này.

## Mã và môi trường

- Firmware ESP-IDF 6.1 / ESP32-S3, profile `aw-car-ai-rgb-128x64`, tiếng Trung.
- Host Windows, Python 3.13, aiohttp 3.13.2, LLVM-MinGW clang C++17/O2.
- Host nạp chính `control_core.cc`, `voice_gate.h` và codec BM-v1 dùng cho
  firmware; Python độc lập đóng vai Motion, không mô phỏng PWM/PID/cơ khí.
- Lõi được đo có digest `114a69dcd53a`; manifest nguồn/compiler/binary ở
  `build/brain/brain-114a69dcd53a.manifest.json`. Giới hạn 200 mm/s và
  1000 mrad/s là cấu hình LAB, chưa hiệu chuẩn xe.

## Kiểm tra chức năng

| Nhóm | Bằng chứng | Kết quả |
| --- | --- | --- |
| Boot, HELLO/ARM/STOP, neutral | `tests/test_brain_core.py` | Đạt, phải có ACK Motion đúng phiên/yêu cầu |
| Sáu hướng, 0/30/100%, thay lệnh | C++ tests và `dashboard/control.test.mjs` | Đạt; neutral giữ ARM, STOP bỏ ARM |
| Manual TTL/deadman | Clock chủ động ở 119999/120000 và 149999/150000 µs | Đạt; lệnh lỗi không gia hạn |
| AI 1 giây, giới hạn 3 giây, quyền 5 phút | Clock chủ động, lệnh mới thay cũ | Đạt; không tự gia hạn quyền |
| Epoch, challenge, sequence wrap, callback cũ | C++/VoiceGate tests | Đạt; thiếu SID/STT hoặc callback muộn bị từ chối |
| Motion reset / STATUS lặp, sai phiên, CRC | C++ và serial peer tests | Đạt; phục hồi phải ARM mới, không phát lại mục tiêu |
| HTTP/JSON/auth/Origin/một WS | `tests/test_brain_web.py` | Đạt; sai kiểu số không được coi là lệnh hợp lệ |
| Internet/mất Web theo mode | C++/HTTP và computer use | Đạt trong giả lập |
| RGB, transcript, không có telemetry | HTTP + browser | Đạt; số đo chưa có là null/“Chưa có dữ liệu” |
| Repository và quy tắc | `python tools/check_repo.py`, unittest, diff check | Đang chốt kết quả cuối |

Full host regression hiện gồm 71 ca Python và 3 ca Node; báo cáo cuối cập
nhật khi hoàn tất build/soak và CI. Không dùng thời gian thực Windows làm
clock cho các kiểm tra biên chức năng; bài soak bên dưới đo thời gian thực.

## Computer use

Thao tác qua trình duyệt thật, cùng asset phục vụ từ Brain:

- Desktop: đăng nhập, W/S/A/D/Q/E, pointer giữ/nhả, chuyển mode, Cho phép,
  ba màu RGB, transcript Trung và tool giả lập; kết thúc hành động về 0.
- Điện thoại 390×844: không tràn ngang, DỪNG nằm trong header cố định;
  Manual vẫn dùng được khi Internet giả lập bị ngắt.
- AI vẫn giữ thời hạn khi Web refresh; hết 5 phút tự DISARMED.
- Trang thứ hai bị từ chối; AI mất Internet thu quyền và về DISARMED.

Ảnh/log cục bộ: `build/brain/cua/desktop-ai.png`, `mobile-ai.png`,
`mobile-manual.png`, `mobile-ai-offline.png`, `second-dashboard-rejected.png`
và `interaction-report.json`. Không commit cookie/PIN của fixture.
Pointer-cancel đi qua cùng đường release có kiểm tra logic; chưa tạo được
ngắt touch thực từ hệ điều hành/điện thoại trong computer use.

## Tải và độ trễ

Bài cuối dùng `tools/brain_soak.py --seconds 1800` qua WebSocket localhost,
20 lệnh/giây, cùng lõi C++. JSON kết quả ở `build/brain/soak-release.json`;
đang chạy đủ 30 phút trên thời gian thực, không tua clock.

Hai bài trước trên bản lõi cũ nhận một STALE đầu phiên vì challenge chưa
được đổi cùng epoch. Đã sửa và thêm hồi quy; không dùng hai bài đó để gọi
bản cuối đạt. Các buffer trace/latency/log đã giới hạn dung lượng.

Đo riêng handler JSON → mock nhận frame UART và RTT ACK WebSocket. Hai số
này **không** chứng minh p95/p99 FreeRTOS/Wi-Fi/UART chân TX, AI cloud hay
thời gian motor dừng. Firmware có cửa sổ 128 mẫu Web hợp lệ → gọi UART
driver, heap free/min và dư stack để đo tiếp trên board; hiện chưa có mẫu.

## Build và phần còn phải nghiệm thu

AW-Car đã build/merge image thành công bằng ESP-IDF 6.1. Stock build và
CI Linux đang kiểm tra hồi quy; cập nhật hash/kết quả cuối sau khi hoàn tất.
Binary ở `firmware/brain/build/merged-binary.bin`, offset 0x0000. Binary,
sdkconfig và log build được ignore, không đẩy bí mật/NVS vào Git.

Chưa nghiệm thu: AP+STA/WPA2/PIN OLED trên board, mic/I²S/loa/RGB/BOOT sau
tích hợp, UART vật lý 17/18, stack/heap/độ trễ ESP32, metadata SID/STT thực
của backend, Motion/FPGA/gate/motor. Thiếu metadata thì tool move khóa;
không bỏ guard để demo. Build và giả lập không thay các phép thử này.

Hướng dẫn chạy: [dashboard](../dashboard/README.md),
[thiết kế Brain](../firmware/brain/docs/dashboard-brain.md),
[Web contract](../dashboard/web-brain-protocol.md),
[UART BM-v1](../firmware/shared/brain-motion-protocol.md).
