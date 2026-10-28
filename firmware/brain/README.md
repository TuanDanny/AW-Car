# Brain - F03 AI/Xiaozhi

Nhánh phát triển: **feat/f03-xiaozhi-ai**, tạo từ origin/main ngày 28/10/2026.
MCU Brain dùng ESP32-S3, một INMP441, MAX98357A và OLED 0,96 inch I²C.
Chủ dự án đã nạp binary stock và xác nhận OLED hiển thị với GPIO 41/42.

Source Xiaozhi v2.5.2 được nhập trực tiếp vào thư mục này để có thể sửa,
commit và review trong cùng kho AW-Car. Source commit upstream:
`49b4380b3faa0ceadd28a3e78aaf0f311c46c57e`.
Binary gốc của người dùng trùng từng byte với variant chính thức
`bread-compact-wifi-128x64`; xem [nguồn và phép đối chiếu](UPSTREAM.md).
Giữ toàn bộ source/board upstream để có baseline và chạy bộ host test;
build chỉ chọn một board/variant.

## Trạng thái

Đây là source stock làm nền phát triển, chưa phải firmware AW-Car đã tích hợp.
Chưa tự build/nạp từ source, chưa nghiệm thu mic/loa/Wi-Fi/PSRAM, chưa có
UART Brain–Motion hoặc điều khiển xe. Kết quả hiển thị là do người dùng báo lại.
AI gửi yêu cầu chuyển động có giới hạn tới Motion; không ghi PWM trực tiếp.
DoA giữ cho nâng cấp. Nguồn/bộ nhớ thực của board cần đối chiếu trước khi đổi cấu hình.

## Build bản stock

Mở terminal ESP-IDF 6.1 đã có toolchain ESP32-S3, sau đó chạy từ thư mục này:

```sh
idf.py --version
python scripts/build.py bread-compact-wifi --name bread-compact-wifi-128x64
```

Lệnh trên build và đóng gói, không tự nạp board. Kết quả ở build/ bị ignore.
ESP-IDF Component Manager tải dependency trong main/idf_component.yml;
giữ dependencies.lock khi lần đầu giải quyết dependency thành công. Bản nguồn
upstream chưa kèm lockfile để khôi phục chính xác dependency của release.
Không khẳng định binary build mới sẽ giống từng byte khi toolchain, dependency,
asset hoặc thời gian build khác nhau.

## Chân tham khảo của profile stock

| Chức năng | GPIO |
| --- | --- |
| OLED SDA / SCL | 41 / 42; đã có xác nhận hiển thị |
| INMP441 WS / SCK / DIN | 4 / 5 / 6; chưa nghiệm thu |
| MAX98357A DOUT / BCLK / LRCK | 7 / 15 / 16; chưa nghiệm thu |

Pinout ở [config.h](main/boards/bread-compact-wifi/config.h). Profile chọn
SSD1306 128×64, địa chỉ 0x3C, layout flash 16 MB. Chưa đo riêng mã controller,
địa chỉ bus và toàn bộ bộ nhớ board; không suy thông số bộ nhớ chỉ từ tên R16N8.
Chưa cấp GPIO cho UART mới trước khi lập bảng các chân đang dùng.

## Kiểm tra trên máy

Từ root AW-Car:

```sh
python tools/check_repo.py --feature-branch
python -m unittest discover -s tests
```

Từ firmware/brain:

```sh
python -B -m unittest discover -s scripts/tests -v
```

Host test kiểm tra công cụ build/release và cấu hình; không thay thế compile
ESP-IDF hoặc phép thử audio, mạng và an toàn trên phần cứng.

## Thứ tự phát triển F03

1. Cài/xác nhận ESP-IDF 6.1, build lại profile stock, lưu lockfile và log.
2. Nạp thử khi chủ dự án muốn; kiểm tra OLED, thu/phát âm và kết nối Xiaozhi.
3. Tạo board/variant AW-Car có danh tính và chính sách OTA riêng; giữ baseline
   stock để đối chiếu. Không sửa pinout board upstream để giả làm board mới.
4. Thêm UART Brain–Motion và lớp giới hạn lệnh; kiểm thử mất mạng/mất lệnh
   trước khi thử chuyển động. Driver/PID/FPGA/nguồn thuộc các nhánh riêng.

Hướng dẫn nền: [README upstream](README.upstream.md),
[custom board](docs/custom-board.md), [license](LICENSE).
Quy tắc làm việc duy nhất nằm ở AGENTS.md tại root AW-Car;
UPSTREAM-DEVELOPMENT.md chỉ giữ hướng dẫn kỹ thuật tham khảo.
