# AW-Car simplev1

Skeleton độc lập: **Web → Motion → SPI → FPGA → DRV8833**, Brain chuyên Xiaozhi.

Nhánh `simplev1`, workspace `D:/Project/AW-Car/simplev1`. Giữ nguyên các nhánh cũ.
Manual trước, AI sau, PID viết sẵn nhưng chưa bật. Không dùng ARM/PIN/Gate handshake.

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

Đọc [build/nạp/thu log](docs/build.md) và [báo cáo kiểm chứng](docs/verification.md).
Ngày10/11: Manual bốn hướng và AI quay trái/phải đã có log SPI trên ba board;
cầuB cả haiDRV đã đo đúng cực tính ở100% với VM USB khoảng5V, chưa motor.
PID mặc định tắt. Chưa nghiệm thu cầuA trên bản mới, nguồn2S hoặc cơ khí xe.
