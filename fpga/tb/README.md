# Mô phỏng RTL

Toàn bộ testbench dùng SystemVerilog (`.sv`), biên dịch bằng `iverilog -g2012`.
Tự kiểm tra bằng Icarus/VVP; lỗi dùng `$fatal(1, ...)`, mỗi bài có
timeout. Chạy từ root: `python tools/run_fpga_tests.py`. Dùng `--list` để xem
bài, `--test tb_encoder_pair` để chọn và `--waves` để lưu VCD trong build.

- `tb_encoder_units`: reset assert/nhả, lọc N=1/3, 16 chuyển pha, đảo chiều,
  invalid và wrap trên bộ đếm thu nhỏ.
- `tb_encoder_pair`: hai bánh, mốc pha ban đầu khác zero, nhiễu ngắn, sticky
  invalid, snapshot trước cạnh đếm, timer/timestamp/sequence wrap. 10 seed cố
  định, mỗi seed 10.000 chuyển hợp lệ mỗi bánh và đối chiếu count độc lập.
- `tb_pulse_encoder_pair`: hai OUT độc lập, khởi động HIGH, glitch ngắn,
  đếm cạnh lên, period/age, timeout, wrap và snapshot count/period/age nguyên tử.
- `tb_single_out_protocol`: STATUS v2 đúng 47 byte, vector Python độc lập và CRC và 4 field mở rộng,
  snapshot đóng băng khi backpressure.
- `tb_single_out_v2_rx`: reject control version v1, nhận version v2 với
  session/sequence/payload và CRC đúng.
- `tb_aw_car_top`: logical top chỉ 2 chân encoder, đếm xung,
  từ chối HELLO v1/nhận v2 qua UART, kiểm tra toàn frame STATUS 47B/CRC và
  gate vẫn OFF khi chưa ARM.
- `tb_encoder_timing`: tham số mặc định, kiểm tra ba chu kỳ snapshot270.000
  tick; mô phỏng clock 27 MHz với độ chính xác ps.
- `tb_encoder_single_out`: FILTER_N=1/3/5, 6.000 cặp xung ngẫu nhiên, HIGH ban
  đầu/giữ mức, nhiễu ngắn cả hai cực, valid bị ngắt, bộ đếm/timestamp/sequence
  wrap, snapshot nguyên tử và reset HIGH. Inversion A/B không làm count OUT giảm.
- `tb_common_matrix`: scoreboard lịch sử mẫu độc lập cho sáu cấu hình lọc
  N=1/2/3/4/5/8, WIDTH=1..4; nhiễu quanh ngưỡng, 2.000 lần đổi mỗi cấu hình,
  reset ở chín pha và reset/nhả khi clock đứng.
- `tb_crc16_matrix`: 327.680 so sánh bằng phép chia đa thức độc lập; toàn bộ
  65.536 CRC trước với bốn mẫu byte và toàn bộ byte với 256 seed bổ sung.
- `tb_guard_sequence`: đủ 65.536 khoảng cách sequence modulo, 32.767 lần thử
  lặp, 16 bit điều khiển sai (gồm chiều), duty có bit cao và context trùng CMD.
- `tb_uart_matrix`: divider tối thiểu8, lẻ9 và biên làm tròn16/17; đủ256 byte
  TX/RX mỗi cấu hình, đo từng tick TX, reset ở cả10 vị trí ký hiệu và phục hồi.
- `tb_frame_tx_random`: 10 seed x256 STATUS có trường ngẫu nhiên, reference
  packing/CRC riêng, stall, metadata đóng băng và5.120 snapshot bị drop.
- `tb_safety_matrix`: bảy cấu hình timer, sáu trạng thái/tám bit fault,
  sự kiện đồng thời, deadline, hold<clear/=clear/>clear và trạng thái bất hợp lệ.
- `tb_fault_recovery_deadline`: HELLO trong FAULT, CLEAR_FAULT trước/đúng/sau
  hạn ở32/80/6.750.000 tick; cấu hình cuối dùng timer250ms danh định27MHz.
  Kiểm tra FAULT không phiên chờ vô hạn, hết hạn hủy context, UART không tự
  mở lại phiên, GPIO recovery mới phục hồi được và không tự cấp quyền motor.
- `tb_pwm_pair`: duty0/1/giữa/P-1/P, từ chối ngoài miền/disabled, shadow cặp,
  10 seed x 1.000 lệnh và đo số tick HIGH/cạnh/chu kỳ bằng scoreboard.
- `tb_motor_pwm_pair`: thời gian zero/setup, lệnh thay thế khi đổi chiều,
  lệnh lỗi không đổi chiều; disable/reset từng bước chuyển và khi clock đứng.
  Thêm luồng lệnh nhanh hơn khoảng zero để bắt lỗi chờ mãi, và lệnh đổi mục
  tiêu đúng clock hết hạn zero phải lấy cặp mới nhất.
- `tb_pwm_timing`: clock27MHz, chu kỳ1.350 tick, duty50/100%, so sánh zero30ms
  (810.000 tick) và40ms (1.080.000 tick), setup27 tick; đếm đúng thời điểm
  phục hồi PWM và các tham số nhỏ nhất hợp lệ (period/zero/setup=1).
- `tb_pwm_widths`: period16/1350/2048/65535, duty100%, zero/one và lệnh sai
  có bit cao (gồm2049 có thể alias thành1 nếu cắt11bit quá sớm); đếm HIGH
  cả period, so khớp PWM với wrapper motor và xóa duty khi disable.
- `tb_drv8833_adapter`: đủ64 tổ hợp reset/enable/PWM/chiều theo bảng TI,
  kiểm tra thả trôi khi mất quyền/reset không cần clock, không phát11/phanh.
- `tb_uart`: host/observer UART độc lập, đủ256 byte ở baud danh định/+2%/-2%,
  pha lệch, back-to-back, false start/stop lỗi/break/reset giữa byte, TX busy.
- `tb_frame_rx`: CRC chuẩn29B1 và vector chung, mutation từng byte CRC bảo vệ,
  version/type/length lỗi, preamble trong dữ liệu, overlap, timeout trước/tại
  hạn, reset/flush mọi vị trí CMD; 10 seed x1.000 trường hợp hỗn hợp/noise/cắt.
- `tb_frame_tx`: STATUS chung đúng từng byte, snapshot đóng băng qua backpressure,
  báo drop, reset/flush ở31 vị trí serializer và phục hồi bằng frame mới.
- `tb_command_guard`: không cấp phiên bằng HELLO; đúng/sai phiên, sequence gap/
  duplicate/cũ/wrap/biên32767/32768, flags/chiều/duty sai; context_load ưu tiên,
  enable/reset và chính sách ALLOW_REVERSE0/1.
- `tb_fpga_link`: 27MHz/115200 thật, nhận CMD/gửi STATUS đồng thời, CRC lỗi/
  duplicate không commit, snapshot nguyên tử/drop, timeout mặc định2/5ms và phục hồi.

- `tb_safety_fsm`: GPIO mới/stale HIGH, session/ARM_PENDING, STATUS sai phiên/
  state, permit sớm, CMD trước/tại deadline, traffic không gia hạn, DISABLE,
  fault/clear/timeout và reset các bước recovery/ARM/CLEAR.
- `tb_safety_timing`: mặc định27MHz, ARM zero tại49/50/51ms; hết hạn đúng
  1.350.000 tick và CMD đúng hạn không cứu watchdog.
- `tb_drive_core`: UART host/CRC/observer độc lập, đối chiếu toàn STATUS với
  snapshot được nhận; encoder chạy hai chiều, UART tới PWM, xác nhận stop bit,
  fault latch ngoài, E-stop10ns, reset khi cached permit HIGH, clock đứng và
  mô hình Motion stale inhibit30+1ms kể cả metadata snapshot lặp/cũ.
  Mặc định chạy>=2s ở2,7MHz, đổi timer/PWM cùng tỷ lệ; `--full-timing` chạy
  cùng kịch bản>=2s ở27MHz/115200/20kHz/50ms, CI bật chế độ này.
- `tb_drive_defaults`: cùng chuỗi lỗi với timer/PWM mặc định27MHz, không
  chạy vòng giữ lệnh2s. Wrapper reuse scenario `.sv`, không sao chép model.
  Hai bài cũ chọn A/B/khóa lùi tường minh để giữ bài hồi quy chính sách cũ.
- `tb_drive_maneuvers`: dùng chính `aw_car_top` không ghi đè tham số, clock27MHz, UART host/CRC và
  observer độc lập; đếm HIGH cả hai PWM qua hai chu kỳ cho đủ bốn tổ hợp chiều
  và nhiều duty (0, 1, bất đối xứng, 100%), rẽ với một bên đứng yên. Kiểm tra
  zero/setup, OUT qua STATUS bit4/CRC, lệnh sai, watchdog, E-stop/reset/DISABLE.
  Giải mã độc lập các chân DRV8833 IN theo bảng cầu H để đếm số tick kích
  thuận/ngược đúng30 ca duty/chiều; IN phải00 trong interlock và mất quyền.
  Trong khoảng40ms nhận CMD mới gần100Hz, kiểm tra không chờ mãi; DISABLE
  giữa coast không phục hồi lệnh cũ. Watchdog hết hạn đúng1.350.000 tick từ
  CMD hợp lệ cuối, không tạm dừng theo interlock.

Hiện có **34 testbench**. Lưu báo cáo JSON và buộc mọi module RTL được
elaborate trong ít nhất một bài PASS bằng:

```sh
python tools/run_fpga_tests.py --timeout 1800 --report fpga/build/regression-report.json --require-module-coverage
```

Thêm `--full-timing` để chạy cả bài tích hợp2s ở27MHz như CI. Báo cáo có
module -> test, số ca `COVER`, phiên bản compiler và SHA256 nguồn. Chỉ test
thành công có đúng marker PASS mới được tính; kiểm tra này không đo coverage
dòng/nhánh/toggle. Xem [bằng chứng và giới hạn](../verification.md).

Mô hình test không mô phỏng metastability hoặc nguồn/mức điện áp. Motion/gate
chỉ là model kiểm chứng hợp đồng, chưa có firmware hoặc sơ đồ điện thực tế. PWM/chiều là tín hiệu logic
trừu tượng; adapter đã kiểm tra bảng IN drive/coast của DRV8833, chưa mô phỏng
công suất/điện/cơ hoặc nghiệm thu driver thật. Không có chế độ phanh chủ động.


- `tb_runtime_diagnostics`:60 kịch bản biên ở ngưỡng1/2/16/17/64, phân biệt
  cảnh báo/lỗi khóa, count wrap, idle/duty0/interlock, trạng thái sai và reset.
- `tb_encoder_period_random`:24.000 mẫu đối chiếu bằng timestamp độc lập,
  valid bị ngắt, silence dài, age bão hòa, khôi phục period và wrap count.
- `tb_diagnostics_uart`:ARM thật trong mô phỏng, CRC sai/session sai qua RX,
  kiểm tra cờ cảnh báo về STATUS CRC đúng mà không dừng giả; tiêm raw PWM sai/
  snapshot đứng, kiểm tra4 chân IN tắt, UART không mở lại và reset xóa lịch sử.

- `tb_diagnostics_default_timeout`:ngưỡng encoder mặc định13.500.000 tick
  (500ms ở27MHz), heartbeat snapshot270.000tick/10ms vẫn khỏe, cảnh báo
  không phát sớm/không tự khóa và giữ lịch sử khi encoder phục hồi.
