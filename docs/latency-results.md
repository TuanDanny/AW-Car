# Độ trễ điện thoại ngày10/11/2026

Lượt ban đầu: Motion `simplev1-2f131b1123c6`, Brain `simplev1-814afb90103b`.
Điện thoại nối AW-CAR; laptop giữ mạng router và ghi COM3/COM7 trong300giây.
VM ngắt, chưa motor. Người dùng bấm tự do khá nhiều:92mẫu xác nhận được giữ,
không phải phép thử1.000click hoặc soak30phút. Bắt đầu30%, về sau console có
duty1175/1350; gộp số đo thời gian, không dùng để hiệu chuẩn tốc độ.

| Hướng | Mẫu | Bấm→STATUS p50 | p95 | Max |
| --- | ---: | ---: | ---: | ---: |
| Tiến | 27 | 79,5ms | 151,2ms | 221,4ms |
| Lùi | 25 | 57,1ms | 115,3ms | 148,4ms |
| Quay trái | 20 | 72,8ms | 117,3ms | 123,2ms |
| Quay phải | 20 | 73,5ms | 111,0ms | 140,8ms |

Gộp92mẫu: bấm→gửi p50=9,7ms/p95=17,7ms; bấm→STATUS p50=69,8ms,
p95=125,2ms, p99/max=221,4ms. STATUS poll100ms. Số đo gồm chờ dispatch của
browser; không quy toàn bộ thành xử lý ESP hoặc độ trễ chiều đi.

Motion ghi501input; cửa sổ256input cuối: mailbox→trước SPI p50=0,253ms,
p95=0,457ms, p99=0,668ms; max từ boot=2,045ms. Đây là counter nội bộ chung,
không phải501trace tương quan từng click. Đạt ngân sách nội bộ p99≤3ms/max≤10ms.

**Chưa đạt toàn bộ budget chẩn đoán đề xuất:** dispatch p95 vượt10ms; riêng
Tiến STATUS p95 vượt150ms và một mẫu vượt200ms. Không nới budget sau khi đo.
Chưa đo cạnh PWM hoặc chuyển động motor.92mẫu chỉ là các lượt đã xác nhận;
không có tổng số click/hủy từ điện thoại nên không suy ra tỉ lệ giao lệnh.

Console không có panic/watchdog/backtrace ở hai board; các dòng nhả/STOP được
quan sát về0, GPIO10LOW. Không suy log lấy mẫu thành bằng chứng mọi lần nhả.
Cửa sổ SPI206,656giây trong lượt đầu có1.955frame bị loại và1.991ACK lệch,
0lỗi API SPI. Đây là điểm cần xử lý riêng, không được mô tả là bus sạch.

Số liệu lọc ở [latency-phone.json](../data/latency-phone.json). Log thô riêng tư
không vào Git. Công cụ/timestamp/giới hạn ở [cách đo](latency-measurement.md).

## Phép thử CS riêng

Đọc driver/header ESP-IDF6.1 và [tài liệu chính thức](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/peripherals/spi_master.html)
cho thấy không nên dựa vào cs_ena_pretrans như bảo đảm setup cho full-duplex.
Đã thử đúng một thay đổi: GPIO5 tự tạo setup/hold/gap2µs, vẫn mode0/1MHz,
wire32byte/CRC và timeout giữ nguyên, không đổi FPGA/dây. Bản thử
`simplev1-a033c4cdd245` chạy150giây, idle/VM ngắt, vẫn tăng frame/ACK lỗi.
**Không chứng minh CS là nguyên nhân và không giữ bản thử trong source cuối.**
Đã phục hồi source `simplev1-2f131b1123c6`, nạp/đọc ngược lại; image có thể khác
SHA lần đầu do metadata commit/build, source ID giữ nguyên. Không dùng mẫu điện
thoại trước để khẳng định có một phép đo điện thoại mới sau lần nạp phục hồi.

Vì lỗi SPI chưa được khoanh vùng, số đo92mẫu chỉ nghiệm thu đường setpoint có
phản hồi. Cần đo bus/tín hiệu vật lý riêng trước khi kết luận độ tin cậy toàn
chuỗi; không bỏ CRC hoặc tăng timeout để đổi kết quả thành PASS.
