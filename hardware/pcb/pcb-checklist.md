# PCB AW-Car — tiêu chí chuyển concept thành PCB có thể sản xuất

## 1. Bố trí khuyến nghị (ảnh và CAD v0.3)

| Hạng mục | Vị trí concept (X, Y, Z mm) | Lý do |
| --- | --- | --- |
| Pack 2S1P + BMS đóng kín | (0, 0, 25) | Gần tâm, hạ trọng tâm, tránh bốn motor |
| PDB (chưa có mạch) | (-83, +22, 68) | Gần phân phối nguồn phía trước tầng giữa |
| Buck logic | (-40, -20, 67) | Xa buck motor, ngắn tới bo điều khiển |
| Buck motor | (+24, -16, 67) | Đường nguồn VM ra hai bên driver |
| Safety gate độc lập | (+86, 0, 70) | Gần đường khóa chung driver, dễ kiểm thử |
| Carrier mạch điều khiển | (0, -2, 98,2) | Khung đỡ trên, nhóm các mạch số |
| Brain / Motion | (-38,-23,109) / (-38,+17,109) | Gần nhau, đầu cắm debug có không gian |
| Tang Nano 9K | (+33,-13,110) | Gần Motion và cổng điều khiển hai driver |
| DRV8833 trái / phải | (+84,+39,104) / (+84,-39,104) | Công suất ở mép, đường motor ngắn |
| Mic / OLED / E-stop | phía trước | Giao tiếp thuận tiện, E-stop thấy/chạm được |
| Loa | (+105,0,106) phía sau | Xa mic, có chỗ hướng lỗ thoát âm |

Trục X âm là trước xe; Y dương là bên trái; Z đo từ mặt sàn trong mô hình.
Số đo vị trí chỉ phục vụ cân đối bố cục, chưa xác nhận được gá bằng vít.

## 2. Điều kiện tiên quyết trước khi đặt PCB

- [ ] Chụp/đo đủ hai tấm acrylic, các lỗ và khoảng cao thực, cùng cột đồng.
- [ ] Xác nhận PCB và pinout hai ESP32-S3, vị trí anten, cổng USB/BOOT.
- [ ] Xác nhận FPGA Nano 9K đúng revision, 3,3 V/1,8 V từng bank và pin .CST.
- [ ] Xác nhận module DRV8833 thật: chip package, VM, GND, INx, nSLEEP,
      thermal, current sense/FAULT có/không; không dùng chung output H-bridge.
- [ ] Xác nhận encoder V2, đĩa mã, module dịch mức và tín hiệu OUT trên oscilloscope.
- [ ] Chọn pack 2S/BMS/sạc/đầu nối/cầu chì/công tắc/công suất buck theo dòng
      đo thực tế, nhiệt và vùng Vin thấp; không từ mAh suy ra dòng xả.
- [ ] Sơ đồ điện đầy đủ có reference designators, pin #, net names, pull-up,
      tụ lọc, điểm đo, an toàn power-on default. KiCad ERC không lỗi.
- [ ] DRC theo nhà sản xuất, clearance, nhiệt, copper width/copper weight,
      vị trí mounting/antennas/USB/test point xác minh từ footprint.
- [ ] Thử motor ở bàn test từng kênh, tính dòng rẽ/skid-steer; E-stop cắt
      cả bốn motor cả khi MCU/FPGA ngừng hoạt động.

## 3. Tối ưu đi dây và độ mượt

1. **Nguồn:** đường pack->cầu chì ngắn, hệ nguồn hai nhánh motor/logic,
   dây dòng lớn đi sát mép riêng theo cặp dương/hồi, không trở lại qua GND ESP32.
2. **PCB signal:** carrier chỉ xử lý 5 V/3,3 V, UART/CRC, encoder đã dịch mức,
   I²C/I²S. Chừa vùng anten theo hướng board thật; không vẽ trace dưới
   anten; tách I²S mic khỏi VM/PWM và dây loa công suất.
3. **Driver:** bulk/decoupling sát VM/GND, copper/via tản nhiệt tùy package,
   driver hai bên xe, 4 đầu ra tách biệt, dây xoắn đôi khi phù hợp để giảm
   vòng nhiễu, cố định tránh đĩa encoder.
4. **Gá cơ khí:** USB nạp còn cắm được khi lắp tầng trên, tháo pin không
   cần tháo cả xe, dây có strain relief và đầu nối được dán nhãn trên PCB.
5. **Điều khiển:** PID theo 2 nhóm trái/phải, anti-windup và ramp setpoint,
   độc lập với E-stop/watchdog. Không coi PCB đẹp là đủ để chạy mượt.

## 4. Bản vẽ cuối phải xuất gì?

- `*.kicad_sch` có netlist pin-level và safety-gate schematic rõ ràng.
- `*.kicad_pcb` đúng footprint, vị trí, màn hình 3D, giữ khoảng anten,
  test point, silkscreen `AW-CAR`, `BRN`, `MTN`, `FPGA`, `M-L/M-R`, phiên bản.
- DRC/ERC + đo trace width/đồng theo tải, BOM theo đúng SKU, Gerber/Drill.
- Checklist đầu nối và dây thực tế, hình 3D đối chiếu vị trí, biên bản bench.

**Hiện chưa có các tệp chế tạo ở trên.** Các hình SVG/PNG hiện tại không
chỉ định sơ đồ điện chân và không được dùng để đặt nhà máy PCB.
