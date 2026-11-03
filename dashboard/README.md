# Web Dashboard

Dashboard HTML/CSS/ES modules thuần, cùng asset trên ESP32 và PC simulator.
Manual/AI, Cho phép/DỪNG/Xóa lỗi, sáu hướng, tốc độ, RGB, transcript/tool events và
telemetry có cờ hợp lệ. Không CDN/framework hoặc JSON đi thẳng xuống FPGA.
Contract: [Web-v1](web-brain-protocol.md).

## Dùng dashboard trên iPhone

1. Nối Wi-Fi `AW-CAR`, mở `http://192.168.4.1` bằng Safari. Nhập PIN hiện
   trên OLED; giữ BOOT lâu để hiện lại. PIN dashboard khác mật khẩu Wi-Fi,
   đổi sau mỗi reset. Chỉ giữ một tab dashboard đang kết nối.
2. RGB hoạt động bằng các nút bật/tắt, ba màu sẵn hoặc ô chọn màu; không
   cần ARM. Nút **Bắt đầu/kết thúc nghe** tương đương nhấn/nhả BOOT ngắn.
   Đợi trạng thái đang nghe rồi nói tiếng Trung; xem nhận dạng, trả lời và
   tool trong nhật ký. Ví dụ: `开红灯`, `开绿灯`, `开蓝灯`, `关灯`.
3. Manual dùng sáu nút giữ để lái, nhả về 0; mức tốc độ mặc định 30%.
   Chỉ mở khi **Cho phép** đã được Motion xác nhận. Khi chưa nối Motion,
   các nút lái khóa và telemetry ghi “Chưa có dữ liệu”.
4. Chọn AI trên dashboard rồi xin phép Motion để nhận hành động xe ngắn.
   Manual vẫn trò chuyện/RGB và nhận DỪNG. Đổi mode, DỪNG hoặc mất liên
   kết an toàn sẽ thu quyền; phải Cho phép lại. Quyền AI tối đa 5 phút.
5. **Xóa lỗi** chỉ sáng khi Motion báo FAULT còn mới và chưa có quyền chạy.
   Sau khi nguyên nhân đã hết, bấm để yêu cầu phục hồi; thành công vẫn phải
   **Cho phép** lại. Không nhả E-stop rồi tự ARM. Chưa ghép gate/motor thật.
6. Để Safari ở trước màn hình khi điều khiển Manual. Ẩn tab/khóa màn hình
   hoặc mất Web sẽ dừng và bỏ ARM. Reconnect không phát lại nút đang giữ.

Ngày03/11 đã thử thực trên iPhone Safari: đăng nhập và giữ WebSocket ổn định,
RGB và nút nghe trên dashboard được người dùng xác nhận hoạt động.
Chưa nghiệm thu lái xe vì chưa có Motion/gate/motor trong vòng thử này.

## Chạy giả lập

Từ root: Python3.13, Node và compiler host C++17 (`g++`/`clang++` hoặc `CXX`).
Windows có thể dùng LLVM-MinGW chính thức trong `build/toolchain/`; không
dùng cross-compiler Xtensa để tạo chương trình chạy trên PC.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r dashboard/requirements-dev.txt
python tools/build_brain_host.py
.venv/Scripts/python.exe dashboard/simulator.py --port 8767
```

Mở `http://127.0.0.1:8767`, mã **123456 chỉ cho simulator localhost**.
Firmware dùng SSID `AW-CAR`; mật khẩu AP giữ trong NVS hoặc đặt cố định
bằng `CONFIG_AWCAR_AP_PASSWORD` ở sdkconfig cục bộ. PIN dashboard vẫn sinh
mỗi boot; không dùng credentials simulator cho ESP32. Simulator không mô phỏng CPU, Wi-Fi/I²S/
FreeRTOS, PID, FPGA hay motor. Mỗi instance chỉ nhận một WebSocket.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests
node --test dashboard/control.test.mjs
```

Thử tải bằng instance riêng, không giành kết nối với trình duyệt:

```powershell
.venv/Scripts/python.exe dashboard/simulator.py --port 8768
.venv/Scripts/python.exe tools/brain_soak.py --url http://127.0.0.1:8768 --seconds 1800 --report build/brain/soak.json
```

`/api/lab` chỉ có trong simulator để tiêm voice/mất mạng/tiến thời gian;
không có trong firmware. Soak dùng thời gian thực; test hạn5phút dùng đồng
hồ ảo riêng, không trộn thành số đo độ trễ thật. Trace Motion giữ256 frame,
sự kiện100, mẫu benchmark tối đa40.000.

## Brain thật + Motion PC test peer

Sau khi có bộ USB–UART **TTL3,3V**, nối Brain TX17→RX adapter,
RX18←TX adapter, GND chung. Không nối5V hoặc ngõ RS232 vào GPIO.
Giữ console/USB Brain riêng, chưa nối driver/motor.

```powershell
.venv/Scripts/python.exe tools/motion_serial_peer.py --port COM_ADAPTER
```

Peer chỉ xác thực BM-v1/lease, số đo tốc độ/pin invalid. Profile mặc định
`AWCAR_MOTION_IS_SIMULATED=y` để ghi nhãn giả lập. Brain đã được nạp ngày
03/11/2026, kiểm tra boot/AP+STA; chưa thử UART vật lý hoặc peer Motion.
Xem [bằng chứng](../docs/brain-dashboard-verification.md).

## Bổ sung ghép Motion 0.1

Core Motion mới ở `codex/esp32-s3-motion`, không thay PC peer mặc định ở đây.
Motion bản COM7 hiện LOCKED, chưa nối UART/gate; không dùng Cho phép như
bằng chứng motor sẽ chạy. Cấu hình `AWCAR_MOTION_IS_SIMULATED` chỉ bỏ nhãn
sau khi đã ghép và xác nhận dữ liệu thật, không sửa để che nhãn giả lập.
Computer use đã thử Xóa lỗi, giao diện hẹp và socket đóng; xem
[báo cáo bổ sung](../docs/brain-motion-clear-verification.md).
