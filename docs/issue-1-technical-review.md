# Rà soát kỹ thuật issue #1 và kế hoạch hiệu chỉnh

Ngày rà soát: **23/10/2026**. Nguồn yêu cầu:
[issue #1 - Tóm tắt yêu cầu của xe](https://github.com/TuanDanny/AW-Car/issues/1),
đang mở, chưa có bình luận tại thời điểm đọc.
Đã đọc lại bản issue cập nhật lúc **11:22 ngày 23/10/2026 (UTC+7)**.

**Cập nhật theo đồ đã có ngày 28/10/2026:** hai ESP32-S3 có Wi-Fi (chủ dự án
ghi `R16N8`, cần ảnh xác nhận mã/bộ nhớ), OLED 0,96 inch **I²C**, INMP441,
MPU6050 và bộ xe acrylic/4 motor/4 bánh/4 đĩa mã. Mốc kiểm kê và thứ tự chọn
mua hiện tại ở [linh kiện](../hardware/components.md); bảng BOM gốc trên issue
và sơ đồ ngày 24/10 chưa được đồng bộ. Ảnh bổ sung cho thấy motor dạng TT,
khung bánh cố định; chủ dự án đã chọn **4WD lái bằng tốc độ hai bên**, thay
servo/Ackermann. Chưa có cảm biến đọc đĩa A/B hoặc thông số điện motor được
xác nhận. Kích thước quảng cáo/mốc đo khác nhau được ghi trong bảng kiểm kê.

Ưu tiên chi phí mới cùng ngày: chủ dự án chỉ cần đo độ lớn tốc độ bằng một
OUT. [Kế hoạch xung đơn](single-channel-encoder-plan.md) chọn hai V2 +
chuyển mức về 3,3 V + RTL xung đơn/protocol v2. **Phần FPGA v2 hiện đã có
mô phỏng; firmware Motion v2 và phần cứng chưa triển khai.** Các mô tả
quadrature ở phần rà soát lịch sử dưới đây áp dụng cho mode A/B v1,
không phải phần cứng một OUT đang chọn; không gán chiều lệnh thành chiều đo.

**Lịch sử quyết định ngày 23/10/2026, phần servo đã được thay ngày 28/10:** thêm FPGA đọc encoder,
phát PWM 2 motor sau và watchdog; Motion giữ PID, servo và an toàn. Board mục
tiêu hiện là Tang Nano 9K, chưa mua/chưa xác nhận fit và timing đúng chip. Kế hoạch mới nhất ở
[FPGA và toàn hệ thống](fpga-drive-plan.md); nội dung issue chưa đồng bộ FPGA.

## 1. Phạm vi và kết luận

Ở lần rà soát ban đầu, dự án đang lên kế hoạch, chưa lắp xe. Kho ở commit
`d32db1daf27cbe58e72cc8057cdf61945b7adade` chỉ có `LICENSE`.
Do đó, đây là rà soát yêu cầu và thiết kế; chưa có mã nguồn để sửa lỗi hoặc
chạy kiểm thử firmware. Các hiệu chỉnh dưới đây được ghi vào tài liệu trong
kho cục bộ, chưa thay đổi nội dung issue trên GitHub.

**Kiến trúc mục tiêu bản đầu:** khung TT 4WD đang có, hai nhóm motor trái/phải,
hai encoder A/B đại diện (một bánh mỗi bên), 2 ESP32-S3, 1 FPGA,
**1 mic INMP441**, an toàn cục bộ, Dashboard, OLED I²C và tương tác giọng nói.
Không dùng servo lái; chưa có bốn vòng điều khiển độc lập. Motor/encoder và
tầng driver phải đối chiếu thực, không coi là đã mua đúng BOM N20 cũ. Người sở hữu chọn
"Dùng 1 mic trước; giữ DoA cho giai đoạn nâng cấp".

Mic bản đầu phục vụ thu giọng nói/lệnh, không dùng để tính góc DoA 360° hay tự
hướng về người nói. Định hướng âm thanh vẫn là mục tiêu nâng cấp, cần cụm thu
đồng bộ và nguyên mẫu chứng minh riêng. Khả năng ước lượng góc không đồng nghĩa
xe đã được phép quay tại chỗ hoặc đi tới mọi góc an toàn. Cần hoàn tất chọn nguồn, driver và
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
- Phần phân tải: bản đầu Brain xử lý thu/phát âm thanh, Xiaozhi, OLED I²C và Web;
  Motion xử lý setpoint/PID hai bên 4WD và an toàn; FPGA đọc 2 encoder A/B,
  phát hai nhóm PWM/chiều cho tầng driver bốn motor và watchdog lệnh.
  DoA chưa nằm trong tải bản đầu; không mua servo lái.
- Tổng quan và BOM dùng 2 ESP32-S3, 1 FPGA mục tiêu Tang Nano 9K; motherboard bản đầu
  có 1 mic và FPGA/đầu nối board FPGA. MCU thứ ba và cụm mic nâng cấp chỉ xem
  xét khi có số đo tải/phương án thu. Ghi chú BOM của mic đổi
  thành "Thu giọng nói/lệnh; chưa hỗ trợ định hướng nguồn âm" để tránh nhầm
  đặc tính thu đa hướng của mic với khả năng xác định góc.

Các câu trên đã được phản ánh trong tài liệu cục bộ; issue GitHub chưa được sửa
bởi lần rà soát này.

## 2. Những yêu cầu đã nắm

| Mã | Kết quả mong muốn | Phạm vi đề xuất |
| --- | --- | --- |
| F01 | Di chuyển mượt, đo m/s và km/h, giữ tốc độ khi tải thay đổi | TT 4WD lái bằng tốc độ hai bên; FPGA đọc encoder/phát PWM, Motion chạy PID trái/phải; xem ghi chú bên dưới |
| F02 | Nâng cấp: xác định hướng người nói, hướng đầu xe về nguồn âm | Hoãn khỏi bản đầu 1 mic; chọn cụm thu đồng bộ, đo độ tin cậy rồi mới cho di chuyển |
| F03 | Xiaozhi nhận lệnh và phản hồi bằng loa | Bản đầu dùng 1 mic; Brain xử lý tương tác; lệnh chuyển động qua lớp kiểm tra; cảnh báo thiết yếu lưu cục bộ |
| F04 | Dừng khi gặp vật cản, mép rơi, nghiêng, va chạm hoặc kẹt | Motion quyết định dừng độc lập Brain, khóa driver ngoài UART FPGA; FPGA tự hết hạn lệnh Motion; E-stop độc lập phần mềm |
| F05 | OLED 0,96 inch I²C đã có: biểu cảm/trạng thái; Dashboard điều khiển/debug | Brain chạy màn hình và mạng; controller/độ phân giải chờ xác nhận; QR/GIF/LVGL phải đánh giá lại, không giữ tiêu chí TFT cũ |
| F06 | Motherboard tích hợp MCU, FPGA/đầu nối FPGA, nguồn, âm thanh | Làm cho cấu hình 2 MCU/1 FPGA/1 mic sau khi nguyên mẫu đạt; DoA nâng cấp có thể cần sửa PCB |

### Ghi chú bổ sung F01 — 30/10/2026

Các ý cần thử, **chưa triển khai/kiểm chứng trên xe**. Áp dụng khung TT 4WD,
hai nhóm motor trái/phải, không servo lái; thay mô tả Ackermann cũ cho F01.

**Cập nhật 01/11/2026:** motor TT **9 V theo shop**, chủ dự án chọn hướng
đơn giản **2S cấp trực tiếp VM DRV8833**, chấp nhận điện áp motor thấp hơn
định mức; không yêu cầu rail motor ổn định 9 V. Nhánh logic vẫn ổn áp riêng.
Xem [ghi chú phần cứng](../hardware/README.md); cần thử lực khi pin yếu,
dòng khởi động/kẹt và nhiệt driver trên xe thực.

- **Giữ tốc độ khi lên dốc/tải tăng:** phản hồi encoder, Motion dùng PI/PID
  tăng/giảm PWM trong giới hạn dòng, nguồn và nhiệt; có chống tích lũy sai số
  khi đầu ra bão hòa [S10]. Dùng mô hình Laplace để phân tích/hiệu chỉnh;
  không cam kết giữ tốc độ khi vượt khả năng motor hoặc bánh trượt.
- **Kích đề-pa:** khi có lệnh chạy hợp lệ và xe đứng yên, tạo cú kích PWM
  ngắn rồi nội suy giảm mượt về điều khiển tốc độ. Hiệu chỉnh mức/thời gian,
  chưa chốt 100%; giới hạn dòng/thời gian, kẹt thì dừng, không kích lặp vô hạn.
  Không tự chạy lúc bật nguồn; dừng an toàn bỏ qua nội suy.
- **Đi theo quãng đường, ví dụ 2 m:** đếm encoder từ lúc đề-pa, hiệu chuẩn
  mm/xung, giữ hướng và giảm tốc trước đích; đo sai số thực do trượt/quán tính.
- **Mã Gray nếu phù hợp:** dùng chuỗi pha khi giải mã encoder A/B [S11];
  cân nhắc con trỏ Gray nếu sau này có FIFO khác miền clock, kèm đồng bộ và
  ràng buộc timing. Encoder một OUT đã chọn không tự đo được chiều quay;
  không ghép OUT hai bánh thành A/B. RTL hiện có A/B, mode một OUT còn phải làm;
  không đổi mọi bộ đếm sang Gray hoặc coi Gray làm xe đi chính xác hơn.

## 3. Các điểm cần sửa trong kế hoạch

Phân biệt **sai mô tả**, **thiếu thiết kế** và **rủi ro cần thử**; không coi mọi
linh kiện trong issue là linh kiện sai.

| Điểm | Phân loại | Hiệu chỉnh kỹ thuật |
| --- | --- | --- |
| LVGL được gọi là Mini OS | Sai mô tả | LVGL là thư viện đồ họa [S1]. Dùng ESP-IDF/FreeRTOS làm nền tảng, xây giao diện dạng Mini OS bằng LVGL. |
| Phương án servo/Ackermann không khớp bộ khung đã có | Đã đổi kiến trúc 28/10 | Chủ dự án chọn nguyên bộ TT 4WD bánh cố định, lái bằng tốc độ hai bên; bỏ servo. Skid-steer có trượt khi rẽ, cần thử dòng/quãng dừng; chưa bật quay tại chỗ. |
| BOM đổi thành 1 mic nhưng F02 vẫn ghi 4 mic và DoA 360° | Mâu thuẫn yêu cầu; đã chốt phương án | Theo xác nhận của người sở hữu: 1 mic cho giọng nói ở bản đầu, giữ DoA cho nâng cấp bằng cụm mic đồng bộ. Issue còn cần sửa mô tả F02. |
| Thu nhiều mic cho DoA chưa có phương án đồng bộ | Thiếu thiết kế ở giai đoạn nâng cấp | I2S standard có 2 slot trái/phải; S3 có 2 bộ I2S [S2]. Nếu chọn 4 INMP441 thì phải chốt đường thu, clock và căn chỉnh mẫu. Đây không còn là điều kiện làm bản đầu. |
| DoA vẫn được đặt ở Motion trong mô tả phân tải | Mô tả chưa đồng bộ phạm vi | Bản đầu không chạy DoA. Khi nâng cấp, ưu tiên giữ thu âm và DoA trên Brain hoặc bộ xử lý âm thanh chuyên dụng sau đo tải; Motion nhận lệnh đã giới hạn. |
| TCRT5000 được coi là cảm biến đo độ cao gầm | Sai mô tả | Đây là cảm biến phản xạ, không phải máy đo khoảng cách tuyệt đối. Datasheet nêu điểm làm việc cực đại khoảng 2.5 mm; khoảng 0.2-15 mm có điều kiện thử [S3]. Chỉ dùng nhận biết nền/mép rơi sau hiệu chuẩn và thử bề mặt. |
| Cấp nguồn bằng 2 buck 5 V chưa đủ đặc tả | Thiếu thiết kế | Phân rail theo điện áp bốn motor và logic thực tế. Module WROOM trần cần nguồn 3.3 V; chân vào 5 V chỉ dùng nếu board phát triển hỗ trợ. Hai buck chung pin không tạo cách ly điện. |
| TB6612FNG được chọn khi chưa biết motor cụ thể | Rủi ro chọn linh kiện | N20 là phương án cũ; bộ hiện có motor dạng TT, chưa rõ SKU/thông số điện. Chọn điện áp/dòng kẹt, rồi đối chiếu đủ bốn motor, nhiệt và driver [S4]; không coi một module hai kênh đủ hai cặp motor. |
| BMS 2S bị để chung với yêu cầu sạc | Thiếu thiết kế | BMS không thay thế bộ sạc. Với Li-ion 4.2 V/cell, pack 2S đầy là 8.4 V; cần sạc CC/CV đúng loại pin, bảo vệ/cân bằng phù hợp, cầu chì và đầu nối đủ dòng. |
| Liên kết UART mới chỉ yêu cầu tốc độ cao | Thiếu thiết kế | Cần đóng khung, CRC, số thứ tự, phiên kết nối, giới hạn lệnh và timeout. Tốc độ UART cao không tự bảo đảm độ trễ hay dừng an toàn. |
| Xiaozhi Lite/Robotics chưa chỉ ra dự án/phiên bản | Thiếu căn cứ triển khai | Ghim repository, commit, board và SDK tương thích. Upstream đã kiểm tra có xử lý giọng nói qua mạng và wake word cục bộ [S5]; không mặc định toàn bộ AI chạy offline trên S3. |
| FSR402 và INA219 được kỳ vọng phát hiện mọi quá lực/kẹt | Thiếu phạm vi đo | FSR chỉ phản ánh lực ở vị trí lắp, cần cơ cấu/hiệu chuẩn. INA219 đo dòng của nhánh đặt shunt [S6]; một cảm biến tổng không xác định riêng motor nào kẹt. Kết hợp encoder và thời gian quá dòng. |
| Hai nhóm 4WD cần setpoint khác nhau khi rẽ | Thiếu thuật toán/kiểm chứng | Motion chuyển vận tốc thẳng/tốc độ quay thành setpoint trái/phải, PID theo bên, giới hạn và chống tích lũy. Cùng duty không bảo đảm hai bánh cùng bên đồng tốc; hai encoder không giám sát hết bốn motor. |
| Chống rơi mới có 2 cảm biến, vật cản chỉ có cảm biến trước | Thiếu vùng bảo vệ | Bản thử đầu chỉ chạy tiến trong vùng đã kiểm chứng. Chỉ cho lùi sau khi bổ sung/kiểm chứng vùng cảm biến phía sau; không tự lùi để hướng về người nói khi chưa có bảo vệ. |

## 4. Kiến trúc đề xuất

### MCU 1 - Brain

- Thu âm bằng 1 INMP441, phát loa, wake word và kết nối Xiaozhi. Bản đầu không
  chạy DoA; lệnh giọng nói đã nhận dạng được xử lý độc lập với việc biết góc người nói.
- OLED 0,96 inch I²C, Wi-Fi và dữ liệu chẩn đoán. Controller, độ phân giải,
  cách vẽ biểu cảm và khả năng dùng LVGL/QR chờ xác nhận màn hình thực.
- Chuyển lệnh Web/giọng nói thành yêu cầu vận tốc thẳng/tốc độ quay có giới hạn.
- Phát cảnh báo thiết yếu từ âm thanh lưu cục bộ khi mất mạng; ưu tiên cảnh báo
  hơn hiệu ứng giao diện. Motion phải dừng trước, không chờ loa hay Dashboard.
- Lệnh từ AI đi qua cùng bộ phân xử với lệnh Web; chỉ một nguồn có quyền điều
  khiển tại một thời điểm. Dừng khẩn cấp và lỗi an toàn luôn có ưu tiên cao hơn.

### MCU 2 - Motion

- Nhận snapshot encoder từ FPGA, tính tốc độ/setpoint/PID hai bên 4WD và giám
  sát an toàn cục bộ. Gửi duty/chiều/quyền chạy cho FPGA, không phát PWM motor.
- Có đường khóa driver riêng ngoài UART; mất phản hồi FPGA hoặc snapshot quá
  hạn phải bỏ arm/khóa driver. Không phát lại duty cache để giữ watchdog.
- Đọc cảm biến theo tác vụ/lịch không chặn vòng điều khiển; mỗi mẫu có timestamp
  và cờ hợp lệ. Lỗi cảm biến thiết yếu có thể dừng xe; lỗi SHT30 chỉ cần báo lỗi.
- Thực thi state machine gồm `DISARMED`, `ARMED` và `FAULT` với điều kiện chuyển
  rõ ràng. Khi khởi động/reset, mặc định `DISARMED`, chưa cấp lệnh chạy motor.
- Timeout điều khiển đưa xe về `DISARMED`; lỗi an toàn nghiêm trọng chốt `FAULT`.
  Chỉ cho arm lại bằng thao tác chủ động sau khi điều kiện lỗi đã hết.

Mục tiêu ban đầu để thử: vòng điều khiển 100 Hz, lệnh Brain-Motion mới 20-50 Hz,
timeout lệnh Brain 250 ms. Liên kết Motion-FPGA dự kiến 100 Hz, timeout 50 ms;
xem [đặc tả cần chốt](fpga-drive-plan.md#4-giao-tiếp-và-an-toàn).
Đây là **giá trị đề xuất cần đo**, không phải kết quả đạt
được hay thông số đủ an toàn cho mọi tốc độ. Lịch đọc ToF phải tôn trọng timing
budget thực của cảm biến; không ép tất cả cảm biến chạy 100 Hz.

### FPGA - khối truyền động

- Đồng bộ/giải mã 2 encoder A/B, chốt số đếm đồng thời và gửi trạng thái Motion.
- Phát hai nhóm PWM/chiều cho tầng driver bốn motor; không cấp công suất trực tiếp motor.
- Kiểm tra lệnh/arm, giới hạn duty và watchdog; reset/mất lệnh không tự chạy lại.
- Trạng thái tắt trước khi FPGA cấu hình/mất nguồn do gate/pull-down ngoài FPGA
  đảm nhận. Watchdog RTL không bảo vệ khi chính clock FPGA dừng; Motion khóa
  driver qua đường riêng. E-stop không phụ thuộc MCU/FPGA.

#### Ghi chú đồ án RTL: đặc tả → waveform → kiểm chứng → PPA

**Ưu tiên từ 31/10/2026:** CPU mini và FPGA AW-Car khó theo hai hướng khác
nhau (datapath/ISA so với giao thức/FSM/an toàn), không so hơn kém bằng
số sao. Trước khi tối ưu, nhóm **chốt đặc tả và waveform kỳ vọng**:

1. **Đặc tả (spec) trước:** sơ đồ khối; input/output (tên, bit, chiều, mức
   tích cực), clock 27 MHz, reset, các parameter; bảng chuyển trạng thái
   Safety FSM và ưu tiên lỗi; giao thức UART/session/CRC; PWM, encoder,
   điều kiện motor được phép chạy. Gắn mỗi yêu cầu với testcase và owner.
2. **Waveform trước:** vẽ timing kỳ vọng, sau đó đối chiếu VCD/GTKWave
   cho 4 luồng: (a) reset/boot motor OFF; (b) HELLO → ARM_ZERO →
   STATUS ARM_PENDING phát hết → Motion permit → ARMED; (c) CMD hợp lệ
   → PWM 20 kHz và snapshot encoder 10 ms; (d) mất CMD 50 ms →
   FAULT, CLEAR (giữ gate_clear 100 µs, tối đa 5 ms), không tự ARM.
   Chú thích mốc clock/thời gian, độ rộng xung, quan hệ valid/ready và
   tín hiệu motor/gate trên waveform; không dùng hình chỉ có xung mà
   thiếu giải thích.
3. **Kiểm chứng:** testbench phải kiểm tra đúng đặc tả và waveform,
   kể cả race ở deadline, CRC lỗi, reset/permit khi PWM HIGH; lưu VCD,
   test log và kết quả PASS/FAIL gắn commit. Mô phỏng không chứng minh
   an toàn khi mất clock hay mạch gate thật.
4. **PPA sau khi đặc tả/test ổn định:** so sánh hai phương án Safety FSM
   **cùng chức năng**: A dùng một `phase_count` chung hiện có, B dùng
   timer riêng cho handshake/watchdog/CLEAR (**B chưa triển khai**).
   Cùng clock, stimulus/seed và thư viện/corner: **Area** (cell, FF,
   diện tích SKY130); **Performance** (logic depth/critical path,
   Fmax nếu STA hợp lệ); **Power** (số bit chuyển mức/chu kỳ từ VCD
   chỉ là proxy nếu thiếu mô hình công suất). Báo LUT/FF/timing Gowin
   ở bảng riêng; không tự điền số đo. Không bỏ CRC/watchdog/gate để giảm PPA.

**Bàn giao theo nhóm:** TV1 chốt FSM/reset/gate, spec chung và hai biến thể
PPA; TV2 chốt UART frame/CRC/session và waveform giao tiếp; TV3 chốt
PWM/encoder, waveform đổi chiều/snapshot. Người điều phối chỉ duyệt khi có
**spec + waveform có chú thích + testcase PASS + bảng PPA hai phương án**
và cả bên phát/bên nhận đã xác nhận interface. Phần cứng ảo,
`make sim`/`make synth`/`make demo`, nhật ký lỗi và phần dùng AI phải
được bổ sung nếu nộp theo quy định môn học; AW-Car là đề ngoài danh sách
nên cần giảng viên chấp thuận.

Cấu hình bản đầu dùng 2 MCU và 1 FPGA. MCU thứ ba chỉ được xem xét
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
   đo nhiễu do motor và rung cơ khí. Không hứa độ chính xác góc trước thử nghiệm.
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
   thẳng thành lệnh quay motor. Bộ lập chuyển động phải xét động học 4WD và vùng an toàn.
7. Bước đầu của nâng cấp DoA chỉ hiển thị hướng. Chỉ bật chuyển động tốc độ thấp sau khi người dùng
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
ước lượng vận tốc tiến tại tâm xe từ hai bánh đại diện; đây không phải phép
đo độc lập với encoder hoặc bằng chứng cả bốn bánh cùng bên đồng tốc.

Quyết định 28/10 bỏ mô hình bicycle/Ackermann. Với 4WD điều khiển theo bên,
đặt `v` là vận tốc tiến (m/s), `omega` là tốc độ quay (rad/s, dương khi rẽ
trái), `W_eff` là khoảng cách hai vệt bánh hiệu dụng cần hiệu chuẩn:

```text
v_left_target  = v - omega * W_eff / 2
v_right_target = v + omega * W_eff / 2
```

Hai motor cùng bên nhận một lệnh nhóm, chưa điều khiển/đo độc lập từng bánh.
Đây là mô hình xấp xỉ: skid-steer trượt khi rẽ nên phải hiệu chuẩn theo nền/tải,
không dùng rộng ngoài bánh 155 mm làm `W_eff` hoặc hứa yaw chính xác. Bản đầu
giới hạn cả hai setpoint không âm, giảm tốc và giới hạn omega; chưa bật lùi
hay quay tại chỗ dù phần cứng có thể hỗ trợ sau này. Encoder đo vận tốc lăn
ước lượng, không đảm bảo vận tốc thật khi trượt bánh. IMU 6 trục phục vụ ước lượng nghiêng;
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

- **Motor/driver:** bộ xe có 4 motor dạng TT và đã chốt dùng hai nhóm trái/phải;
  chưa xác nhận SKU/thông số điện từ hình dáng. Đánh giá bốn cầu H riêng hoặc
  cầu H đủ tổng dòng cặp motor nếu đấu song song; gate phải khóa cả bốn.
  Đối chiếu điện áp, RPM có tải, tỉ số truyền, loại encoder,
  dòng khởi động/kẹt và tải xe. TB6612FNG chỉ là ứng viên cần đối chiếu từng kênh. Datasheet
  nêu 1.2 A trung bình và 3.2 A đỉnh; 3.2 A gắn với xung đơn 10 ms trong bảng
  giới hạn tuyệt đối, không phải mức vận hành thiết kế [S4]. Đối chiếu thêm
  bảng vận hành khuyến nghị, nhiệt PCB/module và điều kiện hai kênh cùng tải.
- **Pin/sạc:** chốt hóa học pin, dòng xả, BMS 2S và bộ sạc đúng loại. Tính ở điện
  áp pack đầy và gần cạn; buck cần đủ headroom, đáp ứng dòng xung. Không sạc
  pack 2S trực tiếp từ nguồn 5 V; mạch sạc phải có topology phù hợp.
- **Các rail:** bốn motor theo định mức và dòng kẹt thực;
  logic/âm thanh theo board/module được chọn. Không mặc định tất cả dùng 5 V.
  Tổng ngân sách dòng phải xét 4 motor khởi động/rẽ trên nền, loa phát lớn và
  Wi-Fi phát đồng thời; dung lượng pin chưa thể suy ra thời gian chạy khi chưa đo tải.
- **Đi dây:** logic và motor chung tham chiếu GND; bố trí đường dòng lớn tránh
  đường mic/ADC, tụ decoupling/bulk gần tải, chống nhiễu motor. Không đưa dòng
  motor lớn qua breadboard hoặc đường nguồn MCU.
- **Mức logic:** UART, I2C và ADC phải tương thích 3.3 V. TB6612FNG có VCC logic
  tách VM motor; chọn VCC phù hợp GPIO. Kiểm tra pull-up I2C trên từng breakout,
  tổng trở khi mắc song song, điện áp ngõ ra encoder và mạch chia áp FSR.
- **FPGA:** mục tiêu Tang Nano 9K, chưa mua/chưa xác nhận fit/timing; cần
  RTL, mô phỏng và báo cáo đúng chip trước mua.
  Quartus chỉ tham khảo trên chip Altera/Intel được hỗ trợ; Tang Nano dùng
  Gowin [S9]. Xét LUT/FF/RAM/DSP/PLL, I/O, timing sau place-and-route, nguồn,
  bộ nạp, tự khởi động và ngân sách; không quy đổi số FF Quartus trực tiếp.
- **GPIO/bus:** lập bảng chân theo đúng module flash/PSRAM và board; loại chân
  bộ nhớ chiếm dụng, chân boot/USB/debug cần giữ [S7]. Chốt controller và độ phân
  giải/controller OLED I²C, I2S/2 đường UART/I2C/ADC và các
  chân FPGA encoder/PWM/chiều/permit; tách enable/inhibit khỏi UART trước PCB.
- **Cảm biến:** dùng MPU6050 đã có, xác nhận breakout và driver; chọn biến
  thể VL53L0X/SHT30/INA219 và kiểm tra địa chỉ I2C. Nếu thêm nhiều ToF trùng địa
  chỉ, thiết kế chân XSHUT/đổi địa chỉ hoặc bộ chia bus. INA219 cần chọn shunt,
  dải đo, công suất và calibration; không mặc định mọi breakout chịu dòng motor.
- **MCU/anten:** hai ESP32-S3 có Wi-Fi đã có, chủ dự án ghi `R16N8`; cần ảnh
  chữ trên module và board trước khi gán Flash/PSRAM, GPIO hoặc chọn anten.
  WROOM-1U là phương án BOM cũ, không phải model đã xác nhận. Chỉ chọn anten
  ngoài khi board/module thực yêu cầu; đối chiếu datasheet đúng mã [S8].

## 8. Yêu cầu tối thiểu cho UART và Dashboard

Phần này áp dụng cho liên kết **Brain-Motion**; liên kết **Motion-FPGA** có
ngân sách và watchdog riêng trong [kế hoạch FPGA](fpga-drive-plan.md).

Đề xuất UART 3.3 V TX/RX chéo, chung GND, khởi đầu 115200 baud 8N1 trên dây
ngắn; chỉ tăng baud sau đo lỗi khi motor chạy. Giới hạn mỗi chiều tối đa 50
frame/s, mỗi frame tối đa 128 byte thì dùng 6400 byte/s, thấp hơn năng lực lý
thuyết 11520 byte/s của 115200 8N1. Đây là ngân sách truyền tải khởi đầu;
wire format Brain–Motion v1 nay đã chốt tại
[`firmware/shared/brain-motion-protocol.md`](../firmware/shared/brain-motion-protocol.md)
nhưng **chưa triển khai trên firmware/hardware**.

Trước khi viết firmware hai đầu, phải đặc tả và kiểm thử:

- Marker/độ dài, phiên bản, loại bản tin, session, sequence, payload, CRC;
  quy định byte order, đơn vị, giới hạn khung và cách tái đồng bộ khi mất byte.
- Lệnh gồm vận tốc có dấu (m/s), tốc độ quay (rad/s), chế độ và hạn dùng tương
  đối. Motion đo hạn dùng bằng đồng hồ cục bộ từ lúc nhận; không so trực tiếp
  timestamp của hai MCU chưa đồng bộ. Motion áp trần timeout cục bộ, không cho
  Brain tăng quá giới hạn đã cấu hình; kiểm tra giá trị hữu hạn và miền vận
  tốc/tốc độ quay/chế độ trước khi nhận lệnh. Bản đầu từ chối vận tốc âm và
  giới hạn omega để hai setpoint bánh không âm; chưa bật quay tại chỗ.
- Chỉ frame lệnh **mới, hợp lệ, đúng phiên và sequence** mới làm mới hạn điều
  khiển. Heartbeat, telemetry, CRC sai hay frame lặp không giữ xe tiếp tục chạy.
- Brain chỉ chuyển tiếp thao tác Web mới hoặc setpoint mới từ bộ điều khiển tự
  hành đang có dữ liệu hợp lệ. Không phát lại lệnh cache để che mất kết nối;
  hàng đợi có giới hạn và loại lệnh cũ.
- Motion giữ trạng thái disarmed khi kết nối lại/reset, yêu cầu handshake và arm
  mới; arm không tự khôi phục setpoint trước đó. Quy định mất/gói đảo thứ tự,
  sequence wrap, đổi session và lỗi parser trước khi triển khai.
- Dashboard chỉ cho một phiên điều khiển đã xác thực; có dead-man/lease, nút
  dừng, giới hạn vận tốc/tốc độ quay và ngắt lệnh khi mất WebSocket, đóng/ẩn tab hoặc
  mất quyền điều khiển. Dừng vẫn phải dựa vào timeout trên Motion khi trình duyệt treo.
- Hiển thị tốc độ mục tiêu/thực, trạng thái arm, lỗi, tuổi telemetry, nguồn,
  cảm biến và lý do từ chối lệnh. Dữ liệu cũ phải hiện mất kết nối, không tiếp
  tục hiển thị như số đo hiện tại. QR dùng địa chỉ truy cập thực theo STA/AP;
  mã QR và việc ở cùng Wi-Fi không thay thế xác thực điều khiển.

## 9. Lộ trình và điều kiện nghiệm thu

Các hàng dưới đây là **bài thử phải thực hiện**, chưa có hàng nào đạt trên xe.

| Giai đoạn | Sản phẩm bàn giao | Điều kiện chuyển bước |
| --- | --- | --- |
| P0 - Chốt thiết kế trước mua | BOM ứng viên, hình học lái, nguồn/gate, đặc tả RTL/giao tiếp, testbench, kế hoạch PPA hai phương án và báo cáo đúng chip | Mô phỏng chức năng/lỗi đạt; tổng hợp/place-and-route/timing đạt trên chip ứng viên; đủ I/O/nguồn/ngân sách; dòng/nhiệt/headroom phù hợp, chốt phạm vi chỉ tiến. Bảng PPA hai phương án là yêu cầu riêng để nộp đồ án RTL, chưa coi đã hoàn thành |
| P1 - FPGA và Motion trên bàn thử | Hai nhóm PWM/encoder/UART/watchdog, driver bốn motor, PID theo bên, cảm biến, state machine dừng | Thử bánh nhấc khỏi đất; boot/reset/chưa nạp/mất nguồn không chạy; kiểm tra PWM/encoder, UART lỗi/mất, clock FPGA đứng, gate đủ bốn motor, cảm biến, kẹt riêng từng bánh/quá dòng và E-stop |
| P2 - UART và Web | Hai MCU, đặc tả giao thức, Dashboard, lái tốc độ thấp | Cố ý ngắt Web/UART, treo/reset Brain, chèn frame sai/lặp/quá dài; Motion dừng trong hạn đo được và không tự khởi động lại; chỉ một nguồn điều khiển |
| P3 - OLED I²C và giọng nói 1 mic | Giao diện phù hợp OLED thực, Xiaozhi, lệnh giọng nói, cảnh báo cục bộ; QR/LVGL chỉ sau đánh giá | Stress Wi-Fi + cập nhật màn hình + thu/phát loa; không reset do sụt nguồn; kiểm tra phân xử Web/giọng nói và timeout; Motion giữ lịch điều khiển; mất Internet vẫn dừng và phát cảnh báo cục bộ được nếu Brain còn hoạt động |
| P4 - Chạy tích hợp và PCB bản đầu | Báo cáo thử tải/nhiễu, sơ đồ và layout motherboard 2 MCU/1 FPGA/1 mic | Sau P0-P3: đo quãng dừng theo tải/nền/điện áp và các chế độ lỗi; thử mép rơi có gá bảo vệ; ghi brownout, nhiệt, CPU/heap, độ trễ; nguyên mẫu đạt rồi mới làm PCB; không chờ DoA |
| P5 - Nâng cấp DoA | Cụm thu đa kênh đồng bộ, bộ dữ liệu đo góc, chế độ hướng âm | Chọn phần cứng; đo lệch/trôi kênh, góc quanh xe, khoảng cách, nhiễu/vọng, motor/loa; chốt ngưỡng tin cậy/sai số chấp nhận trước đánh giá; bật di chuyển sau bài thử động học/vùng bảo vệ 4WD và an toàn; đánh giá lại PCB nếu đổi phần cứng |

Trước mỗi bài thử chuyển động, lập giá trị nghiệm thu định lượng theo xe thật:
tốc độ tối đa, sai số tốc độ, góc nghiêng, dòng/thời gian kẹt, tuổi tối đa từng
cảm biến, thời gian và quãng đường dừng. Cần cơ cấu giữ xe khi thử mép rơi;
không thử bằng cách cho xe tự do tiến tới cầu thang. Tính cả độ trễ 250 ms đề
xuất vào quãng dừng; giảm timeout/tốc độ nếu vùng phát hiện không đủ.

### Những việc còn phải quyết định

Đã có hai ESP32-S3 có Wi-Fi, OLED I²C, INMP441, MPU6050 và bộ cơ khí theo
[kiểm kê](../hardware/components.md). Cần xác nhận mã board/bộ nhớ, controller
màn hình, kích thước/tải xe, motor/dòng kẹt, encoder A/B và khả năng gá bộ đọc;
đã chốt TT 4WD không servo, chưa chốt driver/nguồn, ngân sách hoặc thời gian chạy.
Bản đầu giữ 1 mic, 2 MCU và 1 FPGA mục tiêu Tang Nano 9K, chưa mua. Ngân sách
FPGA/bộ nạp dưới 500.000đ là mục tiêu cũ cần đối chiếu giá/phụ kiện thực,
không phải giá đã xác minh; phần còn lại cần hoàn tất ở P0. Số lượng mic, đường thu đồng bộ
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
- **[S9]** [Sipeed - Gowin IDE cho Tang](https://wiki.sipeed.com/hardware/en/tang/common-doc/get_started/install-the-ide.html): công cụ, chip được hỗ trợ và Programmer; kết quả chọn chip phải qua đánh giá đúng target.
- **[S10]** [MathWorks - Anti-Windup Control Using PID Controller Block](https://www.mathworks.com/help/simulink/slref/anti-windup-control-using-a-pid-controller.html): chống tích lũy sai số khi cơ cấu chấp hành bão hòa.
- **[S11]** [Microchip - Quadrature Encoding](https://onlinedocs.microchip.com/oxy/GUID-954122A4-C243-4CDD-AAB7-64D199581D04-en-US-5/GUID-96E15BCB-15F0-4DC6-876D-66EBF4B40CC7.html): chuỗi Gray A/B và giới hạn của encoder một tín hiệu.

Các tần số, timeout, phân tải, công thức và bài nghiệm thu trong bản này là đề
xuất kỹ thuật cho AW-Car; datasheet không chứng nhận an toàn hay hiệu năng của
toàn bộ xe. Kết quả kiểm tra tài liệu không thay thế phép đo trên nguyên mẫu.
