# Reset và đồng bộ input

Các module SystemVerilog dùng chung trong top và các khối chức năng:

- `reset_sync.sv`: reset active-low, assert bất đồng bộ, nhả sau hai cạnh clock.
- `input_sync_filter.sv`: đồng bộ hai FF rồi lọc cả vector bằng N mẫu ổn định.
  `FILTER_N >= 1`; valid chỉ bật sau mẫu đầu tiên đã đồng bộ/lọc.

Trạng thái: đã mô phỏng và tổng hợp generic. ASYNC_REG đánh dấu FF đồng bộ,
nhưng mô phỏng không chứng minh metastability. Cần kiểm tra mapping và
constraints CDC/reset đúng chip; không dùng bộ lọc để thay gate an toàn ngoài.
Top tích hợp ở [drive_core.sv](../drive_core.sv).

- `status_leds.sv`: observer state/fault, ưu tiên FAULT > CONNECTED > WAITING.
  Một counter và bit pha27MHz; output active-low, không có tín hiệu điều khiển
  ngược vào lõi. LED không thay gate/E-stop hoặc phát hiện mất chính clock đó.
