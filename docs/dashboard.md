# Dashboard Motion simplev1

Trang tiếng Việt tại `esp/motion/web/index.html`, một file chứa HTML/CSS/JS,
không CDN, font tải ngoài, framework hay bước build frontend. Motion phục vụ
HTTP `/` và WebSocket `/ws` trên cùng host; dùng `wss` nếu trang được mở bằng
HTTPS. AP Motion: `AW-CAR` / `123456789`, địa chỉ `http://192.168.4.1`.
Điều khiển chỉ nhận qua interface AP. Router/STA không cung cấp dashboard hoặc `/ws` lái xe.
Đọc `protocol.md` để xem contract phía Motion/Brain/FPGA.

## Sử dụng

- Trang tự mở đúng một WebSocket khi tải. Chỉ một trang được điều khiển.
  Mở tab mới làm Motion hủy mục tiêu, chuyển Manual, thay phiên cũ; tab cũ
  hiển thị `1001 · controller_replaced`. Chọn **Kết nối lại** để tạo phiên mới.
- **Manual**: giữ **Tiến**, **Lùi**, **Quay trái**, **Quay phải** hoặc W/S/A/D.
  Trái/phải quay tại chỗ, hai bên ngược dấu. Không có nút lái chéo.
- **Mức lệnh** 0–100%, mặc định 30%. Đây là phần trăm lệnh duty; không phải
  tốc độ xe đo được. Lệnh PWM trái/phải có dấu, thang ±1350.
- Nhấn **STOP** hoặc Space ngoài ô nhập để gửi STOP ngay. Motion chuyển
  Manual và đổi generation; Web chờ STATUS xác nhận, không tự báo đã dừng.
  Thanh STOP cố định dưới màn hình, kể cả khi cuộn trên điện thoại.
- **AI** khóa bốn nút Manual. STOP, đổi mode, Bắt đầu nghe và Dừng nghe vẫn
  dùng được. Web không phân xử lệnh AI và không kéo dài thời lượng AI.
- **Wi-Fi AI và quản trị** lưu mạng trên Motion và gửi tên mạng/mật khẩu tới Brain.
  Không đổi kết nối AP của điện thoại. SSID 1–32 byte, mật khẩu 0–64 byte UTF-8;
  mật khẩu trống dành cho mạng mở. Trang xóa ô mật khẩu ngay khi gửi, không
  log, lưu localStorage/cookie, ghi URL hay hiển thị lại mật khẩu. Trạng thái
  Brain trả về cho biết mạng/IP và kết quả kết nối. Không tự gửi lại khi nối lại.

## Vòng đời thao tác và kết nối

Press gửi `{"t":"drive","action":"forward","speed":30}` ngay trong sự kiện
bấm; lặp mỗi 50 ms khi giữ. Nút/phím mới thay nút cũ. Thả nút mới nhất gửi
`{"t":"neutral"}` và không khôi phục nút/phím trước; thả nút cũ không ảnh hưởng
nút mới. Không có hàng đợi MOVE hoặc khôi phục thao tác sau STOP/đổi mode.

Socket bận ngắn thì bỏ lần lặp đó, giữ thao tác vật lý; không xếp thêm MOVE.
Tắc liên tục150ms thì hủy giữ, gửi neutral và cần nhấn lại. STATUS cũng không
xếp thêm vào socket đang bận. ACK lặp không ghi lại thông báo/DOM mỗi20Hz;
nhả, cancel, STOP và deadline500ms của Motion giữ nguyên.

Pointer capture giữ được sự kiện nhả ngoài nút. Pointer cancel, mất capture,
blur, trang hidden, đóng trang và focus ô nhập đều xóa thao tác giữ. Phím repeat
không tạo lượt giữ mới. WSAD và Space không điều khiển khi đang nhập liệu.
Thay mode/generation từ STATUS cũng xóa giữ, không phát lại lệnh cũ.

Trang yêu cầu `{"t":"status"}` mỗi 100 ms. Sau 1000 ms không có STATUS hợp lệ,
Web xóa giữ và gửi đúng một neutral nếu trạng thái cuối là Manual; không gửi
STOP lặp, không gửi neutral trong AI. Phản hồi mới cho phép bấm lại nhưng không
khôi phục giữ. Deadline Manual **500 ms thuộc Motion**, độc lập heartbeat và
thời gian chạy JavaScript. Web không thay thế deadline này.

Khi WebSocket đóng, Web xóa giữ ngay, khóa nút lái, hiển thị code/reason và dữ
liệu cuối dưới dạng quá hạn. Không tự reconnect, không replay MOVE. Ngắt WS
không được hiển thị như xác nhận xe vật lý đã dừng; chỉ STATUS mới xác nhận
lệnh Motion đang báo. AI tiếp tục theo deadline riêng khi Web ngắt.

## Dữ liệu hiển thị

`status` dùng đúng shape firmware: `build`, `mode`, `action`, `speed`, `left`,
`right`, `reason`, `generation`; `fpga` gồm connected/applied_seq/count/seen;
`brain` gồm connected/wifi/cloud/listening/speaking/ssid/ip/wifi_result;
`diag` gồm UART, SPI, latency_count/p50/p95/p99/max (µs), heap (byte), uptime_ms.
Chi tiết nằm trong mục chẩn đoán thu gọn. Không có pin, tuning, ARM hoặc PIN.
Encoder một OUT chỉ đếm cạnh lên, không suy chiều từ duty.

`simulator:true` luôn hiện **MÔ PHỎNG · Không phải xe thật**. Trang không tự
tạo số đo, không giả ACK hoặc chèn logic phân xử. `result` chỉ báo nhận/từ chối
yêu cầu; mode/action/PWM vẫn lấy từ STATUS. Không echo reason thô của result
để tránh một phản hồi Wi-Fi chứa thông tin nhập bị hiển thị lại.

## Kiểm thử và ảnh

```powershell
python -m pip install -r test/browser/requirements.txt
python -m playwright install chromium
# Khởi động utils/simulator.py theo README của utils, dùng cổng 8783.
python test/browser/test_dashboard.py --port 8783
```

Suite chỉ gửi lệnh khi STATUS có `simulator:true`. Server cần FPGA/Brain/cloud
khỏe để thử cả mode AI; chạy tuần tự, không dùng chung cổng với một browser
suite khác vì cơ chế takeover. Proxy Playwright của test mất STATUS chỉ lọc
phản hồi từ server thật; không tạo dữ liệu hoặc phân xử thay lõi C++.

Ảnh sau khi chạy server thật: `test/browser/output/dashboard-desktop.png`,
`dashboard-mobile.png`, `dashboard-desktop-viewport.png`,
`dashboard-mobile-viewport.png`. Thư mục output là
bằng chứng sinh ra, không commit. `--output` đổi vị trí, `--only` lọc test.
`--layout-only` chỉ kiểm bố cục file tĩnh ở 1440/390/320 px; ảnh mang tiền tố
`layout-offline-`, không được coi là kiểm thử tích hợp điều khiển.

Các phép thử bao gồm bấm ngay, giữ 20 Hz, thả, nhiều phím, cancel/lost capture,
blur/hidden/input focus, STOP/Space, mode/listen, Wi-Fi, STATUS quá hạn Manual
và AI, takeover, refresh, reconnect tường minh, đúng dấu bốn hướng, STOP luôn
trong viewport và không tràn ngang. Browser test/build không thay nghiệm thu
FPGA, motor, reset, mất liên kết hoặc dừng vật lý trên xe.

## Trạng thái nghiệm thu

- Ngày 10/11/2026: 17/17 browser tests đạt với `simplev1-host`, server cổng
  8783 dùng lõi C++ native. Ảnh desktop/mobile đã chụp và xem trực tiếp.
- Bấm ngay và chu kỳ giữ được đo trên browser/host; không phải số đo độ trễ
  ESP32, UART, SPI hay motor. Các trường latency chưa đo hiển thị `—`.
- Layout tĩnh 1440/390/320 px, cú pháp JS/Python, README và khoảng trắng đạt.
- Lượt sửa giữ nút:22/22 ca browser đạt, gồm backpressure ngắn/dài, giữ touch3s
  và AI mặc định3s. Có tái hiện FAIL của code cũ bằng WebSocket native trước sửa;
  không dùng các số host này để công bố độ trễ Wi-Fi thật.
- Native DLL dùng tên theo hash nên chạy lại suite trong khi simulator mở được;
  unittest/cấu trúc đã được chạy lại và đạt. Browser chuẩn không cần mở COM.
- Web phần cứng đã được người dùng kiểm bốn hướng ở30%; AI trái/phải khớp log
  Motion −405/+405 và +405/−405, sau khoảng1s về0. Các số là duty/ACK, VM còn ngắt.
- Firmware/RTL và bằng chứng board tổng hợp ở [verification.md](verification.md).
