# Web Dashboard ↔ ESP32-S3 Brain — Web-v1

> **Trạng thái:** đặc tả đề xuất, **chưa** có firmware tích hợp/WebSocket server/Dashboard. Web-v1 và [Brain–Motion BM-v1](../firmware/shared/brain-motion-protocol.md) **không dùng chung frame**; Brain thẩm định lệnh JSON rồi mới tạo lệnh UART BM-v1.

## 1. Kết nối và tần suất

| Thông số | Giá trị chọn cho Web-v1 | Chú thích |
|---|---|---|
| Mạng | Wi-Fi **2,4 GHz**, TCP/IP | Dashboard (điện thoại/PC) ↔ Brain |
| Giao thức | **WebSocket + UTF-8 JSON** | Hai chiều; dùng WSS khi triển khai HTTPS/TLS; không mở điều khiển trực tiếp ra Internet |
| `MOVE` | **20 Hz** = mỗi 50 ms | Khi giữ điều khiển; đánh giá lên **50 Hz** sau đo |
| `STATUS` | **10 Hz** = mỗi 100 ms | Phát ngay thêm khi ARM/STOP/FAULT/trạng thái đổi |
| `ttl_ms` | **120 ms** mặc định, cho phép **1..250 ms** | Phù hợp giới hạn của BM-v1 |
| Web dead-man timeout | **150 ms** nếu không có MOVE mới hợp lệ | Brain phải thu hồi quyền, yêu cầu dừng; mốc đề xuất cần đo |
| Motion / FPGA | Motion lease ~120 ms; FPGA CMD watchdog **50 ms** | Các lớp độc lập; **không** cộng thành bảo đảm thời gian dừng |

Các mốc là cấu hình bắt đầu thử nghiệm, **không phải đo đạc AW Car**. Nhấn/nhả nút gửi ngay theo sự kiện, không chờ vòng 50 ms. JSON nhỏ không phải yếu tố quyết định độ trễ; cần đo Wi-Fi, scheduling và hàng đợi.

## 2. Web → Brain: field lệnh

| Field | Kiểu | Giá trị hợp lệ / đề xuất | Ý nghĩa |
|---|---|---|---|
| `type` | string | `CLAIM` / `ARM` / `MOVE` / `STOP` / `CLEAR_FAULT` / `RELEASE` | Loại thao tác |
| `seq` | uint32 | `0..4294967295`; tăng theo lệnh mới trong **phiên Web** | Chống xử lý trùng/cũ |
| `v_mm_s` | integer | `0..32767` **về kiểu BM-v1**; giới hạn thực theo xe sau hiệu chuẩn | Vận tốc tiến, mm/s |
| `omega_mrad_s` | integer | `-32768..32767` về kiểu BM-v1; giới hạn thực theo 2 bánh không lùi | Tốc độ quay; dương rẽ trái |
| `deadman` | boolean | `true` chỉ khi người dùng đang giữ điều khiển | Nhả/mất focus → dừng |
| `ttl_ms` | uint16 | `1..250`; mặc định **120 ms** | Hạn dùng lệnh Motion kiểm soát |

- `MOVE` bắt buộc **đủ 6 field** trên; chỉ nhận nếu đúng phiên Web đã xác thực, `seq` mới, `deadman=true`, đúng giới hạn vận tốc và trạng thái cho phép. Brain **không** truyền thẳng JSON/duty PWM tới FPGA.
- `CLAIM` / `ARM` / `STOP` / `CLEAR_FAULT` / `RELEASE` cần `type` và `seq`, **không** chứa tốc độ giả. CLAIM xin quyền độc quyền; ARM chỉ yêu cầu ARM, không mở driver tức thì; CLEAR không tự ARM lại.
- Brain chỉ cho **một phiên điều khiển** đã xác thực, gắn với WebSocket hiện tại; reconnect phải xin lại quyền, không tự phát lại lệnh cũ. WebSocket hoặc trường `seq` **không phải cơ chế xác thực**.
- Với STOP, Brain ưu tiên giảm quyền ngay kể cả seq trùng/cũ (không cho tăng quyền); RELEASE bỏ quyền điều khiển. Nếu bị ngắt kết nối hoặc tab ẩn, tự thu hồi quyền / để Motion tự hết lease; không phát lệnh cache như lệnh mới.

**Ví dụ MOVE** (chỉ minh họa dữ liệu, `250 mm/s` không phải tốc độ xe đã đo):

```json
{
  "type": "MOVE",
  "seq": 125,
  "v_mm_s": 250,
  "omega_mrad_s": 0,
  "deadman": true,
  "ttl_ms": 120
}
```

## 3. Brain → Web: field ACK và STATUS

| Field | Kiểu | Giá trị / chú thích |
|---|---|---|
| `type` | string | `ACK` / `STATUS` |
| `last_seq` | uint32 / null | Seq Web cuối đã **xử lý tại Brain**; null nếu chưa có |
| `result` | string | `OK` / `REJECTED` / `BUSY` / `BAD_RANGE` / `BAD_SEQUENCE` / `NOT_OWNER` / `UNSAFE` |
| `motion_state` | string | `DISARMED` / `ARMING` / `ARMED` / `FAULT` |
| `fault_flags` | uint16 | `0..65535`, các bit lỗi; 0 = không có bit lỗi |
| `v_est_mm_s` | integer / null | Vận tốc đo/ước lượng (mm/s); null khi số đo không hợp lệ |
| `omega_est_mrad_s` | integer / null | Tốc độ quay ước lượng (mrad/s); null khi không hợp lệ |
| `battery_mv` | uint16 / null | Điện áp pin (mV), null khi chưa đo |
| `encoder_age_ms` | uint16 / null | Tuổi mẫu encoder, null khi chưa có mẫu |
| `telemetry_age_ms` | uint16 / null | Thời gian Brain chưa nhận được STATUS Motion **mới**; đồng hồ Brain |
| `lease_active` | boolean | true khi kết nối Web còn quyền điều khiển |
| `status_flags` | uint8 | `0..255`: cờ hợp lệ/tươi BM-v1; không tự suy ra từ duty |

**ACK** xác nhận Brain xử lý lệnh Web, **không** chứng minh Motion/FPGA đã áp dụng lệnh; muốn xác nhận chạy thực cần phản hồi Motion phù hợp. Nếu telemetry lỗi thời phải hiện `STALE/DISCONNECTED`, không coi số đo cũ là dữ liệu thời gian thực. Giá trị null không được hiển thị thành 0 km/h hay 0 mV.

**Ví dụ STATUS** khi Brain chưa có telemetry Motion hợp lệ:

```json
{
  "type": "STATUS",
  "last_seq": 125,
  "result": "OK",
  "motion_state": "DISARMED",
  "fault_flags": 0,
  "v_est_mm_s": null,
  "omega_est_mrad_s": null,
  "battery_mv": null,
  "encoder_age_ms": null,
  "telemetry_age_ms": null,
  "lease_active": false,
  "status_flags": 0
}
```

`result=OK` nghĩa Brain xử lý lệnh Web hợp lệ; trạng thái `DISARMED` vẫn có nghĩa **không được phép cấp motor**.

## 4. Hợp đồng an toàn & tích hợp

1. Brain phải **xác thực** chủ điều khiển trước khi cấp quyền, giới hạn kích thước JSON (khởi đầu **≤512 byte**), trường bắt buộc, loại dữ liệu, thứ tự `seq` và tốc độ gửi; một phiên chủ duy nhất. Không coi kết nối cùng Wi-Fi là xác thực.
2. Brain đổi MOVE hợp lệ thành **BM-v1** `SET_TWIST(v_mm_s, omega_mrad_s, source_mode=2, ttl_ms)` với **session/sequence UART riêng**; không đưa `seq` Web thẳng xuống UART. Voice và Web phải được Brain phân xử.
3. Bản đầu **không chạy lùi/quay tại chỗ**; yêu cầu tốc độ nhóm trái/phải suy ra từ `v,omega` phải không âm và dưới trần sau hiệu chuẩn. `W_eff`, `V_MAX` chưa có số đo — không tự đặt giới hạn vật lý giả.
4. Web gửi STOP ngay khi nhả nút, mất focus hoặc đổi chế độ; Brain tự thu hồi sau timeout **150 ms** dù không thấy STOP; Motion còn lease riêng **120 ms** theo SET_TWIST hợp lệ; FPGA watchdog riêng **50 ms** nếu không nhận CMD hợp lệ. E-stop + safety gate độc lập UART/MCU/FPGA.
5. Chưa nghiệm thu cho đến khi test mất Wi-Fi/socket, ẩn tab, đổi chủ, duplicate/seq cũ, queue TCP bị trễ, overload CPU, reset Brain/Motion và thời gian driver tắt trên phần cứng.

## 5. Ghi ngay vào Draw.io

- **Giao thức:** `Wi-Fi 2.4 GHz · WebSocket JSON · Web-v1 (spec)`
- **Web → Brain:** `type (CLAIM/ARM/MOVE/STOP/CLEAR/RELEASE), seq (u32), v (mm/s), omega (mrad/s), deadman (bool), ttl (120 ms)`
- **Brain → Web:** `ACK/STATUS: last_seq, result, state, fault, v_est, omega_est, battery, encoder_age, telemetry_age, lease, flags`
- **Rate:** `MOVE 20 Hz (50 ms), STATUS 10 Hz (100 ms), Brain timeout 150 ms`

**Chưa làm:** WebSocket server, Dashboard UI, xử lý Web-v1 → BM-v1 và kiểm chứng độ trễ trên xe.
