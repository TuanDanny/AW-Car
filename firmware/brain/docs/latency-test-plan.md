# F03: đo và tối ưu độ trễ Xiaozhi

Nghiên cứu ngày 29/10/2026 trên source c41de5f, nhánh
feat/f03-xiaozhi-ai, board aw-car-ai-rgb-128x64. Phạm vi hiện tại là
nghiên cứu và thiết kế phép thử; chưa sửa/nạp firmware tối ưu.

Mục tiêu là giảm thời gian chờ và những lượt không nhận lệnh, đồng thời
giữ toàn bộ hành vi hiện có. Một bản chỉ được chấp nhận sau khi so sánh
trước/sau và kiểm tra lại tính năng. Chưa có cơ sở cam kết mức giảm hoặc
không có hồi quy chỉ từ việc đọc source.

## Bằng chứng hiện có

- Firmware dùng hai core, CPU 240 MHz, PSRAM Octal 80 MHz; không thiếu
  thiết lập dual-core. CPU utilization từng core và stack headroom chưa đo.
- Log cục bộ lag-baseline-20261029: theo dõi 150 giây, ba lượt
  idle -> connecting -> listening đều 170 ms, có 6 bản tin STT, không
  timeout/panic; heap nội bộ cuối lượt 147.335 B, minimum 42.664 B.
- 170 ms bắt đầu sau khi main đổi trạng thái, không phải từ lúc bấm hoặc
  nhả BOOT, cũng chưa xác nhận thời điểm PCM đầu vào thực sự sẵn sàng.
- Ba lượt bình thường chưa đại diện cho lỗi thỉnh thoảng mới xuất hiện.
  Các lượt trước đã có MQTT/TLS timeout; chưa xác định nguyên nhân mạng.
- Bật/tắt và ba màu RGB đã có callback và xác nhận phần cứng trong
  [demo RGB](ai-rgb-demo.md). Loa chưa gắn; không coi phát âm thanh đã đạt.

| Điểm trong source | Ý nghĩa đối với phép đo |
| --- | --- |
| BOOT dùng Button::OnClick / BUTTON_SINGLE_CLICK | Có cửa sổ phân loại click sau nhả; cấu hình 180 ms, tick 5 ms, điều kiện lớn hơn ngưỡng tạo khoảng chờ danh định 185 ms, chưa gồm debounce/lịch chạy |
| Application::Schedule chạy callback trong main | Đưa hàm vào Schedule không tạo worker chạy song song |
| ContinueOpenAudioChannel gọi OpenAudioChannel đồng bộ | DNS/MQTT/TLS/đợi server hello có thể giữ main nhiều giây khi lỗi mạng |
| Đợi MQTT server hello tối đa 10 giây | Cần đo riêng; đây không phải giới hạn tổng của mọi chặng reconnect |
| EnableVoiceProcessing(true) đặt cờ warmup | AudioInputTask gặp cờ sẽ vTaskDelay 120 ms trước lượt đọc tiếp |
| Nhãn LISTENING cập nhật trước StartListeningAudio | Khi còn playback, pending_listening_start chờ hàng phát hết; nhãn UI chưa chứng minh mic đã gửi tiếng |
| Opus đang dùng frame 60 ms | Có thời gian gom frame; thay cỡ frame cần xác minh phía máy chủ, tải CPU và chất lượng |
| Timer thông báo LVGL lấy DisplayLockGuard | Có đường chờ khóa tối đa 30 giây trong esp_timer; chưa chứng minh đã tranh chấp ở lượt lỗi |

Nguồn: [nút](../main/boards/common/button.cc),
[main loop](../main/application.cc), [MQTT](../main/protocols/mqtt_protocol.cc),
[audio](../main/audio/audio_service.cc),
[tham số audio](../main/audio/audio_service.h),
[timer UI](../main/display/lvgl_display/lvgl_display.cc),
[khóa UI](../main/display/display.h).

## Đo đúng từng chặng

Dùng esp_timer_get_time, mã lượt tăng cục bộ và thế hệ kết nối. Không dùng
giờ đồng hồ hoặc timestamp của hai máy chưa đồng bộ để trừ trực tiếp.

| Mốc | Vị trí cần ghi |
| --- | --- |
| T0 / T1 | Nút xuống / nhả đã debounce; nếu cần thời gian cạnh điện thật thì thêm logic analyzer |
| T2 | Callback single-click được thư viện nút phát |
| T3 | Main thực sự xử lý yêu cầu BOOT |
| T4 | Bắt đầu/kết thúc DNS, MQTT/TLS, publish hello và nhận server hello |
| T5 | Quyết định bật thu sau khi xử lý playback/pending_listening_start |
| T6 | I²S RX có clock, frame hợp lệ đầu tiên; ghi riêng lần RX mới bật và lần đã chạy liên tục |
| T7 | AFE phát dữ liệu giọng nói đầu tiên và gói Opus đầu tiên gửi thành công |
| T8 | Nhận văn bản STT từ máy chủ |
| T9 | Nhận yêu cầu MCP / callback RGB ghi thành công |
| T10 | Nhận đoạn trả lời đầu tiên / mẫu phát đầu tiên; xác nhận loa thực bằng phép đo khi đã gắn loa |

T2-T1 đo phân loại click; T3-T2 đo hàng đợi main; T6-T1 đo nhả nút đến
đường thu sẵn sàng. T9-T7 bao gồm truyền mạng và xử lý máy chủ, không gán
toàn bộ cho CPU ESP32. Đo riêng thời điểm bắt đầu/kết thúc câu nói nếu
muốn tính độ trễ sau khi người dùng nói xong.

Không dùng I²S có clock hoặc frame khác zero làm bằng chứng duy nhất rằng
nhận dạng đã sẵn sàng. Dùng câu/chirp kiểm tra có thời điểm biết trước để
đối chiếu từ đầu câu, clipping và đoạn bị mất. Clock có thể đã chạy cho
wake word từ trước khi mở hội thoại.

Marker đi qua bộ đệm dung lượng cố định, có bộ đếm mất marker và worker
ghi log ưu tiên thấp. Không printf từng frame hoặc chờ khóa trong callback
timer. Bản nền và bản thử phải bật cùng mức trace; đo thêm bản tắt trace
để biết chính phép đo có làm thay đổi độ trễ hay không.

Đo CPU theo task/core, stack high-water mark, internal/PSRAM free/minimum/
largest block, queue depth/drop, thời gian codec và chờ LVGL. Runtime stats
đã bật. Hàm PrintTaskCpuUsage có sẵn chia phần trăm cho hai core: một task
chiếm một core tương ứng khoảng 50% bảng đó. Không gọi phép lấy mẫu có
vTaskDelay trực tiếp trong main. Không bật PrintTaskList dùng buffer cố định
1.000 B mà chưa xử lý dung lượng an toàn. Core không ghim lúc tạo có thể
thay đổi affinity khi dùng FPU; cần quan sát runtime trước khi đổi pinning.

## Thứ tự tối ưu đề xuất

| Ưu tiên | Thay đổi cần thử | Điều kiện giữ chức năng |
| --- | --- | --- |
| 1 | Đo marker và sửa tín hiệu UI “sẵn sàng nghe” khớp đường thu thực | Giữ toàn bộ playback, VAD và cơ chế chờ phát hết; không chỉ đổi nhãn để làm đẹp số |
| 2 | Chặn reconnect cũ khi kết nối đã phục hồi; đánh thức waiter khi đã có lỗi disconnect | Giữ native/protocol reconnect, timeout hợp lệ, heartbeat và TLS; kiểm tra thứ tự các sự kiện |
| 3 | Chuyển open/reconnect sang worker sở hữu tài nguyên mạng | Main tiếp tục nhận BOOT; single-flight, yêu cầu có thế hệ và hủy; callback muộn không mở lại phiên đã đóng; UI chỉ cập nhật ở main |
| 4 | Đánh giá warmup 120 ms theo trạng thái I²S/codec thực | RX đang chạy ổn định có thể có fast path; RX mới khởi động vẫn phải chờ dữ liệu hợp lệ, giữ từ đầu câu và chống dữ liệu cũ |
| 5 | Đưa công việc UI khỏi callback esp_timer | Timer chỉ gửi sự kiện; giữ đầy đủ nội dung/thời hạn thông báo, bỏ tác vụ cũ khi thông báo đã được thay thế |
| 6 | Đưa phân giải DNS chỉ phục vụ log ra khỏi đường tương tác | Giữ khả năng chẩn đoán; kết nối vẫn dùng hostname/SNI và kiểm tra chứng chỉ như cũ; không giả định tiết kiệm một RTT vì resolver có cache |

Worker mạng là thay đổi kiến trúc có rủi ro thứ tự/vòng đời; cần thử giả lập
mạng trước khi nạp, không chỉ thay một lời gọi bằng task rồi coi là xong.

Khoảng warmup hiện nằm trước ReadAudioData. Khi RX đang tắt, việc ngủ trước
khi EnableInput bật clock không tự chứng minh mic đã ổn định. Datasheet
INMP441 quy định thời gian khởi động/phục hồi theo số xung SCK; không áp
nguyên số mili giây trong ví dụ của datasheet ở tần số clock khác. Cần đo
SCK và trạng thái cấp nguồn/CHIPEN thực trước khi giảm chờ.

## Những lựa chọn chưa nên đổi ngay

- BOOT chuyển single-click sang press-down/up có thể nhanh hơn, nhưng đổi
  ý nghĩa nhấn giữ/nhấn nhiều lần. Giữ hành vi hiện tại trong giai đoạn
  yêu cầu không đổi tính năng; đánh giá riêng nếu sau này đổi UX.
- Giữ Opus 60 ms trước. Chỉ thử 20/40 ms khi backend xác nhận hỗ trợ và
  handshake/decoder phù hợp; đo cả CPU, số gói, mất âm và nhận dạng.
- Không bỏ wake word, VAD, pre-roll, hàng phát, ngắt lời, TLS, xác thực hay
  watchdog để giảm số đo. Không bật full-duplex khi chưa xác nhận AEC.
- Khi mở thoại, code đã yêu cầu Wi-Fi PERFORMANCE và thư viện ánh xạ sang
  WIFI_PS_NONE. Không coi bật chế độ này lần nữa là tối ưu mới; không bỏ
  chính sách tiết kiệm điện khi chờ để đổi lấy số đẹp trong một phép thử.
- Không chia core 50/50 theo số task. Chỉ thử affinity/priority, -Os sang
  -O2, đặt hotspot vào IRAM hoặc pool buffer khi profiling chỉ ra nhu cầu.
  Giữ headroom cho Wi-Fi/âm thanh; tăng throughput không đồng nghĩa giảm
  độ trễ lệnh. Không đổi DIO/QIO hoặc clock bộ nhớ trước khi xác nhận board.
- MQTT đang được giữ qua các lượt thoại; không mô tả giữ MQTT kết nối như
  một cải tiến chưa có. Phiên audio/UDP có vòng đời riêng với MQTT.

## Thử trước/sau và kiểm tra hồi quy

Đề xuất 30-50 lượt cho mỗi tình huống, lặp xen kẽ bản nền/bản thử nếu có
thể, cùng board/mic/nguồn/router/vị trí và cùng bộ câu nói. Mỗi bản chỉ đổi
một nhóm tối ưu; giữ bản đã nạp thành công để quay lại khi một ca thất bại.
Lưu source commit, SDK/lockfile, build hash, cấu hình và trạng thái kết nối.
Các tối ưu thử nghiệm nên bật riêng cho profile AW-Car, có cách tắt; đường
mặc định của các board stock giữ nguyên. Không sửa managed_components để
lưu bản vá lâu dài hoặc dùng thay đổi chung chưa thử trên các codec khác.

| Tình huống | Phải kiểm tra |
| --- | --- |
| Vừa boot / đã chờ / mở thoại liên tiếp | Thời điểm thu thật, đủ từ đầu câu, không giữ mẫu cũ |
| BOOT khi chờ, khi đang nghe, khi AI đang trả lời | Đúng hành vi toggle/đóng/ngắt; không gộp hoặc nhân đôi lệnh do lỗi mới |
| MQTT đang nối / broker mất / mất sau publish hello / hello đến muộn | Main phản hồi, hủy đúng, không callback cũ hồi sinh phiên đã đóng |
| Mất Wi-Fi rồi phục hồi; reconnect nền và BOOT gần nhau | Trạng thái mạng cuối đúng, không reset một kết nối đã hồi phục |
| Bật/tắt, đỏ/xanh lá/xanh dương, alias và câu diễn đạt khác | Có tool call và LED thực đúng; không dùng so khớp transcript để thay AI |
| OLED cập nhật chữ/thông báo cùng lúc nói | UI, mic, timer và RGB tiếp tục hoạt động; không kéo dài khóa chung |
| Thu/phát âm thanh, ngắt lời, wake word và chế độ cấu hình | Không cắt âm, echo, mất chức năng hoặc đổi nút; phần chưa gắn loa chưa được đánh dấu đạt |
| Dùng liên tục 1-2 giờ | Heap/fragmentation/stack ổn định, không tăng drop, watchdog hoặc reset |

Báo median, p95, lớn nhất, số lượt và từng loại lỗi: mất click, mất đầu
câu, nhận dạng sai, timeout mạng, sai tool/màu, reset. Báo p95 của lượt
hoàn tất cùng tỷ lệ lỗi/timeout, không chỉ lấy ba lượt tốt để kết luận.

Mục tiêu ban đầu để thẩm định, chưa phải kết quả đã đạt: p95 callback nút
đến main xử lý dưới 50 ms; p95 nhả BOOT đến thu sẵn sàng dưới 500 ms khi
mạng đã kết nối ổn định. Không dùng mục tiêu này để hạ timeout máy chủ
hoặc tự bỏ những câu nói chưa nhận xong. Chỉ chấp nhận bản có độ trễ tốt
hơn trong so sánh phù hợp và bộ tính năng/hành vi vẫn đạt.

Build firmware, host tests và các kiểm tra repo vẫn phải chạy. Tác vụ
nghiên cứu này chưa chạy các phép thử fault injection, thống kê 30-50 lượt,
đo CPU/stack, gắn loa hay chứng minh các mốc mục tiêu trên.

## Tài liệu đối chiếu

- [Espressif: đo và tối ưu tốc độ, ESP-IDF 6.1](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-guides/performance/speed.html).
- [Espressif: ESP Timer và giới hạn callback](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/system/esp_timer.html).
- [Espressif: FreeRTOS SMP và affinity](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/system/freertos_idf.html).
- [Espressif: các loại sự kiện nút](https://docs.espressif.com/projects/esp-iot-solution/en/latest/input_device/button.html).
- [TDK: INMP441, power management và I²S](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf).
- [Giao thức MQTT/audio hiện tại](mqtt-udp.md); [kiến trúc audio](../main/audio/README.md).
