# Kiểm thử FPGA

Chạy từ root: `python utils/build_fpga.py --rtl-only`. Cần Icarus/VVP;
runner dùng bản cài sẵn hoặc `--iverilog`/`--vvp`. Không truy cập phần cứng.

- `tb_spi`: atomic CS, 37 pha tương đối27MHz với SPI1MHz, CS abort/độ dài thiếu/
  thừa đến512bit, mỗi reserved byte, magic/version/CRC/range, seq trước/restart/
  wrap, golden vector, snapshot các field cùng thời điểm, reset giữa frame.
  Hai core có tốc độ observer khác nhau phải cho cùng SPI/PWM mọi tick.
- `tb_pwm_encoder`: các duty0,±1,±10,±675,±1349,±1350; đếm tick HIGH từng chu kỳ
  1350tick, đổi tại biên, zero một chu kỳ khi đảo trực tiếp, không overlap;
  baseline HIGH/noise hai chiều, period/age chính xác, count wrap/age saturation.
  Chỉ overflow32bit được force để tăng tốc; đường hoạt động thường chạy thật.
- `tb_watchdog`: chạy đủ13.500.000tick500ms mặc định, không rút ngắn; CRC sai gần
  deadline không refresh; tắt PWM và tự hồi phục với lệnh mới, không fault latch.
- `tb_nano9k`: black-box shell chuẩn, POR không nhấn reset, lọc256tick, encoder
  phải count/period/age, RX CRC/seq trước, PWM full hai dấu, frame lỗi và S2.
  Cùng bench chạy lại trên netlist Gowin sau PnR với primitive hãng cài sẵn.
- `spi_test_master`: stimulusSPI mode0, CRC reference theo byte và decoderRX;
  golden độc lập bằng Python `binascii.crc_hqx` ở `data/fpga_spi_vectors.*`.

Mô phỏng mapped là chức năng, không annotate SDF. STA và phần cứng báo riêng.
