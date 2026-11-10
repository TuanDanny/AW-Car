# Source ba board hiện hành — prototype v1

Chủ dự án đã nghiệm thu Manual/AI, giữ/nhả mượt và mặc định AI3giây ngày10/11/2026,
đồng thời yêu cầu đưa source đang dùng lên main. Nhánh phát triển:
`codex/simplev1-ota`; main cập nhật qua PR/squash và CI, không force-push.
`simplev1` đồng bộ sau CI main. Tag baseline ban đầu giữ nguyên để phục hồi.

| Board | Source / bản đã nạp |
| --- | --- |
| Brain ESP32-S3 | `simplev1-814afb90103b`, Xiaozhi/âm thanh/OLED, mặc định3giây |
| Motion ESP32-S3 | `simplev1-2f131b1123c6`, Web/AP+STA/SPI/OTA và observer đo tùy chọn |
| Tang Nano9K | RTL/constraints giữ nguyên mốc `fff2940`; UserCode `0x0000A6C1` |

Manifest công khai đã lọc: [current-release.json](../data/current-release.json).
Hai build ID được tính lại từ source/defaults/lockfile và key ID đã dùng, kiểm
manifest/SHA với kết quả nạp. Không đưa private key, NVS, image hay log thô vào
Git. Build mới cần bộ khóa riêng của thiết bị; Git/source hợp lệ không tự khôi
phục khóa đó. Bitstream FPGA có SHA256
`64212c9aa7f73ec7779f27e3f2fd48f7b7e3a62ae9eee3a9dffc78a0ecb4cf43`;
đã nạp/reload Flash ở mốc trước, không tuyên bố có byte-readback FPGA mới.

Giữ luồng Web→Motion→SPI→FPGA→DRV, Manual chỉ AP192.168.4.1. Router dùng Xiaozhi,
log và OTA. Không đổi wiring/PID/RTL trong lần đưa main này. Observer `/#latency`
chỉ nạp khi đo, không tự phát MOVE và không thêm xử lý vào car_control.

Bằng chứng: `data/web-hold-fix-checkpoint.json`, các checkpoint AP+STA/management/
OTA và `docs/verification.md`. Người dùng đã xác nhận giữ/nhả mượt và AI khoảng
3giây rồi về0 trên điện thoại, với VM ngắt/chưa motor. Phép đo số bấm→STATUS trên
điện thoại có92mẫu: p50=69,8ms, p95=125,2ms, max=221,4ms tới STATUS setpoint.
Motion→trước SPI p99=0,668ms/max=2,045ms. Không coi STATUS/ACK là cạnh PWM vật lý.
Toàn bộ budget chẩn đoán chưa đạt; frame/ACK SPI tăng đáng kể trong lượt này,
thử CS bằng GPIO không giải quyết và đã bỏ bản thử. Nguyên nhân chưa xác định,
không gọi bus hoặc toàn chuỗi là đã nghiệm thu ổn định. Chưa soak A/B30phút,
chưa nghiệm thu motor/pin2S/PID. Xem [kết quả đo](latency-results.md).

Xem [nạp/OTA/log](ota-usage.md), [đấu nối](../schematic/README.md) và
[cách đo độ trễ](latency-measurement.md). [Mốc skeleton cũ](skeleton-baseline.md)
chỉ mô tả tag ban đầu; không dùng build ID cũ để chọn app hiện hành.
