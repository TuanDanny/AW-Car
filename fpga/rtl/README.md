# RTL

- `simplev1_core.sv`: nối các khối, reset nhả đồng bộ, chốt setpoint/seq, watchdog500ms.
- `spi32.sv`: SPI oversample27MHz, CRC bit nối tiếp, commit tại CS lên, SR32 RX cố định.
- `encoder.sv`: hai FF + lọc256tick; baseline, count unsigned, period/age32bit.
- `pwm_pair.sv`: 1350tick/chu kỳ, signed duty, chân output đăng ký, zero một chu kỳ
  khi đổi cực; guard40ms do Motion thực hiện.
- `status_leds.sv`: observer chờ/kết nối, không điều khiển khối chức năng.

Input module dùng `wire logic`, tất cả register dùng `posedge clk`27MHz;
reset có assert bất đồng bộ. Không dùng SCLK làm clock. Test ở `test/rtl`.
