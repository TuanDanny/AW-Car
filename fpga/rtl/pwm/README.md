# PWM hai nhóm motor và trình tự đổi chiều

Hai kênh trái/phải dùng cho hai bên TT 4WD, không phải điều khiển độc lập cả
bốn motor. Adapter driver phải ánh xạ PWM/chiều sang từng cầu H phù hợp.

- `pwm_pair.sv`: duty trái/phải cập nhật nguyên tử tại boundary; lệnh mới nhất
  thay cặp shadow. Mỗi chu kỳ đúng duty tick HIGH, gồm0/100%; PWM register
  để tránh glitch carry counter. Sai miền loại cả cặp; command_rejected báo
  khi lấy lệnh, command_applied báo ở clock commit.
- `motor_pwm_pair.sv`: chiều trừu tượng bit0 trái/bit1 phải,0 thuận/1 ngược;
  không phát IN1/IN2/brake riêng driver. Đổi chiều bất kỳ tắt PWM cả cặp,
  đợi ZERO_CYCLES, đổi chiều, đợi SETUP_CYCLES rồi nạp duty. Lệnh mới trong
  khoảng chờ thay cả cặp và bắt đầu lại khoảng zero; sai miền không đổi
  trình tự đang hợp lệ.

Mặc định PERIOD_CYCLES=1350, DUTY_WIDTH=16, duty0..1350. enable là quyền chạy
đồng bộ từ safety_fsm trong drive_core, không phải raw MCU/E-stop. LOW mask
ngay đầu ra; giữ LOW ít nhất một cạnh clock để xóa active/shadow/chiều chờ.
Cấp lại enable nhưng chưa có lệnh mới thì duty vẫn zero. Không nhả/cấp enable
bất đồng bộ để thay FSM/gate: PWM độc lập không chốt lỗi khi clock đứng.

Cổng lệnh và active duty giữ DUTY_WIDTH bit; thanh ghi nội bộ chỉ dùng
`max(1, $clog2(PERIOD_CYCLES + 1))` bit (11 bit với1350). Kiểm tra sai miền
trên toàn bộ lệnh trước khi thu hẹp; trả active duty bằng zero-extension.
Độ rộng duty phải chứa cả PERIOD_CYCLES để giữ100% khi period là lũy thừa2.

ZERO_CYCLES=27000 (1ms), SETUP_CYCLES=27 (1us) tại27MHz là tham số mô phỏng,
chưa phải thời gian dừng rotor/dead-time cầu H. Motion phải xác nhận vận tốc
phù hợp trước đảo chiều; xe bản đầu vẫn chỉ tiến. Adapter driver, gate/FAULT
và watchdog không nằm trong hai module PWM này.

PERIOD_CYCLES/ZERO_CYCLES/SETUP_CYCLES >=1; DUTY_WIDTH biểu diễn được cả
PERIOD_CYCLES. Cùng chiều commit không quá một chu kỳ PWM; sau interlock có
thêm một clock LOAD. Watchdog ở lớp an toàn quyết định enable; không nối
lõi độc lập trực tiếp vào motor.

Trạng thái: đã mô phỏng duty/boundary/đổi chiều/reset/clock-stop và tổng hợp
generic; chưa có driver/motor hoặc phép đo thực. Script:
`yosys -s fpga/synth_pwm.ys`, chạy từ root sau khi có `fpga/build/`.
Top toàn lõi: [drive_core.sv](../drive_core.sv).
