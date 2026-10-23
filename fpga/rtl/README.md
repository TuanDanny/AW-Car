# RTL độc lập hãng

Lõi Verilog dùng một clock domain; không tạo clock bằng logic.

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

Mặc định 27 MHz, FILTER_N=3, count/timestamp32, sequence16, snapshot270.000
tick (10 ms). Filter là tham số thử nghiệm, phải chọn lại theo PPR/RPM/dạng
xung thực; chưa cam kết tốc độ encoder trên xe. Đảo chiều từng bánh bằng
INVERT_LEFT/RIGHT. Nguồn reset bên ngoài phải bảo đảm assert khi khởi động;
chưa có target/power-on reset riêng hãng.

Thuộc tính ASYNC_REG đánh dấu các FF đồng bộ; vẫn cần kiểm tra mapping và
constraints đúng công cụ/target. Mô phỏng không chứng minh metastability.
