# RTL độc lập hãng

Toàn bộ lõi dùng SystemVerilog (`.sv`), một clock domain; không tạo clock bằng
logic. Dùng `logic`, `always_ff` cho thanh ghi, `assign` cho đường tổ hợp đơn
giản và enum cho FSM. Không dùng khởi tạo biến để thay phép gán liên tục.

- `reset_sync`: reset active-low, assert bất đồng bộ, nhả sau hai cạnh clock.
- `input_sync_filter`: đồng bộ hai FF rồi lọc cả vector bằng N mẫu ổn định.
  `FILTER_N >= 1`; `valid` chỉ bật sau mẫu đầu tiên đã đồng bộ/lọc.
- `quadrature_decoder`: X4, `00 -> 01 -> 11 -> 10 -> 00` là dương. Mẫu đầu
  thiết lập pha, không tính là chuyển động. Nhảy hai bit báo lỗi, không đếm;
  lấy trạng thái mới làm mốc để tiếp tục. Count modulo 2^COUNT_WIDTH.
- `encoder_pair`: hai encoder, snapshot nguyên tử mỗi SNAPSHOT_CYCLES.
  Snapshot lấy count và timestamp trước cập nhật cùng cạnh; sequence tăng
  mỗi mẫu. `snapshot_valid` là pulse một clock. Status bit 0/1 là invalid
  sticky trái/phải, bit 2/3 là decoder đã có mốc trái/phải; reset xóa sticky.
- `pwm_pair`: duty trái/phải cập nhật nguyên tử tại boundary; lệnh mới nhất
  thay cặp shadow. Mỗi chu kỳ có đúng duty tick HIGH, gồm 0 và 100%. PWM được
  register để tránh glitch từ carry counter. Lệnh ngoài miền bị loại cả cặp;
  `command_rejected` báo ở clock lấy lệnh, `command_applied` ở clock commit.
- `motor_pwm_pair`: thêm hai bit chiều trừu tượng (bit0 trái, bit1 phải;
  0=thuận, 1=ngược theo quy ước), không phát IN1/IN2/brake riêng driver.
  Khi chiều bất kỳ đổi, tắt PWM cả hai bánh, đợi ZERO_CYCLES, đổi chiều,
  đợi SETUP_CYCLES rồi nạp duty. Lệnh mới trong khoảng chờ thay toàn bộ cặp
  và bắt đầu lại khoảng zero; lệnh sai miền không đổi trình tự đang hợp lệ.

PWM mặc định PERIOD_CYCLES=1350, DUTY_WIDTH=16, duty0..1350. `enable` là quyền
chạy đồng bộ từ FSM an toàn sẽ triển khai sau, không phải tín hiệu raw từ MCU
hoặc E-stop. Khi enable LOW, đầu ra bị mask ngay; giữ LOW qua ít nhất một
cạnh clock để xóa active/shadow/chiều chờ. Khi cấp lại enable mà chưa có lệnh
mới thì duty vẫn zero. Không nhả/cấp enable bất đồng bộ để thay FSM hoặc gate
phần cứng: khi clock đứng và permit cũ bị mở lại, lõi PWM riêng không tự chốt lỗi.

ZERO_CYCLES mặc định27000 (1 ms), SETUP_CYCLES=27 (1 us) chỉ là tham số mô phỏng.
Chưa có driver/motor cụ thể, nên chưa được xem đây là thời gian dừng rotor
hay dead-time cầu H. Motion phải xác nhận vận tốc phù hợp trước khi đảo chiều;
chính sách xe bản đầu vẫn chỉ tiến. Adapter driver, gate/FAULT và watchdog
chưa nằm trong module PWM này.

Ràng buộc tham số: PERIOD_CYCLES/ZERO_CYCLES/SETUP_CYCLES >=1; DUTY_WIDTH phải
biểu diễn được giá trị PERIOD_CYCLES (gồm duty100%). Cùng chiều, commit không
quá một chu kỳ PWM; sau interlock có thêm một clock LOAD trước khi PWM chạy.
Không yêu cầu lệnh liên tục để giữ duty: watchdog ở lớp an toàn sẽ quyết định
enable, nên không nối lõi độc lập trực tiếp vào motor.

Mặc định 27 MHz, FILTER_N=3, count/timestamp32, sequence16, snapshot270.000
tick (10 ms). Filter là tham số thử nghiệm, phải chọn lại theo PPR/RPM/dạng
xung thực; chưa cam kết tốc độ encoder trên xe. Đảo chiều từng bánh bằng
INVERT_LEFT/RIGHT. Nguồn reset bên ngoài phải bảo đảm assert khi khởi động;
chưa có target/power-on reset riêng hãng.

Thuộc tính ASYNC_REG đánh dấu các FF đồng bộ; vẫn cần kiểm tra mapping và
constraints đúng công cụ/target. Mô phỏng không chứng minh metastability.
