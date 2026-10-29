# F03: demo giọng nói điều khiển LED RGB

Chốt phạm vi ngày 29/10/2026 theo chủ dự án: dùng mic nói với Xiaozhi để
bật, tắt và đổi màu LED RGB trên ESP32-S3. Mục tiêu là chứng minh AI gọi
chức năng điều khiển ngoại vi thực. LED trên board đủ cho bước demo đầu.
Chưa triển khai điều khiển motor/UART Motion trong demo này.

## Trạng thái hiện tại

- Source stock đã build/nạp và hiển thị OLED, kết nối Wi-Fi.
- Mic INMP441 đã gắn; thử ngày 29/10 có văn bản nhận dạng và AI trả lời
  bằng tiếng Trung qua log. Chủ dự án xác nhận OLED hiện câu vừa nói và
  chọn giữ tiếng Trung. Loa chưa gắn; chưa kiểm chứng âm thanh trả lời.
- Demo dùng nhấn/nhả BOOT một lần để bắt đầu nghe từ chế độ chờ; nói
  "ni hao" sau khi mở nghe đã có nhận dạng và phản hồi trên OLED. Chưa
  nghiệm thu đánh thức bằng giọng nói; "ni hao" không phải toàn bộ câu
  đánh thức của model đang build ("ni hao xiao zhi").
- Đã thêm board aw-car-ai-rgb, variant aw-car-ai-rgb-128x64, giữ pin của
  profile stock. RGB WS2812 tại GPIO48, thứ tự GRB; boot mặc định tắt.
- AwCarRgbLight sở hữu pixel/RMT và ba tool MCP. OnStateChanged không ghi
  LED nên lệnh được giữ qua nghe/nói/idle; OLED tiếp tục báo trạng thái.
- Profile demo không đăng ký lamp GPIO18 hoặc dùng SingleLed; board stock
  bread-compact-wifi được giữ nguyên để đối chiếu.
- Build/merge và nạp đã thành công; log boot có RGB48, OLED, đăng ký ba
  tool và chuyển activating -> idle. Đang thử lệnh qua giọng nói; chỉ kết
  luận đạt khi log APPLIED khớp và chủ dự án xác nhận màu/bật/tắt thực.

## Thiết kế và cách kiểm tra

Luồng: tiếng nói -> mic -> Xiaozhi/AI -> MCP tool call -> callback trên
ESP32-S3 -> LED RGB. Không dùng việc AI nói "đã tắt" làm bằng chứng duy nhất;
cần log gọi tool, callback và quan sát LED thực đúng yêu cầu.

1. Board/variant có danh tính riêng cho OTA, giữ OLED 41/42 và mic 4/5/6;
   không thay cấu hình stock. Build bằng ESP-IDF 6.1 với --language zh-CN.
2. Chỉ một bộ điều khiển sở hữu RGB48. Màu và power lưu trong RAM, reset
   về tắt; mở lại đèn khôi phục màu trước, lần đầu là trắng 32/32/32.
3. Tool có mô tả tiếng Trung kèm ví dụ đỏ/xanh lá/xanh dương. Không mở
   quyền ghi GPIO tùy ý hoặc điều khiển motor.
4. Schema và callback kiểm tra RGB trong 0..255. Callback chỉ cập nhật
   trạng thái/trả thành công sau khi driver ghi xong; lỗi trả tool error,
   get_state báo chưa biết trạng thái nếu lần ghi trước lỗi.
5. Kiểm tra build, boot và đăng ký tool, rồi thử câu nói qua mic. Log
   AwCarRgb: APPLIED ghi power và RGB sau lần ghi thành công; trạng thái
   phần mềm và log không thay phép quan sát màu thực trên board.

Giao diện tool đã đăng ký trong profile demo:

| Tool | Tham số / hành vi |
| --- | --- |
| self.rgb_light.set_power | on: boolean; tắt xuất RGB=0, bật dùng màu đã chọn hoặc màu mặc định |
| self.rgb_light.set_color | r/g/b: số nguyên 0..255; đặt màu và bật đèn |
| self.rgb_light.get_state | Đọc trạng thái bật/tắt và màu để kiểm chứng |

Lỗi driver dùng cơ chế lỗi sẵn có của McpServer upstream (JSON-RPC error),
chưa đổi lớp MCP chung sang tool result isError=true. Không báo APPLIED
hoặc thành công khi driver lỗi; chưa thử chèn lỗi driver trên phần cứng.

## Tiêu chí thử qua mic

Nhấn/nhả BOOT một lần, đợi màn hình chuyển sang nghe rồi nói. Nếu về chờ,
nhấn BOOT để bắt đầu lượt mới. Chưa nghiệm thu nhận dạng tiếng Việt.

| Câu nói | Pinyin | Kết quả cần quan sát |
| --- | --- | --- |
| 把灯打开 | Bǎ dēng dǎ kāi | set_power(true), sáng màu gần nhất/mặc định |
| 把灯关掉吧 | Bǎ dēng guān diào ba | set_power(false), tắt cả khi AI trả lời/về chờ |
| 把红灯打开 | Bǎ hóng dēng dǎ kāi | set_color(255,0,0), đèn đỏ và bật ngay |
| 把绿灯打开 | Bǎ lǜ dēng dǎ kāi | set_color(0,255,0), đèn xanh lá |
| 把蓝灯打开 | Bǎ lán dēng dǎ kāi | set_color(0,0,255), đèn xanh dương |
| 关灯 / 开灯 | Guān dēng / kāi dēng | Hiểu cách nói ngắn, tắt/bật đúng |

Ghi kết quả từng câu, tool/giá trị trả về và xác nhận nhìn LED; không ghi
SSID, thông tin tài khoản hoặc mã kích hoạt vào repo. Khi đủ các ca bật/tắt/
đổi màu mới kết luận demo AI điều khiển ngoại vi đạt. Chưa coi đây là nghiệm
thu điều khiển xe hoặc hoàn tất toàn bộ F03.

## Bằng chứng build/nạp ngày 29/10/2026

| Hạng mục | Kết quả |
| --- | --- |
| SDK / variant | ESP-IDF 6.1 / aw-car-ai-rgb-128x64, ngôn ngữ zh-CN |
| Build / merge | Thành công, app 2.577.424 byte, phân vùng app 0x3f0000 |
| Compile time / ELF SHA | Oct 29 2026 11:54:04 / 06c72b260cd32e8865f84ca6512bdbed38b65fb80952fd2dbf8072134a99bcde |
| SHA-256 merged nguyên bản | a80a46b7fae9278da9b37f632699ea86c5b7155579eb907dadc5ee5bcd44c0cb |
| Nạp | COM3, 0x0000; esptool xác minh hash dữ liệu ghi |
| Giữ cấu hình | Sao lưu mới toàn bộ 16 MB, chỉ giữ NVS 0x9000 dài 0x4000, bảng phân vùng trùng nhau |
| Boot | Đúng tiền tố ELF mới; RGB48 tắt, OLED 41/42, ba tool đã đăng ký; activating -> idle |
| Kiểm tra repo | check_repo, 28 unittest và git diff --check đạt |
| Thử giọng nói / LED thực | Đang chờ đối chiếu log APPLIED và xác nhận từng màu từ chủ dự án |

Backup và image có NVS chỉ lưu cục bộ trong build/, không commit/upload.

Nguồn trong repo: [board demo và pinout](../main/boards/aw-car-ai-rgb/README.md),
[RGB driver/tool](../main/boards/aw-car-ai-rgb/rgb_light.cc),
[MCP usage](mcp-usage.md),
[board stock để đối chiếu](../main/boards/bread-compact-wifi/compact_wifi_board.cc).
