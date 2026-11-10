# Review tối ưu simplev1 — giữ flow đã nghiệm thu

Ngày10/11/2026, nền main97f9fcd. Đây là review và phép thử host, **chưa sửa
firmware, nạp board hoặc thay main**. Dữ liệu ở
[optimization-review.json](../data/optimization-review.json).

## Kết luận từ số đo hiện có

92mẫu điện thoại: bấm→STATUS p50=69,8ms/p95=125,2ms/max=221,4ms.
Motion mailbox→trước SPI: p99=0,668ms/max=2,045ms, đạt ngân sách nội bộ.
Không cộng hai đồng hồ hoặc suy STATUS thành cạnh PWM thật. Chưa biết bao nhiêu
phần của9,7ms trung vị bấm→gửi là chờ event của browser hay chạy callback.

Lõi hiện đã dùng task notify khi có lệnh, một task sở hữu SPI, polling/no DMA
cho32byte, JSON/log ngoài đường deadline, TCP_NODELAY trên WS. Bởi vậy giảm tick
5ms hoặc tăng priority không phải bước đầu hợp lý. CPU Motion hiện240MHz,
FREERTOS_HZ1000, PM không bật; không có căn cứ tăng thêm clock.
Tài liệu [SPI Espressif](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/peripherals/spi_master.html)
ủng hộ polling cho giao dịch nhỏ; DMA không mặc nhiên nhanh hơn trường hợp này.

## Các ứng viên, theo thứ tự thực hiện

| Ưu tiên | Thay đổi nhỏ | Lợi ích hướng tới | Bằng chứng / giới hạn |
| --- | --- | --- | --- |
| 1 | Chỉ ghi text/attribute khi giá trị đổi; dùng chung Intl.NumberFormat | Bớt công việc main thread Web | Probe DOM giảm75,6%; chưa đo cải thiện ms trên điện thoại |
| 2 | Nhận biết motion busy theo ý định chuyển động, gồm Waking/Reversing | Tránh mở retry STA trong khoảng PWM tạm0 | Probe C++ tái hiện; chưa đo tác động radio |
| 3 | Nếu profiler cho thấy đáng kể, cache quantile chẩn đoán tại HTTP task | Bớt sort256mẫu và xử lý phụ mỗi STATUS | Có std::sort/cJSON trên đường HTTP; chưa đo chi phí trên MCU |
| 4 | Chỉ thử STATUS20Hz sau tối ưu trên, khi cần phản hồi màn hình sớm hơn | Giảm chờ poll100ms | Tăng số bản tin/JSON/render; không chứng minh motor nhanh hơn |

Riêng lỗi SPI frame/ACK cần một lượt cách ly trước khi thử tăng clock hoặc coi
chuỗi truyền động đã ổn định. Tối ưu UI có thể làm độc lập, không phải đợi đổi RTL.

### 1. Web: giảm ghi lặp, giữ toàn bộ logic điều khiển

`esp/motion/web/index.html:324` render nhiều text mỗi100ms dù nội dung không đổi;
`controls()` cũng ghi lại một số attribute. Candidate đơn giản là helper kiểm
text hiện tại trước khi gán. Không chuyển xử lý mode/generation/mất kết nối vào
requestAnimationFrame, không trì hoãn STOP/MOVE để chờ vẽ. Giữ pointer capture,
focus, nhả/cancel, lặp20Hz và quy tắc backpressure đã nghiệm thu.

Đã đo Chromium desktop viewport390×844 với simulator native, **không phải CPU
Android hoặc Wi-Fi ESP**: hai lượt baseline3giây và hai lượt candidate3giây,
mỗi lượt30STATUS. Baseline750DOM mutation/lượt; candidate183/lượt; Manual và
duty0/0 hiển thị như nhau, không có page error. Candidate chỉ inject setter
có điều kiện trong context browser riêng; không ghi vào HTML production.
Số liệu này không đo CPU tiết kiệm bao nhiêu hoặc suy ra độ trễ giảm tương ứng.

Hàm number() đang gọi toLocaleString('vi-VN') lặp. Có thể tái dùng một formatter
theo [MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/toLocaleString).
[web.dev](https://web.dev/articles/optimize-inp) phân biệt thời gian chờ event,
thực thi callback và vẽ: cần tách các mốc này trước khi gán toàn bộ độ trễ cho DOM.

### 2. Motion: một điểm phân loại idle cần sửa có kiểm thử

`esp/motion/main/runtime.cpp:74–79` hiện lấy left/right khác0 làm motion busy.
Khi snapshot là Waking hoặc Reversing, action vẫn khácNeutral nhưng cả hai duty
bằng0 và mailbox có thể đã rỗng. NetworkPolicy khi đến hạn có thể nhận active=false
và cho Connect. Probe dùng Control/NetworkPolicy C++ thật đã tái hiện hai trạng thái.

Ứng viên: bổ sung `snapshot_.car.action != simple::Action::Neutral` vào điều kiện
hiện tại, giữ kiểm pending và OTA. Không đổi tốc độ, thời gian thức driver hoặc
guard đảo chiều. Chỉ trì hoãn/hủy attempt STA khi có intent; không ngắt STA đã online.

Đây là cải thiện một khe hở cụ thể, không chứng minh hết mọi race Wi-Fi. Network
task kiểm100ms, còn có khoảng input đã được control lấy nhưng snapshot chưa publish;
phải đo A/B trước khi kết luận hết jitter. Chưa xác định đây là nguyên nhân của mẫu
221,4ms. Kiểm Waking/Reversing/neutral/STOP/OTA và STA online/offline trước khi giữ sửa.

### 3. Chẩn đoán và phản hồi

`web.cpp:78` sort tối đa256mẫu trong HTTP task, không phải control task. Có thể
cache quantile tại chính task HTTP nếu đo thấy tốn thời gian; không thêm task hoặc
queue mới. State, generation và quyền điều khiển vẫn lấy snapshot mới; không dùng
cache chẩn đoán để đánh dấu kết nối còn sống. Chưa có bằng chứng để thay cả JSON
bằng binary hay viết lại serializer cố định kích thước.

STATUS10Hz có phần chờ đến poll tiếp theo. Tăng20Hz chỉ giảm thành phần phản hồi,
đồng thời tăng tải. ACK hiện chỉ là đã nhận yêu cầu; xin STATUS ngay sau ACK vẫn có
thể gặp snapshot cũ/Waking. Không được tô UI như đã áp dụng PWM để làm số đo đẹp hơn.

## Chưa nên thay

- Giữ SPI1MHz/32byte/CRC, PWM20kHz, UART, các chân và RTL đã nghiệm thu. Không thử
  tăng tốc trên bus đang báo lỗi. Phép thử CS GPIO trước đã không giải quyết lỗi.
- Giữ Manual500ms, AI mặc định3giây, STOP/đổi mode/không replay, guard40ms và wake1ms.
- Giữ20Hz lệnh và5ms kiểm tra nền: notify đã gửi lệnh mới ngay, không chờ hết5ms.
- Không đổi giao thức sang UDP/MQTT, thêm worker điều khiển hoặc queue push HTTP.
- Không tăng số socket/buffer hoặc đặt toàn bộ code vào IRAM khi chưa có profiler.
- Không bật WIFI_PS_NONE như một bảo đảm AP nhanh hơn: tài liệu
  [power save Espressif](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-guides/wifi-driver/wifi-performance-and-power-save.html)
  mô tả modem sleep cho station-only; app lái đi qua SoftAP. Cần đọc mode thực và
  A/B, không đồng nhất tiết kiệm điện của STA ESP với power save của điện thoại.

## Cách áp dụng sau review

Giữ main làm baseline. Thử từng nhóm riêng: UI trước; busy/STA sau; cache hoặc
STATUS sau cùng khi có số đo. So cùng điện thoại/vị trí/router/tải, tách cold start,
đang giữ và đảo chiều. Bổ sung timestamp handler-entry để tách input queue và JS;
chỉ bật instrument khi đo. Mẫu hủy/mất phản hồi ghi riêng, không bỏ thành0ms.

Chạy hồi quy25ca browser, core/giao thức và build đúng phần đổi. Thử điện thoại
lại giữ/nhả, STOP trùng MOVE, nhiều nút, đổi mode, reconnect/không replay, AI3giây,
BOOT/OLED/loa và OTA. Giữ ngân sách nội bộ p99≤3ms/max≤10ms và budget chẩn đoán cũ;
không nới ngưỡng sau đo. Bỏ candidate nếu có lỗi flow hoặc không có lợi ích đo được.
Giả lập không nghiệm thu radio, cạnh PWM hoặc motor thật.
