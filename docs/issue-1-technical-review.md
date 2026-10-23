# Rà soát kỹ thuật issue #1 và kế hoạch hiệu chỉnh

Ngày rà soát: **23/10/2026**. Nguồn yêu cầu:
[issue #1 - Tóm tắt yêu cầu của xe](https://github.com/TuanDanny/AW-Car/issues/1),
đang mở, chưa có bình luận tại thời điểm đọc.
Đã đọc lại bản issue cập nhật lúc **11:22 ngày 23/10/2026 (UTC+7)**.

## 1. Phạm vi và kết luận

Người sở hữu xác nhận dự án đang lên kế hoạch, chưa lắp xe. Kho ở commit
`d32db1daf27cbe58e72cc8057cdf61945b7adade` chỉ có `LICENSE`.
Do đó, đây là rà soát yêu cầu và thiết kế; chưa có mã nguồn để sửa lỗi hoặc
chạy kiểm thử firmware. Các hiệu chỉnh dưới đây được ghi vào tài liệu trong
kho cục bộ, chưa thay đổi nội dung issue trên GitHub.

**Cấu hình bản đầu đã xác nhận với người sở hữu:** xe lái trước bằng servo,
2 motor sau có encoder theo BOM đề xuất, 2 ESP32-S3, **1 mic INMP441**,
an toàn cục bộ, Dashboard, TFT và tương tác giọng nói. Người sở hữu chọn
"Dùng 1 mic trước; giữ DoA cho giai đoạn nâng cấp".

Mic bản đầu phục vụ thu giọng nói/lệnh, không dùng để tính góc DoA 360° hay tự
hướng về người nói. Định hướng âm thanh vẫn là mục tiêu nâng cấp, cần cụm thu
đồng bộ và nguyên mẫu chứng minh riêng. Khả năng ước lượng góc không đồng nghĩa
xe có thể quay tại chỗ hoặc đi tới mọi góc. Cần hoàn tất chọn nguồn, driver và
các bài thử trước khi chốt BOM/PCB bản đầu; không cần chờ DoA để nghiệm thu bản này.

### Nội dung issue còn cần đồng bộ

Bảng linh kiện đã ghi **1 mic**, **02 MCU** nhưng F02 vẫn ghi **4 mic/0-360°**;
phần tổng quan còn tùy chọn MCU thứ ba và cụm mic chưa ghi số lượng. Theo lựa
chọn đã xác nhận trong cuộc trò chuyện, cần sửa nội dung issue thành:

- Phần điều khiển giọng nói: "Bản đầu dùng 1 mic INMP441 để thu giọng nói/lệnh
  điều khiển. Định hướng nguồn âm thanh và tự hướng xe về người nói dành cho
  giai đoạn nâng cấp bằng cụm mic thu đồng bộ."
- F02: "Định hướng giọng nói (nâng cấp): xác định góc người nói bằng cụm mic thu
  đồng bộ; số lượng và phần cứng sẽ chốt khi thử nghiệm. Chưa triển khai trên
  cấu hình 1 mic." Brain xử lý âm thanh; Motion thực hiện lệnh đã giới hạn.
- Phần phân tải: bản đầu Brain xử lý thu/phát âm thanh, Xiaozhi, TFT và Web;
  Motion xử lý servo, PID và an toàn. DoA chưa nằm trong tải xử lý bản đầu.
- Tổng quan dùng 2 ESP32-S3; motherboard bản đầu có 1 mic. MCU thứ ba và cụm mic
  nâng cấp chỉ xem xét khi có số đo tải/phương án thu. Ghi chú BOM của mic đổi
  thành "Thu giọng nói/lệnh; chưa hỗ trợ định hướng nguồn âm" để tránh nhầm
  đặc tính thu đa hướng của mic với khả năng xác định góc.

Các câu trên đã được phản ánh trong tài liệu cục bộ; issue GitHub chưa được sửa
bởi lần rà soát này.

## 2. Những yêu cầu đã nắm

| Mã | Kết quả mong muốn | Phạm vi đề xuất |
| --- | --- | --- |
| F01 | Di chuyển mượt, đo m/s và km/h | Servo lái trước, 2 motor sau, encoder và PID riêng từng motor |
| F02 | Nâng cấp: xác định hướng người nói, hướng đầu xe về nguồn âm | Hoãn khỏi bản đầu 1 mic; chọn cụm thu đồng bộ, đo độ tin cậy rồi mới cho di chuyển |
| F03 | Xiaozhi nhận lệnh và phản hồi bằng loa | Bản đầu dùng 1 mic; Brain xử lý tương tác; lệnh chuyển động qua lớp kiểm tra; cảnh báo thiết yếu lưu cục bộ |
| F04 | Dừng khi gặp vật cản, mép rơi, nghiêng, va chạm hoặc kẹt | Motion đọc cảm biến, quyết định dừng và ghi mã lỗi độc lập với Brain |
| F05 | TFT 2.8 inch: biểu cảm, tốc độ, QR; Dashboard điều khiển/debug | Brain chạy giao diện LVGL và mạng; Dashboard hiển thị cả trạng thái lỗi và độ mới dữ liệu |
| F06 | Motherboard tích hợp MCU, nguồn, âm thanh và các đầu nối | Làm cho cấu hình 2 MCU/1 mic sau khi nguyên mẫu đạt; DoA nâng cấp có thể cần sửa PCB |

## 3. Các điểm cần sửa trong kế hoạch

Phân biệt **sai mô tả**, **thiếu thiết kế** và **rủi ro cần thử**; không coi mọi
linh kiện trong issue là linh kiện sai.

| Điểm | Phân loại | Hiệu chỉnh kỹ thuật |
| --- | --- | --- |
| LVGL được gọi là Mini OS | Sai mô tả | LVGL là thư viện đồ họa [S1]. Dùng ESP-IDF/FreeRTOS làm nền tảng, xây giao diện dạng Mini OS bằng LVGL. |
| Servo Ackermann được kỳ vọng xoay đầu về mọi hướng | Thiếu ràng buộc cơ khí | Xe có bán kính quay hữu hạn; phải chạy theo cung. Servo và thanh liên kết phải tạo đúng hình học lái; một servo tự nó chưa đảm bảo Ackermann. Không cam kết quay tại chỗ. |
| BOM đổi thành 1 mic nhưng F02 vẫn ghi 4 mic và DoA 360° | Mâu thuẫn yêu cầu; đã chốt phương án | Theo xác nhận của người sở hữu: 1 mic cho giọng nói ở bản đầu, giữ DoA cho nâng cấp bằng cụm mic đồng bộ. Issue còn cần sửa mô tả F02. |
| Thu nhiều mic cho DoA chưa có phương án đồng bộ | Thiếu thiết kế ở giai đoạn nâng cấp | I2S standard có 2 slot trái/phải; S3 có 2 bộ I2S [S2]. Nếu chọn 4 INMP441 thì phải chốt đường thu, clock và căn chỉnh mẫu. Đây không còn là điều kiện làm bản đầu. |
| DoA vẫn được đặt ở Motion trong mô tả phân tải | Mô tả chưa đồng bộ phạm vi | Bản đầu không chạy DoA. Khi nâng cấp, ưu tiên giữ thu âm và DoA trên Brain hoặc bộ xử lý âm thanh chuyên dụng sau đo tải; Motion nhận lệnh đã giới hạn. |
| TCRT5000 được coi là cảm biến đo độ cao gầm | Sai mô tả | Đây là cảm biến phản xạ, không phải máy đo khoảng cách tuyệt đối. Datasheet nêu điểm làm việc cực đại khoảng 2.5 mm; khoảng 0.2-15 mm có điều kiện thử [S3]. Chỉ dùng nhận biết nền/mép rơi sau hiệu chuẩn và thử bề mặt. |
| Cấp nguồn bằng 2 buck 5 V chưa đủ đặc tả | Thiếu thiết kế | Phân rail theo điện áp motor, servo và logic thực tế. Module WROOM trần cần nguồn 3.3 V; chân vào 5 V chỉ dùng nếu board phát triển hỗ trợ. Hai buck chung pin không tạo cách ly điện. |
| TB6612FNG được chọn khi chưa biết motor N20 cụ thể | Rủi ro chọn linh kiện | N20 chỉ mô tả kích thước/họ motor. Chọn điện áp, tỉ số truyền và dòng kẹt trước, rồi đối chiếu dòng, nhiệt và chế độ làm việc driver [S4]. Không dùng thông số dòng đỉnh làm dòng liên tục. |
| BMS 2S bị để chung với yêu cầu sạc | Thiếu thiết kế | BMS không thay thế bộ sạc. Với Li-ion 4.2 V/cell, pack 2S đầy là 8.4 V; cần sạc CC/CV đúng loại pin, bảo vệ/cân bằng phù hợp, cầu chì và đầu nối đủ dòng. |
| Liên kết UART mới chỉ yêu cầu tốc độ cao | Thiếu thiết kế | Cần đóng khung, CRC, số thứ tự, phiên kết nối, giới hạn lệnh và timeout. Tốc độ UART cao không tự bảo đảm độ trễ hay dừng an toàn. |
| Xiaozhi Lite/Robotics chưa chỉ ra dự án/phiên bản | Thiếu căn cứ triển khai | Ghim repository, commit, board và SDK tương thích. Upstream đã kiểm tra có xử lý giọng nói qua mạng và wake word cục bộ [S5]; không mặc định toàn bộ AI chạy offline trên S3. |
| FSR402 và INA219 được kỳ vọng phát hiện mọi quá lực/kẹt | Thiếu phạm vi đo | FSR chỉ phản ánh lực ở vị trí lắp, cần cơ cấu/hiệu chuẩn. INA219 đo dòng của nhánh đặt shunt [S6]; một cảm biến tổng không xác định riêng motor nào kẹt. Kết hợp encoder và thời gian quá dòng. |
| 2 motor sau có thể bị đặt cùng tốc độ khi rẽ | Thiếu thuật toán | Bánh trong và ngoài đi quãng đường khác nhau. Tạo setpoint khác nhau theo góc lái, chạy PID từng bánh; xử lý giới hạn và chống tích lũy sai số. |
| Chống rơi mới có 2 cảm biến, vật cản chỉ có cảm biến trước | Thiếu vùng bảo vệ | Bản thử đầu chỉ chạy tiến trong vùng đã kiểm chứng. Chỉ cho lùi sau khi bổ sung/kiểm chứng vùng cảm biến phía sau; không tự lùi để hướng về người nói khi chưa có bảo vệ. |

## 4. Kiến trúc đề xuất

### MCU 1 - Brain

- Thu âm bằng 1 INMP441, phát loa, wake word và kết nối Xiaozhi. Bản đầu không
  chạy DoA; lệnh giọng nói đã nhận dạng được xử lý độc lập với việc biết góc người nói.
- TFT, LVGL, QR truy cập Dashboard, Wi-Fi và dữ liệu chẩn đoán.
- Chuyển lệnh Web/giọng nói thành yêu cầu vận tốc và góc lái có giới hạn.
- Phát cảnh báo thiết yếu từ âm thanh lưu cục bộ khi mất mạng; ưu tiên cảnh báo
  hơn hiệu ứng giao diện. Motion phải dừng trước, không chờ loa hay Dashboard.
- Lệnh từ AI đi qua cùng bộ phân xử với lệnh Web; chỉ một nguồn có quyền điều
  khiển tại một thời điểm. Dừng khẩn cấp và lỗi an toàn luôn có ưu tiên cao hơn.

### MCU 2 - Motion

- Đếm encoder, điều khiển PWM, servo, PID và giám sát an toàn cục bộ.
- Đọc cảm biến theo tác vụ/lịch không chặn vòng điều khiển; mỗi mẫu có timestamp
  và cờ hợp lệ. Lỗi cảm biến thiết yếu có thể dừng xe; lỗi SHT30 chỉ cần báo lỗi.
- Thực thi state machine gồm `DISARMED`, `ARMED` và `FAULT` với điều kiện chuyển
  rõ ràng. Khi khởi động/reset, mặc định `DISARMED`, chưa cấp lệnh chạy motor.
- Timeout điều khiển đưa xe về `DISARMED`; lỗi an toàn nghiêm trọng chốt `FAULT`.
  Chỉ cho arm lại bằng thao tác chủ động sau khi điều kiện lỗi đã hết.

Mục tiêu ban đầu để thử: vòng điều khiển 100 Hz, lệnh điều khiển mới 20-50 Hz,
timeout lệnh 250 ms. Đây là **giá trị đề xuất cần đo**, không phải kết quả đạt
được hay thông số đủ an toàn cho mọi tốc độ. Lịch đọc ToF phải tôn trọng timing
budget thực của cảm biến; không ép tất cả cảm biến chạy 100 Hz.

Cấu hình bản đầu dùng 2 MCU theo BOM đã cập nhật. MCU thứ ba chỉ được xem xét
khi có số đo CPU, heap/DMA, độ trễ hoặc xung đột ngoại vi chứng minh 2 MCU không
đáp ứng; thêm MCU cũng làm tăng yêu cầu đồng bộ và debug.

## 5. Âm thanh bản đầu và định hướng âm thanh nâng cấp

### Bản đầu: 1 mic

Một mic cung cấp một kênh thu, dùng cho wake word và gửi giọng nói đến hệ thống
nhận dạng Xiaozhi theo cấu hình thực tế. Thu được âm từ nhiều phía không có
nghĩa xác định được phía phát âm. Một mic cố định không cung cấp các kênh đồng
thời để tính chênh lệch thời gian đến giữa các mic cho DoA 360°.

Vì vậy, bản đầu cho phép lệnh giọng nói như đi/dừng/rẽ sau nhận dạng và kiểm tra
giới hạn; chưa tự suy ra hướng người nói hay tự di chuyển theo hướng đó. Bộ
phân xử lệnh và Motion vẫn áp dụng cùng điều kiện arm, timeout và cảm biến như
điều khiển Web. Chốt chân I2S RX/TX, mức logic, clock, nguồn, nhiễu và việc
thu/phát loa trên nguyên mẫu; mất mạng vẫn cần cảnh báo thiết yếu lưu cục bộ.

### Nâng cấp DoA: cần chọn lại đường thu

Các yêu cầu dưới đây dành riêng cho nâng cấp, không ràng buộc nghiệm thu hay
PCB bản đầu. Chưa chốt phải mua 4 INMP441; chỉ giữ phương án đó để đánh giá.

1. Chọn bố trí mic không thẳng hàng, đo tọa độ và hướng lắp, chọn sample rate,
   đo nhiễu do motor/servo và rung cơ khí. Không hứa độ chính xác góc trước thử nghiệm.
2. Nếu giữ 4 INMP441: khảo sát 2 cặp stereo trên 2 đường dữ liệu, dùng clock
   BCLK/WS chung và kiểm chứng cấu hình master/slave, thời điểm bắt đầu, lệch
   DMA, thứ tự kênh và trôi mẫu. Đây là phương án thử, chưa phải sơ đồ đã xác nhận.
   Khả năng S3 có 2 I2S không tự chứng minh 4 mẫu đã đồng bộ. Phải kiểm tra cả
   việc phát loa đồng thời; I2S có thể dùng full duplex khi cấu hình phù hợp [S2].
3. Phương án thay thế: module array có đầu ra nhiều kênh đồng bộ, hoặc bộ gom
   dữ liệu thích hợp. Chế độ TDM trên S3 không tự biến mic I2S stereo thành mic
   TDM; phải kiểm tra tương thích của phần cứng đầu vào.
4. Giữ PCM tại khối thu. Ví dụ 4 kênh, 16 kHz, 16 bit có payload
   `4 * 16000 * 2 = 128000 byte/s`; UART 8N1 cần ít nhất 1.28 Mbit/s chỉ cho
   payload, chưa tính framing. UART 460800 baud không đủ cho cấu hình này.
5. Đánh giá thuật toán như GCC-PHAT/SRP-PHAT với VAD, ngưỡng tin cậy và khoảng
   trễ vật lý theo khoảng cách mic. Giai đoạn đầu bỏ kết quả khi loa đang phát;
   chỉ nghe và nói đồng thời sau khi AEC được kiểm chứng.
6. Xuất `angle_body`, `confidence`, độ mới kết quả và cờ hợp lệ. Góc quy ước:
   0° phía trước, 90° bên trái, 180° phía sau, 270° bên phải. Không đưa góc này
   thẳng thành góc servo. Bộ lập chuyển động phải xét hình học lái và vùng an toàn.
7. Bản đầu chỉ hiển thị hướng. Chỉ bật chuyển động tốc độ thấp sau khi người dùng
   arm và bài thử DoA/an toàn đạt; góc không tiếp cận được bằng cung tiến an toàn
   thì dừng và báo trạng thái. Mất độ tin cậy hoặc kết quả quá hạn thì dừng chế độ này.

## 6. Truyền động, cảm biến và dừng an toàn

Đo đường kính bánh hiệu dụng `D` (m) và số tick `N` thực sự trên **một vòng bánh**,
bao gồm hộp số và cách giải mã x1/x2/x4. Với số tick có dấu `dn` trong `dt` giây:

```text
v_wheel = (dn / N) * pi * D / dt        # m/s
speed_kmh = 3.6 * v_vehicle
```

Trong mô hình lăn không trượt, dùng `v_vehicle = (v_left + v_right) / 2` để
ước lượng tốc độ tâm cầu sau; đây không phải phép đo vận tốc độc lập với encoder.

Với mô hình bicycle ở tốc độ thấp: `R = L / tan(delta)`, trong đó `L` là chiều
dài cơ sở và `delta` là góc lái tương đương đã hiệu chuẩn, không phải góc servo
trực tiếp. Ví dụ rẽ trái, `R > 0`, bề rộng cầu sau `W`, tốc độ tâm cầu sau `v`:

```text
v_left  = v * (1 - W / (2 * R))
v_right = v * (1 + W / (2 * R))
```

Rẽ phải thì đổi vai bánh trong/ngoài. Đi thẳng đặt hai setpoint bằng nhau;
giới hạn góc theo cơ khí, giữ `abs(R) > W/2` cho mô hình cung tiến này và giảm tốc
cả cặp theo cùng tỉ lệ khi chạm giới hạn motor. Encoder đo vận tốc lăn ước lượng,
không đảm bảo vận tốc thật khi trượt bánh. IMU 6 trục phục vụ ước lượng nghiêng;
không coi yaw tích phân gyro là hướng la bàn tuyệt đối.

Các điều kiện dừng phải bao gồm mất lệnh mới, lỗi cảm biến thiết yếu/quá hạn,
vật cản, mất nền, nghiêng quá mức, kẹt bánh và nguồn ngoài giới hạn đã xác định.
Dùng lọc và hysteresis nhưng phải tính thời gian lọc vào độ trễ dừng. Kẹt bánh
cần đối chiếu yêu cầu chạy, vận tốc thực, dòng và thời gian; tránh báo nhầm lúc khởi động.

**Phân biệt dừng và phanh:** TB6612FNG có các chế độ short brake, stop và standby;
`STBY = LOW` làm ngõ ra trở kháng cao [S4], không giữ/phanh bánh chủ động.
Chọn trình tự giảm tốc/phanh/ngắt driver phù hợp, đo quãng đường cho cả phanh
chủ động lẫn thả trôi. Khi mất nguồn hoặc dừng khẩn cấp cắt nguồn motor, phải
tính theo trường hợp thả trôi. Có pull-down STBY bên ngoài, watchdog và mạch
dừng khẩn cấp cắt nguồn motor hoặc khóa driver độc lập với CPU; một nút chỉ
gửi sự kiện phần mềm không đáp ứng yêu cầu này. Nhả nút dừng không được tự chạy lại.

Giới hạn vận tốc phải dựa trên phép đo, không chỉ khoảng cách đặt ngưỡng ToF:

```text
d_required >= v * T_total + v^2 / (2 * a_min) + margin
```

`T_total` gồm lấy mẫu, lọc, lập lịch và phản ứng cơ cấu; `a_min > 0` là giảm tốc
thấp nhất đo được trong điều kiện tải/nền thử. Với mép rơi, khoảng cảm biến
phát hiện trước vùng tiếp xúc bánh cũng phải đủ lớn so với quãng dừng. Nếu
chưa chứng minh được giảm tốc hoặc vùng phát hiện, chưa cho chạy gần mép rơi.
TCRT5000 cần thử nền tối/sáng/bóng và ánh sáng môi trường; nếu không đạt ở độ cao
lắp thật thì thay/bổ sung cảm biến hướng xuống có dải đo phù hợp, rồi thử lại.

## 7. Nguồn và linh kiện cần chốt trước khi mua

- **Motor/driver:** chọn SKU N20, điện áp, RPM có tải, tỉ số truyền, loại encoder,
  dòng khởi động/kẹt và tải xe. TB6612FNG chỉ là ứng viên cho 2 motor. Datasheet
  nêu 1.2 A trung bình và 3.2 A đỉnh; 3.2 A gắn với xung đơn 10 ms trong bảng
  giới hạn tuyệt đối, không phải mức vận hành thiết kế [S4]. Đối chiếu thêm
  bảng vận hành khuyến nghị, nhiệt PCB/module và điều kiện hai kênh cùng tải.
- **Pin/sạc:** chốt hóa học pin, dòng xả, BMS 2S và bộ sạc đúng loại. Tính ở điện
  áp pack đầy và gần cạn; buck cần đủ headroom, đáp ứng dòng xung. Không sạc
  pack 2S trực tiếp từ nguồn 5 V; mạch sạc phải có topology phù hợp.
- **Các rail:** motor theo định mức motor; servo theo model thật và dòng kẹt;
  logic/âm thanh theo board/module được chọn. Không mặc định tất cả dùng 5 V.
  Tổng ngân sách dòng phải xét 2 motor khởi động, servo bị tải, loa phát lớn và
  Wi-Fi phát đồng thời; dung lượng pin chưa thể suy ra thời gian chạy khi chưa đo tải.
- **Đi dây:** logic và motor chung tham chiếu GND; bố trí đường dòng lớn tránh
  đường mic/ADC, tụ decoupling/bulk gần tải, chống nhiễu motor. Không đưa dòng
  motor/servo lớn qua breadboard hoặc đường nguồn MCU.
- **Mức logic:** UART, I2C và ADC phải tương thích 3.3 V. TB6612FNG có VCC logic
  tách VM motor; chọn VCC phù hợp GPIO. Kiểm tra pull-up I2C trên từng breakout,
  tổng trở khi mắc song song, điện áp ngõ ra encoder và mạch chia áp FSR.
- **GPIO/bus:** lập bảng chân theo đúng module flash/PSRAM và board; loại chân
  bộ nhớ chiếm dụng, chân boot/USB/debug cần giữ [S7]. Chốt controller và độ phân
  giải TFT, SPI, backlight, buffer LVGL, chân I2S/UART/I2C/ADC/PCNT/PWM trước PCB.
- **Cảm biến:** chọn cụ thể MPU6050 hoặc BMI270 và driver tương ứng; chọn biến
  thể VL53L0X/SHT30/INA219 và kiểm tra địa chỉ I2C. Nếu thêm nhiều ToF trùng địa
  chỉ, thiết kế chân XSHUT/đổi địa chỉ hoặc bộ chia bus. INA219 cần chọn shunt,
  dải đo, công suất và calibration; không mặc định mọi breakout chịu dòng motor.
- **Anten:** module WROOM-1U có đầu nối anten ngoài [S8]; chọn anten/cáp và bố trí
  theo module. Không tự thêm đường RF từ chip ra IPEX nếu dùng nguyên module.

## 8. Yêu cầu tối thiểu cho UART và Dashboard

Đề xuất UART 3.3 V TX/RX chéo, chung GND, khởi đầu 115200 baud 8N1 trên dây
ngắn; chỉ tăng baud sau đo lỗi khi motor chạy. Giới hạn mỗi chiều tối đa 50
frame/s, mỗi frame tối đa 128 byte thì dùng 6400 byte/s, thấp hơn năng lực lý
thuyết 11520 byte/s của 115200 8N1. Đây là ngân sách đề xuất, chưa là wire format.

Trước khi viết firmware hai đầu, phải đặc tả và kiểm thử:

- Marker/độ dài, phiên bản, loại bản tin, session, sequence, payload, CRC;
  quy định byte order, đơn vị, giới hạn khung và cách tái đồng bộ khi mất byte.
- Lệnh gồm vận tốc có dấu (m/s), góc lái tương đương, chế độ và hạn dùng tương
  đối. Motion đo hạn dùng bằng đồng hồ cục bộ từ lúc nhận; không so trực tiếp
  timestamp của hai MCU chưa đồng bộ. Motion áp trần timeout cục bộ, không cho
  Brain tăng quá giới hạn đã cấu hình; kiểm tra giá trị hữu hạn và miền vận
  tốc/góc/chế độ trước khi nhận lệnh. Bản đầu từ chối vận tốc âm.
- Chỉ frame lệnh **mới, hợp lệ, đúng phiên và sequence** mới làm mới hạn điều
  khiển. Heartbeat, telemetry, CRC sai hay frame lặp không giữ xe tiếp tục chạy.
- Brain chỉ chuyển tiếp thao tác Web mới hoặc setpoint mới từ bộ điều khiển tự
  hành đang có dữ liệu hợp lệ. Không phát lại lệnh cache để che mất kết nối;
  hàng đợi có giới hạn và loại lệnh cũ.
- Motion giữ trạng thái disarmed khi kết nối lại/reset, yêu cầu handshake và arm
  mới; arm không tự khôi phục setpoint trước đó. Quy định mất/gói đảo thứ tự,
  sequence wrap, đổi session và lỗi parser trước khi triển khai.
- Dashboard chỉ cho một phiên điều khiển đã xác thực; có dead-man/lease, nút
  dừng, giới hạn vận tốc/góc và ngắt lệnh khi mất WebSocket, đóng/ẩn tab hoặc
  mất quyền điều khiển. Dừng vẫn phải dựa vào timeout trên Motion khi trình duyệt treo.
- Hiển thị tốc độ mục tiêu/thực, trạng thái arm, lỗi, tuổi telemetry, nguồn,
  cảm biến và lý do từ chối lệnh. Dữ liệu cũ phải hiện mất kết nối, không tiếp
  tục hiển thị như số đo hiện tại. QR dùng địa chỉ truy cập thực theo STA/AP;
  mã QR và việc ở cùng Wi-Fi không thay thế xác thực điều khiển.

## 9. Lộ trình và điều kiện nghiệm thu

Các hàng dưới đây là **bài thử phải thực hiện**, chưa có hàng nào đạt trên xe.

| Giai đoạn | Sản phẩm bàn giao | Điều kiện chuyển bước |
| --- | --- | --- |
| P0 - Chốt thiết kế | BOM có SKU/datasheet, hình học lái, sơ đồ nguồn, bảng chân, giới hạn vận hành | Tính dòng/nhiệt/headroom; chọn được rail, sạc/BMS/driver phù hợp; chốt phạm vi chỉ tiến và vùng thử |
| P1 - Motion trên bàn thử | Motor/encoder/servo, PID, cảm biến, state machine dừng | Thử bánh nhấc khỏi đất trước; boot/reset không chạy; chiều và tốc độ encoder đúng; giới hạn cơ khí servo; xử lý mất cảm biến, quá dòng/kẹt và E-stop |
| P2 - UART và Web | Hai MCU, đặc tả giao thức, Dashboard, lái tốc độ thấp | Cố ý ngắt Web/UART, treo/reset Brain, chèn frame sai/lặp/quá dài; Motion dừng trong hạn đo được và không tự khởi động lại; chỉ một nguồn điều khiển |
| P3 - TFT và giọng nói 1 mic | LVGL, QR, Xiaozhi, lệnh giọng nói, cảnh báo cục bộ | Stress Wi-Fi + GIF + thu/phát loa; không reset do sụt nguồn; kiểm tra phân xử Web/giọng nói và timeout; Motion giữ lịch điều khiển; mất Internet vẫn dừng và phát cảnh báo cục bộ được nếu Brain còn hoạt động |
| P4 - Chạy tích hợp và PCB bản đầu | Báo cáo thử tải/nhiễu, sơ đồ và layout motherboard 2 MCU/1 mic | Sau P0-P3: đo quãng dừng theo tải/nền/điện áp và các chế độ lỗi; thử mép rơi có gá bảo vệ; ghi brownout, nhiệt, CPU/heap, độ trễ; nguyên mẫu đạt rồi mới làm PCB; không chờ DoA |
| P5 - Nâng cấp DoA | Cụm thu đa kênh đồng bộ, bộ dữ liệu đo góc, chế độ hướng âm | Chọn phần cứng; đo lệch/trôi kênh, góc quanh xe, khoảng cách, nhiễu/vọng, motor/loa; chốt ngưỡng tin cậy/sai số chấp nhận trước đánh giá; bật di chuyển sau bài thử cung lái và an toàn; đánh giá lại PCB nếu đổi phần cứng |

Trước mỗi bài thử chuyển động, lập giá trị nghiệm thu định lượng theo xe thật:
tốc độ tối đa, sai số tốc độ, góc nghiêng, dòng/thời gian kẹt, tuổi tối đa từng
cảm biến, thời gian và quãng đường dừng. Cần cơ cấu giữ xe khi thử mép rơi;
không thử bằng cách cho xe tự do tiến tới cầu thang. Tính cả độ trễ 250 ms đề
xuất vào quãng dừng; giảm timeout/tốc độ nếu vùng phát hiện không đủ.

### Những việc còn phải quyết định

Chưa có dữ liệu để chốt kích thước/tải xe, bánh, SKU motor/servo, dòng kẹt,
loại board S3, màn hình, ngân sách và thời gian chạy mong muốn. Bản đầu đã chốt
1 mic và 2 MCU; phần còn lại cần hoàn tất ở P0. Số lượng mic, đường thu đồng bộ
và tiêu chí sai số DoA dành cho P5, chưa được chứng minh. Đây là đầu vào thiết
kế, không phải lỗi đã được sửa trên phần cứng.

## 10. Nguồn kỹ thuật đã đối chiếu

- **[S1]** [LVGL - Introduction](https://docs.lvgl.io/master/intro/introduction/index.html): bản chất thư viện giao diện.
- **[S2]** [ESP-IDF - I2S trên ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/i2s.html): 2 I2S, slot standard, clock và full duplex; khi triển khai phải dùng tài liệu đúng phiên bản SDK đã ghim.
- **[S3]** [Vishay - datasheet TCRT5000](https://www.vishay.com/docs/83760/tcrt5000.pdf): bảng Product Summary/Basic Characteristics và đồ thị khoảng cách, không phải cam kết đo độ cao tuyệt đối.
- **[S4]** [Toshiba - datasheet TB6612FNG, bản lưu tại Pololu](https://www.pololu.com/file/0J86/TB6612FNG.pdf): Absolute Maximum Ratings, Operating Range và H-SW Control Function; thông số IC không thay cho khả năng tản nhiệt của module thực tế.
- **[S5]** [Xiaozhi README tại commit 7e69845](https://github.com/78/xiaozhi-esp32/blob/7e69845d818553ac045efbcde746b22bef6eecf6/README.md): wake word offline, truyền âm thanh qua mạng, custom board và yêu cầu SDK. Đây là nguồn tham chiếu đã đọc, chưa phải lựa chọn dependency của AW-Car.
- **[S6]** [Texas Instruments - INA219](https://www.ti.com/product/INA219): đo điện áp bus và sụt áp shunt, cấu hình/calibration dòng.
- **[S7]** [Espressif - ESP32-S3 Schematic Checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html): nguồn, bộ nhớ, GPIO và các chân strapping.
- **[S8]** [Espressif - ESP32-S3-WROOM-1/1U](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf): nguồn và biến thể module/anten; cần đối chiếu đúng mã mua thực tế.

Các tần số, timeout, phân tải, công thức và bài nghiệm thu trong bản này là đề
xuất kỹ thuật cho AW-Car; datasheet không chứng nhận an toàn hay hiệu năng của
toàn bộ xe. Kết quả kiểm tra tài liệu không thay thế phép đo trên nguyên mẫu.
