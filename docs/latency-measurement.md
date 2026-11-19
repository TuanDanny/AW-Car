# Đo độ trễ Web đến FPGA ACK

Kết nối điện thoại với AW-CAR và mở `http://192.168.4.1/#latency`. Giữ VM ngắt,
chọn Manual và ghi lại mức **Thanh ga**. Ga 20% tương ứng duty mục tiêu 56%.
Giữ mỗi nút Tiến, Lùi, Quay trái, Quay phải 0,5–1 giây rồi nhả 1 giây. Lặp đến
khi đủ ít nhất 10 mẫu mỗi hướng. Bộ đo lấy mẫu khi người dùng bấm.

| Số đo | Mốc đầu và cuối |
| --- | --- |
| Bấm → gửi | Timestamp sự kiện PointerEvent đến khi Web gửi lệnh đầu |
| Bấm → FPGA ACK | Timestamp PointerEvent đến lúc Web nhận ACK của lệnh qua WebSocket |
| Motion nhận → FPGA ACK | Thời gian trên đồng hồ Motion từ lúc nhận lệnh đến ACK SPI đã đối chiếu |
| Mailbox → bắt đầu SPI | Thời gian nội bộ Motion, đo riêng trong runtime |

ACK chủ động dùng số thứ tự để khớp lệnh. Nếu Web dùng đường phản hồi dự phòng,
thời gian có thể bao gồm nhịp thăm dò 100 ms và chờ duty về đúng mục tiêu
sau đề-pa. Dòng kết quả trên Web ghi **ACK chủ động** hoặc **ACK dự phòng**
cho mẫu vừa nhận. Ghi lại nhãn này khi lấy mẫu vì log nối tiếp dùng cùng
scope `phone_to_spi_ack` cho hai đường xác nhận.
Mẫu bị hủy hoặc quá hạn được đếm riêng. Phép đo cạnh PWM và chuyển động bánh
cần thiết bị đo riêng.

Motion ghi log nối tiếp `latency_probe` theo hướng và hai khoảng thời gian
microsecond. Có thể tổng hợp số liệu đã lưu bằng lệnh sau.

```powershell
python utils/analyze_phone_latency.py build/private/latency-phone/COM7.txt --output build/latency-phone.json
```

Ngân sách chẩn đoán trước đây là p95 ≤10 ms cho bấm → gửi và p95 ≤150 ms
cho bấm → phản hồi. [Số đo cũ](latency-results.md) và [A/B prototype v2](optimization-results.md)
dùng STATUS khớp duty, ở Manual 30% trên Web đời trước. Các số đó là mốc lịch sử
với phương pháp đo riêng. Bỏ `#latency` để tắt bộ đo.
