# Kiểm tra hai binary Xiaozhi ở root

**Cập nhật trạng thái02/11/2026:** báo cáo bên dưới giữ phép đối chiếu binary
ngày28/10. Source đã được build/nạp và thử mic/OLED/AI điều khiển RGB trên
[nhánh AI](https://github.com/TuanDanny/AW-Car/tree/feat/f03-xiaozhi-ai/firmware/brain);
không dùng các mục chưa triển khai trong báo cáo lịch sử để phủ nhận bản đã thử.
Binary chỉ giữ cục bộ, không đưa vào Git.


Ngày kiểm tra: 28/10/2026. Agent đọc file/phân tích và đối chiếu bản phát
hành công khai; không kết nối, xóa flash hoặc nạp board. Giữ nguyên hai file
gốc, không commit binary. Chủ dự án sau đó xác nhận đã tự nạp bản S3,
thử OLED ở GPIO 41/42 và màn hình đã hiển thị; đây là kết quả người dùng
báo lại, chưa phải phép đo trực tiếp của agent.

## Kết quả nhận diện

| Trường | merged-binary-esp32s3.bin | merged-binary.bin |
| --- | --- | --- |
| Dung lượng file | 8.949.609 byte | 3.415.609 byte |
| Chip ID trong header | 9, ESP32-S3 | 0, ESP32 thường |
| Project / version app | xiaozhi / 2.5.2 | xiaozhi / 2.5.2 |
| Build app | 11/10/2026, 18:42:07 | 11/10/2026, 18:47:20 |
| ESP-IDF ghi trong app | v6.1 | v6.1 |
| Profile đọc từ chuỗi binary | bread-compact-wifi-128x64 | bread-compact-esp32-128x32 |
| Flash trong header | 16 MB, DIO, 80 MHz | 4 MB, DIO, 40 MHz |
| Bootloader trong merged file | 0x0 | 0x1000 |
| App trong merged file | ota_0 ở 0x20000 | factory ở 0x10000 |
| Checksum/hash bootloader và app | Hợp lệ | Hợp lệ |

Đã tách đúng các image con trong thư mục build bị ignore và kiểm tra bằng
`esptool 5.6.0 image-info`, đồng thời đối chiếu checksum/hash qua parser
offline theo định dạng image Espressif. Cài công cụ phân tích chỉ trong
build, không thêm dependency vào dự án hoặc thay môi trường global.
Các byte NVS/assets chưa được nghiệm thu chức năng. Checksum/hash image
khớp không chứng minh nhà phát hành, chữ ký tin cậy hoặc boot được trên xe.

SHA-256 của toàn file để đối chiếu bản sao:

- S3: `933f2219153b0e2e22ce3833ecf3091631bbffb7181a963a1f7cf011c65533be`.
- ESP32: `3e0a65a0bb6e13640b969449d964874727bec886793f69dfc1bfa494561df7ee`.

## Điều kiện dùng cho Brain AW-Car

File có hậu tố esp32s3 đúng dòng chip mục tiêu. File không hậu tố dùng
ESP32 thường, không thay cho bản S3. Bản S3 có phân vùng assets từ
0x800000 dài 0x800000, kết thúc tại 16 MB; không suy từ file khoảng
8,53 MiB rằng board flash 8 MB dùng được.

Chủ dự án ghi board là R16N8; chưa xác nhận đó là N16R8 hay biến thể khác.
Cần nhận diện flash thực tối thiểu 16 MB cho bảng phân vùng này, PSRAM,
revision chip và pinout board trước khi thay cấu hình hoặc tích hợp thêm. Việc
đã boot/hiển thị không xác nhận toàn bộ vùng flash/PSRAM. Header không xác nhận RAM/PSRAM
8 MB. Mặc định nguồn upstream v2.5.2 cho S3 dùng OPI PSRAM, nhưng chưa có
sdkconfig/ELF của đúng binary để khẳng định mọi tùy chọn build giống tag.

Profile S3 nhận diện 128x64, binary có các hàm/chuỗi SSD1306. Upstream
v2.5.2 ánh xạ profile này tới SSD1306 I²C 128×64, địa chỉ 0x3C. Chủ dự án
đã xác nhận màn hình 0,96 inch I²C hiển thị khi nối GPIO 41/42. Cấu hình
nguồn tương ứng là SDA=41, SCL=42; chưa đo địa chỉ bus hoặc đọc mã IC để
xác nhận riêng controller vật lý/độ phân giải.
INMP441 và MAX98357A phù hợp hướng audio I²S của profile, vẫn cần xác minh
nguồn, cực tính, kênh mic và chân thực trước đấu.

## GPIO tham khảo từ upstream v2.5.2

Bảng này đọc từ config.h cùng profile/tag, **chưa phải GPIO đã đo hoặc
giải mã chắc chắn từ machine code của file local**. Không coi là pinout
đã phê duyệt cho hai board đang có hoặc cho UART Brain–Motion.

| Chức năng | GPIO tham khảo |
| --- | --- |
| Mic I²S WS / SCK / DIN | 4 / 5 / 6 |
| Loa I²S DOUT / BCLK / LRCK | 7 / 15 / 16 |
| OLED SDA / SCL | 41 / 42; người dùng xác nhận hiển thị với cặp GPIO này |
| BOOT / touch / volume up / volume down | 0 / 47 / 40 / 39 |
| LED / lamp demo | 48 / 18 |

Đây là firmware Xiaozhi dựng sẵn tham khảo. Chưa có bằng chứng hỗ trợ
giao thức lệnh Brain–Motion/FPGA của AW-Car. Vẫn chưa có mã nguồn firmware
tích hợp AW-Car trong repo; đã có xác nhận hiển thị OLED từ người dùng,
chưa có kết quả nghiệm thu thu/phát âm, mạng hoặc an toàn
trên phần cứng. Không đưa PWM motor vào binary stock hoặc coi nạp file
là hoàn tất firmware Brain.

## Khả thi lấy lại source từ binary

### Kết luận cho đúng file đang có

Không thể khôi phục nguyên vẹn project C/C++ ban đầu chỉ bằng đổi `.bin`
sang `.cc`: quá trình biên dịch/tối ưu đã bỏ comment, macro, nhiều tên biến,
kiểu dữ liệu và cách tổ chức source. Có thể disassemble Xtensa và decompile
ra mã giả để nghiên cứu một số hàm, nhưng mã giả không phải project có thể
build lại ngay. Log còn tên hàm/file không có nghĩa binary chứa đủ source
hoặc đầy đủ symbol/debug như ELF.

**Trường hợp này có đường khả thi hơn: đã tìm được mã nguồn công khai mà
upstream công bố dùng cho đúng firmware chính thức trùng file local.**
Đã tải ZIP đúng variant, xác minh digest ZIP với GitHub API và SHA256SUMS,
rồi giải nén và so sánh trực tiếp toàn bộ byte với file ở root:

| Bằng chứng | Kết quả |
| --- | --- |
| Release / variant | v2.5.2 / bread-compact-wifi-128x64 |
| ZIP phát hành | v2.5.2_bread-compact-wifi-128x64.zip, 1.959.385 byte |
| SHA-256 ZIP | c591d3d6ab98cb82f1c920b07a5a886f806c5d8d3aff7bcd50c44717c37d538e |
| File bên trong ZIP | merged-binary.bin, 8.949.609 byte |
| SHA-256 binary chính thức và local | 933f2219153b0e2e22ce3833ecf3091631bbffb7181a963a1f7cf011c65533be |
| So sánh trực tiếp byte | Trùng hoàn toàn |
| Source commit trong release manifest | 49b4380b3faa0ceadd28a3e78aaf0f311c46c57e |
| ESP-IDF theo release manifest/workflow | 6.1.0 / image espressif/idf:v6.1 |
| Nội dung ZIP firmware | Chỉ có merged-binary.bin, không có ELF/map/sdkconfig |

Hash trùng và phép so sánh byte xác nhận file local là cùng binary với
attachment đã kiểm tra; source commit được xác định theo manifest của
upstream. Chưa tự build source để chứng minh khả năng tái tạo binary giống
từng byte. Việc này còn phụ thuộc toolchain, dependency, asset và metadata
build. Kết quả đối chiếu áp dụng file root, chưa đọc lại flash/OTA trên board.

### Source đã tải để nghiên cứu

Bản snapshot theo commit trên được tải và giải nén trong thư mục bị ignore:

```text
build/firmware-inspection/upstream-v2.5.2/
  comparison.json
  release-manifest.json
  SHA256SUMS
  source-download.json
  xiaozhi-esp32-49b4380b3faa0ceadd28a3e78aaf0f311c46c57e/
```

Snapshot có 1.740 file từ kho upstream, giữ nguyên LICENSE. Không đưa source
tham khảo vào firmware/brain hoặc commit dependency mới trong tác vụ này.
Đây không phải mã decompile hoặc firmware AW-Car đã tích hợp; component
ngoài kho và asset/model có thể vẫn cần được tải khi build.

Các vị trí cần đọc bên trong snapshot:

| Muốn chỉnh | File nguồn |
| --- | --- |
| GPIO OLED/mic/loa/nút | main/boards/bread-compact-wifi/config.h |
| Chọn profile SSD1306 128×64 | main/boards/bread-compact-wifi/config.json |
| Khởi tạo I²C, OLED, audio và các nút | main/boards/bread-compact-wifi/compact_wifi_board.cc |
| Luồng ứng dụng Xiaozhi | main/application.cc |
| Hiển thị OLED | main/display/oled_display.cc |
| Giao tiếp mạng | main/protocols/ |
| Dependency cần giải quyết khi build | main/idf_component.yml |
| Tạo board AW-Car riêng | docs/custom-board.md |

Hướng tiếp theo là dựng lại bản stock trước, giữ OLED 41/42 đã chạy, sau đó
mới thêm board/profile AW-Car và UART Brain–Motion trên nhánh tính năng.
Không chọn chân UART khi chưa đối chiếu toàn bộ GPIO đang dùng. Với bản
custom, dùng danh tính board/variant và chính sách OTA riêng theo hướng dẫn
upstream để giữ đúng cấu hình sau cập nhật.

Lệnh build tham khảo, chạy từ root snapshot trong môi trường ESP-IDF 6.1
đã cài đủ toolchain/dependency:

```sh
python scripts/build.py bread-compact-wifi --name bread-compact-wifi-128x64
```

**Chưa chạy lệnh build này, chưa cài ESP-IDF, chưa chạy Ghidra/decompiler và
chưa thay firmware trên board.** Kết quả nghiên cứu đủ để chọn lấy source
upstream thay vì tái dựng toàn bộ project bằng dịch ngược. Nếu có hàm cần
đối chiếu machine code, có thể dùng Ghidra với Xtensa little-endian 32-bit,
import các segment theo load address của image ESP-IDF; không import nguyên
merged file như một khối code liên tục. Chưa thử luồng này với binary local.

## Nguồn đối chiếu

- [Espressif: image-info](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/esptool/basic-commands.html).
- [Espressif: định dạng image và app descriptor](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/app_image_format.html).
- [Xiaozhi v2.5.2: config.json của bread-compact-wifi](https://github.com/78/xiaozhi-esp32/blob/v2.5.2/main/boards/bread-compact-wifi/config.json).
- [Xiaozhi v2.5.2: config.h, GPIO tham khảo](https://github.com/78/xiaozhi-esp32/blob/v2.5.2/main/boards/bread-compact-wifi/config.h).
- [Xiaozhi v2.5.2: display/audio của profile](https://github.com/78/xiaozhi-esp32/blob/v2.5.2/main/boards/bread-compact-wifi/compact_wifi_board.cc).
- [Xiaozhi v2.5.2: mặc định ESP32-S3/PSRAM](https://github.com/78/xiaozhi-esp32/blob/v2.5.2/sdkconfig.defaults.esp32s3).
- [Release v2.5.2 và source commit](https://github.com/78/xiaozhi-esp32/releases/tag/v2.5.2).
- [ZIP firmware đã đối chiếu](https://github.com/78/xiaozhi-esp32/releases/download/v2.5.2/v2.5.2_bread-compact-wifi-128x64.zip).
- [Release manifest](https://github.com/78/xiaozhi-esp32/releases/download/v2.5.2/release-manifest.json).
- [Hướng dẫn tạo board riêng](https://github.com/78/xiaozhi-esp32/blob/v2.5.2/docs/custom-board.md).
- [Espressif: các điều kiện build tái lập](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/reproducible-builds.html).
- [Ghidra: hỗ trợ Xtensa little-endian 32-bit trong source hiện tại](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Processors/Xtensa/data/languages/xtensa.ldefs).
