# Web Dashboard

Dashboard HTML/CSS/ES modules thuần, cùng asset trên ESP32 và PC simulator.
Manual/AI, Cho phép/DỪNG, sáu hướng, tốc độ, RGB, transcript/tool events và
telemetry có cờ hợp lệ. Không CDN/framework hoặc JSON đi thẳng xuống FPGA.
Contract: [Web-v1](web-brain-protocol.md).

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
Firmware sinh PIN mỗi boot và mật khẩu AP riêng trong NVS; không dùng
credentials simulator cho ESP32. Simulator không mô phỏng CPU, Wi-Fi/I²S/
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
