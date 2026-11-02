# AW-Car PCB v0.3 — bố trí bo mạch đẹp, rõ đường dây, chưa sản xuất

Đây là **bản concept điện–cơ** liên kết với CAD xe (ngày 30/10/2026). Mục tiêu:
xe gọn, ít dây chéo, dễ tháo ráp/đo kiểm và không cho nhiễu motor lan vào
AI/FPGA. Tất cả phép đặt mạch đang theo **khối bao hình học giả định**, không
phải kích thước PCB/gá thực tế. **Không gửi Gerber / không đấu Li-ion theo
hình concept này.** Xem kích thước ở `../cad/layout.json`.

## File và cách mở

| File | Công dụng |
| --- | --- |
| `pcb-system-layout.svg` và `.png` | Mặt bằng xe, bố trí carrier, sơ đồ phân nguồn |
| `pcb-routing-corridors.svg` và `.png` | Khu vực đường tín hiệu (không phải trace thật) |
| `connector-contract.csv` | Danh sách connector theo chức năng, chưa gán chân |
| `generate_pcb_concept.py` | Sinh lại ảnh từ CAD v0.3, không cần KiCad |
| `pcb-checklist.md` | Kiến trúc 2 PCB, quy tắc layout và nghiệm thu |

Chạy từ root:

```powershell
python hardware/cad/generate_aw_car.py
python hardware/pcb/generate_pcb_concept.py
python -m unittest discover -s tests -q
```

## Quyết định kiến trúc

**Không đặt động cơ/pin thô lên một motherboard duy nhất.** Dùng hai vai trò
PCB tách rời để dễ kiểm tra và sửa lỗi:

**1. Interface carrier** khoảng **150 × 78 × 1,6 mm** đặt phía trên acrylic,
giữ ESP32-S3 Brain, Motion, Nano9K, IMU và đầu tín hiệu. Chỉ mang nguồn
logic 5 V/3,3 V phù hợp và các tín hiệu nhỏ; nếu lựa chọn motherboard tiếp
điểm header chính xác được xác minh, có thể làm mạch KiCad hai/bốn lớp sau.
Board ESP32 phải đặt anten mép/ngoài carrier hoặc khoét vùng anten đúng hướng;
**mặt bằng hiện chỉ có hình chữ nhật, chưa có lỗ gá/anten keepout thực.**

**2. Power distribution board (PDB)** khoảng **36 × 25 × 1,6 mm** ở tầng giữa,
gần nhánh pin; chia nguồn sau pack/BMS/cầu chì tới motor buck và logic buck.
Đây mới là khối bao, không được coi là bo có khả năng tải 6–8 A. Công suất
qua PCB phải được tính theo stack-up, nhiệt, bề dày đồng, vias, dây và
connector sau khi đo dòng motor; có thể dùng **dây/đầu nối phân phối nguồn**
định mức phù hợp thay cho trace công suất nếu rẻ/an toàn hơn.

**3. Pack thấp, giữa xe:** dự kiến 2S1P hàn sẵn **đã có BMS trong pack**,
không cộng thêm một BMS thứ hai. Lắp hộp/kẹp chống rung cách điện; chưa mua
và chưa có kích thước thật. Cầu chì tổng trên dây pack dương đặt sát pack,
không chuyển xa sang PDB chỉ để đẹp. Dây sạc theo sơ đồ pack/BMS được duyệt.

## Màu/hành lang tín hiệu

- **Đỏ/cam:** pack được bảo vệ -> cầu chì -> switch tổng -> PDB -> buck motor
  -> VM driver trái/phải -> 4 motor. Motor trái/phải **mỗi motor một cầu H**;
  không nối tắt đầu ra driver, không dùng jumper header điều khiển làm dây
  công suất. Dùng cặp dây cấp/return theo cùng tuyến ở mép xe, giữ vòng dòng
  nhỏ, cố định chống va cọ bánh/encoder.
- **Xanh:** logic buck 5 V -> các board qua mạch/đầu nối phù hợp; 3,3 V chỉ
  từ bộ điều áp 3,3 V được xác minh. UART Brain–Motion, UART Motion–FPGA,
  encoder V2 qua level-shift 5 V -> 3,3 V, I²C IMU/OLED/ToF, I²S mic/amp.
  Không chạy song song dài với dây motor/buck hoặc qua vùng anten.
- **Xám:** return/GND có tham chiếu chung cho MCU/FPGA/encoder/driver;
  nhánh motor có đường về phân phối riêng, không đẩy dòng 4 motor qua mass
  USB/ESP32. Không "cắt" mọi ground thành hai mạng hoàn toàn tách biệt.
- **Đỏ safety:** E-stop dạng NC -> gate chốt lỗi OFF -> tước quyền ENABLE của
  **cả hai DRV**, kết hợp Motion permit + FPGA permit ở đường hardware.
  Nhấn/nhả E-stop hoặc mất clock không tự ARM. Phải xác nhận tín hiệu nSLEEP,
  breakouts và trạng thái default khi 3,3/5 V mất hoàn toàn.

## Đúng chuẩn kỹ thuật trước khi PCB thật

1. Chụp cả mặt trước/sau các board ESP32, FPGA, DRV8833, buck, level shift;
   đo kích thước PCB + cổng USB + đầu nối + chiều cao và tọa độ lỗ gá.
2. Với ESP32-S3 anten tích hợp: xác minh *vị trí anten thực*, đặt anten hướng
   ra mép carrier, không phủ đồng/linh kiện bên dưới, kiểm tra khuyến nghị
   vùng thoáng **ít nhất 15 mm** quanh anten ở mức sản phẩm cuối (tùy cấu hình).
   Không suy đoán anten ở bên nào từ tên "R16N8".
3. Sơ đồ điện KiCad cần hoàn thành trước: netlist, power tree, GPIO/bank
   Nano9K **3,3/1,8 V**, điện áp encoder, chi tiết adapter PWM/IN1/IN2,
   latch gate, testpoint, ESD/fuse/sạc; kiểm tra ERC.
4. PCB cần footprint đúng SKU, lớp GND liên tục khi hợp lý, đường motor ngắn,
   tụ VM/GND **sát IC/breakout** theo datasheet, thermal pad/vias (nếu có),
   clearances/dòng theo dòng đo. Kiểm tra DRC/3D fit trước Gerber.
5. Chạy bench từng nhánh nguồn và gate với driver chưa nối motor; rồi đo
   khởi động 1 -> 4 motor có giới hạn dòng. Mạch E-stop phải tự hoạt động
   ngay cả khi FPGA dừng clock. Không chạy test Li-ion trên breadboard.

### Tài liệu tham khảo thiết kế

- Espressif, [ESP32-S3 PCB Layout Design](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html): khuyến nghị vị trí anten, mặt đồng/GND và nhiễu RF.
- Texas Instruments, [DRV8833 datasheet](https://www.ti.com/lit/ds/symlink/drv8833.pdf): bypass VM/GND gần IC, nhiệt PowerPAD và quy tắc PCB.
- Cấu hình nguồn dự kiến ở `../power-plan.md`; phần FPGA/GPIO safety ở
  `../../firmware/shared/fpga-safety.md`.

**Tóm lại:** file này giúp chọn vị trí và xây sơ đồ chính xác, nhưng chưa có
footprints, netlist, trace, Gerber hoặc kết quả kiểm nghiệm tải/nhiệt.
