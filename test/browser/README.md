# Kiểm thử dashboard simplev1

Python Playwright, Chromium headless; kiểm tra trang thật qua WebSocket của
`utils/simulator.py`, dùng lõi C++ native. Không có bộ phân xử/xe giả bằng JS.
Mặc định server `http://127.0.0.1:8783`; simulator cần FPGA/Brain/cloud khỏe để
kiểm tra chuyển AI. Không chạy suite lên xe thật: test chủ động gửi lệnh.

```powershell
python -m pip install -r test/browser/requirements.txt
python -m playwright install chromium
python test/browser/test_dashboard.py --port 8783
```

`--url` chọn URL khác, `--output` chọn thư mục ảnh; `--only` lọc tên test.
`--layout-only` mở file HTML tĩnh và chụp bố cục offline, không kết luận về
hành vi điều khiển. Chạy bình thường chụp toàn trang `dashboard-desktop.png`,
`dashboard-mobile.png` và viewport tương ứng `dashboard-desktop-viewport.png`
(1440×1000), `dashboard-mobile-viewport.png` (390×844).
Ảnh/log sinh ra ở `output/`, được bỏ qua bởi Git. Không ghi mật khẩu vào log.

Suite có kiểm tra bấm tức thời, giữ 20 Hz, nhả ngoài nút nhờ pointer capture,
cancel, nhiều phím, không khôi phục phím cũ, blur/hidden, focus ô nhập,
STOP/Space, mode/listen, Wi-Fi, mất STATUS một lần, AI mất STATUS, tab takeover
1001/controller_replaced, refresh và nối lại tường minh. Proxy mất STATUS chỉ
bỏ bản tin từ server thật, không tự tạo phản hồi hay phân xử lệnh.

Ca18 bật MAINTENANCE qua native core: thao tác giữ bị xóa, khóa nút lái/mode và
thoát bảo trì không phát lại lệnh. Fixture `/sim/*` chỉ có trên localhost.

Ca19/20 dùng WebSocket browser thật (không proxy Playwright) để chèn bufferedAmount
bận60ms và bận kéo dài: giữ ngắn được tiếp tục, tắc dài phải nhấn lại. Ca21 giữ
touch3giây qua nhiều STATUS; ca22 xác nhận AI bỏ duration chạy3giây. Đây là kiểm
điều kiện phần mềm, không giả làm số đo Wi-Fi điện thoại thật.

Ca AI dùng `/sim/event` để kiểm tra thời lượng native, STOP/generation cũ và
AI tiếp tục khi đóng Web. Mỗi test reset simulator; không chạy đồng thời một
suite khác cùng cổng. Thời gian bấm/chu kỳ giữ đo trên browser/host, không
phải độ trễ ESP32, SPI hoặc motor.

`python -m unittest discover -s test` bỏ qua browser khi không được chỉ định;
đặt `AW_CAR_BROWSER_URL=http://127.0.0.1:8783` để chạy cùng discovery.
