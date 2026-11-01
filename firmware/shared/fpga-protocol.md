# Motion–FPGA wire protocol v1

Liên kết riêng, UART full-duplex 115200 8N1, logic 3,3 V, idle HIGH. Clock
đánh giá 27 MHz; bộ chia làm tròn 234 tick/bit, baud FPGA khoảng 115384,6
(+0,16%). Các số nhiều byte và CRC truyền little-endian, UART truyền LSB trước.
CRC chỉ phát hiện lỗi đường truyền, không xác thực người gửi.

## Frame

| Offset | Trường | Số byte |
| --- | --- | --- |
| 0 | Preamble `A5 5A` | 2 |
| 2 | Version `01` | 1 |
| 3 | Type | 1 |
| 4 | Payload length, không tính header/CRC | 1 |
| 5 | Session uint32; zero nghĩa là chưa có phiên | 4 |
| 9 | Sequence uint16 | 2 |
| 11 | Payload | theo type |
| 11 + length | CRC16 | 2 |

CRC-16/CCITT-FALSE: polynomial `0x1021`, init `0xFFFF`, refin/refout=false,
xorout=`0x0000`; tính từ version đến hết payload. Check `123456789` = `29B1`.
Preamble không được escape; byte giống preamble trong nội dung là dữ liệu.

| Type | Hướng | Payload | Tổng byte |
| --- | --- | --- | --- |
| `01` HELLO | Motion -> FPGA | rỗng | 13 |
| `02` ARM_ZERO | Motion -> FPGA | rỗng, yêu cầu arm ở duty zero | 13 |
| `03` CMD | Motion -> FPGA | flags8, direction8, duty_left16, duty_right16 | 19 |
| `04` DISABLE | Motion -> FPGA | rỗng | 13 |
| `05` CLEAR_FAULT | Motion -> FPGA | rỗng | 13 |
| `80` STATUS | FPGA -> Motion | bảng dưới | 31 |

CMD: flags phải zero, direction chỉ dùng bit0 trái/bit1 phải, 0=thuận,
1=ngược; bit7..2 phải zero. Duty mặc định 0..1350 tick HIGH/chu kỳ, không phải %.
Top xe `drive_core` mặc định `ALLOW_REVERSE=1`; guard/link dùng độc lập vẫn
mặc định 0 và có thể khóa lùi bằng cấu hình. Direction `00` tiến, `11` lùi,
`01` trái ngược/phải thuận (quay trái), `10` trái thuận/phải ngược (quay phải).
Lệnh sai bất kỳ trường nào bị loại cả cặp. Đổi chiều vẫn qua zero/setup;
định nghĩa thuận/ngược cần đúng với adapter và cách lắp từng bên motor.

STATUS payload18 byte: left_count32 ở +0, right_count32 ở +4, timestamp32 ở
+8, snapshot_seq16 ở +12, safety_state8 ở +14, fault16 ở +15,
encoder_status8 ở +17: bit0/1 invalid A/B sticky trái/phải, bit2/3 đã có mốc,
bit4 là mode (1=một OUT, 0=A/B X4); bit7..5 zero. Bit4 dùng bit dự phòng của
v1, không đổi version/length/offset/CRC. Motion phải kiểm tra cờ mode thay vì
mặc định mọi count đều có dấu.
Đây là điều chỉnh từ payload17/frame30 trong đề xuất trước để không mất
trạng thái encoder. Header sequence bằng snapshot_seq, không tăng khi gửi
lại snapshot cũ. State/fault từ `safety_fsm`; mã và trình tự ARM/clear ở
[hợp đồng an toàn](fpga-safety.md), link không tự tạo FSM.
Mỗi frame31 mất khoảng 2,69 ms; 100 Hz chiếm 31.000 bit/s mỗi chiều TX.

Mode một OUT: count32 là số cạnh lên không dấu, modulo2^32; tăng khi có xung
bất kể chiều lệnh, motor đang bật hay thả trôi. Mẫu đầu không sinh xung.
Motion lấy delta không dấu modulo32 và chia số xung/vòng đã hiệu chuẩn cùng
delta timestamp để tính độ lớn tốc độ. Không có thông tin chiều quay thực;
chiều lệnh chỉ là dự định, không phải phép đo. Invalid bits bằng 0 không chứng
minh sensor còn hoạt động. A/B giữ quy ước X4/có dấu và cờ lỗi như trước.

## Parser và giao diện RTL

RX chỉ nhận type01..05 và đúng length cố định; không nhận STATUS quay ngược.
Khoảng cách byte tối đa dưới 54.000 tick (2 ms); toàn frame phải xong trước
135.000 tick (5 ms), tính từ byte A5 mở đầu. Đạt hạn tại cùng tick có byte:
timeout thắng. Framing error/break hoặc `context_load` hủy frame đang nhận.
Frame lỗi không tạo `frame_valid`, không ghi command, không gia hạn watchdog.

Parser streaming giữ header/payload6 byte, không có FIFO frame32 byte. Các
trường xuất ra chỉ có nghĩa khi `frame_valid=1`; chúng có thể đổi trong lúc
nhận nhưng guard chỉ commit sau CRC. Khi lỗi, parser tìm lại A5/5A, có xử lý
A5/A5/5A. Một frame tốt nằm trong frame bị cắt có thể bị mất; sau lỗi/timeout
parser nhận lại frame tốt kế tiếp. Motion nên ngừng phát ít nhất 5 ms rồi
handshake lại sau reconnect; không giả định tìm được mọi preamble nằm lồng.

TX nhận nguyên tử snapshot + session/state/fault khi `snapshot_valid &&
snapshot_ready`; giữ nguyên đến hết frame. Không có queue: snapshot đến lúc
busy bị bỏ và báo `snapshot_dropped` một clock. `byte_valid/data` giữ nguyên
khi downstream chưa ready; CRC/index chỉ tiến khi handshake. Busy serializer
kết thúc khi byte CRC cuối được UART nhận, UART vẫn phải phát đủ stop bit.
`context_load` hủy serializer cũ; UART có thể hoàn tất byte đang phát, Motion
phải loại frame thiếu CRC/sai phiên. Không tăng snapshot_seq để che mẫu mất.

## Ranh giới an toàn, phiên và sequence

`fpga_link` không có PWM/permit, không tự arm hoặc tự cấp phiên từ HELLO.
HELLO chỉ báo đề nghị session khác zero cho FSM. FSM an toàn phải xác minh
handshake hai chiều/chống frame cũ sau reset rồi cấp `active_session`,
`session_active`, `sequence_base` bằng `context_load` một clock. Tín hiệu này
đồng thời flush parser/TX và bỏ sự kiện đến cùng clock. Khi đổi/hủy phiên phải
`context_load`, không chỉ thay giá trị session. Reset bắt đầu không có quyền
chạy; không buộc các đầu vào quyền này HIGH ở top thực tế.

Guard chấp nhận ARM_ZERO/CLEAR_FAULT khi phiên đúng và sequence mới; việc có
thực hiện hay không thuộc FSM. CMD còn cần `command_enable` từ FSM ARMED và
mọi trường hợp lệ. Delta modulo16 phải `0 < delta < 32768`; mốc đầu là
sequence_base. Chỉ sự kiện hợp lệ nêu trên cập nhật mốc. CMD sai/disabled
không tiêu thụ sequence; duplicate/cũ/sai phiên không phát command_valid.

DISABLE có CRC/format đúng luôn tạo yêu cầu giảm quyền, không phụ thuộc phiên
hay sequence và không đổi mốc; không thể dùng DISABLE để cấp lại quyền.
HELLO không đổi mốc. Sự kiện mang session/sequence đã latch cùng pulse.
Guard chỉ phát sự kiện, `safety_fsm` khởi tạo watchdog khi ARM_ZERO và chỉ
gia hạn bằng CMD mới hợp lệ khi ARMED; timeout thắng CMD đến đúng hạn.

Session32 tự nó không chống buffer cũ sau reset cả hai đầu. Đã bổ sung GPIO
recovery_req/recovery_ack và trình tự STATUS ARM_PENDING trước Motion permit;
xem [hợp đồng an toàn](fpga-safety.md). `status_sent/status_session/status_state`
của link xác nhận sau stop bit CRC cuối, không phải khi serializer nhận xong
snapshot. Phần này đã được thử bằng model, chưa nghiệm thu ARM trên xe.

## Vector chung

[fpga-vectors.hex](fpga-vectors.hex) lưu mỗi vector một word256 bit: byte cao
nhất là độ dài, 31 byte thấp chứa frame, byte thấp nhất phát trước; phần dư
zero. Thứ tự/tên và dữ liệu nằm trong `tools/fpga_protocol.py`, CRC dùng
`binascii.crc_hqx` độc lập RTL. Chạy `python tools/fpga_protocol.py` để kiểm
tra fixture, `--write-vectors` chỉ khi chủ động đổi đặc tả. Testbench đọc cùng
fixture; Python tests phát hiện fixture lệch reference. Chưa có firmware Motion.
