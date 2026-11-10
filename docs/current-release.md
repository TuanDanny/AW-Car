# Source ba board hiện hành — prototype v2

Ngày11/11/2026, chủ dự án duyệt giữ các tối ưu có lợi, đưa lên main và chỉ giữ
main làm nhánh chính thức/skeleton cho tính năng sau. Phát hành qua PR/squash,
CI PR và CI chạy lại trên main; tag `prototype-v2` sau khi đạt. Giữ tag v1,
không force-push; xóa local/remote `simplev1` và `codex/simplev1-ota` sau cùng.

| Board | Source / bản đã nạp |
| --- | --- |
| Brain ESP32-S3 | `simplev1-814afb90103b`, Xiaozhi/âm thanh/OLED, mặc định3giây |
| Motion ESP32-S3 | `simplev1-33495b1fe7e0`, Web/AP+STA/SPI/OTA, tối ưu DOM và STA busy |
| Tang Nano9K | RTL/constraints giữ nguyên mốc `fff2940`; UserCode `0x0000A6C1` |

Manifest công khai đã lọc: [current-release.json](../data/current-release.json).
Motion đọc ngược Flash đúng SHA256
`d62c815ba037b262a162d1d82b11ef8073add9432509eb2b908e1136582baab9`;
NVS, partition table, otadata và motioncfg giữ nguyên. Brain build lại vẫn đúng
image cũ, không nạp lại. Build ID được đối chiếu source/defaults/lockfile và
key ID đã dùng. Không commit private key, NVS, image hoặc log thô; build lại
cho thiết bị cần bộ khóa được giữ riêng ở workspace. Bitstream FPGA có SHA256
`64212c9aa7f73ec7779f27e3f2fd48f7b7e3a62ae9eee3a9dffc78a0ecb4cf43`;
đã nạp/reload Flash ở mốc trước, không tuyên bố có byte-readback FPGA mới.

## Flow skeleton giữ ổn định

Web→Motion→SPI→FPGA→DRV; Manual chỉ AW-CAR/192.168.4.1, router dành Xiaozhi,
OTA và log. Bốn hướng, giữ/nhả20Hz, STATUS10Hz, STOP/timeout về0, chuyển mode
hủy lệnh cũ, không replay. AI mặc định30%/3giây cho từng lệnh, PID mặc định tắt.
Giữ wiring, âm thanh, OLED, BOOT, giao thức và khoảng đảo chiều/thức driver.
Không mang trở lại PIN/ARM/Gate handshake của kiến trúc cũ.

V2 chỉ thêm setter Web có điều kiện/formatter dùng chung và nhận biết ý định
chuyển động khi trì hoãn STA retry. Không tăng STATUS hoặc thêm task/queue.
Observer `/#latency` tùy chọn chỉ đo, không tự phát MOVE.

## Bằng chứng và giới hạn

26ca browser đạt; 28unit test với một browser opt-in skip trong discovery,
52.301native assertion/127Brain check. Build cả hai ESP32 đạt. Người dùng xác
nhận bản B giữ/nhả mượt, STOP, AI3giây, OLED/loa bình thường, VM ngắt/chưa motor.

So A60/B61 mẫu cùng observer: bấm→STATUS p50 từ218,6 xuống102,2ms; p95 vẫn305,2ms,
max426,8→405,5ms. DOM mutation giảm87,6% trên host. Chưa đạt toàn bộ budget độ
trễ, không khẳng định mức giảm do riêng thay DOM hoặc tương đương PWM vật lý.
Xem [báo cáo A/B](optimization-results.md). Bộ92mẫu cũ ở
[latency-results.md](latency-results.md) là mốc trước, không trộn với A/B mới.

Log B264giây không tăng lỗi SPI/UART, không thấy panic/watchdog; A bổ sung có
hai lỗi SPI mới. Lịch sử có lỗi frame/ACK SPI chưa xác định nguyên nhân, nên
không tuyên bố đã giải quyết độ tin cậy bus bằng lượt ngắn này. Không có soak
30phút, đo cạnh PWM, motor/nguồn2S/PID hoặc chu kỳ OTA/rollback mới trong đợt V2.
Prototype v2 là skeleton phần mềm đã kiểm thử, không phải nghiệm thu xe có tải.

Xem [nạp/OTA/log](ota-usage.md), [đấu nối](../schematic/README.md) và
[cách đo độ trễ](latency-measurement.md). [Mốc skeleton cũ](skeleton-baseline.md)
chỉ mô tả tag ban đầu; không dùng build ID cũ để chọn app hiện hành.
