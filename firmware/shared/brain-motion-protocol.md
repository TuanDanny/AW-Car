# Brain–Motion wire protocol v1 — đặc tả field đã chốt cho bản đầu

**Trạng thái:** CHỐT ĐẶC TẢ để Brain và Motion triển khai tương thích; **đã triển khai phía Brain, codec dùng chung, golden vector và Motion test peer PC; chưa có firmware Motion thật hoặc nghiệm thu hai board**. Giao thức này **khác** liên kết Motion–FPGA tại [fpga-protocol.md](fpga-protocol.md). Bản đầu TT 4WD lái theo hai nhóm, không có bốn PID độc lập; Xiaozhi/Web không phát PWM.

## 1. Transport và cấu trúc chung

- UART **full-duplex 115200 baud, 8N1, 3,3 V**, TX nối RX chéo, GND chung. Tần số gửi lệnh Brain mục tiêu **20–50 Hz**; STATUS Motion đề xuất **20 Hz**, đồng thời gửi sau sự kiện HELLO/ARM/STOP/FAULT. 50 frame/s là **ngân sách tối đa mỗi chiều** cho v1.
- Các số nguyên nhiều byte dùng **little-endian**; số có dấu dùng two's complement. Không gửi float/JSON ở tầng UART.
- CRC-16/CCITT-FALSE: poly `0x1021`, init `0xFFFF`, refin/refout=false, xorout `0x0000`. Tính từ **Version** đến hết Payload, **không** gồm 2 byte preamble. CRC truyền **low byte trước**. Test chuẩn `123456789 → 0x29B1`.
- Byte header giống Motion–FPGA để tái sử dụng logic **đóng gói** (hai protocol độc lập, không gửi frame SET_TWIST trực tiếp sang FPGA):

| Offset từ đầu frame | Field | Byte | Kiểu/giá trị |
|---:|---|---:|---|
| 0 | `SOF` | 2 | `A5 5A` |
| 2 | `version` | 1 | `uint8 = 0x01` |
| 3 | `type` | 1 | Mã loại bản tin bên dưới |
| 4 | `length` | 1 | `uint8`: số byte payload **chính xác** theo type |
| 5 | `session_id` | 4 | `uint32` khác 0 cho phiên điều khiển |
| 9 | `sequence` | 2 | `uint16`, của bên gửi, tăng theo frame mới |
| 11 | `payload` | N | Theo `type` |
| 11+N | `crc16` | 2 | CRC16 little-endian |

**Tổng byte = 13 + N**; tối đa **30 byte** cho các type v1 dưới đây. Frame length/type sai, version khác 1, CRC sai → loại, không áp dụng lệnh và không gia hạn lease. Parser cần timeout và resync sau frame lỗi; giới hạn khung v1 là **32 byte**. Không dựa vào CRC để xác thực điều khiển Web/người dùng.

## 2. Loại bản tin — mã cố định

| Type | Hướng | Payload | Tổng byte | Chức năng |
|---|---|---:|---:|---|
| `0x01 HELLO` | Brain → Motion | 0 | 13 | Mở session mới khi Motion đang DISARMED |
| `0x02 ARM_REQUEST` | Brain → Motion | 0 | 13 | Yêu cầu Motion làm quy trình ARM an toàn, **không tự mở driver** |
| `0x03 SET_TWIST` | Brain → Motion | 7 | 20 | Gửi vận tốc tiến / quay mới |
| `0x04 STOP` | Brain → Motion | 0 | 13 | Yêu cầu dừng, bỏ arm/lease ngay |
| `0x05 CLEAR_FAULT` | Brain → Motion | 0 | 13 | Yêu cầu phục hồi chủ động khi nguyên nhân lỗi đã hết |
| `0x80 STATUS` | Motion → Brain | 17 | 30 | ACK/REJECT và telemetry |

## 3. SET_TWIST payload (7 byte, Brain → Motion)

| Offset payload | Field | Kiểu | Đơn vị / giới hạn | Vì sao chọn |
|---:|---|---|---|---|
| +0 | `v_mm_s` | `int16` (2B) | **mm/s**, phiên bản đầu có dấu; cho phép tiến/lùi trong giới hạn cấu hình, chưa hiệu chuẩn xe | Motion cần vận tốc thẳng, không cần Brain tính PWM; integer tránh khác biệt float và giữ độ phân giải 1 mm/s |
| +2 | `omega_mrad_s` | `int16` (2B) | **mrad/s**, dương = quay trái, âm = quay phải | Cho Motion tính hai setpoint bánh theo `v_left=v-omega*W_eff/2`, `v_right=v+omega*W_eff/2` |
| +4 | `source_mode` | `uint8` (1B) | `1=VOICE(Xiaozhi)`, `2=WEB(thủ công)`; còn lại reject | Biết nguồn lệnh cho phân xử, theo dõi lỗi; **không** là chứng cứ được phép arm |
| +5 | `ttl_ms` | `uint16` (2B) | **1..250 ms**, mặc định Brain gửi **120 ms** | Một lệnh không được sử dụng mãi nếu đứt nguồn điều khiển; Motion đo bằng **đồng hồ Motion khi nhận** |

Ví dụ `v=0,250 m/s`, `omega=+0,400 rad/s`, từ Web, TTL=120 ms ⇒ payload little-endian: **`FA 00 90 01 02 78 00`**.
Golden frame tham khảo với `session_id=0x12345678`, `sequence=2`, `type=0x03`:
`A5 5A 01 03 07 78 56 34 12 02 00 FA 00 90 01 02 78 00 76 9B`
(20 byte; CRC `0x9B76` tính bằng Python `binascii.crc_hqx`). Đây là **vector đặc tả**, chưa phải bài test firmware tích hợp.

**Guard bắt buộc:** Motion không nhận `SET_TWIST` khi chưa ARMED, không có lease Brain hợp lệ, mất nguồn an toàn/cảm biến thiết yếu, phiên sai, sequence cũ, TTL ngoài miền hoặc target trái/phải vượt giới hạn. Bản Brain hiện cho phép tiến/lùi/quay tại chỗ: `v` và hai target bánh có thể âm; Motion phải kiểm tra giới hạn riêng và ACK/REJECT rõ. Giới hạn LAB của Brain/PC peer là |v|<=200 mm/s, |omega|<=1000 mrad/s, không phải giới hạn xe đã đo. `W_eff` là tham số cơ khí phải hiệu chuẩn, không phải field truyền mỗi lệnh.

**Sequence:** Trong cùng phiên, một lệnh mới nếu `0 < ((seq_new - seq_last_accepted) mod 65536) < 32768`; duplicate/cũ không gia hạn lease. Brain phải tăng sequence cho yêu cầu *thực sự mới* từ một phiên/source hợp lệ; không đổi sequence để phát lại lệnh cache khi Web/voice mất nguồn. `session_id` là số khác 0, do Brain sinh mới (ưu tiên RNG) mỗi lần handshake; Motion chỉ thay phiên khi DISARMED và giữ motor bị khóa. Sau reset/STOP/FAULT không tự áp dụng setpoint cũ.

**Lease:** TTL bắt đầu lúc Motion **nhận trọn frame hợp lệ** theo đồng hồ cục bộ của Motion; Motion không cho phép lớn hơn 250 ms. HELLO/ARM/STATUS không gia hạn lệnh chuyển động. Khi lease quá hạn, Motion dừng cập nhật lệnh, hạ đường `motion_permit` tới gate phần cứng và xử lý DISABLE tới FPGA best-effort. Mất nguồn Brain/Web không được chữa bằng cách UART task tự tạo lệnh giả. E-stop/gate an toàn **độc lập cả hai MCU**.

## 4. STATUS payload (17 byte, Motion → Brain)

| Offset payload | Field | Kiểu | Vì sao chọn |
|---:|---|---|---|
| +0 | `last_req_seq` | `uint16` (2B) | Sequence yêu cầu Brain **cuối đã được xử lý** (kể cả reject) để đối chiếu phản hồi |
| +2 | `applied_seq` | `uint16` (2B) | Sequence SET_TWIST **cuối được nhận áp dụng**; không đánh đồng CMD bị reject với CMD đã nhận |
| +4 | `result_code` | `uint8` (1B) | Kết quả xử lý `last_req_seq`; lý do từ chối nếu có |
| +5 | `motion_state` | `uint8` (1B) | DISARMED/ARMING/ARMED/FAULT để Brain hiển thị và không tưởng đã ARM xong |
| +6 | `fault_flags` | `uint16` (2B) | Xác định nguồn lỗi để chẩn đoán, không chỉ báo lỗi chung chung |
| +8 | `v_est_mm_s` | `int16` (2B) | Vận tốc xe **ước lượng từ cảm biến**, không phải giá trị yêu cầu |
| +10 | `omega_est_mrad_s` | `int16` (2B) | Tốc độ quay **ước lượng**, chỉ tin khi cờ hợp lệ tương ứng bật |
| +12 | `battery_mv` | `uint16` (2B) | Điện áp pin mV, dễ hiển thị và phát hiện sụt nguồn; chưa có đo thì cờ invalid |
| +14 | `encoder_age_ms` | `uint16` (2B) | Tuổi mẫu encoder/snapshot theo đồng hồ Motion; tránh trình bày số đo cũ là số mới |
| +16 | `status_flags` | `uint8` (1B) | Cho Brain biết trường nào đáng tin và tình trạng lease/permit |

Giá trị khởi tạo: `last_req_seq=0xFFFF`, `applied_seq=0xFFFF`, `result_code=0xFF (NONE)`. `encoder_age_ms=0xFFFF` khi chưa có mẫu; khi không đo được pin, `battery_mv=0` **và** `BATTERY_VALID=0`. `sequence` ở header STATUS thuộc bộ đếm **riêng của Motion**, tăng khi phát STATUS; **không** chứng minh encoder mới.

**`motion_state`:** `0 DISARMED`, `1 ARMING`, `2 ARMED`, `3 FAULT`. `result_code`: `0 OK`, `1 BAD_STATE`, `2 BAD_SESSION`, `3 BAD_SEQUENCE`, `4 BAD_PAYLOAD_OR_RANGE`, `5 UNSAFE`, `6 LEASE_EXPIRED`, `7 BUSY`, `255 NONE`. Frame không qua CRC không được tạo ACK hợp lệ.

**`status_flags`:** bit0 `V_EST_VALID`, bit1 `OMEGA_EST_VALID`, bit2 `BATTERY_VALID`, bit3 `FPGA_SNAPSHOT_FRESH`, bit4 `BRAIN_LEASE_ACTIVE`, bit5 `MOTION_PERMIT_HIGH`, bit6..7 reserved=0. Cờ tốc độ/chiều quay không được tự bật chỉ vì biết duty/chiều **ra lệnh**. Đối với encoder V2 một OUT, không suy ra chiều quay thực tế từ chiều yêu cầu.

**`fault_flags` v1** (bit bật = lỗi): bit0 E_STOP_OR_GATE; bit1 FPGA_LINK_STALE; bit2 ENCODER_INVALID_OR_STALE; bit3 CRITICAL_SENSOR_FAULT; bit4 OVERCURRENT (nếu có phần cứng đo); bit5 POWER_UNDERVOLT (nếu có đo); bit6 PID_FAILURE; bit7 INTERNAL_FAILURE; bit8..15 reserved=0. Không báo giả lỗi/sensor chưa tích hợp. Trạng thái FAULT cần phục hồi chủ động; mất lease thông thường chuyển DISARMED và có result/status phù hợp, không tự ARM.

## 5. Trình tự điều khiển, phân xử nguồn và an toàn

1. Brain (Xiaozhi hoặc Web) tạo yêu cầu, chỉ **một nguồn** có quyền điều khiển; Web cần dead-man, voice cần hành động **có thời hạn/giới hạn** chứ không ra lệnh chạy vô hạn.
2. Sau reset/mất kết nối: Motion mặc định DISARMED, gate LOW. Brain gửi `HELLO(session mới)`, nhận STATUS xác nhận; yêu cầu `ARM_REQUEST` riêng. Motion kiểm tra nguồn, E-stop/permit/cảm biến, làm handshake Motion–FPGA và chỉ trả `motion_state=ARMED` sau khi thực sự hoàn tất.
3. Brain gửi `SET_TWIST` mới theo chu kỳ (20–50 Hz dự kiến). Motion kiểm tra CRC/session/seq/TTL/giới hạn, đổi `(v,omega)` thành hai setpoint bánh, tính PID từ STATUS encoder FPGA, gửi `CMD(duty_left,duty_right,dir)` mới sang FPGA khoảng 100 Hz. FPGA lại xác thực theo **giao thức riêng** và chỉ tạo PWM khi Safety FSM cho phép.
4. Motion gửi STATUS định kỳ và khi có sự kiện; Brain dùng `last_req_seq/result_code/applied_seq`, `motion_state`, `status_flags` và `encoder_age_ms` để hiển thị, không coi STATUS cũ là chứng nhận motor đang chạy.
5. `STOP` có format+CRC đúng được phép **giảm quyền ngay bất kể session/sequence** (không cho tăng quyền hoặc tiêu thụ mốc sequence), hạ permit và bỏ setpoint; không cần chờ STATUS để tắt. `CLEAR_FAULT` chỉ là **yêu cầu**: Motion phải thấy nguyên nhân lỗi đã hết và chạy quy trình phục hồi FPGA; CLEAR thành công vẫn DISARMED và đòi HELLO/ARM mới. Khi Brain hoặc Motion mất kết nối, hết lease, reset hoặc gặp lỗi, **mạch gate riêng** đảm bảo motor không tiếp tục chạy chỉ vì UART treo.

**Không phải xác thực bảo mật:** CRC16/session/sequence bảo vệ tính toàn vẹn/chống lặp của phiên, không chứng minh Brain là thiết bị tin cậy. Web phải kiểm soát phiên điều khiển tại Brain; phân quyền từ Web/giọng nói không thể dựa trên `source_mode` do dữ liệu gửi tự khai.

## 6. Ví dụ kiểm thử bắt buộc trước khi gọi là đã triển khai

- Golden vectors HELLO, ARM_REQUEST, SET_TWIST, STOP, CLEAR_FAULT, STATUS (little-endian + CRC16 tính đúng và sai).
- Tiến/lùi/quay hợp lệ, tốc độ vượt giới hạn, `ttl_ms=0/251`, source không hợp lệ, `seq` lặp/cũ/quấn vòng, phiên khác, CRC sai, thiếu byte, độ dài sai.
- Brain reset khi Motion ARMED; Web mất dead-man; voice command hết thời hạn; STOP và CMD cùng lúc (STOP phải thắng); lệnh đúng tick hết lease; E-stop/encoder cũ/FPGA STATUS đứng yên → gate tắt.
- Kiểm tra tốc độ cập nhật và ngắt lệnh trên **hai board thật**; không lấy test giao thức Motion–FPGA làm bằng chứng Brain–Motion đã chạy.

### Chỗ dùng trong sơ đồ Draw.io

- **Trên đường kết nối:** `UART 115200 8N1 · 3.3V · Protocol BM-v1 (spec)`
- **Brain → Motion:** `SET_TWIST(v_mm_s, omega_mrad_s, source_mode, ttl_ms) + session/seq/CRC`
- **Motion → Brain:** `STATUS(last_req_seq, applied_seq, result, state, faults, v/omega, battery, age, flags)`

**Đã triển khai phía Brain:** codec C++, parser/serializer, session/ARM, host tests và PC serial peer. UART1 Brain TX=GPIO17, RX=GPIO18 là cấu hình phần mềm, chưa kiểm tra chân header thật. **Chưa thực hiện:** firmware Motion thật, liên kết hai board, deadline/gate/nguồn trên xe.

## Neutral và STOP — quyết định 03/11/2026

`SET_TWIST(0,0)` là mục tiêu đứng yên, giữ ARM nếu các lease còn hợp lệ.
`STOP` bỏ quyền chạy; phải HELLO/ARM lại. Manual chỉ chuyển tiếp yêu cầu mới
đã qua Web guard; không tạo sequence mới để tái phát một mục tiêu khác0 cũ.
AI được phát yêu cầu trong hành động tối đa3s; hết hành động phát0, trong
cửa sổ cho phép5phút chỉ giữ mục tiêu0 nếu không có hành động mới.
UART byte shape, version1, payload7/17 và CRC không đổi.
