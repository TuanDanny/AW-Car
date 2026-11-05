# Phần cứng

TT 4WD, hai nhóm trái/phải, hai ESP32-S3, Tang Nano 9K, một INMP441 và OLED
I²C. Encoder một OUT mỗi bên; motor TT được shop xác nhận loại 9V. Không
dùng servo lái. Cấu hình nguồn dự kiến pack 2S tới VM DRV8833, rail logic riêng;
vẫn cần đo dòng kẹt/nhiệt và chọn BMS/sạc/cầu chì phù hợp.

- [Bảng dây Motion và hai đường permit](motion-wiring.md): GPIO, UART,
  trình tự kiểm tra gate/E-stop và giới hạn bản driver-LOCKED.
- [Kế hoạch toàn hệ thống](../docs/fpga-drive-plan.md).

Đã có board nhưng chưa ghép gate/motor/UART vật lý. FPGA không cấp công suất
motor; OUT encoder 5V phải chuyển mức. Xác minh bank 3,3V/1,8V theo chân Tang.
Chỉ tách thư mục BOM/schematic/PCB khi có tài liệu thực tế để lưu.
