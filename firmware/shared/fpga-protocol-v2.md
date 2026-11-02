# Motion ↔ FPGA protocol v2 — encoder 1 OUT mỗi bên

**Trạng thái:** Có RTL FPGA và mô phỏng unit/serializer/parser/top logic ở `fpga/rtl/drive_core_single_out.sv`; **chưa có firmware ESP32-S3 Motion nhận v2, chưa nạp Tang Nano 9K hoặc đo thực**. Protocol v1 A/B tại [fpga-protocol.md](fpga-protocol.md) vẫn giữ regression; KHÔNG trộn v1/v2.

## 1. Framing và UART

- UART **115200 8N1**, TX/RX logic 3,3 V, full-duplex; CRC-16/CCITT-FALSE poly `0x1021`, init `0xFFFF`, CRC low-byte trước. Số nhiều byte little-endian.
- Frame: `A5 5A | version8=02 | type8 | length8 | session32 | sequence16 | payload(N) | crc16`; tổng 13+N.
- Motion gửi version **02**: `HELLO 01` (0 byte), `ARM_ZERO 02` (0), `CMD 03` (6), `DISABLE 04` (0), `CLEAR_FAULT 05` (0). CMD duty/direction, session/sequence, CRC, Safety FSM và watchdog như v1. **Parser v2 chủ động từ chối version 01**.
- FPGA trả `STATUS 0x80`: payload **34 byte**, frame **47 byte**. Danh định 47×10/115200 ≈ **4,08ms/frame**; 100Hz dùng ~47kbit/s chiều TX (40,8% baud). Đây là ngân sách, không phải đo thực tế.

## 2. STATUS v2 — payload 34 byte

| Offset | Field | Kiểu | Ý nghĩa |
|---:|---|---|---|
| +0 | `left_count` | uint32, 4B | Số cạnh lên trái (không có chiều), modulo 2³² |
| +4 | `right_count` | uint32, 4B | Số cạnh lên phải |
| +8 | `timestamp` | uint32, 4B | Tick FPGA mặc định 27 MHz, modulo 2³² |
| +12 | `snapshot_seq` | uint16, 2B | Seq snapshot 10ms, tăng dù TX drop |
| +14 | `safety_state` | uint8, 1B | Safety FSM |
| +15 | `fault` | uint16, 2B | Bitmask lỗi Safety FSM |
| +17 | `encoder_status` | uint8, 1B | Các bit v2 (bảng dưới) |
| +18 | `left_period_ticks` | uint32, 4B | Chu kỳ giữa 2 cạnh lên trái; 0 nếu chưa có đủ 2 |
| +22 | `right_period_ticks` | uint32, 4B | Chu kỳ giữa 2 cạnh lên phải |
| +26 | `left_age_ticks` | uint32, 4B | Thời gian từ cạnh lên trái cuối, tính tick |
| +30 | `right_age_ticks` | uint32, 4B | Thời gian từ cạnh lên phải cuối, tính tick |

**Bits encoder_status v2:**

| Bit | Field | Khi =1 |
|---|---|---|
| 0 | `LEFT_PERIOD_VALID` | Đủ 2 cạnh trái, age chưa bão hòa |
| 1 | `RIGHT_PERIOD_VALID` | Đủ 2 cạnh phải, age chưa bão hòa |
| 2 | `LEFT_INITIALIZED` | Đã biết mức logic trái sau đồng bộ/lọc |
| 3 | `RIGHT_INITIALIZED` | Đã biết mức logic phải |
| 4 | `SINGLE_OUT_MODE` | Luôn bằng 1 trong v2 này |
| 5 | `LEFT_EDGE_SEEN` | Có cạnh trái từ baseline/timeout |
| 6 | `RIGHT_EDGE_SEEN` | Có cạnh phải từ baseline/timeout |
| 7 | `DIRECTION_KNOWN` | **Luôn bằng 0** (không đo được chiều) |

`age_ticks = 0xFFFFFFFF`: chưa có cạnh hoặc tuổi đã bão hòa (~159s ở 27MHz). Khi bão hòa, `PERIOD_VALID`=0. `period_ticks=0` nếu chưa có hai cạnh; chỉ đọc period nếu flag hợp lệ. Snapshot giữ nguyên tử count/period/age/status; TX busy thì bỏ snapshot mới, không giữ nguyên timestamp để giả tạo dữ liệu mới.

## 3. Tín hiệu vật lý và cách ước lượng

- IR V2 trái `OUT_L` → **chuyển mức 5V→3,3V** nếu OUT thực lên 5V → `left_out`.
- IR V2 phải `OUT_R` → chuyển mức tương tự → `right_out`. GND chung. Dùng GPIO thuộc I/O bank 3,3V của Nano 9K, xác minh theo chân/board thực; không đưa 5V vào FPGA.
- Không có pha A/B thứ hai. GPIO xung **không phải UART/I²C/SPI**. Bộ đồng bộ 2 FF, lọc mặc định **FILTER_N=3 tick FPGA**; chỉ đếm **cạnh lên** sau LOW đã lọc. Boot ở HIGH chỉ lấy mốc, không tính xung giả.
- Một OUT đo được **độ lớn tốc độ**, không đo được chiều quay thực. Không suy ra chiều bằng `direction` của PWM; Motion phải đánh cờ dữ liệu tốc độ/omega hợp lệ theo cảm biến đáng tin.
- Với **D** là đường kính lăn thực (m), **N** là số cạnh được đếm mỗi vòng bánh thực, tần số clock **27MHz**:
  - `speed_mps ≈ π × D × 27000000 / (N × period_ticks)`.
  - `speed_mps ≈ delta_count × π × D / (N × delta_seconds)`.
  - `N` phải đo trên bộ đĩa/motor thực; không coi nhãn 20 khe chắc chắn tương ứng 20 xung/vòng tại bánh. 10ms snapshot vẫn có thể quá thô ở tốc độ thấp; dùng period/age khi ít xung.

## 4. An toàn và việc còn lại

- GPIO Safety độc lập `motion_permit`, `fpga_permit`, `safety_ok`, `gate_fault_n`, `recovery_req/ack`, `gate_clear` và watchdog CMD **50ms** không đổi. Mất xung encoder không tự mở gate.
- Motion phải **triển khai parser STATUS v2**, xác nhận version/status bit4 và bit7, xử lý period/age validity, trần tốc độ, xe đứng yên vs đứt dây/đĩa kẹt; firmware hiện chưa triển khai.
- Chưa có pinout/constraint, PnR/STA cho Tang Nano 9K và mạch gate/driver vật lý; không coi mô phỏng là xe đã hoạt động.
- V1 golden vectors/bench vẫn giữ. Test v2: `tb_pulse_encoder_pair`, `tb_single_out_protocol`, `tb_single_out_v2_rx`, `tb_single_out_top`.

## 5. Chú thích Draw.io

- **Encoder → FPGA:** `2× GPIO OUT_L/OUT_R · level 5V→3,3V · FPGA 27MHz · snapshot 100Hz · 1 OUT/bên (không đo chiều)`
- **Motion ↔ FPGA:** `UART 115200 8N1 · Protocol v2/02 · CMD duty/dir · STATUS payload 34B/frame 47B · CRC16`
