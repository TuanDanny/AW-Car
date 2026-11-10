# Đo độ trễ bốn nút trên điện thoại

Điện thoại nối AW-CAR, mở `http://192.168.4.1/#latency`; giữ VM ngắt, chưa motor.
Chọn Manual30%. Bấm lần lượt Tiến/Lùi/Trái/Phải, mỗi nút giữ0,5–1giây và nhả1giây.
Lặp10vòng để có tối thiểu10mẫu/hướng. Trang chỉ quan sát, không tự phát MOVE.
Laptop giữ FPT và ghi COM7 bằng `utils/serial_log.py`.

Mốc A là PointerEvent.timeStamp của browser (không phải tiếp xúc ngón tay vật lý).
Mốc B là lúc gửi MOVE đầu tiên. Mốc C là khi nhận STATUS đúng hướng/duty, mode và
generation còn nguyên, seq/SPI có tiến triển. A/B/C cùng đồng hồ performance của
điện thoại; không cộng hoặc trừ clock ESP và browser. Lượt đổi mode, tắc/hủy hoặc
không xác nhận trong2giây không được ghi thành0ms.

- A→B: thời gian browser tiếp nhận và gửi thao tác.
- A→C: phản hồi setpoint phần mềm, gồm radio, xử lý Motion và poll STATUS100ms.
- Motion mailbox→trước SPI: đo riêng trong runtime, ngân sách hiện có p99≤3ms,
  max≤10ms. Counter này bao gồm MOVE/neutral/STOP/mode, không phải trace từng click.
- Cạnh PWM thật, ngắt lực kéo và chuyển động cơ khí chưa được phép suy từ C.
  Cần logic analyzer/oscilloscope hoặc mạch timestamp đầu ra để đo vật lý.

Mỗi mẫu xuất đúng một dòng `latency_probe` gồm hướng, dispatch_us, confirm_us;
không chứa credential/ASR. Phân tích:

```powershell
python utils/analyze_phone_latency.py build/private/latency-phone/COM7.txt --output data/latency-phone.json
```

Chỉ kết luận sơ bộ với N≥10 mỗi hướng. Budget chẩn đoán đề xuất: A→B p95≤10ms;
A→C p95≤150ms, p99≤200ms, max≤300ms, có tính phần poll100ms. Đây là budget của
phép thử setpoint, không phải tiêu chuẩn ngành hay giới hạn dừng vật lý. JSON
để pass=null khi thiếu mẫu. Không gọi localhost là số đo Wi-Fi ESP.

Observer là file JS riêng, chỉ tải khi có `#latency`; đường điều khiển bình thường
không chạy bộ đo. Bỏ hash và tải lại để tắt. Giữ mọi luật STOP/timeout hiện tại.
