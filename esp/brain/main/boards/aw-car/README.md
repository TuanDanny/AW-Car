# AW-Car simplev1 hardware

Mic WS/BCLK/DIN=4/5/6, loa DIN/BCLK/LRCK=7/15/16, OLED SDA/SCL=41/42,
BOOT=0, WS2812=48; UART1 TX17/RX18 460800 tới MotionRX14/TX13.
Mic16kHz, loa24kHz, SSD1306 128×64 tại0x3C.

STA dùng SsidManager/NVS cũ, không tạo SoftAP. Credential từ Motion
được xếp hàng rồi lưu/kết nối ở task riêng, retry1..30s; không ghi password
vào log. LED chỉ thay đổi theo snapshot trạng thái, không điều khiển xe.
Quản trị HTTPS/mDNS trên STA. OTA xác nhận local init/main loop/UART, không đợi cloud;
khi nhận cập nhật sẽ vô hiệu hóa context lái và gửi STOP trước flash.
