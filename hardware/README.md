# Phần cứng

Nơi lưu BOM có mã linh kiện, bảng chân, sơ đồ nguồn, cơ khí và thiết kế PCB.

**Cập nhật 01/11/2026:** bốn motor TT của xe là bản **9 V theo thông tin shop
do chủ dự án cung cấp**; chưa có mã/datasheet hoặc phép đo dòng kẹt tương ứng.
Các ví dụ nguồn 6 V/6,5 V trước đây không dùng làm định mức của bộ motor này.

Phương án pin/converter cần chốt lại: Li-ion 2S sạc 4,2 V/cell đầy là 8,4 V,
nên 2S + buck không tạo được rail motor 9 V. Nếu cần rail 9 V ổn định, đánh giá
2S + boost/buck-boost hoặc 3S + buck 9 V đủ dòng; chưa tự đổi lựa chọn mua pin.
3S đầy 12,6 V không được nối trực tiếp vào DRV8833 vì dải VM hoạt động chỉ
2,7–10,8 V theo [TI](https://www.ti.com/product/DRV8833). Nguồn và driver phải
được đánh giá theo dòng khởi động/kẹt, nhiệt và quá độ của đúng motor 9 V.

Trạng thái: đang chọn linh kiện, chưa có nguyên mẫu. Bản đầu dùng 2 ESP32-S3,
1 FPGA và 1 mic. Chưa chốt/mua board FPGA; xem [kế hoạch chọn chip và board](../docs/fpga-drive-plan.md).
Chốt dòng kẹt motor, driver, sạc/BMS, các rail, mức logic GPIO và mạch khóa driver
khi reset/mất nguồn/chưa cấu hình FPGA trước khi mua. FPGA không cấp công suất
trực tiếp cho motor. Loa vẫn cần nguồn/khối công suất tương ứng.
Chỉ tách thư mục BOM/schematic/PCB khi có tài liệu thực tế để lưu.
