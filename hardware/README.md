# Phần cứng

Nơi lưu BOM có mã linh kiện, bảng chân, sơ đồ nguồn, cơ khí và thiết kế PCB.

[Giao tiếp DRV8833](drv8833-interface.md): bảng nối bốn chân IN từ FPGA tới
hai module/bốn motor, chế độ drive/coast và điều kiện STBY/mức logic.

**Cập nhật 01/11/2026:** bốn motor TT của xe là bản **9 V theo thông tin shop
do chủ dự án cung cấp**; chưa có mã/datasheet hoặc phép đo dòng kẹt tương ứng.
Các ví dụ nguồn 6 V/6,5 V trước đây không dùng làm định mức của bộ motor này.

**Phương án ưu tiên theo chủ dự án:** pin Li-ion 18650 **2S1P + BMS 2S**,
cấp trực tiếp nhánh motor qua cầu chì/đường dừng tới **VM của hai DRV8833**,
mỗi motor một cầu H. Không cần buck/boost riêng cho nhánh motor ở bản đầu;
9 V là định mức motor, không đặt yêu cầu giữ nguồn motor đúng 9 V.

Pin 2S danh định 7,2–7,4 V, đầy 8,4 V khi sạc 4,2 V/cell; nằm trong dải VM
2,7–10,8 V của [DRV8833 theo TI](https://www.ti.com/product/DRV8833). Điện áp
tới motor còn phụ thuộc PWM và sụt áp cầu H/dây. Cần thử lực khởi động/rẽ khi
pin yếu, dòng khởi động/kẹt, nhiệt driver và quá độ; chưa coi phù hợp mọi tải.
Sạc dùng loại 2S 8,4 V CC/CV phù hợp pack, cầu chì theo dòng/dây thực.

Nhánh ESP32/FPGA/âm thanh vẫn qua nguồn ổn áp riêng, dự kiến buck 5 V đúng
đầu vào từng board; chung GND theo phân phối phù hợp, không cấp điện áp pack
vào GPIO hoặc các chân nguồn thấp áp. Tụ lọc đặt gần VM driver vẫn cần thiết.

Trạng thái: đang chọn linh kiện, chưa có nguyên mẫu. Bản đầu dùng 2 ESP32-S3,
1 FPGA và 1 mic. Chưa chốt/mua board FPGA; xem [kế hoạch chọn chip và board](../docs/fpga-drive-plan.md).
Chốt dòng kẹt motor, driver, sạc/BMS, các rail, mức logic GPIO và mạch khóa driver
khi reset/mất nguồn/chưa cấu hình FPGA trước khi mua. FPGA không cấp công suất
trực tiếp cho motor. Loa vẫn cần nguồn/khối công suất tương ứng.
Chỉ tách thư mục BOM/schematic/PCB khi có tài liệu thực tế để lưu.
