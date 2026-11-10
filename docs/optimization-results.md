# Tối ưu nhỏ simplev1: kết quả trước/sau

Ngày11/11/2026. Baseline main `97f9fcd`; source tối ưu `79b4204` trên
`codex/simplev1-ota`. Bản B đã nạp riêng Motion. Sau số đo và xác nhận người dùng,
chủ dự án duyệt đưa lên main thành prototype v2 qua PR và CI.
Kế hoạch và lý do chọn ở [review](optimization-review.md); số liệu đầy đủ ở
[comparison](../data/optimization-comparison.json), [121 mẫu điện thoại](../data/optimization-phone-samples.json)
và [benchmark Web](../data/optimization-web-render.json).

## Kết luận

Giữ hai thay đổi nhỏ: Web chỉ ghi DOM khi giá trị đổi và dùng chung formatter;
Motion xem Waking/Reversing là đang có ý định chuyển động để trì hoãn retry STA.
Đã giảm công việc Web và không phát hiện hồi quy trong các ca đã chạy.
Trung vị phản hồi trên điện thoại thấp hơn trong lượt B, **p95 vẫn305,2ms**:
chưa đạt toàn bộ ngân sách độ trễ đề xuất, chưa chứng minh hết jitter Wi-Fi.

Không triển khai cache quantile hoặc tăng STATUS20Hz: chưa có số đo chi phí MCU
đủ để đổi thêm. Không thêm task, queue, dependency firmware hoặc thuật toán lái.

## A/B trên điện thoại thật

Laptop giữ mạng router; điện thoại lái qua AW-CAR/192.168.4.1, Manual30%, VM ngắt,
chưa motor. Cùng điện thoại/vị trí theo hướng dẫn. Observer `latency.js` giữ nguyên
byte, cùng poll100ms. Chỉ đo PointerEvent→send và PointerEvent→STATUS đúng setpoint,
không đo ngón tay chạm vật lý hoặc cạnh PWM. Giữ tất cả8mẫu A đầu và52mẫu bổ sung;
không bỏ outlier để làm đẹp số. B có61mẫu sau khi tải lại bản Web mới.

| Mốc, ms | A — trước, N60 | B — sau, N61 |
| --- | ---: | ---: |
| Bấm→gửi p50 | 10,0 | 10,1 |
| Bấm→gửi p95 | 22,3 | 13,7 |
| Bấm→gửi p99 / max | 220,6 | 68,4 |
| Bấm→STATUS p50 | 218,6 | 102,2 |
| Bấm→STATUS p95 | 305,2 | 305,2 |
| Bấm→STATUS p99 / max | 426,8 | 405,5 |

Trung vị bấm→STATUS thấp hơn53,25% trong hai lượt đo này. Không gán toàn bộ mức
giảm cho sửa DOM: A/B tuần tự, không crossover ngẫu nhiên; hai thay đổi được ghép
chung và trạng thái radio/browser có thể khác. Số mẫu mỗi hướng13–17 còn ít;
p95/p99 theo từng hướng thường chính là mẫu lớn nhất. JSON giữ cả kết quả từng
hướng và budget cũ, không nới ngưỡng. Chưa có số đếm lượt hủy/mất phản hồi từ
serial nên đây không phải tỷ lệ giao lệnh thành công.

Motion mailbox→trước SPI: p99 cửa sổ cuối A0,587ms/B0,764ms, đều đạt ngân sách
nội bộ3ms; max quan sát2,004/2,282ms dưới10ms. A chạy lâu trước đó, B vừa reboot:
max từ boot và các cửa sổ256input này không phải phép so tốc độ tương ứng từng
click. Không kết luận Motion xử lý nhanh hơn từ bảng điện thoại.

## Công việc Web trên host

Chromium desktop viewport390×844, hai lượt3giây mỗi bản, HTML production qua
HTTP/WebSocket simulator native riêng, cùng instrument và chỉ neutral. Không
phát MOVE tự động lên board. Mỗi bản nhận60STATUS.

| Chỉ số | Trước | Sau |
| --- | ---: | ---: |
| DOM mutation / STATUS | 25,0 | 3,1 |
| Tổng mutation | 1.500 | 186 |
| Callback STATUS p50 | 0,3ms | 0,1ms |
| Callback STATUS p95 | 0,5ms | 0,2ms |
| Callback STATUS max | 1,7ms | 0,3ms |

Mutation giảm87,6%. Callback chỉ là JavaScript đồng bộ, không gồm paint và không
đại diện CPU Android hay Wi-Fi. Phép thử getter/setter inject trong review cũ là
thăm dò riêng; bảng này dùng HTML đã sửa thực tế.

## Bằng chứng giữ flow

- 26/26ca browser sạch, chạy riêng một client/suite: bốn hướng, giữ/nhả/cancel,
  nhiều nút, STOP, mode/generation, stale STATUS, backpressure, touch, takeover,
  reconnect không replay, AI3giây và render giá trị mới.
- 28unit test đạt, một suite browser opt-in được skip trong discovery; browser
  đã chạy riêng. Native52.301assertion, Brain context127check. Test dùng đúng
  predicate Runtime, kiểm Waking/Reversing duty0, pending/OTA, STOP/idle và STA
  online. Không dùng GPIO giả để báo radio thật đã đạt.
- Build ESP-IDF6.1 của Brain và Motion đạt. Brain image vẫn đúng SHA cũ; chỉ nạp
  Motion `simplev1-33495b1fe7e0`, SHA256
  `d62c815ba037b262a162d1d82b11ef8073add9432509eb2b908e1136582baab9`.
  Đọc ngược Flash đúng; NVS, partition table, otadata và motioncfg giữ nguyên.
- Người dùng xác nhận trên bản B: giữ/nhả10giây, STOP, AI mặc định3giây,
  OLED/loa vẫn bình thường. Log B kết thúc AI neutral, duty0/0, driver_gpio0.
- Cửa sổ B264giây: không tăng SPI/UART error, không thấy panic/watchdog.
  A có0lỗi SPI tăng trong cửa sổ đầu và2trong cửa sổ bổ sung. Khoảng giữa hai
  capture không liên tục; không lấy chênh counter cả đời làm số lỗi của lượt đo.

Giữ20Hz input,10Hz STATUS, Manual timeout500ms, wake1ms, đảo chiều40ms, SPI1MHz,
PWM20kHz và source Brain/FPGA. So byte xác nhận handler STATUS/event/timeout cùng
observer đo không đổi. STA đã online vẫn được giữ khi lái; helper chỉ sửa phân
loại busy, chưa loại trừ khe input đã lấy nhưng snapshot chưa publish hoặc độ
trễ polling network100ms.

## Giới hạn và trạng thái phát hành

Chưa chạy lại chu kỳ OTA/rollback, soak30phút, thử radio khi STA mất mạng, đo
cạnh PWM, motor hoặc nguồn2S trong đợt này. Không thay firmware Brain hay RTL nên
không tổng hợp Gowin lại. Kiểm tra cấu trúc và diff đạt; log thô, Wi-Fi, ASR và
Flash dump vẫn ở thư mục private được Git bỏ qua.

Main97f9fcd là mốc A để đối chiếu. Theo duyệt tiếp11/11, đưa source lên main,
tag prototype-v2 sau CI và xóa hai nhánh tác vụ. Giữ các tag baseline; không coi
kết quả này là nghiệm thu động cơ hoặc độ trễ toàn xe.
