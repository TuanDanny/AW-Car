# Brain + dashboard — mốc giả lập

Nhánh feat/f03-xiaozhi-ai, nền112914e. Giữ profile AI RGB đã thử, thêm AP+STA,
dashboard, lõi điều khiển, UART BM-v1 và tool xe có thời hạn. Không có firmware
Motion/PID hoặc motor thật. Contract: [Web](../../../dashboard/web-brain-protocol.md),
[UART](../../shared/brain-motion-protocol.md).

## Runtime

`main/aw_car/control_core` không phụ thuộc RTOS, I/O/cấp phát. Host simulator
nạp chính C++ đã compile; Python chỉ là Motion test peer/HTTP adapter.
VoiceGate cũng dùng chung để kiểm SID/STT/epoch/callback muộn. Chưa kiểm
metadata backend live; thiếu metadata thì khóa move, không ghép transcript
để bỏ qua AI. Tool stop/get_state không tăng quyền.

Control12/core1, UART11/core1, GPTimer5ms chỉ notify. Wi-Fi/TCP-IP và
audio input8/output4/codec2 giữ nền. Main Xiaozhi vẫn có đường chờ mạng nhưng
không sở hữu dừng/timeout. Latest-target không xếp hàng; STOP riêng.
Không TX ring; gửi frame tiếp sau khi frame trước hoàn tất. HTTP queue work
ở server task, tối đa một batch trạng thái chờ. Journal100 trong PSRAM,
không ghi flash. Nếu không cấp phát được journal, không lấy RAM control để
giữ log; trạng thái báo log không sẵn sàng.

AP `AW-CAR` và STA tái dùng SSID NVS; không gọi StartConfigAp upstream vì hàm
đó dừng STA. Dashboard đổi Wi-Fi khi DISARMED. STA subnet trùng192.168.4.x
bị báo lỗi. AP không cấp Internet cho điện thoại; giữ kết nối dù máy báo
không Internet. Không đổi pin OLED41/42, mic4/5/6, ampli7/15/16, RGB48, BOOT0.
UART1 TX17/RX18 chưa xác nhận header thật. Không dùng console làm UART Motion.
`AWCAR_MOTION_IS_SIMULATED=y` mặc định, không đổi partition/NVS khi build.
Giữ BOOT lâu: thu hồi quyền và hiện lại PIN một dòng; SSID/mật khẩu/AP URL
chạy trên dòng chat OLED. Nhấn/nhả BOOT ngắn vẫn bắt đầu/kết thúc hội thoại.

WebSocket có handler riêng `websocket_transport`: ESP-IDF xóa `req->uri`
giữa các request, kể cả frame sau handshake. Không route frame theo chuỗi
`/ws` và không trả HTTP response trên socket đã upgrade. PONG được đọc bỏ
đúng giới hạn; JSON chỉ nhận TEXT hoàn chỉnh tối đa512byte. Test host biên
dịch chính adapter này với stub I/O SDK, gồm1.000 frame URI rỗng.

## Build và kiểm tra

```powershell
python tools/build_brain_host.py
.venv/Scripts/python.exe -m unittest discover -s tests
node --test dashboard/control.test.mjs dashboard/connection.test.mjs
.venv/Scripts/python.exe -B -m unittest discover -s firmware/brain/scripts/tests
```

Từ firmware/brain trong ESP-IDF6.1:

```powershell
$env:CMAKE_NINJA_FORCE_RESPONSE_FILE='1'
python scripts/build.py aw-car-ai-rgb --name aw-car-ai-rgb-128x64 --language zh-CN
```

Merged image ở build/merged-binary.bin, offset0x0000. Sau mốc giả lập,
đã nạp COM3 ngày03/11/2026, sao lưu 16 MB và giữ NVS. Boot/PSRAM/OLED/audio
init và AP+STA đã kiểm tra; chưa thử HTTP/WS từ client AP, âm thanh thực
hoặc UART Motion. [Bằng chứng](../../../docs/brain-dashboard-verification.md),
[chạy simulator/USB–UART peer](../../../dashboard/README.md).

Report/log build/ảnh computer use ở build/brain của root, binary/credentials
không commit. Báo cáo bàn giao phân biệt host RTT/handler→mock-UART với độ
trễ ESP32, cloud AI hoặc thời gian motor dừng.

Bản AP+STA/backoff, WS generation/post-handshake, UART RX event và dashboard
tối giản ngày04/11 ở [báo cáo mới](../../../docs/brain-network-reliability.md).
Các hạn chế phần cứng của báo cáo mới thay trạng thái nghiệm thu lịch sử ở trên.
