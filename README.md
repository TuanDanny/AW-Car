# AW-Car — prototype v1

Skeleton độc lập: **Web → Motion → SPI → FPGA → DRV8833**, Brain chuyên Xiaozhi.

`main` là bản **prototype v1 hiện hành**; `simplev1` được đồng bộ theo mốc nghiệm thu.
Workspace chính: `D:/Project/AW-Car`; worktree skeleton: `D:/Project/AW-Car/simplev1`.
Manual trước, AI sau, PID viết sẵn nhưng chưa bật. Không dùng ARM/PIN/Gate handshake.

**Bản hiện hành:** [source ba board và phạm vi nghiệm thu](docs/current-release.md).
Hai tag `prototype-v1` / `simplev1-skeleton-v1` giữ mốc ban đầu để phục hồi.

| Thư mục | Nội dung |
| --- | --- |
| [esp](esp/README.md) | Hai firmware ESP-IDF 6.1 và lõi dùng chung |
| [fpga](fpga/README.md) | SPI/PWM/encoder SystemVerilog + Gowin |
| [schematic](schematic/README.md) | Đấu nối bản simple, chưa PCB |
| [docs](docs/README.md) | Contract, nguồn tham khảo, hướng dẫn và nghiệm thu |
| [data](data/README.md) | Vector chuẩn và bằng chứng đã lọc |
| [utils](utils/README.md) | Build/test/thu log |
| [test](test/README.md) | Kiểm thử host, browser và RTL |

Xem [contract](docs/protocol.md) trước khi thay giao thức. Không coi mô phỏng hoặc
build thành công là bằng chứng xe đã chạy. Phép thử phần cứng phải ghi riêng.

Manual vẫn chỉ qua AW-CAR/192.168.4.1; router phục vụ AI, OTA và log.
Xem [cách dùng OTA/log](docs/ota-usage.md) và [đo độ trễ](docs/latency-measurement.md).

Đọc [build/nạp/thu log](docs/build.md) và [báo cáo kiểm chứng](docs/verification.md).
Ngày10/11: Manual bốn hướng và AI quay trái/phải đã có log SPI trên ba board;
cầuB cả haiDRV đã đo đúng cực tính ở100% với VM USB khoảng5V, chưa motor.
PID mặc định tắt. Chưa nghiệm thu cầuA trên bản mới, nguồn2S hoặc cơ khí xe.
