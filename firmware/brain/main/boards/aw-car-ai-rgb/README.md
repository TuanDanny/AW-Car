# AW-Car AI RGB - F03

Board riêng dựa trên bread-compact-wifi của Xiaozhi v2.5.2 (MIT).
Danh tính board aw-car-ai-rgb, variant aw-car-ai-rgb-128x64; giữ profile stock
để đối chiếu. Không dùng OTA stock để thay bản demo này.

| Phần cứng | GPIO |
| --- | --- |
| SSD1306 128x64 I²C 0x3C SDA / SCL | 41 / 42 |
| INMP441 WS / SCK / SD | 4 / 5 / 6; VDD=3V3, L/R=GND |
| MAX98357A DOUT / BCLK / LRCK | 7 / 15 / 16; chưa thử loa |
| RGB WS2812 GRB / BOOT | 48 / 0 |

aw_car_board.cc khởi tạo OLED, audio, BOOT và bộ điều khiển RGB duy nhất.
rgb_light.h/.cc sở hữu pixel/RMT và đăng ký ba tool MCP thường, AI có thể gọi:

- self.rgb_light.set_power(on): bật dùng màu gần nhất, tắt giữ màu đã chọn.
- self.rgb_light.set_color(r,g,b): mỗi kênh 0..255; đặt màu và bật ngay.
- self.rgb_light.get_state(): trạng thái phần mềm sau lần ghi thành công.

LED tắt lúc boot; bật lần đầu dùng trắng 32/32/32. Màu/lệnh giữ trong RAM
qua nghe/nói/idle, reset về tắt. OLED tiếp tục báo trạng thái. Không đăng ký
lamp GPIO18, không khởi tạo SingleLed hoặc timer trạng thái cho pixel này.
Lỗi driver trả tool error; log APPLIED chỉ xuất sau khi ghi thành công,
không thay phép quan sát màu vật lý. Không có đường điều khiển motor.

Build từ firmware/brain trong môi trường ESP-IDF 6.1 đã export:

```powershell
$env:CMAKE_NINJA_FORCE_RESPONSE_FILE = '1'
python scripts/build.py aw-car-ai-rgb --name aw-car-ai-rgb-128x64 --language zh-CN
```

Nhấn/nhả BOOT, đợi chế độ nghe rồi nói câu tiếng Trung trong
[hướng dẫn demo](../../../docs/ai-rgb-demo.md). Build và thử thật phải được
ghi ở tài liệu đó trước khi kết luận hoàn tất demo.
