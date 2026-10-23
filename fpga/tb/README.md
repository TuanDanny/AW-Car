# Mô phỏng RTL

Testbench tự kiểm tra bằng Icarus/VVP; lỗi dùng `$fatal(1, ...)`, mỗi bài có
timeout. Chạy từ root: `python tools/run_fpga_tests.py`. Dùng `--list` để xem
bài, `--test tb_encoder_pair` để chọn và `--waves` để lưu VCD trong build.

- `tb_encoder_units`: reset assert/nhả, lọc N=1/3, 16 chuyển pha, đảo chiều,
  invalid và wrap trên bộ đếm thu nhỏ.
- `tb_encoder_pair`: hai bánh, mốc pha ban đầu khác zero, nhiễu ngắn, sticky
  invalid, snapshot trước cạnh đếm, timer/timestamp/sequence wrap. 10 seed cố
  định, mỗi seed 10.000 chuyển hợp lệ mỗi bánh và đối chiếu count độc lập.
- `tb_encoder_timing`: tham số mặc định, kiểm tra ba chu kỳ snapshot270.000
  tick; mô phỏng clock 27 MHz với độ chính xác ps.

Mô hình test không mô phỏng metastability hoặc nguồn/mức điện áp. Các test này
chưa nghiệm thu UART, watchdog hay toàn hệ thống.
