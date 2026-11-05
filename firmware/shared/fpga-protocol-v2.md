# Motion ↔ FPGA protocol v2 — encoder 1 OUT mỗi bên

**Trạng thái 03/11/2026:** RTL v2 ở nhánh FPGA (`7ab91b2` trong co-sim), top `aw_car_top.sv`; đã có Motion 0.1 parser/core/ESP-IDF và co-sim UART/GPIO. **Checkout Motion từ main còn baseline RTL v1; chưa nạp/đo Tang Nano 9K hoặc motor thật**. Protocol v1 A/B tại [fpga-protocol.md](fpga-protocol.md) vẫn giữ regression; KHÔNG trộn v1/v2.

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
| +15 | `fault` | uint16, 2B | Low byte Safety FSM, high byte diagnostic sticky (mục 6) |
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
- Motion 0.1 đã có **parser STATUS v2**, xác nhận version/status bit4 và bit7, period/age validity và độ mới. Timeout không xung dùng tốc độ/độ phân giải; một OUT không chứng minh đứng yên hay chiều thực. Có thêm driver_permit độc lập; xem [safety](fpga-safety.md).
- Chưa có pinout/constraint, PnR/STA cho Tang Nano 9K và mạch gate/driver vật lý; không coi mô phỏng là xe đã hoạt động.
- V1 golden vectors/bench vẫn giữ. Test v2: `tb_pulse_encoder_pair`, `tb_single_out_protocol`, `tb_single_out_v2_rx`, `tb_aw_car_top`.

## 5. Chú thích Draw.io

- **Encoder → FPGA:** `2× GPIO OUT_L/OUT_R · level 5V→3,3V · FPGA 27MHz · snapshot 100Hz · 1 OUT/bên (không đo chiều)`
- **Motion ↔ FPGA:** `UART 115200 8N1 · Protocol v2/02 · CMD duty/dir · STATUS payload 34B/frame 47B · CRC16`

## 6. Runtime diagnostics — extension 02/11/2026

Layout vẫn34 byte/47 byte, version02. `fault[7:0]` giữ nguyên lỗi Safety FSM.
`fault[15:8]` là chẩn đoán mới, sticky từ lúc reset FPGA; HELLO/DISABLE hoặc
CLEAR_FAULT không xóa lịch sử chẩn đoán. Firmware đọc toàn bộ word16-bit,
không coi mọi bit cảnh báo là điều kiện FAULT. Đây là mở rộng các bit trước
đây chưa dùng; firmware v2 cũ cần cập nhật cách phân loại nếu kiểm tra fault==0.

| Mask | Mã | Hành động tại FPGA |
| --- | --- | --- |
| 0100 | RX_FRAME_ERROR | Cảnh báo frame/parser/CRC lỗi; lệnh lỗi không được áp dụng |
| 0200 | COMMAND_REJECTED | Cảnh báo guard từ chối phiên/sequence/duty/chiều |
| 0400 | SNAPSHOT_DROPPED | Cảnh báo TX đang bận, bỏ mẫu; sequence phản ánh mất mẫu |
| 0800 | SNAPSHOT_STALL | Không có snapshot trong2×SNAPSHOT_CYCLES; khóa driver, cần reset FPGA |
| 1000 | LEFT_ENCODER_NO_EDGE | Cảnh báo yêu cầu trái khác0 nhưng không đổi count đủ ngưỡng |
| 2000 | RIGHT_ENCODER_NO_EDGE | Cảnh báo tương tự bên phải |
| 4000 | PWM_REJECT_HISTORY | Lưu sự kiện khối PWM từ chối lệnh; Safety FSM vẫn xử lý lỗi PWM riêng |
| 8000 | INTERNAL_INVARIANT | Raw PWM khi chưa enable/đang interlock, hoặc safety_state ngoài0..5; khóa driver, cần reset |

Encoder timeout mặc định **CLK_HZ/2 =500ms tại27MHz**, không tính thời gian
DISARMED, duty yêu cầu0 hoặc interlock. Mỗi count mới reset bộ đếm chờ của
bên tương ứng, kể cả wrap. Đây là cảnh báo, không kết luận cảm biến hỏng hoặc
motor kẹt: có thể xe chạy rất chậm/tải lớn hoặc dây/đĩa có vấn đề. Motion chọn
ngưỡng/chính sách theo tốc độ tối thiểu thực, không dùng500ms như cam kết vật lý.

Snapshot stall và invariant là chốt dừng độc lập trong RTL (`diagnostic_stop`),
chặn `fpga_permit`/4 chân IN và đưa health của Safety FSM xuốngLOW. Sau đó
Safety FSM có thể chốt thêm bit0002, hủy phiên. Reset xóa chẩn đoán nhưng vẫn
cần GPIO recovery và ARM mới; UART không được tự xóa hai chốt này.

Mất clock/nguồn/UART hỏng hoàn toàn có thể khiến FPGA **không gửi được log**.
Motion vẫn phải timeout STATUS mới, hạ permit/khóa gate độc lập; E-stop phần
cứng không phụ thuộc clock. UART STATUS là log số, không chen chuỗi printf vào
luồng nhị phân. ESP32 nên in khi state/fault thay đổi, giới hạn tần suất log
để không làm nghẽn tác vụ điều khiển. Motion 0.1 đã có log giới hạn tốc độ
và console USB; chưa có log UART FPGA/gate/motor vật lý.

ESP32 chỉ xử lý sau khi CRC/version/length/session/độ mới hợp lệ. Với payload
34 byte đã kiểm tra, cách lấy trường để ghi console (đoạn ghép vào firmware thật):

```cpp
uint16_t f = uint16_t(payload[15]) | (uint16_t(payload[16]) << 8);
ESP_LOGI("fpga", "state=%u fault=0x%04x", unsigned(payload[14]), unsigned(f));
bool reset_required = (f & 0x8800u) != 0;
bool safety_fault = (f & 0x00ffu) != 0;
// Motion còn phải kiểm tra state==ARMED, lease và tuổi STATUS trước khi cho chạy.
```

Công cụ PC giải mã một frame HEX đã thu, xác thực CRC rồi xuất JSON và tên lỗi:
`python tools/fpga_protocol.py --decode-status "A5 5A ..."` (thay bằng đủ47 byte).
Đây không phải firmware ESP32 hoặc công cụ nạp/chạy motor.
