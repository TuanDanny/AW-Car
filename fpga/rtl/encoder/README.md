# Encoder và snapshot

- `pulse_counter.sv`: một OUT đã đồng bộ/lọc, đếm cạnh LOW -> HIGH một lần/xung.
  Mẫu đầu chỉ làm mốc, kể cả HIGH; giữ HIGH/LOW không đếm thêm. Bộ đếm không dấu
  modulo 2^COUNT_WIDTH, tăng cả khi lùi hoặc thả trôi; không suy dấu từ lệnh motor.
- `quadrature_decoder.sv`: X4, `00 -> 01 -> 11 -> 10 -> 00` là dương.
  Mẫu đầu thiết lập pha, không đếm. Nhảy hai bit báo lỗi, không đếm;
  lấy trạng thái mới làm mốc. Count modulo 2^COUNT_WIDTH.
- `encoder_pair.sv`: hai encoder, snapshot nguyên tử mỗi SNAPSHOT_CYCLES.
  Mặc định `SINGLE_OUT=1`, dùng `left_out/right_out`; A/B không dùng. Chọn
  `SINGLE_OUT=0` để dùng `left_ab/right_ab` qua `quadrature_decoder` như trước.
  Snapshot lấy count/timestamp trước cập nhật cùng cạnh; sequence tăng mỗi
  mẫu, snapshot_valid pulse một clock. Status bit0/1 là invalid sticky
  trái/phải, bit2/3 là decoder đã có mốc; reset xóa sticky.
- `pulse_counter.sv`: một OUT, đếm **cạnh lên** sau mốc khởi tạo,
  không đếm xung giả nếu boot HIGH. Đếm uint32, period và age; không có chiều.
- `pulse_encoder_pair.sv`: 2 OUT trái/phải, lọc độc lập, snapshot count /
  period / age / flags nguyên tử 10ms; dùng bit STATUS **v2** riêng.

Dùng bộ đồng bộ/lọc từ [common](../common/README.md). Mặc định FILTER_N=3,
count/timestamp32, sequence16, snapshot270.000 tick (10 ms tại27MHz).
INVERT_LEFT/RIGHT chỉ đổi quy ước chiều A/B. Ngưỡng lọc phải chọn theo
PPR/RPM/dạng xung thực, không được loại xung hợp lệ ở tốc độ cao nhất.

Ở mode một OUT, invalid sticky bằng 0; bit2/3 vẫn báo đã có mốc. Một đường
OUT không thể tự phát hiện mất xung hoặc cảm biến kẹt mức. Link thêm cờ mode
ở `encoder_status[4]` trong STATUS: 1=một OUT, 0=A/B X4. Motion cần kiểm tra
cờ này, lấy `delta=(new-old) mod 2^32`, rồi tính
`RPM=60*delta*CLK_HZ/(pulses_per_wheel_rev*delta_timestamp)`.
Delta timestamp cũng lấy modulo32 và phải khác 0; kiểm tra độ mới/hợp lệ
của snapshot trước khi dùng. Chiều mong muốn không thay cho chiều thực đo.
Với đĩa 20 khe gắn trực tiếp trục ra, một cạnh lên/khe cho 20 xung/vòng;
cần đếm thực tế để hiệu chuẩn, không nhân X4 như A/B. Chọn cửa sổ dài hơn
10 ms khi tốc độ thấp để giảm lượng tử hóa; không chia hoặc PID trong RTL.
Hai mức HIGH/LOW phải ổn định đủ FILTER_N mẫu; đo xung thật trước khi chốt lọc.

Trạng thái: đã có testbench/reset/nhiễu/wrap/snapshot và tổng hợp generic.
Chưa đo encoder thật; Motion chịu trách nhiệm chính sách lỗi/khởi tạo encoder.
Script: `yosys -s fpga/synth_encoder.ys`, chạy từ root kho sau khi có
`fpga/build/`. Top toàn lõi: [drive_core.sv](../drive_core.sv).
