# Nguồn tham khảo và lựa chọn

| Phần | Nền/phiên bản | Phần sử dụng và đánh giá |
| --- | --- | --- |
| Brain | [78/xiaozhi-esp32 v2.5.2](https://github.com/78/xiaozhi-esp32/tree/49b4380b3faa0ceadd28a3e78aaf0f311c46c57e), MIT | Giữ audio/OLED/MCP/cloud đã chạy, chọn một board; không nhập framework Web/điều khiển cũ. Chi tiết ở esp/brain/UPSTREAM.md. |
| SDK | ESP-IDF6.1, local HEAD fff9895c82d744c7237be8847347bdd1b07c6643 | Driver SPI/UART/HTTP/Wi-Fi chính thức; examples WebSocket/SoftAP là public-domain/CC0, SDK chủ yếu Apache2.0. |
| PID | [pms67/PID](https://github.com/pms67/PID/tree/b871f94ebbeba8879304af916bfd63b07630f270), MIT | Tham khảo công thức PID có clamp và đạo hàm trên measurement; bản C++ gọn tự chứa, chưa bật trên xe. Không thêm Arduino chỉ để lấy thư viện PID. |
| SPI | [nandland/spi-slave](https://github.com/nandland/spi-slave/tree/e12af3489df78d30dd745b00d163a3848bdcea69), MIT | Tham khảo mode0/MSB/CS và test; không copy thiết kế clock SCLK/CDC. RTL simplev1 tự oversample bằng27MHz, .sv thuần. |
| PWM/encoder | AW-Car target nhánh đã thử308cf5a | Tái dùng kinh nghiệm pinout/POR/PWM/encoder; không nhập Safety FSM/Gate/UART-v2 cũ. |

SPI1MHz/32byte mất256us **trên dây**. Polling/noDMA/một task sở hữu bus phù hợp
giao dịch nhỏ; xem [SPI master ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/peripherals/spi_master.html).
Không dùng Fmax FPGA, thời gian wire hay số đo localhost để suy độ trễ toàn xe.
