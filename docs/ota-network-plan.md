# AP+STA / OTA simplev1 — kế hoạch đã duyệt

Ngày 10/11/2026, chủ dự án giao áp dụng bản review tại
`D:/Download/AW-Car_simplev1_KeHoach_APSTA_OTA_REVIEW.md` và xác nhận:
**lái xe chỉ qua AP AW-CAR / 192.168.4.1; router chỉ AI, OTA và log**.
Nhánh làm việc: `codex/simplev1-ota`, từ `fff2940`; main/skeleton giữ mốc nghiệm thu.

## Ranh giới

- Manual: điện thoại → AP Motion → `/ws` → core → SPI/FPGA; không qua router.
- Brain dùng STA cho Xiaozhi; AI gửi UART sang Motion theo mode/timeout hiện hành.
- Quản trị qua STA sẽ có service riêng có xác thực; không tái sử dụng owner `/ws`.
- Không GUI laptop, Arduino Core, thay chân, đổi SPI/RTL/PID, audio/OLED hoặc timeout500ms.
- Hostname không tự tạo OTA. `.local` cần mDNS; hostname DHCP hiện chỉ là bước chuẩn bị.
- Bản đang phát triển chưa có management server/OTA receiver; không quảng cáo service chưa có.

## Cổng kiểm thử và checkpoint

| Mốc | Trạng thái hiện tại | Điều kiện trước mốc tiếp |
| --- | --- | --- |
| 0: build identity/baseline | Đã sửa hash bao gồm sdkconfig.defaults; có hash sdkconfig sinh ra | Hai ESP build được, regression và baseline có phạm vi rõ |
| 1: Motion AP+STA | Có source/build, đã nạp thử app qua USB; chưa nghiệm thu mạng | Test AP Manual độc lập, STA có IP/mất router/reconnect và so latency |
| 2: AP-only control | Đã chặn local socket không thuộc AP tại `/`, handshake và frame `/ws` | Test trực tiếp từ STA kể cả giả Host/Origin; AP vẫn giữ/nhả/STOP đúng |
| 3: discovery/log | Chưa triển khai | Poll log nhỏ có giới hạn, không tranh phiên điều khiển; fallback IP |
| 4: Brain OTA | Chưa triển khai | Xác thực/đúng board, local health không cần cloud, update lỗi/rollback thật |
| 5: Motion OTA | Chỉ có bảng phân vùng ứng viên chưa kích hoạt | USB migration giữ dữ liệu, MAINTENANCE khóa MOVE/công suất, rollback thật |
| 6: Arduino compatibility | Mới đối chiếu uploader chính thức | Receiver phải thực sự tương thích; binary vẫn build ESP-IDF |
| 7: A/B | Chưa thực hiện | p99≤3ms/max≤10ms là mục tiêu input→SPI; button→PWM/STOP đo riêng |

Theo cổng kiểm thử trong bản review, không mở OTA hoặc thay partition/bootloader trên
board trước khi hoàn thành kiểm mạng/điều khiển và chuẩn bị migration. Mỗi mốc có diff,
test, báo cáo; chưa PASS phần cứng phải ghi đúng trạng thái chờ.

## AP+STA đang thử

Form Wi-Fi hiện gửi credential UART sang Brain và xếp hàng lưu vào namespace
`simple_sta` của Motion. Phản hồi `queued` chỉ nói đã nhận yêu cầu; STATUS có kết quả
riêng cho từng board. Lỗi/lưu Wi-Fi không được gọi là đã nối Internet/Xiaozhi.

Chỉ task network quản lý retry. Một attempt chờ association/DHCP tối đa15s;
backoff1/2/4/8/16s, sau5 failure nghỉ60s giữa attempt. Khi có mục tiêu chuyển động,
không bắt đầu attempt mới và hủy attempt đang kết nối; chờ idle2s mới thử lại.
Kết nối STA đã hoạt động không bị ngắt bởi thao tác lái. Không pin lwIP CPU vì chưa
có kết quả A/B để giữ thay đổi đó. AP/STA vẫn chung radio, không cam kết jitter0.

`getsockname()` và IP interface AP là kiểm tra quyền đường lái. Host/Origin vẫn giữ
whitelist; chúng không đủ để xác định interface. GET `/` qua STA trả403; WS qua STA
bị từ chối kể cả khi client giả Host/Origin của AP. STA chưa có API quản trị ở mốc này.
ESP-IDF6.1 tạo HTTP socket IPv6 khi LWIP_IPV6 bật; địa chỉ IPv4 có thể có dạng
`::ffff:192.168.4.1`. Bộ lọc nhận IPv4 thuần và IPv4-mapped IPv6, từ chối IPv6 khác.
Native test kiểm cả AP/STA dạng mapped; cần thêm thử trên board vì test host trước
đã chưa bao phủ đúng socket ESP-IDF và bản nạp đầu chặn nhầm AP.

Từ laptop đang ở router, dùng `python utils/probe_ap_boundary.py --ip <Motion-STA-IP>`
để thử bốn request chỉ GET/handshake; không phát MOVE, không chuyển Wi-Fi laptop.

## Nguồn tham khảo

- [ESP-IDF6.1 OTA/rollback](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/system/ota.html).
- [Arduino espota uploader](https://github.com/espressif/arduino-esp32/blob/master/tools/espota.py):
  dùng invitation/auth qua UDP và ESP kết nối TCP ngược về laptop; cần receiver riêng.
  Không thể nạp project ESP-IDF bằng việc đổi tên hostname trong Arduino IDE.
