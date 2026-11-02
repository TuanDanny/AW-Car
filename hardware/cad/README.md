# AW-Car CAD v0.3 — bố trí mạch/nguồn gọn, CHƯA là bản vẽ gia công

Mục đích: dựng mô hình 3D tham số của bộ TT 4WD theo **ảnh chủ dự án gửi
30/10/2026**, kiểm tra vùng chiếm chỗ,
đường nguồn/tín hiệu và trình tự lắp. Các board/motor là **khối bao hình học**,
không phải STEP của đúng SKU. **Không khoan/cắt acrylic theo bản này** khi
chưa đo lại khung, lỗ gá, kích thước PCB, motor/encoder, pin và E-stop thực.

## Cập nhật theo ảnh xe thực gửi ngày 30/10/2026

- **Hình dáng:** Hai tấm acrylic trong suốt, hai đầu thuôn/bo cong, vùng giữa
  mở rộng và hai bên chừa đường bánh. Bốn TT trục đôi và đĩa mã trong 4 bánh;
  không có servo. Các lỗ tròn/rãnh bắt vít trên ảnh **chưa được truy vết**;
  đường cong CAD là phác họa đối xứng, không phải viền đo từ ảnh phối cảnh.
- **Chiều dài:** 260 mm theo người bán, chưa đo thực.
- **Chiều rộng mâu thuẫn:** đoạn mô tả thứ nhất ghi 155 mm **ngoài hai bánh**;
  đoạn sau lại ghi 260 × 155 mm **không có lốp** và 260 × 175 mm **có lốp**.
  CAD tạm dùng **khung rộng 155 mm, cả lốp rộng 175 mm**, dựa trên mô tả sau.
  Phải đo thực cả hai giá trị trước khi thiết kế gá/khung bảo vệ.
- **Bánh Ø60 mm, rộng 20 mm**, **wheelbase 176 mm**, tâm vệt bánh trái/phải
  155 mm, cao trục 30 mm là **giả định để tạo hình**, không phải thông số shop
  hoặc kết quả đo. Chiều cao hai tầng 43–94 mm cũng là giả định.
- **Vật liệu:** Acrylic mô phỏng xanh nhạt trong suốt; màu vàng/đen TT và
  bánh 5 chấu chỉ là mô hình hình học; 4 đĩa encoder chưa mô phỏng đúng số khe.
- **Pin:** vẫn ưu tiên 2S1P thấp giữa gầm, khoảng hở sơ bộ 14 mm; cần tính
  thêm đầu ốc, dây, gá bảo vệ, võng khung và sàn gồ ghề ngoài thực tế.

## Mở và tái tạo

- `aw_car_assembly.scad`: CAD chỉnh được trong OpenSCAD (mm); chọn View > Show Axes.
- `aw_car_assembly.obj` + `.mtl`: mô hình 3D nhiều màu để xem trong Blender/FreeCAD.
- `aw_car_viewer.html`: mở trực tiếp bằng Edge/Chrome, kéo chuột xoay 3D, đổi
  góc nhìn và ẩn tấm trên; **chạy offline**, không cần CDN/đăng nhập/cài ứng dụng.
- `aw_car_isometric.png`, `aw_car_top.png`, `aw_car_side.png`: ảnh xem nhanh.
- `wiring-plan.svg`: sơ đồ *phân vùng dây*, **không phải schematic điện**.
- `clearance-report.json`: kiểm tra hình học/khối lượng *xấp xỉ*.
- `layout.json`: thông số gốc; sau khi thay phải chạy lại generator.
- `assembly-and-motion-plan.md`: kế hoạch từ cơ khí, nguồn, encoder tới
  firmware PI/PID và tiêu chí chạy thử để đạt chuyển động mượt/an toàn.
- `../pcb/`: bố trí hai PCB (carrier + phân phối nguồn), sơ đồ phân vùng
  tín hiệu/công suất và yêu cầu để chuyển thành thiết kế KiCad thật.

Chạy từ root repository (Python 3.10+, Pillow tùy chọn để xuất PNG):

```powershell
python hardware/cad/generate_aw_car.py
python hardware/cad/generate_aw_car.py --check
```

Script chỉ ghi/kiểm tra tệp trong `hardware/cad/`; `--check` không ghi gì.
Không cần cài OpenSCAD để tạo OBJ/SCAD/SVG. Nếu Python không có Pillow,
vẫn tạo được các tệp khác và in cảnh báo thiếu PNG.

## Quy ước trục và thiết kế

- X: trước âm (-X), sau dương (+X); Y: trái dương (+Y), phải âm (-Y);
  Z: thẳng đứng, mặt sàn = 0. Tất cả kích thước tính bằng mm.
- 4 TT motor quay bánh cố định, hai nhóm trái/phải, **không có servo**.
- Pin 2S1P ở chính giữa *dưới* tấm đáy, không đặt ngang vùng 4 motor.
  Khoảng hở mặt đất và cách gá pin phải đo, chống rung và che cell.
- Pack 2S1P đã có BMS bên trong vỏ pack (không dựng BMS thứ hai ngoài pack).
- Tầng dưới: motor và pack; tầng giữa: bo phân nguồn PDB, buck motor, buck
  logic, gate độc lập. Tầng trên: **carrier PCB 150×78 mm** giữ Brain/Motion/
  Nano9K, hai DRV8833 bố trí ngoài mép carrier, OLED, mic, loa, IMU, E-stop.
- PDB/phân vùng copper ở đây chỉ là **khái niệm**, phải chốt footprint,
  connector, schematic, gán GPIO/bank trước khi vẽ trace hay sản xuất.
- Loa được bố trí phía sau, xa mic phía trước để giảm ghép âm; vẫn phải thử
  tiếng vọng/AEC và ảnh hưởng âm thanh trong lúc motor hoạt động.
- Dây VM motor và hồi dòng đi **vành ngoài**; dây encoder/sensor/UART đi
  theo **vành trong** khác tuyến; về điểm phân phối GND phù hợp, không tách
  GND hoàn toàn. Dây tín hiệu tránh anten Wi-Fi, loa/I2S, động cơ.
- E-stop NC dùng để **tước quyền chạy qua mạch gate chốt lỗi**; không mặc định
  dòng motor chảy qua tiếp điểm NC. BMS, cầu chì, sạc và nSLEEP/STBY của
  module driver cần sơ đồ điện/đo thực trước khi đấu.
- Mô hình có hai tấm acrylic trong suốt, các bo mạch minh họa; **lỗ gia công/
  ốc/pin header chưa định vị**.

## Điều kiện để chuyển CAD phác thảo thành CAD đúng kích thước

1. Đo hai tấm acrylic: tọa độ mép/khoét bánh, độ dày và tâm tất cả lỗ.
2. Đo khoảng cách tâm bánh trước–sau, tâm vệt bánh trái–phải, đường kính
   bánh cả lốp, chiều rộng bánh, chiều cao trục và khoảng sáng gầm.
3. Đo bốn motor TT và vị trí trục/đĩa mã/gá encoder, xác nhận khe V2.
4. Đo PCB ESP32-S3, Nano9K, 2 driver, 2 buck, BMS, E-stop, loa và gá pin;
   chừa đầu cắm, dây uốn, anten, USB debug và vùng tản nhiệt.
5. Thử lắp dummy giấy/3D hoặc mô hình mock-up trước khi khoan; xác nhận
   không chạm bánh lúc quay, không kẹp dây, không cạ sàn và E-stop ấn được.

**Quan trọng:** `layout.json` giờ dùng **260 × 155 mm và 175 mm cả lốp** dựa
trên ảnh và mô tả mới. Thông tin v0.1 (250 × 148 mm) là tham khảo cũ; không
được trộn những mốc đo của hai bản. Tấm cong mới cần chụp thẳng đứng có thước
và đo từng lỗ mới có thể truy viền/định vị gá chính xác.
TT motor được dùng envelope 70 × 22 × 18 mm theo mẫu phổ biến SunFounder,
**không phải số đo đúng motor TT của bộ xe bạn đang có**.
Ước lượng khối lượng/trọng tâm dùng trọng lượng giả định (cả hai tấm acrylic
ước chừng 235 g), **không** được dùng để tính tải motor hay khả năng chống lật.

## An toàn và nghiệm thu

- Chưa chứng minh đủ tải DRV8833: cần xác nhận package (PW vs PWP/RTY),
  dòng khởi động/kẹt, tản nhiệt và nguồn theo motor thật.
- Hai encoder một OUT dùng RTL pulse/protocol v2 riêng, không tương thích với
  decoder A/B v1; chưa có firmware Motion v2, chuyển mức/pinout và thử trên xe,
  nên không coi đường dây trong hình là tính năng đã hoạt động.
- Không thiết kế hở cell Li-ion hoặc coi gá pin in 3D là bảo vệ điện; dùng
  pack 2S có BMS, dây/bảo vệ/sạc đúng và gá chống chập.
- Phải thử STOP khi mất clock FPGA, mất GPIO/MCU/nguồn điều khiển, E-stop,
  mất UART, brownout; mạch gate giữ OFF mặc định và không tự chạy sau nhả.
- Tinh chỉnh PID/ramp/giới hạn gia tốc chỉ sau khi xác nhận motor/driver/encoder;
  skid-steer 4WD sinh dòng tăng khi quay, không mặc định quay tại chỗ an toàn.

Đọc thêm `../components.md`, `../power-plan.md`, `../../firmware/shared/fpga-safety.md`
và `../../docs/single-channel-encoder-plan.md`.
