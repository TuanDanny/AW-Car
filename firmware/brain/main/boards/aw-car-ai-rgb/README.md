# AW-Car Brain — WS2812 báo trạng thái

Board profile vẫn mang tên `aw-car-ai-rgb`/`aw-car-ai-rgb-128x64` để giữ
cấu hình và baseline stock. Pixel GPIO48 hiện dành riêng cho báo trạng thái;
toàn bộ tool AI và điều khiển RGB Web thử nghiệm trước đây đã được xóa.

| Phần cứng | GPIO |
| --- | --- |
| SSD1306 I²C SDA/SCL | 41/42 |
| INMP441 WS/SCK/SD | 4/5/6, nguồn3V3, L/R=GND |
| MAX98357A DIN/BCLK/LRC | 7/15/16 |
| WS2812 / BOOT | 48/0 |
| UART Brain TX/RX | 17/18 → MotionRX14/TX13, GND chung |

`status_led.h/.cc` sở hữu duy nhất pixel/RMT. `OnStateChanged` không ghi
LED; Xiaozhi không đổi màu khi nghe/nói/idle. Không còn `rgb_light` hoặc
self.rgb_light tools. Dashboard chỉ đọc `indicator`, không có command RGB.
Mic, OLED, BOOT, nút nghe Web, tool xe và AP+STA giữ nguyên chức năng.

Ưu tiên đỏ (fault Motion hoặc STATUS quá hạn150ms sau khi đã có dữ liệu),
xanh dương (chưa Wi-Fi/STATUS hoặc chờ AI trong modeAI), xanh lá (các điều
kiện Brain được theo dõi khỏe). Wi-Fi ở đây là STA cóIP; AP AW-CAR có thể
vẫn phục vụ dashboard khi LED xanh dương. Idle/STOP/không ARM không là lỗi.

Web status task kiểm cờ mỗi50ms ngoài control/UART/HTTP handler, chỉ ghi
RMT khi đổi màu; cùng màu đổi reason chỉ cập nhật metadata. Độ sáng12/255,
lỗi ghi retry tối đa1Hz. LED lỗi không reset firmware hoặc cấp quyền motor.
Xem [contract và kiểm thử LED](../../../../../docs/status-led.md).

Build từ firmware/brain sau export ESP-IDF6.1:

```powershell
$env:CMAKE_NINJA_FORCE_RESPONSE_FILE = '1'
python scripts/build.py aw-car-ai-rgb --name aw-car-ai-rgb-128x64 --language zh-CN
```

Profile cặp board thật dùng `AWCAR_MOTION_IS_SIMULATED=n`, không suy từ màu
LED rằng xe đã ARM, motor chạy hoặc cloud thực sự nghe được tiếng loa.
