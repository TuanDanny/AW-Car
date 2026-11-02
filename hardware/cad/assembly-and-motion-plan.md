# AW-Car v0.2 — kế hoạch cơ khí, nguồn và điều khiển chạy mượt

> **Mô hình kỹ thuật sơ bộ, không phải xác nhận vật lý.** Đã cập nhật theo
> ảnh bộ khung hai tấm acrylic bo cong và thông số 260 × 155/175 mm. Kích thước từ quảng
> cáo khung và envelope linh kiện ước lượng. Dự án chưa có ESP32 Motion firmware,
> adapter DRV8833, mạch E-stop/gate, hoặc test chạy xe thật. Ưu tiên bảo vệ
> motor/pin và người xung quanh trước tối ưu cảm giác lái.

## A. Bố trí vật lý dự kiến

| Vùng | Vị trí trong mô hình | Mục đích | Cần đo/chốt |
| --- | --- | --- | --- |
| 4 motor TT | Gần bốn bánh, dưới tấm đáy | Dây motor ngắn, trọng lượng thấp | Lỗ gá, hướng trục, nhiệt/cọ lốp |
| Pack Li-ion 2S1P | Giữa, dưới đáy, Z 14–36 mm | Trọng tâm thấp; trái/phải cân | Kích thước pack hàn sẵn, gá bảo vệ, khoảng gầm |
| BMS | Trên pack, dưới đáy | Dây cell ngắn | Vỏ cách điện, vị trí sạc/connector |
| Motor buck / Logic buck | Tầng giữa, tách thành hai module | Giảm nhiễu motor vào MCU/loa | Footprint, giới hạn dòng, nhiệt, airflow |
| Gate an toàn | Tầng giữa, gần dây enable driver | OFF mặc định, chốt lỗi độc lập | Schematic và hành vi mất nguồn/clock |
| Brain / Motion | Trên, phía đầu xe | USB debug, âm thanh, Wi-Fi | PCB R16N8, anten không bị che |
| Nano 9K / 2 DRV8833 | Trên, gần phía sau | UART/IN driver ngắn; gần motor | Pinout, connector, nSLEEP/STBY, heatsink |
| OLED / Mic | Phía trước, dễ quan sát và nghe | Dễ tương tác | Nguồn 3,3 V, USB, khe mở mic |
| Loa 4 Ω 3 W | Phía sau, xa mic | Giảm phản hồi âm/tiếng vọng | Thể tích, hướng màng loa, tránh rung |
| MPU6050 | Gần vùng giữa, cố định cứng | Giảm sai số do rung/đòn bẩy | Tư thế trục, tọa độ so với CG |
| VL53L0X x1 | Giữa đầu xe, hướng tiến | Đo vật cản phía trước | Móc gá, vùng nhìn, phản xạ, quãng dừng |
| E-stop NC | Góc trước bên trái | Với tới nhanh, tránh vô ý va chạm | Ø lỗ 22 mm nếu dùng mẫu đã dự kiến |

**Chú ý quan trọng:** Hình phác có đường biên cong và khoét tương đối để
tránh vùng bánh TT, khác với các lỗ/rãnh/vị trí gá thật đang nhìn thấy trong
ảnh phối cảnh. **Không cắt tấm đang sở hữu theo tọa độ giả định**. Cần chụp
thẳng góc vuông tấm acrylic có thước đo và đo tâm lỗ, sau đó sửa `layout.json`.
Thông tin chiều rộng quảng cáo mâu thuẫn: một chỗ nói 155 mm ngoài bánh, một
chỗ nói 155 mm không lốp và 175 mm cả lốp; mô hình đang theo cách hiểu thứ hai.

**Bố trí nhóm motor:** một DRV8833 điều khiển hai motor một bên, mỗi motor
chiếm *một cầu H riêng*. Lệnh duty/chiều lấy theo nhóm trái/phải từ FPGA
qua adapter, không nối tắt đầu ra hai cầu. Không suy ra mã trên IC hay mức
1,5 A/kênh nếu package thực là bản khác; đo tải/bốc nóng mới chốt.

## B. Phân nguồn và dây

`wiring-plan.svg` cho thấy vùng tín hiệu/công suất, **không chỉ định dây đến
pin**. Kiến trúc ưu tiên:

```text
2S1P hàn sẵn + BMS
   -> cầu chì phù hợp dây / đầu nối (trị số sau đo tải)
   -> điểm phân phối nguồn và hồi dòng
       +-> buck logic 5V -> MCU/FPGA/AMP (3,3V từ nguồn phù hợp)
       +-> buck motor chỉnh được -> VM hai DRV8833 -> bốn cầu H
                                             ^
E-stop NC + giám sát rail -> latch gate OFF mặc định --|
Motion permit -----------[đường riêng]---------------|
FPGA permit -------------[đường riêng]---------------|
```

- Dây motor đi theo hai mép xe, bó riêng tín hiệu encoder/UART/I²C/I²S; đi
  GND chung có bố trí, không đẩy dòng motor về qua chân GND ESP32.
- Tránh dây chạy dọc/áp ngay anten ESP32, không ép dây vào lốp hoặc đĩa mã.
- Tăng tiết diện/đầu nối theo *dòng đo*, bố trí chống kéo bật và chống rung.
- Pin 2S cần bảo vệ cơ/điện, chống chập và có thể tháo an toàn; không đặt cell
  hở cạnh mép acrylic sắc. Dùng sạc 2S CC/CV phù hợp, không sạc lúc xe chạy
  nếu chưa có mạch power-path.
- Không gắn module nguồn đang nóng sát pack hoặc mic/loa. Kiểm tra hai rail
  khi Wi-Fi + ampli + 4 motor khởi động đồng thời, đặc biệt pin gần cạn.

## C. Các giai đoạn thực hiện, có tiêu chí chuyển bước

| Giai đoạn | Việc phải làm | Tiêu chí hoàn tất |
| --- | --- | --- |
| 0. Đo thật | Đo khung, tâm bánh, board, pack, mô-tơ, encoder; cập nhật CAD | Kích thước/ảnh có mốc, plate/wheel/board không đụng, lắp mock-up |
| 1. Nguồn & STOP | Kiểm tra pack, BMS, sạc, cầu chì, buck, gate chốt lỗi/E-stop | Power-up an toàn; driver OFF mặc định/mất nguồn/lỗi, đo điện áp dưới tải |
| 2. Một motor → bốn motor | Thử driver theo đúng package; đo dòng startup/stall và nhiệt; đánh dấu cực tính | 4 cầu H chạy riêng, không sụt nguồn logic, STOP cắt cả bốn kênh |
| 3. Đo tốc độ | Gá hai V2 một OUT, level shift, cập nhật FPGA pulse/period và protocol v2 | Đếm xung chính xác theo nhiều tốc độ và nhiễu tải, không tự suy ra chiều |
| 4. FPGA trên 9K | Wrapper + constraints, Gowin PnR/STA, UART/ARM/STOP trên board | Fit/timing thực; mất clock/CRC sai/timeout không duy trì quyền motor |
| 5. ESP32 Motion | PID/PI hai nhóm, ramp/limit, parser STATUS, lease, IMU/ToF, stale inhibit | Chạy ngắn tốc độ thấp, PID không giật, mất phản hồi thì ngừng |
| 6. Brain + UX | Tích hợp Xiaozhi/OLED/loa/Web → Brain–Motion có lease | AI/Web không thể vượt giới hạn Motion; E-stop luôn ưu tiên |
| 7. Chạy kiểm thử | Thử tải, rẽ, nền bám khác, pin yếu, âm thanh đang phát, lỗi cảm biến | Có log, video, số liệu dừng/thẳng/nhiệt/ổn định để báo cáo |

Không nối motor vào một top RTL chưa xác thực adapter/gate. Đừng dùng mô phỏng
FPGA đã PASS làm thay chứng nhận điện/nhiệt/mức logic.

## D. Kiểm soát chuyển động mượt (đề xuất cho Motion)

1. **Đầu vào có giới hạn:** Brain gửi mục tiêu vận tốc thẳng `v` và vận tốc
   quay `omega` kèm lease, Motion tự kẹp tốc độ, gia tốc, vùng an toàn và
   có quyền từ chối. Giao thức Brain–Motion chưa được viết.
2. **Bản đầu chỉ chạy tiến và rẽ bằng chênh lệch tốc độ hai bên.** Không bật
   lùi, hai bánh ngược chiều hoặc quay tại chỗ khi 2 encoder OUT chỉ đo độ lớn
   vận tốc và mặt sau/chống rơi chưa được bảo vệ.
3. **Điều tốc:** bước đầu PI 2 bên ở khoảng **50 Hz** (mốc thử, không phải tần số
   đã đạt). Dùng snapshot FPGA ~10 ms với period/age để cải thiện đo tốc độ
   rất thấp; không coi số xung x1 là số tick X4. PI có anti-windup, reset
   tích phân khi disarm, giới hạn duty, kiểm tra mất xung/encoder.
4. **Ramp và feed-forward:** làm mềm setpoint (slew-rate/acceleration limit),
   deadband chỉ sau đo ma sát/hysteresis; có thể thử 0,10–0,20 m/s² trên nền
   phẳng không người gần, rồi điều chỉnh từ log chứ không áp cứng. Thời gian
   dừng phải ưu tiên quãng an toàn, không để ramp chậm che lệnh STOP.
5. **Tải thật:** vì hai motor chung một bên không được đo độc lập, PID chỉ điều
   khiển mức nhóm, không bảo đảm 4 bánh cùng tốc độ. Giới hạn rẽ gấp, theo
   dõi dòng/nhiệt và so sánh IMU yaw với lệnh. IMU không thay encoder.
6. **Không suy luận lỗi bằng telemetry cũ:** UART STATUS sequence phải mới,
   session đúng, thời gian đo hợp lệ; Motion phải kéo permit LOW khi mất
   snapshot quá hạn (~30 ms theo hợp đồng đang đặc tả), đồng thời FPGA có
   watchdog lệnh mới hợp lệ 50 ms. E-stop/gate ngoài vẫn hoạt động nếu clock
   FPGA ngừng hẳn.

## E. Chỉ tiêu đo sau khi có xe thật (mục tiêu thử, KHÔNG phải kết quả)

- Xe tăng/giảm tốc không giật mạnh, hai bánh một bên không bị quay sai chiều;
  log target/measured/duty/IMU/voltage để điều chỉnh PI/ramp.
- Trên sàn phẳng đã hiệu chuẩn: thử đi thẳng 2 m nhiều lượt, đặt mục tiêu
  lệch ngang không quá 10 cm; phải đo và báo số thật, chưa khẳng định đạt.
- Thử E-stop, mất nguồn logic, reset từng MCU/FPGA, mất clock, mất UART,
  brownout và encoder rút dây: driver phải trở về OFF và không tự chạy lại.
- Trước khi tăng tốc: đo khoảng dừng trên nhiều mặt sàn, rồi tính khoảng
  dừng sớm cho ToF duy nhất ở phía trước; **không** cho rằng một ToF bảo vệ
  toàn bộ mép rơi, góc cua, chiều lùi hoặc vật tối/nhỏ.
- Thử 10–15 phút với tải thật, kiểm tra nhiệt driver, converter, pin, tụt
  nguồn logic, rung cơ khí, tiếng rè/echo của loa và mic. Chọn giới hạn
  nhiệt/dòng theo đúng datasheet và phép đo, không dùng ngưỡng tùy ý.

## F. Checklist đo kích thước thực trước khi in/khoan

| Cần đo | Hiện trạng |
| --- | --- |
| Chiều dài/rộng *đường viền mỗi tấm* và độ dày acrylic | Bản hàng mới 260 × 155 mm không lốp, rộng cả lốp 175 mm, có mâu thuẫn chú thích 155 mm; chưa đo |
| Các tâm lỗ, đường kính, rãnh, đường khoét bánh | Chưa có |
| Khoảng tâm bánh (wheelbase/track), rộng bánh, Ø bánh và khoảng sáng gầm | Chưa đo; CAD giả định 176/155/60 |
| Động cơ TT: envelope, tọa độ trục/đĩa, hướng lắp | Có loại TT, chưa đo model |
| Module V2: rãnh/độ cao cạnh đĩa, gá 2 bên, kích thước level-shifter | Chưa nhận/đo |
| ESP32-S3 Brain/Motion: PCB, USB, anten, trụ đỡ | Chưa đối chiếu hai board |
| Nano9K: footprint, height USB, bank I/O, pinout | Board mục tiêu, chưa mua |
| 2 DRV8833: package, chân STBY/nSLEEP, đầu nối và chiều cao tản nhiệt | Chưa xác minh |
| Pack 2S + BMS, buck logic/motor, E-stop 22 mm, loa Ø40 mm | Dự kiến, chưa mua/đo |

Đến khi có số đo thực, cập nhật `layout.json`, chạy lại `generate_aw_car.py`,
kiểm tra mô hình và đối chiếu bằng mock-up. Chỉ sau đó thêm lỗ gá thực, gá
in 3D, khe pin/đường dây và xuất bản vẽ gia công.
