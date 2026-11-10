# Brain simplev1

Xiaozhi thật, giữ tiếng Trung, mic16k/loa24k/OLED128x64. Wi-Fi STA-only dùng danh
sách NVS namespace `wifi` cũ. Chưa cấu hình thì OLED chờ và có thể cấu hình qua Web
Motion; Brain không phát AP/PIN riêng. Retry backoff1..30s; không quét chu kỳ khi
đã nối. Motion Manual không phụ thuộc Wi-Fi Internet/Brain/cloud.

BOOT hoặc nút Bắt đầu nghe trên Web bắt đầu một lượt nghe rõ ràng. Trong AI,
generation của Motion được chụp trước khi mở cloud, chỉ bind khi có session_id thật;
callback MCP giữ bản sao, kiểm lại trước truyền UART. STOP đổi generation và đưa
Motion về Manual nhưng không đóng hội thoại. Chuyển lại AI phải bắt đầu lượt nghe
mới; phiên cloud cũ không tự có lại quyền lái. Session metadata thiếu thì tool move
bị từ chối, không nới kiểm tra để làm demo.

Các tool: self.car.move(action,speed=30,duration=3000), self.car.stop,
self.car.get_state. Duration100..3000ms, bốn action forward/backward/left/right.
Không nói thời gian thì mặc định3giây; câu có thời gian riêng vẫn giữ giá trị đó.
Callback chỉ ghi mục tiêu mới nhất, không ngủ chờ. Thông báo queued không phải
bằng chứng cầu H/motor đã nhận lệnh. Không có tool ARM, đổi mode hay ghi PWM.

UART1 460800 TX17/RX18, không trộn text console. Worker nhận nonblocking, mục tiêu
đánh thức ngay; status5Hz. Console COM3 USBSerial/JTAG 115200. LED xanh lá khi có
IP và cloud, xanh dương khi đang chờ; nghe/nói không đổi màu trạng thái.

Phân vùng Brain giữ16MBv2: NVS0x9000/0x4000; otadata0xd000; app0x20000;
assets0x800000. Không xóa NVS/otadata khi nạp bản phát triển. Công cụ nạp phải kiểm
table/slot đang hoạt động, không viết raw app vào0x0000 hoặc dùng merged image phủ NVS.

Host policy test hiện kiểm127 trường hợp, không thay chứng nhận session metadata,
Wi-Fi/Internet, mic/loa/OLED thực trên firmware mới. Xem báo cáo nghiệm thu riêng.
