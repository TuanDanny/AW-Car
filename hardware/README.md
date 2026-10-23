# Phần cứng

Nơi lưu BOM có mã linh kiện, bảng chân, sơ đồ nguồn, cơ khí và thiết kế PCB.

Trạng thái: đang chọn linh kiện, chưa có nguyên mẫu. Bản đầu dùng 2 ESP32-S3,
1 FPGA và 1 mic. Chưa chốt/mua board FPGA; xem [kế hoạch chọn chip và board](../docs/fpga-drive-plan.md).
Chốt dòng kẹt motor, driver, sạc/BMS, các rail, mức logic GPIO và mạch khóa driver
khi reset/mất nguồn/chưa cấu hình FPGA trước khi mua. FPGA không cấp công suất
trực tiếp cho motor. Servo và loa vẫn cần nguồn/khối công suất tương ứng.
Chỉ tách thư mục BOM/schematic/PCB khi có tài liệu thực tế để lưu.
