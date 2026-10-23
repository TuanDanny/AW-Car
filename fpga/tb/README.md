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
- `tb_encoder_timing`: tham số mặc định, kiểm tra ba chu kỳ snapshot270.000
  tick; mô phỏng clock 27 MHz với độ chính xác ps.
- `tb_pwm_pair`: duty0/1/giữa/P-1/P, từ chối ngoài miền/disabled, shadow cặp,
  10 seed x 1.000 lệnh và đo số tick HIGH/cạnh/chu kỳ bằng scoreboard.
- `tb_motor_pwm_pair`: thời gian zero/setup, lệnh thay thế khi đổi chiều,
  lệnh lỗi không đổi chiều; disable/reset từng bước chuyển và khi clock đứng.
- `tb_pwm_timing`: clock27MHz, chu kỳ1.350 tick, duty50/100%, zero27.000 tick,
  setup27 tick và các tham số nhỏ nhất hợp lệ (period/zero/setup=1).
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

Mô hình test không mô phỏng metastability hoặc nguồn/mức điện áp. Các test này
chưa nghiệm thu handshake ARM, watchdog hay toàn hệ thống. PWM/chiều là tín hiệu logic
trừu tượng, chưa kiểm tra truth table/phanh của một driver cụ thể.
