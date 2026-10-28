# F03: demo giọng nói điều khiển LED RGB

Chốt phạm vi ngày 29/10/2026 theo chủ dự án: dùng mic nói với Xiaozhi để
bật, tắt và đổi màu LED RGB trên ESP32-S3. Mục tiêu là chứng minh AI gọi
chức năng điều khiển ngoại vi thực. LED trên board đủ cho bước demo đầu.
Chưa triển khai điều khiển motor/UART Motion trong demo này.

## Trạng thái hiện tại

- Source stock đã build/nạp và hiển thị OLED, kết nối Wi-Fi.
- Mic INMP441 chưa gắn; chủ dự án để thử giọng nói cho lần sau.
- Profile bread-compact-wifi khai báo RGB tại GPIO48, dùng SingleLed/WS2812
  với thứ tự GRB; cần kiểm tra LED thực trên board trước khi chốt demo.
- SingleLed hiện báo trạng thái: nghe đổi đỏ, nói đổi xanh lá, idle tắt.
- LampController đăng ký self.lamp.turn_on/turn_off/get_state, nhưng điều
  khiển GPIO18 theo LAMP_GPIO. Đây chưa phải bộ lệnh điều khiển RGB trên board.
- Chưa có mã demo RGB/MCP mới, chưa build/nạp hoặc nghiệm thu demo này.

## Cách thực hiện dự kiến

Luồng: tiếng nói -> mic -> Xiaozhi/AI -> MCP tool call -> callback trên
ESP32-S3 -> LED RGB. Không dùng việc AI nói "đã tắt" làm bằng chứng duy nhất;
cần log gọi tool, callback và quan sát LED thực đúng yêu cầu.

1. Tạo board/variant AW-Car riêng dựa trên profile OLED đang chạy, giữ pin
   OLED/mic/loa đã chọn và xác minh GPIO RGB. Giữ bản stock để đối chiếu.
2. Dùng một bộ điều khiển duy nhất sở hữu LED/RMT. Lệnh bật/tắt/màu phải
   được giữ khi Xiaozhi chuyển sang nghe/nói/idle; tránh màu báo trạng thái
   ghi đè lệnh người dùng. OLED tiếp tục hiển thị trạng thái hệ thống.
3. Trong profile demo, thay lamp GPIO18 bằng nhóm tool RGB có mô tả rõ ràng
   để AI không chọn nhầm ngoại vi. Không mở quyền ghi GPIO tùy ý.
4. Tham số RGB kiểm tra trong miền 0..255; callback báo lỗi khi driver lỗi,
   trả về trạng thái đã áp dụng khi thành công. Có cách đọc lại trạng thái
   phần mềm để đối chiếu log; trạng thái đó không phải cảm biến đo ánh sáng.
5. Thử gọi tool ở mức firmware trước, sau đó gắn mic để thử qua hội thoại.

Giao diện tool dự kiến, chưa đăng ký trong firmware:

| Tool | Tham số / hành vi |
| --- | --- |
| self.rgb_light.set_power | on: boolean; tắt xuất RGB=0, bật dùng màu đã chọn hoặc màu mặc định |
| self.rgb_light.set_color | r/g/b: số nguyên 0..255; đặt màu và bật đèn |
| self.rgb_light.get_state | Đọc trạng thái bật/tắt và màu để kiểm chứng |

## Tiêu chí thử khi đã gắn mic

| Câu ví dụ | Kết quả cần quan sát |
| --- | --- |
| "Bật đèn lên" | AI gọi tool bật, RGB sáng đúng màu đang chọn/mặc định |
| "Tắt đèn đi" | AI gọi tool tắt, RGB tắt và vẫn tắt khi AI trả lời/xong hội thoại |
| "Cho đèn chuyển sang màu đỏ" | RGB đỏ, callback/log khớp tham số |
| "Đổi sang xanh lá" / "Chuyển sang xanh dương" | Hai màu khác nhau, không nhầm kênh GRB |
| "Không cần sáng nữa, tắt giúp tôi" | Hiểu cách diễn đạt khác, có tool call và LED tắt |

Ghi kết quả từng câu, tool/giá trị trả về và xác nhận nhìn LED; không ghi
SSID, thông tin tài khoản hoặc mã kích hoạt vào repo. Khi đủ các ca bật/tắt/
đổi màu mới kết luận demo AI điều khiển ngoại vi đạt. Chưa coi đây là nghiệm
thu điều khiển xe hoặc hoàn tất toàn bộ F03.

Nguồn trong repo: [MCP usage](mcp-usage.md),
[board stock](../main/boards/bread-compact-wifi/compact_wifi_board.cc),
[pinout](../main/boards/bread-compact-wifi/config.h),
[SingleLed](../main/led/single_led.cc),
[LampController](../main/boards/common/lamp_controller.h).
