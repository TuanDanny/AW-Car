# Web-v1 — contract Brain/Dashboard ngày03/11/2026

Có source Brain/simulator dùng chung lõi C++; dashboard/RGB/nghe đã thử
trên ESP32 và iPhone. Phần lái/CLEAR mới kiểm chứng host, chưa ghép Motion thật.
HTTP assets/WebSocket UTF-8 JSON tại AP192.168.4.1; UART riêng tuân
[BM-v1](../firmware/shared/brain-motion-protocol.md), không truyền JSON xuống FPGA.

## Phiên và lệnh

`POST /api/login {pin:string}` lấy cookie HttpOnly/SameSite=Strict. PIN6số
sinh mỗi boot, hiển thị OLED;5lần sai/30s bị hạn chế. `/api/pairing` chỉ hiện
lại mã, không cấp quyền. WS `/ws` kiểm cookie+Origin, chỉ một kết nối.
Không coi cùng Wi-Fi/sequence là xác thực. Firmware bind AP, AP dùng WPA2.
JSON tối đa512byte; số nguyên hữu hạn, không nhận bool/float thay integer.

| type | Field / hành vi |
| --- | --- |
| HEARTBEAT | Duy trì console, không tạo quyền/lệnh chạy |
| SET_MODE | `mode:Manual/AI,epoch`; STOP và đợi Motion DISARMED |
| ARM | `epoch`; HELLO phiên UART mới rồi ARM_REQUEST, đợi STATUS xác nhận |
| CLEAR_FAULT | `epoch`; chỉ Web, Motion FAULT còn mới, tăng epoch, STOP/HELLO/CLEAR rồi đợi DISARMED/fault=0 |
| MOVE | `seq,epoch,challenge,v_mm_s,omega_mrad_s,ttl_ms,deadman` |
| STOP | Dừng, thu quyền, tăng epoch; không đòi sequence mới |
| RGB | `on:bool` hoặc `r,g,b:integer 0..255`, chung driver MCP |
| CHAT_TOGGLE | Hành vi nhấn/nhả BOOT của Xiaozhi |

Mode/ARM chỉ từ dashboard. MOVE chỉ trong Manual+ARMED; deadman=false chỉ
hợp lệ khi v=omega=0. Neutral giữ ARM, STOP bỏ ARM. Giới hạn LAB |v|<=200mm/s,
|omega|<=1000mrad/s, chưa hiệu chuẩn xe. TTL1..250ms, mặc định120; timeout150ms.
Sequence uint32 mới nếu delta modulo32 thuộc(0,2^31); challenge cùng epoch
trẻ hơn120ms. Brain cấp challenge50ms, giữ3giá trị gần nhất; TCP tới muộn
không tự biến thành nguồn mới. Lệnh lỗi không gia hạn.

## Phản hồi

`ACK {last_seq,result,stage:Brain}` chỉ xác nhận Brain xử lý. Result:
OK/UNSAFE/BUSY/BAD_RANGE/BAD_SEQUENCE/STALE/WRONG_MODE. STATUS10Hz;
CHALLENGE xen kẽ50ms, STATUS cũng chứa challenge.

STATUS có `mode,authorized,switching,clearing,epoch,challenge,v,omega,v_max,omega_max`,
`motion_state,fault_flags,status_flags,last_req_seq,applied_seq,result_code`,
`telemetry_age_ms,encoder_age_ms,v_est_mm_s,omega_est_mrad_s,battery_mv`,
`ai_online,ai_remaining_ms,action_remaining_ms,reason,rgb,chat_state,data_source`.
Firmware thêm `voice_context_ready`, RX/Web counters và p95/p99 cửa sổ128mẫu
từ nhận MOVE hợp lệ tới gọi UART driver, chưa phải thời gian chân TX/motor.
Bind cloud session chưa đủ cho move: còn kiểm STT/envelope/epoch/deadline.

Số đo invalid là null. STATUS Motion phải mới theo session/sequence;150ms
thu quyền, frame đúng tick hết hạn không cứu phiên. Reconnect/STOP/reset/lỗi
đòi ARM chủ động. Header STATUS tăng không chứng minh encoder mới.

## Manual/AI

- Boot Manual/chưa cho phép. Giữ nút gửi ngay rồi20Hz; nhả gửi0 ngay. Nút
  mới thay cũ, nhả không khôi phục nút cũ. Space DỪNG khi không nhập liệu.
  Mất focus/ẩn tab/socket Manual thu quyền.
- AI chỉ lái sau chọn AI và Cho phép; quyền5phút không gia hạn. Sáu hướng,
  tốc độ0..100% mặc định30%, thời lượng100..3000ms mặc định1000ms. Hành động
  mới thay cũ, hết thời gian về0; không xếp hàng.
- Web đóng trong AI chỉ mất console. Mất Internet/Xiaozhi hoặc STATUS
  Motion thì mất quyền. Không tự đổi mode/ARM. Manual vẫn chat/RGB; AI
  không lái trong Manual. STOP luôn giảm quyền ở cả hai mode.
- Đổi mode tăng epoch, hủy mục tiêu, STOP, đợi ACK đúng STOP/DISARMED.
- Move cần đúng cloud session envelope, STT cùng phiên trong5s, callback
  không chờ quá120ms ở main và một motion tool/STT. Chống lặp64ID/phiên.
  STOP/mode đổi retire session và yêu cầu audio session mới; thiếu SID
  không được suy từ mode hiện tại. RPC stop ưu tiên ngay khi nhận.

## Bằng chứng

Host C++/HTTP/WebSocket/input tests và `tools/brain_soak.py` kiểm phần mềm.
Soak localhost đo RTT ACK và handler→mock-UART, không đo Wi-Fi/FreeRTOS/
cloud AI/GPIO/motor. Computer use dùng cùng asset. AP+STA/audio/UART TTL
thật, metadata backend và deadline vật lý cần board.

## Xóa lỗi và mất kết nối — bổ sung Motion

Xóa lỗi không cấp quyền chạy. Trong lúc `clearing`, khóa Cho phép/Xóa lỗi;
STOP mới hủy phục hồi. Brain phân biệt BUSY với reject, đòi ACK đúng seq và
trạng thái DISARMED/fault=0 trước báo thành công. Motion từ chối ARM rõ ràng
được báo `arm_rejected`, không chờ hết 500ms. Không tạo tool AI ARM/CLEAR.

Socket đóng xóa nhãn quyền cũ và khóa nút; reconnect không tự chạy. Asset HTTP
trả Cache-Control:no-store để bản giao diện cũ không còn sau nâng firmware.
Nút nghe/RGB và BOOT hiện có được giữ; chưa nạp thay đổi này lên Brain thật.
