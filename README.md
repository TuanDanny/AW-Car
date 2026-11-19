# AW-Car

Xe 4WD hai bên độc lập. **Web → Motion → SPI → Tang Nano9K → DRV8833** là
đường điều khiển trực tiếp. Brain chạy Xiaozhi, mic, loa và OLED, rồi gửi lệnh
AI sang Motion qua UART. Manual hoạt động qua AW-CAR tại `192.168.4.1`.
Wi-Fi router phục vụ Xiaozhi, OTA và log.

[Bản hiện hành, mốc nghiệm thu và phần cứng chờ bổ sung](docs/current-release.md)
ghi mã nguồn và mã firmware của cả ba board. `main` là nhánh chính thức.
`prototype-v1` và `prototype-v2` là hai mốc phục hồi.

| Thư mục | Nội dung |
| --- | --- |
| [esp](esp/README.md) | Firmware Brain, Motion và giao thức C++ dùng chung |
| [fpga](fpga/README.md) | SPI, PWM và encoder SystemVerilog trên Tang Nano9K |
| [schematic](schematic/README.md) | Bản vẽ đấu nối tham chiếu |
| [docs](docs/README.md) | Hướng dẫn, contract và lịch sử kiểm chứng |
| [data](data/README.md) | Vector giao thức và bằng chứng đã lọc |
| [utils](utils/README.md) | Build, kiểm tra, OTA và thu log |
| [test](test/README.md) | Kiểm thử host, trình duyệt và RTL |

Bắt đầu từ [Dashboard](docs/dashboard.md), [OTA và log](docs/ota-usage.md)
hoặc [hướng dẫn build](docs/build.md). Đọc [contract](docs/protocol.md)
trước khi đổi giao thức và [bảng chân đang chạy](docs/current-release.md#chân-cảm-biến-và-phần-cứng-chờ-bổ-sung)
trước khi đi dây.
