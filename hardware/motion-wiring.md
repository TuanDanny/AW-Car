# Đấu nối Motion — mốc vòng hở

Chủ dự án xác nhận Motion COM7 và Tang Nano9K ngày03/11/2026. Đã đọc được
ESP32-S3 rev0.2/flash16MB/PSRAM8MB. Bảng là profile phần mềm, chưa thay xác
nhận header/dây/điện áp thực. TT9V theo shop, pack2S cấp VM DRV8833; logic riêng.

| Motion ESP32-S3 | Nối tới | Khi boot |
| --- | --- | --- |
| TX17/RX18 UART1 | Brain RX18/TX17 | BM-v1,115200 8N1 |
| TX15/RX16 UART2 | FPGA RX/TX bank3,3V | v2,115200 8N1 |
| GPIO4 motion_permit | FPGA logical permit | LOW |
| GPIO5 recovery_req | FPGA request | LOW |
| GPIO6 | FPGA recovery_ack | Input pull-down |
| GPIO7 | FPGA fpga_permit | Input pull-down |
| GPIO8 | safety_ok từ mạch E-stop/nguồn | Input pull-down, HIGH=khỏe |
| GPIO9 | gate_fault_n từ chốt ngoài | Input pull-down, HIGH=đã clear |
| GPIO10 driver_permit | Mạch gate driver độc lập | LOW |
| GPIO0 BOOT | Nút tại Motion | STOP, không ARM/CLEAR |
| GND | GND logic Brain/FPGA/driver | Không dẫn dòng motor qua dây tín hiệu |

GPIO43/44 dành console CH343; không đổi USB19/20, flash/PSRAM26–37 hoặc
strap3/45/46. Override trùng/không hợp lệ bị chặn khi boot. Pin Tang phải chốt
theo revision/schematic/CST; Nano9K có bank3,3V và1,8V, không đưa UART/GPIO
3,3V vào bank1,8V. OUT encoder5V phải chuyển mức trước FPGA.

## Hai đường cho phép

Gate: `driver_permit AND fpga_permit AND safety_ok AND gate_fault_n`.
motion_permit là tín hiệu logic tới FPGA, không thay driver_permit.
DỪNG hạ driver_permit ngay, gửi DISABLE, đợi STATUS DISARMED mới hạ logical
permit. Lỗi/quá hạn hạ cả hai và chốt lỗi. Giữ guard mất permit của RTL.

Gate/chốt phải tắt khi MCU/FPGA chưa cấu hình, mất clock hoặc mất nguồn.
E-stop độc lập hai MCU/clock FPGA; nhả nút không tự clear/ARM. Không buộc
safety/gate HIGH để chạy demo. GPIO10 cho mạch gate, không mặc định nối
trực tiếp STBY: module có thể kéo chân này lên VM. Xác minh nSLEEP/mức điện;
không đưa VM/5V vào ESP32. Sau gate HIGH giữ duty0 ít nhất1ms rồi mới chạy.
DRV8833 drive/coast, disable không phanh cơ học.

Hai DRV8833, một module mỗi bên; mỗi cầu H cấp một motor riêng. AIN1/BIN1
cùng nhận IN1 bên đó, AIN2/BIN2 cùng nhận IN2; không nối chập đầu ra công suất.
Chỉnh cực dây từng motor khi nâng bánh. Chưa đo dòng kẹt/nhiệt/quãng trôi hoặc
nghiệm thu cú kích100% trên motor thực.

## Trình tự thử

1. LOCKED: console/cấu hình/GPIO LOW, chưa cấp năng lượng motor.
2. Hai UART và GPIO recovery/clear/ARM logic, gate giữ tắt.
3. Xác minh gate/E-stop/nguồn/IO và reset từng board.
4. Đo D/N/W, dòng/nhiệt; build cho phép driver, validated khi DISARMED.
5. Nhấc bánh thử hướng/dừng/đảo/kích có hạn, rồi thử vùng phẳng có kiểm soát.
   Mốc này chưa có cảm biến chống rơi/vật cản.
