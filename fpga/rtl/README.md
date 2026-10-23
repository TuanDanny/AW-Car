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

## Liên kết Motion–FPGA

- `uart_rx`: đồng bộ RX hai FF, kiểm tra start giữa bit, nhận 8N1; stop LOW
  báo framing_error, LOW liên tục 11 bit báo break_error một lần, đợi HIGH
  để phục hồi. Byte chỉ có nghĩa khi valid một clock.
- `uart_tx`: ready/valid, chỉ lấy data khi ready; truyền đủ start/8 data/stop,
  báo done sau stop đầy đủ. Pulse valid khi busy không được xếp hàng.
- `crc16_byte`: tổ hợp cập nhật CCITT-FALSE từng byte, polynomial1021;
  parser/serializer bắt đầu bằng FFFF và không tính hai byte preamble.
- `frame_rx`: nhận type điều khiển01..05, tối đa payload6, CRC/length/type/
  version đúng mới phát frame_valid. Không đọc trường staging ngoài pulse.
  Timeout2ms giữa byte/5ms toàn frame; timeout thắng byte đến đúng hạn.
  Framing/break hoặc flush hủy frame; preamble lồng có thể cần bỏ một frame
  rồi phục hồi. Không có FIFO frame32 byte.
- `frame_tx`: đóng băng snapshot/session/state/fault ở handshake snapshot;
  STATUS31 byte. Busy không nhận mẫu mới, báo snapshot_dropped; không queue.
  Dữ liệu byte giữ nguyên khi downstream chưa ready, CRC chỉ tiến khi nhận byte.
- `command_guard`: đúng phiên, sequence mới theo modulo16, duty/flags/chiều
  hợp lệ và command_enable mới phát command_valid cặp. ALLOW_REVERSE mặc định0.
  HELLO chỉ đề nghị phiên; ARM_ZERO/CLEAR_FAULT chỉ là yêu cầu cho FSM. DISABLE
  đúng format/CRC được nhận kể cả phiên cũ để giảm quyền, không đổi mốc sequence.
- `fpga_link`: nối các khối trên, xuất sự kiện và nhận snapshot; **không có
  PWM/permit/FSM/watchdog**. Reset rst_n phải nhả đồng bộ ở lớp tích hợp.

UART dùng CLK_HZ/BAUD dương, bộ chia làm tròn `(CLK_HZ + BAUD/2)/BAUD`, ít nhất
8 tick/bit; mặc định27MHz/115200 =234 tick/bit. Các timeout parser phải >=1
và đủ dài cho frame/baud cấu hình. Chỉ thay CLK_HZ không tự đổi timeout:
54000/135000 là tham số đánh giá27MHz, cần đổi cùng clock.

FSM tương lai phải cấp session_active/active_session/sequence_base bằng
context_load; hủy/đổi phiên cũng pulse context_load. Khi đó parser/TX bị flush,
guard bỏ sự kiện cùng clock và xóa cặp duty đang lưu. command_enable phải đến
từ trạng thái ARMED. Không dùng UART/HELLO làm quyền chạy. Event session/sequence
đã latch cùng pulse; không dùng lại cặp duty nếu không có command_valid mới.
TX có thể hoàn tất byte UART cũ khi flush: phía Motion phải loại frame thiếu
CRC/sai phiên, không coi UART byte đang chạy là snapshot mới.

Chi tiết offset/CRC/vector và phần handshake còn phải thiết kế ở
[wire protocol](../../firmware/shared/fpga-protocol.md). Lõi guard chưa quyết
định timeout/ARM và không thay thế gate độc lập Motion/E-stop/nguồn.
