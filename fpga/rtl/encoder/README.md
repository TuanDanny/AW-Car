# Encoder và snapshot

- `quadrature_decoder.sv`: X4, `00 -> 01 -> 11 -> 10 -> 00` là dương.
  Mẫu đầu thiết lập pha, không đếm. Nhảy hai bit báo lỗi, không đếm;
  lấy trạng thái mới làm mốc. Count modulo 2^COUNT_WIDTH.
- `encoder_pair.sv`: hai encoder, snapshot nguyên tử mỗi SNAPSHOT_CYCLES.
  Snapshot lấy count/timestamp trước cập nhật cùng cạnh; sequence tăng mỗi
  mẫu, snapshot_valid pulse một clock. Status bit0/1 là invalid sticky
  trái/phải, bit2/3 là decoder đã có mốc; reset xóa sticky.

Dùng bộ đồng bộ/lọc từ [common](../common/README.md). Mặc định FILTER_N=3,
count/timestamp32, sequence16, snapshot270.000 tick (10 ms tại27MHz).
INVERT_LEFT/RIGHT đổi quy ước chiều từng bánh. Ngưỡng lọc phải chọn theo
PPR/RPM/dạng xung thực, không được loại xung hợp lệ ở tốc độ cao nhất.

Trạng thái: đã có testbench/reset/nhiễu/wrap/snapshot và tổng hợp generic.
Chưa đo encoder thật; Motion chịu trách nhiệm chính sách lỗi/khởi tạo encoder.
Script: `yosys -s fpga/synth_encoder.ys`, chạy từ root kho sau khi có
`fpga/build/`. Top toàn lõi: [drive_core.sv](../drive_core.sv).
