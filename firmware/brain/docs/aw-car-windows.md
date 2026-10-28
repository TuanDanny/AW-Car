# Build và nạp Brain trên Windows

Source Xiaozhi của F03 là project ESP-IDF C/C++, dùng ESP-IDF 6.1.
Arduino IDE không biên dịch trực tiếp project này thành sketch Arduino.

## Môi trường đã thiết lập

- ESP-IDF: C:\Espressif\frameworks\esp-idf-v6.1, tag v6.1.
- Toolchain/cache/virtualenv: C:\Espressif.
- Python của IDF: C:\Espressif\python_env\idf6.1_py3.13_env\Scripts\python.exe.
- Chip đã đọc thực qua COM3: ESP32-S3 rev 0.2, flash 16 MB, PSRAM 8 MB.
- USB-Serial/JTAG tích hợp; số COM có thể thay đổi khi cắm lại hoặc đổi máy.
- Profile: bread-compact-wifi-128x64; OLED SDA=41, SCL=42.

SDK và dependency tải về ở ngoài Git. File dependencies.lock nằm trong
firmware/brain cần được giữ để các lần build dùng cùng phiên bản component.
Không sửa managed_components để lưu thay đổi ứng dụng.

## Mỗi lần mở PowerShell mới

Từ root AW-Car:

```powershell
$env:IDF_TOOLS_PATH = 'C:\Espressif'
$env:PYTHONUTF8 = '1'
$env:CMAKE_NINJA_FORCE_RESPONSE_FILE = '1'
. C:\Espressif\frameworks\esp-idf-v6.1\export.ps1
Set-Location firmware/brain
idf.py --version
```

Build lần đầu/chọn lại profile:

```powershell
python scripts/build.py bread-compact-wifi --name bread-compact-wifi-128x64
```

Response file tránh giới hạn dòng lệnh Windows khi project có nhiều include
directory. Nếu build cũ gặp CreateProcess / command line too long, giữ các
object đã tạo và chạy:

```powershell
idf.py -DCMAKE_NINJA_FORCE_RESPONSE_FILE=ON reconfigure build merge-bin
```

Sau khi đã có đúng cấu hình, build tăng dần bằng:

```powershell
idf.py build
idf.py merge-bin
```

Image tổng ở build/merged-binary.bin; app riêng ở build/xiaozhi.bin.
Compile firmware chưa thay thế kiểm thử trên board hoặc nghiệm thu giọng nói.

## Địa chỉ nạp

File **merged-binary.bin** bắt đầu ở **0x0000**, gồm bootloader, bảng phân
vùng, app và assets. App riêng của profile này ở 0x20000 theo bảng phân vùng.

```powershell
python -m esptool --chip esp32s3 --port COM3 --baud 921600 write-flash 0x0000 build/merged-binary.bin
```

Ghi toàn bộ merged image có thể ghi lại NVS. Trong lần thử trên máy chủ dự án,
đã đọc bản sao 16 MB trước khi nạp; bản đã ghi giữ vùng NVS cũ vì
bảng phân vùng trùng nhau. Các file có cấu hình thiết bị/Wi-Fi phải giữ cục
bộ ở build/, không commit hoặc upload lên GitHub.

Khi phát triển tăng dần, ESP-IDF có thể tự dùng đúng từng offset từ flash_args:

```powershell
idf.py -p COM3 flash monitor
```

Lệnh này nạp các image trong danh sách flash_args, thông thường giữ NVS.
Kiểm tra danh sách đó trước khi dùng nếu thêm image NVS hoặc đổi bảng phân vùng.
Thoát monitor bằng Ctrl+]. Mỗi thời điểm chỉ để một chương trình giữ cổng COM.

## Phạm vi kết quả

Lần thử ngày 29/10/2026 trên nhánh feat/f03-xiaozhi-ai, source tại commit
bc5f05e; không sửa logic C/C++ hoặc pinout để build. Bản đầu gặp giới hạn
dòng lệnh Windows khi compile project_elf_src_esp32s3.c; bật response file
đã giải quyết, build/merge-bin kết thúc với exit code 0.

| Hạng mục | Bằng chứng |
| --- | --- |
| SDK / app | ESP-IDF v6.1 / Xiaozhi 2.5.2 |
| Compile time trong app | 29/10/2026 00:04:12 |
| App riêng | 2.577.536 byte, còn khoảng 38% phân vùng app |
| Merged image từ build | 8.949.619 byte |
| SHA-256 merged nguyên bản | 14927599fee3e7038fc130c14cfa18a198171e8c140a99df6e988bd1cfc2d977 |
| ELF SHA-256 | 61608896dbf67306b96bdf7b37bc91fda1b9a465073680259a257530dd69309c |
| Địa chỉ nạp | 0x0000, esptool 5.6.0 qua COM3; hash ghi đã xác minh |
| Cấu hình thiết bị | NVS cũ giữ nguyên; bootloader/app/assets lấy từ build mới |
| Log boot | App 2.5.2, thời gian build và tiền tố ELF SHA khớp |
| PSRAM / OLED | Nhận PSRAM 8 MB, SSD1306 khởi tạo và bật hiển thị |
| Audio / Wi-Fi | Simplex I²S và codec khởi tạo, đã kết nối Wi-Fi |
| Theo dõi 45 giây | Không ghi nhận Guru Meditation/abort/assert/backtrace |
| Xác nhận người dùng | OLED hiển thị xiaozhi.me kèm mã kích hoạt |
| Sau mã kích hoạt | Người dùng báo đã hoàn tất thao tác; chưa thu được log chuyển sang idle |
| Chưa nghiệm thu | Mic chưa gắn; người dùng để kiểm thử thu/phát âm và hội thoại cho lần sau. UART Brain–Motion chưa có |

Nạp dùng bản merged chỉ thay vùng NVS 0x9000 dài 0x4000 bằng bản sao từ
thiết bị; đã đối chiếu bảng phân vùng trùng nhau và byte ngoài vùng đó giữ
nguyên. Esptool thêm padding căn chỉnh ở cuối khi ghi. Mã kích hoạt và thông
tin Wi-Fi không được lưu trong tài liệu hoặc commit.

Binary tự build khác hash release. Kết quả trên chứng minh build/nạp/boot
của bản mới, chưa chứng minh tái tạo bit-for-bit binary phát hành hoặc hoàn
thành tính năng AI.

Build log và dữ liệu thiết bị nằm trong build/ tại root, image/ELF/map ở
firmware/brain/build/. Kết quả nạp/boot của lần thử hiện tại được ghi trong
README Brain khi có bằng chứng từ log; hiển thị thực và chất lượng mic/loa
cần đối chiếu thêm với người sử dụng.
