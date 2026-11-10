# Contract simplev1 (version 1)

Không tương thích BM-v1/FPGA-v2 cũ. Mọi số nhiều byte little-endian. CRC16/CCITT-FALSE:
poly 0x1021, init 0xFFFF, refin/refout false, xorout 0. `123456789` → 0x29B1.

## Hành vi

Mode Manual=0, AI=1. Action Neutral=0, Forward=1, Backward=2, Left=3, Right=4.
Left/Right là quay tại chỗ. Speed 0..100%, mặc định 30%; duty = round(speed*1350/100).
Mapping: Forward=(+,+), Backward=(-,-), Left=(-,+), Right=(+,-).
Boot Manual/0; STOP thắng MOVE cùng đợt xử lý, chuyển Manual và tăng generation.
Đổi mode/trang mới cũng tăng generation và hủy mục tiêu. Web ngắt trong Manual về 0;
AI không phụ thuộc Web. Thả nút về 0; nút mới thay nút cũ, không khôi phục nút cũ.
Manual hết hạn 500 ms. AI duration=0 là 1000 ms, khác 0 phải trong 100..3000 ms.
AI mới thay cũ. Brain mất UART/cloud trong AI → 0/Manual. Manual không phụ thuộc Brain.
FPGA mất lệnh hợp lệ 500 ms về 0. Đảo cực phải có 40 ms neutral.

OTA Motion dùng MAINTENANCE cục bộ, không phải ARM/Gate của kiến trúc cũ:
vào/ra đều tăng generation, hủy mục tiêu và về Manual0; trong lúc này từ chối
mode/MOVE. GPIO10LOW và ACK hai gói SPI duty0 là điều kiện trước ghi flash.
Reason bổ sung ở cuối enum là Maintenance=15; wire layout/version không đổi.

## UART: 460800 8N1

Khung: `53 31 | version:u8=1 | type:u8 | length:u8<=128 | seq:u16 | payload | crc:u16`.
CRC tính từ version đến hết payload (không gồm magic). Parser nhận từng byte, không
chờ gom khung, chịu mảnh/garbage và tự tìm lại magic. seq phục vụ trace, không handshake.
Console USB riêng, không chèn text vào UART điều khiển.

| Type | Hướng | Payload |
| --- | --- | --- |
| 0x01 BrainState | Brain→Motion, 5 Hz | 40 byte: flags:u8, wifi_result:u8, rssi:i8, reserved:u8=0, ipv4[4], ssid[32] (zero padded) |
| 0x02 AiMove | Brain→Motion | generation:u32, action:u8, speed:u8, duration_ms:u16 |
| 0x03 Stop | Brain→Motion | Rỗng; luôn được xử lý, không đòi generation |
| 0x81 MotionState | Motion→Brain, 5 Hz | 28 byte, bảng dưới |
| 0x82 Listen | Motion→Brain | enabled:u8 (0/1) |
| 0x83 WifiConfig | Motion→Brain | ssid_len:u8 (1..32), pass_len:u8 (0..64), ssid, password; không NUL |

BrainState.flags: bit0 Wi-Fi có IP, bit1 cloud connected, bit2 listening, bit3 speaking.
wifi_result: 0 không yêu cầu, 1 đang lưu/kết nối, 2 đã có IP, 3 lỗi.
MotionState: offset0 generation:u32; 4 mode:u8; 5 action:u8; 6 speed:u8; 7 reason:u8;
8 left:i16; 10 right:i16; 12 fpga_link:u8; 13..15 zero; 16 left_count:u32;
20 right_count:u32; 24 applied_seq:u16; 26..27 zero.
AiMove chỉ hợp lệ trong AI và đúng generation. Brain gắn generation vào phiên nghe
ngay khi bắt đầu, không cập nhật generation của callback đang chờ sau STOP/đổi mode.
Phiên hội thoại cũ vẫn nói chuyện; phiên lái mới phải bắt đầu lượt nghe mới.

## SPI: 32 byte full-duplex, mode 0, 1 MHz, MSB first

Motion master SPI2, polling/no DMA, duy nhất control task truy cập. CS setup/hold
ít nhất 2 us; khoảng giữa giao dịch ít nhất 2 us. Chu kỳ nền 5 ms, lệnh mới gửi ngay.
SPI không phải luồng UART: mỗi lần CS thấp là đúng một khung, thiếu/thừa byte bị bỏ.

TX: bytes0..1=`53 31`; 2 version=1; 3 reserved=0; 4 seq:u16;
6 left:i16; 8 right:i16; 10..29 reserved=0; 30 CRC:u16 (bytes0..29).
Duty signed -1350..1350. Sai magic/version/length/range/reserved/CRC không đổi duty và
không làm mới watchdog. Lệnh chỉ commit nguyên tử khi CS lên sau đủ 256 bit.

RX: bytes0..1=`53 52`; 2 version=1; 3 flags; 4 applied_seq:u16;
6 left_count:u32; 10 right_count:u32; 14 left_period_ticks:u32;
18 right_period_ticks:u32; 22 left_age_ticks:u32; 26 right_age_ticks:u32;
30 CRC:u16 (bytes0..29).
Flags: bit0 timeout, bit1 left_seen, bit2 right_seen; còn lại 0.
period=0 đến khi có hai cạnh lên; age=0 khi chưa có cạnh, sau đó saturate ở UINT32_MAX.
Đơn vị tick 27 MHz, count uint32 wrap. Một OUT không đo chiều.

RX là snapshot đóng băng trong toàn giao dịch, phản ánh lệnh trước; không thể ACK lệnh
TX chưa nhận đủ CRC. Motion kiểm CRC và applied_seq tiến triển, không coi buffer cũ
là liên kết sống. Master reset được phép bắt đầu seq mới; không có ARM/session SPI.

## WebSocket JSON (Motion)

HTTP `/`, WS `/ws`, không PIN/cookie. AP AW-CAR/123456789, 192.168.4.1.
Chỉ interface AP được mở dashboard/lái xe; kiểm tra local socket IP ngoài Host/Origin.
STA/router chỉ dành cho AI và quản trị, không nhận MOVE/mode qua `/ws`.
Chỉ một socket điều khiển; socket mới stop/Manual rồi thay socket cũ. Origin cùng host.

Ví dụ: `{"t":"drive","action":"forward","speed":30}`; action forward/backward/left/right.
`{"t":"neutral"}` khi nhả; `{"t":"stop"}`; `{"t":"mode","mode":"ai"}`;
`{"t":"listen","enabled":true}`; `{"t":"wifi","ssid":"...","password":"..."}`;
`{"t":"status"}` mỗi 100 ms. Drive gửi ngay và lặp 50 ms khi giữ, không gửi hàng đợi cũ.
Web tự xóa phím khi blur/hidden/close và không auto reconnect/restore MOVE.
Status trả mode/action/speed/duty/generation, SPI/Brain/cloud, counts, reason/build ID.
`maintenance:true` khóa nút lái/mode và xóa thao tác đang giữ; STOP vẫn gửi được.
Không có tốc độ/pin giả, ARM hay báo target/ACK thành số đo xe đã chạy.
