# Motion 0.1 — contract triển khai

Nhánh codex/esp32-s3-motion từ main094b37c; Brain tiếp tục PR13 draft.
Hai UART + vòng hở TT4WD, encoder một OUT/bên, FPGA PWM20kHz. PI/PID,
ToF/TCRT5000/MPU6050, quãng đường và OTA để mốc sau.

## Tổ chức và độ trễ

Lõi Motion/link FPGA/mô hình truyền động là C++17 thuần chung host/MCU.
Một task sở hữu trạng thái; RX chỉ đưa event. Core1 control20/TX19; core0
hai RX18/console3/log2. GPTimer1ms notify, CMD100Hz. STOP/fault ưu tiên riêng.
Không heap/I/O/log trong lõi; RX16event, TX latest1/cổng, log32, latency128.
Queue đầy/event cũ thu hồi quyền, không lấy dữ liệu cũ gia hạn lệnh. ISR GPIO
và timer giám sát control20ms ở IRAM; E-stop phần cứng vẫn độc lập.

Console chỉ khi DISARMED/link idle. Save/load NVS khóa validated, reply có ID,
publish cấu hình trước ACK; không flash lúc chạy. PSRAM/Wi-Fi/BLE không dùng.
Đo nhận frame→UART, mục tiêu p95<=2ms/p99<=5ms trên ESP32; không lấy số host
làm bằng chứng RTOS/GPIO. Kích200ms và chờ đảo chiều là hành vi chủ đích.

## Chuyển động

- Với mm/s,mrad/s,Wmm: `left=v-omega*W/2000`, `right=v+omega*W/2000`.
  Vượt trần bánh giảm cả hai cùng tỷ lệ, duty0..1350.
- Nghỉ ổn định500ms rồi mục tiêu khác0: kích và nội suy tuyến tính về mức
  yêu cầu trong200ms. Biên độ `min(limit,requested/0.30)`; vùng thấp không bị
  ép100%. Giữ tỷ lệ hai bên, phía yêu cầu0 vẫn0. Frame20Hz/đổi tốc độ không
  reset cú kích. Neutral0 hủy kích ngay, giữ ARM; STOP/lỗi/hết lease bỏ quyền.
- Đổi dấu một bên: coast cả hai, giữ mục tiêu mới nhất. Tốc độ không dấu
  <=20mm/s liên tục100ms hoặc nghỉ/không cạnh500ms theo snapshot mới được
  coi là chậm ước lượng; một OUT không chứng minh đứng yên. Chờ tối đa1500ms
  rồi FAULT. Giữ thêm interlock FPGA40ms/setup1us. AI hết giờ thì hủy, không bù.
- Có duty nhưng không xung: hạn theo hai chu kỳ xung dự kiến+200ms, chặn
  750ms..10s theo tốc độ/độ phân giải. Dừng cả xe, không tự kích lại. Không
  lấy cảnh báo500ms của FPGA làm ngưỡng hỏng chung cho mọi tốc độ thấp.

Mặc định host/lab: circumference188496um,20xung/vòng,W120mm, full_speed200mm/s,
|v|<=200,|omega|<=1000. Chưa đo trên xe. validated0 và build LOCKED chặn ARM;
cần pinout/gate, D/N/W, nguồn/dòng được xác nhận trước bật. V/omega đo có dấu
và pin chưa có thì invalid, không gán chiều yêu cầu thành chiều đo.

## Giao thức và an toàn

BM-v1 giữ wire20/30byte, TTL1..250ms (mặc định120), STATUS20Hz. Sau ARM đợi
SET_TWIST đầu tối đa120ms, không giữ quyền vô hạn. HELLO trong FAULT chỉ mở
phục hồi; CLEAR xong DISARMED, hủy context lái, cần HELLO/ARM mới. Bit8 fault
BM=REVERSAL_TIMEOUT; bit5 status=driver_permit. applied_seq chỉ là Motion nhận
mục tiêu, chưa chứng minh FPGA/motor thực thi.

FPGA v2 CMD19/STATUS47byte; GPIO LOW→req/ack→quiet5ms→HELLO→ARM_ZERO→STATUS
ARM_PENDING đúng phiên+ack→logical permit→STATUS ARMED+fpga_permit→driver
permit→wake1ms. Watchdog FPGA50ms không gia hạn bởi telemetry/phát lại cache.
Snapshot/session/seq/timestamp phải mới;30ms stale khóa trong1ms tiếp.
fault&0x8800 cần reset FPGA; các cảnh báo sticky khác chỉ log. Hai word lỗi
BM/FPGA có nghĩa khác nhau, không sao chép trực tiếp.

DỪNG hạ driver_permit ngay, DISABLE xác nhận trong30ms rồi mới hạ logical
permit; không phát sinh lost-permit fault thông thường. Lỗi nghiêm trọng hạ
cả hai. BOOT chỉ STOP, giữ nút ngăn tăng quyền. CLEAR Web vẫn cần Cho phép lại.

## Nghiệm thu

Test biên/golden CRC, sáu hướng/kích/đảo, STOP/TTL/seq/session/wrap, snapshot
đứng, encoder không xung, cấu hình/phục hồi. Ghép hai lõi C++ thật, rồi RTL
aw_car_top27MHz. Soak30phút>=1000lệnh, hash/queue/phân vị. Build/console board
LOCKED trước; UART/gate/motor và quãng dừng là cổng nghiệm thu phần cứng riêng.
