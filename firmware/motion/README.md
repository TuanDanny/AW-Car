# Motion — ESP32-S3 MCU 2

ESP-IDF6.1 cho TT4WD, hai nhóm trái/phải, encoder một OUT/bên. Mốc0.1.0 có
hai UART, lease/ARM/STOP/CLEAR, khóa driver độc lập, vòng hở, kích đề-pa và
chờ đảo chiều. PWM do FPGA phát; PI/PID, ToF/TCRT5000/MPU6050 để mốc sau.

**Mặc định ENABLE_DRIVER=n và validated=0: từ chối ARM.** Đã build và kiểm tra
console/GPIO mặc định tắt trên COM7; chưa nối UART Brain/FPGA/gate/motor.
Xem [báo cáo](../../docs/motion-verification.md),
[contract](../../docs/motion-plan.md), [bảng dây](../../hardware/motion-wiring.md).

Nhánh từ main094b37c; RTL trong nền main còn baseline cũ. Motion bắt buộc
**FPGA v2 từ feat/f01-fpga-drive (7ab91b2 khi thử)**, không fallback v1.
Chưa có bitstream/CST/STA Nano9K được nghiệm thu; không dùng RTL v1 để ghép.

## Build

Kích hoạt ESP-IDF6.1, chạy trong thư mục này:

```powershell
idf.py build merge-bin
```

Image `build/merged-binary.bin` nạp tại **0x0000**, sau xác nhận đúng board và
sao lưu flash. Flash16MB, CPU240MHz; PSRAM không dùng, Wi-Fi/BLE không khởi tạo.
Factory app đơn, chưa OTA. NVS riêng motioncfg có version/CRC; không xóa toàn
flash trong ứng dụng. Không dùng backup của Brain để nạp cho Motion.

## Console USB

UART0 115200 trên COM7, tách UART1 Brain và UART2 FPGA:

```text
help
status
config
set track_mm 120
set kick_ms 200
save
load
defaults
stop
```

`set/save/load/defaults` chỉ khi DISARMED, link idle, permit LOW. Save/load
khóa ARM suốt thao tác flash, có transaction ID; set sửa RAM, save mới lưu.
validated=1 còn đòi build cho phép driver; console không thể mở bản LOCKED.
Không có USB ARM/MOVE/CLEAR. BOOT chỉ STOP, giữ nút ngăn tăng quyền.

Status có fault Motion/raw FPGA, phase/duty/count/tốc độ không dấu, heap/stack,
RX→UART và sample_count. Chưa có số đo trả null/invalid, không gán chiều lệnh
thành chiều đo. Log text chỉ ở console, không chen vào UART nhị phân.

## Kiểm thử từ root

```powershell
python tools/build_motion_host.py
python -m unittest discover -s tests
python tools/motion_brain_integration.py --brain-root <checkout-AI>
python tools/motion_rtl_cosim.py --fpga-root <checkout-FPGA> --iverilog <iverilog> --vvp <vvp>
python tools/motion_soak.py --seconds 1800 --output build/motion/soak-final.json
python tools/motion_board_check.py --port COM7 --reset --console-test
```

Host cần C++17, đặt CXX nếu compiler chưa trong PATH. Board check cần Python
SDK với pyserial/esptool; chỉ nhận build LOCKED, thử rồi lưu lại defaults.
Raw log/full flash backup/build ở local ignored; xem nguồn tại [main](main/README.md).
