# Linh kiện đã có và kế hoạch mua từng món

Cập nhật kiểm kê **28/10/2026**, đồng bộ quyết định **02/11/2026**, theo xác nhận của chủ dự án, ảnh giao hàng và ảnh bộ xe.
**Nguồn hiện hành:** motor 9 V theo shop, pin 2S cấp thẳng DRV8833;
logic 5 V riêng. Các ví dụ 6 V bên dưới là trao đổi lịch sử hoặc trường hợp
có điều kiện, không phải cấu hình motor hiện tại.

Đây là mốc kiểm kê hiện tại; BOM trong issue #1 và sơ đồ ngày 24/10 là tham chiếu
cũ. Chưa có kết quả đo điện hoặc kiểm thử tích hợp cho các món đã có.

## 1. Linh kiện đã có

| Mã | Linh kiện | Số lượng | Đã biết và việc cần xác nhận |
| --- | --- | --- | --- |
| MCU | ESP32-S3 có Wi-Fi, chủ dự án ghi mã `R16N8` | 2 | Dùng lần lượt làm Brain và Motion; cần ảnh chữ trên module/hai mặt board để xác nhận mã, pinout, anten và bộ nhớ |
| DISP | OLED 0,96 inch, **I²C** | 1 | Chủ dự án đã nạp Xiaozhi và xác nhận hiển thị ở GPIO 41/42; source profile SDA=41, SCL=42. Chưa đo controller vật lý, độ phân giải, địa chỉ bus và mức nguồn/pull-up |
| MIC | Mic INMP441, chủ dự án gọi “Mic 441” | 1 | Thu âm ở Brain; cần xác nhận module, chân và điện áp từ ảnh thực |
| AMP | Module khuếch đại I²S MAX98357A | 1 | Chủ dự án xác nhận đã có; dùng phát giọng nói từ Brain, chưa kiểm thử nguồn/đấu nối/loa thực |
| IMU | MPU6050 | 1 | IMU ở Motion; đã chọn theo đồ có sẵn, không cần mua BMI270 thay thế khi chưa có lý do kỹ thuật |
| CHASSIS | Khung acrylic hai tầng, gá motor/bánh cố định | 2 miếng | Bộ 4WD trong ảnh; kích thước quảng cáo và mốc đo được ghi bên dưới, cần đo thực |
| MOTOR | Motor giảm tốc DC TT màu vàng, trục đôi | 4 | Chủ dự án xác nhận dòng TT; ảnh lắp ráp thấy bánh ngoài và đĩa mã trên trục trong. Shop xác nhận bản 9 V qua chủ dự án; chưa rõ SKU, RPM/dòng kẹt. Một OUT không phải A/B |
| WHEEL | Bánh xe màu vàng | 4 | Trang hàng ghi đường kính khoảng 60 mm; đo đường kính lăn thực, giữ cả bốn bánh cố định theo phương án 4WD |
| DISC | Đĩa mã đo tốc độ, mô tả “20 dòng” | 4 | Chưa xác nhận số khe thực; ảnh không liệt kê cảm biến quang/Hall, chưa phải bằng chứng có tín hiệu encoder A/B |
| SCREW | Ốc vít | 8 | Theo ảnh; kiểm tra chiều dài/cỡ ren khi lắp |
| SPACER | Cột đồng, đai ốc và phụ kiện đi kèm | 1 bộ, chưa rõ số chiếc | Theo ảnh giao hàng |
| GUIDE | Bản vẽ lắp ráp 3D tiếng Trung | 1 | Theo ảnh giao hàng; cần xem bản vẽ/ảnh thực để xác định cấu trúc bộ xe |

“Đã có” nghĩa là chủ dự án xác nhận sở hữu, chưa đồng nghĩa phù hợp điện/cơ
hoặc đã chạy thử. Không tự suy ra có pin, driver, servo, cảm biến đọc đĩa hoặc
board FPGA từ danh sách phụ kiện cơ khí.

Ảnh bộ xe mới còn có hộp pin trông như loại bốn ngăn, dây nối và gá motor.
Đây là hình sản phẩm; cần kiểm kê kiện thực có giao các món đó hay không và
loại cell/cách đấu của hộp pin. Không đánh dấu đã có cell pin hoặc coi hộp này
là giá pin 18650/BMS/bộ sạc.

### Kích thước từ ảnh trang hàng, chưa đo thực

| Thông tin | Giá trị trên ảnh | Cách sử dụng |
| --- | --- | --- |
| Chiều dài xe | 260 mm ở ảnh kích thước; khoảng 250 mm ở ảnh mô tả | Hai số chưa thống nhất mốc đo/phiên bản; không chọn một số làm kích thước CAD chính xác |
| Bề rộng | 155 mm từ ngoài hai bánh; khoảng 148 mm trong mô tả tấm đáy | Có thể khác mốc đo; chưa suy ra khoảng cách tâm hai vệt bánh |
| Đường kính bánh | Khoảng 60 mm | Giá trị quảng cáo để tham khảo, chưa thay hiệu chuẩn encoder/tốc độ |
| Độ dày tấm acrylic | Khoảng 3 mm | Kiểm tra thực trước chọn gá/cột/ốc |
| Chiều dài cơ sở và khoảng cách tâm bánh trái/phải | Chưa có | Phải đo; không dùng chiều dài toàn xe hoặc rộng ngoài bánh thay thế |

## 2. Các điểm phải đối chiếu trước khi mua tiếp

### ESP32-S3 và OLED

Giữ nguyên `R16N8` là cách chủ dự án cung cấp, **chưa coi đó là mã hãng đã xác
minh**. Espressif có biến thể `ESP32-S3-WROOM-1-N16R8` với Flash 16 MB và PSRAM
8 MB; chỉ áp dụng thông số đó sau khi đối chiếu đúng chữ trên module. Không
mặc định board đang có là WROOM-1U, có IPEX hoặc cần mua anten rời.

ESP32-S3 hỗ trợ Wi-Fi; chưa cần mua module Wi-Fi ngoài. OLED bản đầu dùng I²C,
không phải SPI/TFT. Người dùng xác nhận hiển thị với Xiaozhi stock ở GPIO 41/42;
profile chính thức dùng SDA=41, SCL=42, SSD1306 128×64, địa chỉ 0x3C. Chưa đo
riêng controller vật lý/độ phân giải/địa chỉ của module. Xem
[kiểm tra firmware và source](../docs/xiaozhi-binary-review.md).
Giao diện ưu tiên biểu cảm/trạng thái;
QR, GIF, LVGL và bố cục phải đánh giá lại theo màn hình thực, không giữ mặc
định tiêu chí của TFT 2,8 inch. Chưa gán GPIO trước khi có pinout hai board.

### Bộ khung, motor và encoder

Ảnh lắp ráp bổ sung xác nhận cách bố trí TT trục đôi: đầu ngoài gắn bánh,
đầu trong gắn đĩa mã. Chưa thấy rõ board đọc/đường dây tín hiệu A/B trong
ảnh; cần đối chiếu module đọc thực, không coi đĩa đã gắn là đủ encoder.
Tên TT và màu vỏ chưa xác định điện áp, tỉ số truyền hoặc dòng kẹt.

Tham chiếu riêng: Adafruit 3777 là một mẫu TT 3–6 V được hãng khuyến nghị
dùng với DRV8833 có giới hạn dòng. Hãng đo mẫu đó kẹt khoảng 1,1 A ở 3 V và
1,5 A ở 6 V. Đây **không phải SKU/thông số đã xác nhận của bộ xe AW-Car**;
không lấy số đo này chốt dòng motor, nguồn hoặc khả năng tải của module Hshop.

**Chủ dự án đã chọn tận dụng nguyên bộ 4WD, lái bằng chênh lệch tốc độ hai
bên.** Đây là quyết định mới thay phương án servo/Ackermann trước đây.
Hai motor bên trái nhận lệnh nhóm trái, hai motor bên phải nhận lệnh nhóm
phải; không cần mua servo MG90S/cơ cấu lái trước cho bản đầu.

Giữ hai kênh duty/chiều cho hai nhóm trái/phải; Motion tính hai setpoint/PID
theo nhóm. RTL A/B v1 vẫn còn để hồi quy, nhưng đã có chế độ **hai encoder
một OUT + protocol v2** riêng; firmware Motion v2 chưa triển khai. Phương án
tầng công suất ưu tiên đánh giá là bốn cầu H, mỗi motor
một cầu, hai cầu cùng bên nhận cùng lệnh logic qua adapter có đảo cực phù
hợp và chung đường khóa an toàn. Nếu dùng hai cầu H, mỗi cầu cấp hai motor
song song thì phải kiểm tra tổng dòng khởi động/kẹt và nhiệt của cả cặp;
không mặc định một TB6612FNG đủ bốn motor, không nối song song đầu ra hai
cầu H khi datasheet không cho phép.

Mục tiêu bản đầu là hai bộ encoder **một OUT**, một bánh đại diện mỗi bên; A/B
là phương án thay thế. Cùng duty
không bảo đảm hai motor cùng bên quay cùng tốc độ. Hai encoder không giám
sát đủ bốn bánh; phải kiểm thử trượt/kẹt từng bánh và đo dòng phù hợp. Nếu
cần bốn vòng PID/encoder độc lập thì phải mở rộng RTL/giao thức/test riêng,
không tuyên bố thiết kế hai kênh đã đáp ứng.

Lái kiểu skid-steer có trượt ngang khi rẽ, ảnh hưởng dòng tải và odometry;
phải thử mặt nền/tải, hiệu chuẩn và giới hạn tốc độ. Chưa bật quay tại chỗ
bằng hai bên ngược chiều hoặc lùi cho tới khi có vùng bảo vệ và bài thử phù
hợp; bản đầu vẫn áp chính sách chỉ tiến trong vùng đã kiểm chứng.

Đĩa có khe chỉ là phần cơ của bộ đo. RTL A/B v1 yêu cầu **hai pha lệch nhau**;
module V2 chỉ có một OUT **phải dùng top single-OUT/protocol v2**, không nối
chung OUT vào A/B hay coi chiều lệnh motor là chiều quay thực. Cần kiểm tra
mức OUT/chuyển mức 3,3 V, gá và số cạnh trên mỗi vòng bánh thực. Chưa coi “20
dòng” là 20 hay 80 tick/vòng bánh khi chưa biết cảm biến, đĩa và cách đếm.

## 3. Danh sách còn phải xác nhận/chọn

Các mục dưới đây **chưa được chủ dự án báo là đã có**, không phải lệnh mua
ngay. Xác nhận tồn kho và thông số từng món rồi mới đổi trạng thái.

| Nhóm | Món cần đối chiếu | Số lượng mục tiêu | Điều kiện chốt |
| --- | --- | --- | --- |
| Đo tốc độ | Ưu tiên V2 một OUT để giảm chi phí, chỉ đo độ lớn tốc độ | 2 bộ, một bánh đại diện mỗi bên | RTL xung đơn/protocol v2 đã có mô phỏng; cần chuyển mức 5 V -> 3,3 V, firmware Motion v2, gá và kiểm thử; chưa xác nhận mua |
| Ghép mức encoder | **Module MOSFET 4 kênh hai chiều 3,3 V ↔ 5 V, có HV/LV/GND** | 1 module, dùng 2 kênh | Đã chọn số lượng 1; chưa xác nhận nhận hàng. Ứng viên Hshop HS0666V, mã MOSFET thực chưa xác nhận; cần đo xung/mức và gá dây |
| Công suất | **DRV8833 theo ảnh Hshop, dự kiến 2 module** | 4 cầu H, mỗi motor một kênh | Giữ làm ứng viên thử với TT; shop công bố 1,5 A/kênh, package từ ảnh chưa chắc. Chưa xác nhận đã mua hoặc đạt tải |
| Lái | Servo và cơ cấu Ackermann | Không mua cho bản 4WD | Đã chuyển sang chênh lệch tốc độ hai bên theo lựa chọn chủ dự án |
| FPGA | Tang Nano 9K và phụ kiện nạp/USB | 1 board mục tiêu | Wrapper/constraints/PnR/STA đúng chip, pin/mức logic, nguồn, giá; chưa mua/chưa xác nhận fit/timing |
| Nguồn — món đang đánh giá | **Pack Li-ion 18650 2S1P hàn sẵn, có BMS 2S** | 1 pack / 2 cell dự kiến | Đề xuất cell 2500–3000 mAh xả cao, mục tiêu pack/BMS chịu 10 A liên tục thực; chưa chọn/mua. 2S2P / 4 cell là tùy chọn thêm dung lượng; xem power-plan.md |
| Sạc | **Bộ sạc Li-ion 2S 8,4 V CC/CV, 1 A dự kiến** | 1 | Chỉ dùng khi cell/pack/BMS cho phép, đúng cổng/cực; chưa chọn mẫu/mua. Nếu có sạc nguyên bộ thì không cần mua thêm module sạc rời |
| Phân phối nguồn | Nhánh motor **2S → cầu chì/đường dừng → VM DRV8833 trực tiếp**, logic 5 V ổn áp riêng | Hai nhánh nguồn dự kiến | Theo quyết định motor 9 V, bỏ yêu cầu buck motor 6–6,5 V. Cần đo lực/rẽ lúc pin yếu, dòng kẹt, nhiệt và quá độ |
| Cầu chì | Đế cầu chì lá mini ô tô DC 32 V, mắc sát đầu ra pack | 1 tổng dự kiến, nhánh tùy thiết kế | Chưa chốt trị số A: theo dòng khởi động/đường cong cầu chì và dây/đầu nối, không lấy dòng BMS làm dòng cầu chì |
| An toàn | E-stop, gate/chốt lỗi, giám sát nguồn, cầu chì/công tắc | Theo sơ đồ điện | Tắt mặc định, khóa độc lập UART/clock FPGA, phục hồi không tự chạy |
| Dừng khẩn — món đang chọn | **Nút E-stop đầu nấm đỏ, tự giữ, xoay nhả, lỗ gá 22 mm, có tiếp điểm NC** | 1 bộ đầy đủ đầu nút + thân/tiếp điểm | 1 NC tối thiểu; 1 NC + 1 NO nếu giá phù hợp. Chưa chọn SKU/mua; dùng trong vòng cho phép gate, không mặc định cắt trực tiếp dòng bốn motor |
| Âm thanh | **Loa thụ động toàn dải 4 Ω 3 W**, hai dây, đường kính 40 mm, cao 20 mm theo shop | 1 loa | Mẫu đang đánh giá từ ảnh; ghép MAX98357A đã có, cần gá và thử âm; chưa xác nhận đã mua/có loa |
| Vật cản | **VL53L0X Màu Xanh**, biến thể Shopee đã chọn | 1 phía trước | Chủ dự án xác nhận chọn ngày 28/10/2026; Motion đọc I²C. Chưa xác nhận mua/nhận hàng, giá và sơ đồ breakout đúng biến thể; đối chiếu nguồn/bus 3,3 V trước đấu |
| Mép rơi | **Module TCRT5000 dò line đơn, có biến trở và DO/AO** | 2 dự kiến, trước trái/phải | Món đang đánh giá; cấp 3,3 V nếu module hỗ trợ, Motion đọc. Cần gá đầu quang sát sàn và thử nền/ánh sáng; chưa chọn SKU/mua, không bảo đảm chống rơi chỉ từ tên cảm biến |
| Nguồn/dòng | INA219 hoặc giải pháp đo dòng phù hợp | Chưa chốt số kênh | Vị trí shunt, dải dòng, công suất và phát hiện kẹt một bánh khi bánh cùng bên vẫn quay |
| Va chạm | FSR402 và mạch đọc/cơ cấu truyền lực | Để sau, chưa mua | Chủ dự án yêu cầu dừng bổ sung cảm biến để ưu tiên các phần trọng yếu; không đưa FSR402 vào lượt mua hiện tại |
| Môi trường | SHT30 | Để sau, chưa mua | Ưu tiên nguồn/truyền động/an toàn trước; không cần mua cùng MPU6050 |
| Đấu nối/thử | Dây, đầu nối, gá, linh kiện lọc/chuyển mức, dụng cụ đo | Theo sơ đồ | Kiểm kê đồ đã có; không chọn định mức dây/nguồn từ tên board ESP32 |
| PCB | Motherboard | Giai đoạn sau | Chỉ làm sau nguyên mẫu và các bài thử đạt |

### Bộ đọc đang đánh giá: encoder hồng ngoại V2 một kênh

**Cập nhật theo ưu tiên chi phí của chủ dự án:** chỉ cần đo độ lớn tốc độ,
nên chuyển hướng thiết kế sang **hai V2 một OUT + chuyển mức + mode xung đơn
trong FPGA**. Không bắt buộc mua A/B hoặc bốn đầu đọc; phương án chi tiết ở
[kế hoạch xung đơn](../docs/single-channel-encoder-plan.md). RTL và protocol
v2 phía FPGA đã triển khai/test mô phỏng; **chưa có firmware Motion v2,
pinout/kiểm thử phần cứng**, chưa xác nhận đã mua. Những lựa chọn
A/B/ghép bốn đầu đọc dưới đây chỉ là phương án thay thế.

Chủ dự án yêu cầu module **phổ biến, rẻ, dễ đấu dây**, nên điều chỉnh đề
xuất mua: ưu tiên **mạch chuyển mức MOSFET 4 kênh hai chiều 3,3 V/5 V** có
chân HV/LV/GND và các cặp HV1/LV1... Ưu tiên này thay yêu cầu LVC125A rời.
Ứng viên cụ thể: [Hshop HS0666V](https://hshop.vn/mach-chuyen-muc-tin-hieu-logic-4-kenh),
giá niêm yết kiểm tra ngày 28/10/2026 là 10.000đ/module, chưa phí giao hàng.
Nhà bán mô tả bốn MOSFET, không ghi mã MOSFET; không khẳng định HS0666V
chắc chắn dùng BSS138. SparkFun/Adafruit có mạch BSS138 cùng nhóm nguyên lý
dùng cho tín hiệu số tốc độ thấp, làm căn cứ chọn hướng kiểm chứng.

Ánh xạ dự kiến của module chuẩn HV/LV: HV=5 V, LV=3,3 V, GND chung;
OUT trái -> HV1, LV1 -> input FPGA trái thuộc bank 3,3 V; OUT phải -> HV2,
LV2 -> input FPGA phải. Phải kiểm tra nhãn/pin của module thực trước đấu.
Chỉ dùng chuyển tín hiệu, không cấp công suất hoặc hạ nguồn qua các kênh.
Đo HIGH/LOW, thời gian lên/xuống và số xung qua bộ chuyển tại tốc độ motor
cao nhất thực; dây ngắn, tải nhỏ, thử nhiễu khi cả bốn motor hoạt động. Đây
chưa là bằng chứng module generic bất kỳ đã đạt với bộ đọc V2.

SN74LVC125A vẫn là phương án buffer khi cần mạch chủ động, nhưng không
cần mua lô năm IC SMD chỉ để làm nguyên mẫu hai OUT. TXS0108E và các board
HV/LV không xác định linh kiện không được coi là tương đương chỉ qua tên
“hai chiều”; vẫn cần đối chiếu OUT, ngưỡng, tải và dây. Chưa xác nhận mua.

Chủ dự án gửi ảnh sản phẩm “Cảm biến encoder hồng ngoại V2” và nhấn mạnh
phải phù hợp **hai ESP32-S3 đang có và FPGA Tang Nano 9K mục tiêu**. Chưa
xác nhận đã mua. Ảnh cho thấy ba chân **OUT, VCC, GND**; theo mô tả shop:
nguồn 5 V, dòng hoạt động 15 mA, đầu ra TTL 5 V, LOW khi bị chắn/HIGH khi
không bị chắn, rãnh 5,5 mm, hai lỗ cách 20,5 mm, lỗ 3 mm, kích thước
21,5×27,5 mm. Các giá trị này là thông tin người bán, chưa đo thực hoặc
đối chiếu datasheet đúng sensor/IC trên module.

Module có thể tạo xung để đo độ lớn tốc độ khi đĩa đi qua khe, nhưng một
OUT **không phải encoder quadrature A/B** và không tự đo được chiều quay.
Đường hiện tại là cảm biến -> FPGA -> snapshot UART -> Motion; không chuyển
encoder sang MCU để bỏ qua giao diện FPGA. `encoder_pair.sv` nhận hai pha
mỗi bên qua left_ab/right_ab, nên hai module V2 (mỗi bên một) chưa đáp ứng
RTL hiện tại.

Về điện, xử lý OUT như tín hiệu có thể lên 5 V cho đến khi đo/xác nhận mạch
ra. Không nối trực tiếp vào GPIO ESP32-S3 hoặc bank FPGA thiết kế 3,3 V.
Cần giao tiếp số chịu được đầu vào 5 V, cho đầu ra phù hợp 3,3 V, đối chiếu
ngưỡng HIGH/LOW, cạnh và tốc độ xung. Nano 9K có BANK0/1/2 ở 3,3 V và BANK3
ở 1,8 V theo sơ đồ 3672; phương án này ưu tiên chân bank 3,3 V cho encoder/
UART/GPIO ngoài, không mặc định toàn board là 1,8 V hoặc cần hạ mọi tín hiệu
3,3 V xuống 1,8 V. Chưa chọn pinout/revision board thực. Chưa chốt mạch chuyển mức vì chưa
rõ output push-pull/open-collector và sơ đồ breakout. Không tự cấp VCC=3,3 V
cho module được shop ghi 5 V, hoặc mặc định chia áp bất kỳ đủ ngưỡng TTL.

Đối chiếu phương án (ưu tiên hiện tại là dòng hai V2 đo một kênh):

| Phương án | Điều kiện | Giới hạn |
| --- | --- | --- |
| Phương án thay thế: hai bộ encoder A/B thật, một mỗi bên | Hợp trục/đĩa/gá TT, hai pha đúng và mức ra 3,3 V hoặc giao tiếp mức phù hợp | Không còn bắt buộc mua khi chủ dự án chỉ cần độ lớn tốc độ |
| Ghép các đầu đọc V2 thành A/B | Tối thiểu hai đầu đọc trên cùng đĩa mỗi bên (bốn module cho hai bên), gá lệch 1/4 chu kỳ mẫu khe theo modulo chu kỳ, chuyển mức đủ bốn tín hiệu, đo xác nhận pha | Không phải chỉ mua bốn rồi lắp tùy vị trí; chưa xác nhận đủ không gian/gá. 90 độ pha điện không mặc định là 90 độ cơ |
| Ưu tiên: hai V2, một mỗi bên, đo một kênh | Chủ dự án ưu tiên tiết kiệm, chỉ cần độ lớn tốc độ; thêm mode RTL xung đơn, giao thức nhận biết mode, chuyển mức đúng | Mới là đề xuất thiết kế, chưa triển khai; không coi chiều lệnh là chiều thực, không đo được chiều trôi/ngược |

Chưa thay HDL, không nối OUT vào cả A lẫn B, không tạo một pha trễ nhân tạo
rồi tuyên bố đo được chiều. Trước mua phải kiểm tra đĩa đi qua khe, vị trí
trục/khung, khoảng hở khi quay và việc gá hai đầu đọc nếu chọn phương án ghép.

### Driver đang đánh giá: 2 module DRV8833

Ngày 28/10/2026 chủ dự án gửi ảnh module DRV8833 của Hshop và dự định dùng
hai chiếc. Trạng thái **dự kiến chọn, chưa xác nhận đã mua hoặc đạt tải**.
Ảnh cận bổ sung cùng ngày: dòng trên IC **có vẻ là `8833PW`**, chưa đọc chắc
chắn từ ảnh kích thước nhỏ. Bảng marking TI ánh xạ `8833PW` sang bản PW,
còn bản PWP có marking `DRV8833`. Nếu đúng là PW thì phải đối chiếu mức
0,5 A RMS/kênh, không áp mức 1,5 A của PWP/RTY. Nhận diện ảnh này chưa đủ
căn cứ kết luận shop báo sai hoặc loại mẫu module. **Giữ phương án hai
DRV8833 làm ứng viên**, chưa xác nhận đủ tải; hai module tăng số kênh,
không tăng dòng cho từng kênh. Xác nhận mã hàng/package và dòng motor khi
có dữ liệu. Nếu không có datasheet motor đúng SKU, kiểm chứng trên bàn với
nguồn giới hạn dòng, đo dòng/nhiệt và thử lỗi có kiểm soát trước nghiệm thu;
không mặc định dòng không tải thay được dòng khởi động/kẹt.
Ảnh ghi 25.000đ/module, tổng hai chiếc theo ảnh là 50.000đ, chưa gồm phí giao
hàng; đây không phải báo giá được giữ cố định. Chưa chọn TB6612FNG cho bản này.

Ánh xạ dự kiến, không phải sơ đồ đi dây đã xác minh:

| Module | Cầu H/kênh | Motor |
| --- | --- | --- |
| Trái | A | Trái trước |
| Trái | B | Trái sau |
| Phải | A | Phải trước |
| Phải | B | Phải sau |

Mỗi motor có một cặp đầu ra riêng; không đấu hai motor vào một kênh, không
ghép các đầu ra cầu H. Hai kênh cùng bên nhận cùng yêu cầu tốc độ/chiều,
nhưng phải kiểm tra cực tính từng motor để cùng lăn tiến. Vẫn chỉ có hai
PID theo bên, chưa phải điều khiển phản hồi riêng bốn motor.

Đối chiếu TI: DRV8833 có hai cầu H, VM 2,7–10,8 V. Tại điều kiện công bố
VM=5 V, 25°C, bản PWP/RTY có mức 1,5 A RMS/kênh; bản PW chỉ 0,5 A RMS/kênh.
Mức đỉnh 2 A không thay dòng vận hành/khả năng tản nhiệt module. Không suy
ra package từ ảnh xa; cần mã IC/schematic hoặc xác nhận từ nhà bán.

Ảnh mặt dưới cho thấy nhãn VM, GND, AIN1/AIN2, BIN1/BIN2, STBY, các cặp
A01/A02 và B01/B02, cùng các chân NC. Đây là bằng chứng nhãn breakout,
chưa chứng minh kết nối bên trong STBY hoặc chức năng nFAULT trên chân NC.

Ngõ điều khiển chấp nhận mức HIGH 3,3 V của MCU/FPGA (ngưỡng tối thiểu IC:
IN=2 V, nSLEEP=2,5 V). Đây chưa là xác nhận toàn bộ breakout. Chân shop ghi
STBY cần kiểm tra nối tới nSLEEP; không tự coi NC là nFAULT. Gate an toàn
phải giữ cả hai module tắt khi boot/lỗi và không được thay bằng nối STBY
cố định HIGH. Sleep đưa ngõ ra Hi-Z/thả trôi, không phải phanh chủ động.

Adapter dự kiến chuyển PWM/chiều trừu tượng của FPGA thành hai IN cho mỗi
cầu H: IN1=PWM/IN2=0 cho một chiều, IN1=0/IN2=PWM cho chiều kia, sau chuẩn
hóa cực tính; duty zero đưa cả hai IN LOW. Cần viết/test adapter và kiểm
tra STBY, thời gian thức dậy, gate/boot/reset trước dùng thật. Chưa đổi RTL
hoặc coi chân DIR của FPGA có thể nối trực tiếp thay IN2.

Điều kiện còn thiếu trước chốt mua/nguồn: điện áp và dòng khởi động/kẹt
từng motor TT, package/PCB/tản nhiệt và khả năng giới hạn dòng của module.
VM phải phù hợp motor, không lấy mức tối đa driver làm điện áp motor;
nguồn motor không đi qua chân nguồn ESP32, GND phải được bố trí chung đúng.
Cần thử tải/rẽ/kẹt có kiểm soát và đường khóa đủ bốn kênh; bảo vệ tự phục
hồi bên trong driver không thay chốt lỗi ngoài của AW-Car.

### Loa đang đánh giá cho MAX98357A đã có

Chủ dự án xác nhận đã có MAX98357A, không mua lại ampli. Mẫu đang đánh giá
theo ảnh shop là **1 loa thụ động toàn dải 4 Ω 3 W**, hai dây: đường kính
ngoài 40 mm, màng 35 mm, nam châm 22 mm, cao 20 mm. Đây là thông số shop,
chưa đo thực hoặc xác nhận mua. Từ khóa mua: `loa toàn dải 4 ohm 3W 40mm`.

So với chiều dài xe 260 mm, đường kính loa bằng khoảng 15,4%; so với bề
rộng tấm khoảng 148 mm là 27%. Kích thước phù hợp để bố trí sơ bộ, chưa
chứng minh vừa bố cục đầy đủ hai MCU/FPGA/pin. Dự trù vùng gá khoảng
50 × 50 mm và chiều sâu 25–30 mm cho loa/dây/gá; đây là khoảng dự phòng
thiết kế, cần kiểm tra khi bố trí thực. Cao loa 20 mm chưa bảo đảm lọt giữa
hai tầng; cần đo khoảng hở. Ưu tiên tầng trên, mặt loa thoáng, gá qua viền
và tránh gần mic INMP441 để giảm ghép âm; không ép lên màng loa.

Shop ghi “tần số phản hồi 170 kHz”, không phải dải đáp tuyến âm thanh đủ
căn cứ; không tự sửa thành 170 Hz. “Độ nhạy 100 dB/W” thiếu khoảng cách,
tần số và điều kiện đo. Chưa dùng hai con số này dự đoán độ lớn/độ rõ;
cần dữ liệu đúng mẫu hoặc nghe thử giọng nói khi motor hoạt động.

Loa nối giữa OUT+/OUT− của ampli, không nối một đầu loa xuống GND vì ngõ
ra cầu BTL. Dự kiến cấp ampli từ rail 5 V phù hợp; I²S từ ESP32-S3 dùng
logic 3,3 V, không cần dùng bộ chuyển mức encoder cho đường âm thanh này.
Tham chiếu Adafruit: tải từ 4 Ω, ở 5 V/4 Ω đạt khoảng 2,5 W tại 1% THD,
mức 3 W gắn với 10% THD; không coi 3 W là công suất sạch liên tục đã đo.
Chưa thử âm thanh hoặc chốt GPIO trên board Brain thực.

### Đã chọn: VL53L0X Màu Xanh phía trước

Chủ dự án xác nhận chọn **VL53L0X Màu Xanh**, ô dưới bên trái trong bốn
biến thể trên trang Shopee đã gửi. Số lượng mục tiêu **1 module**, phía
trước xe, Motion đọc I²C. Lựa chọn này thay đề xuất mua Hshop TOF200C.
Đã chọn không đồng nghĩa đã thanh toán/nhận hàng; chưa kiểm thử module.

Chưa có ảnh/thông số riêng của biến thể xanh sau khi chọn. Không gán giá
53.000đ của ô `VL53L0/1XV2 Màu đỏ` hoặc nguồn/bus/kích thước của Hshop cho
mẫu xanh. Hướng tích hợp là cấp 3,3 V nếu breakout hỗ trợ, GND chung và
SDA/SCL ở mức phù hợp 3,3 V; đối chiếu nhãn từng chân thực, chưa gán GPIO.
Giữ mặt quang thoáng, không bị acrylic/gá che; kích thước ngoài và lỗ gá
chờ mẫu thực hoặc thông số đúng biến thể.

**Mẫu đã so sánh, không phải lựa chọn hiện tại: Hshop TOF200C VL53L0X, SKU HS0201V.** Trang
shop công bố rõ VL53L0X, nguồn 3,3–5 V, mức giao tiếp 3,3 V, I²C, dòng tối
đa khoảng 40 mA và kích thước 20 × 11 mm. Giá niêm yết kiểm tra 28/10/2026
là 115.000đ, chưa giao hàng; cao hơn 62.000đ so với giá 53.000đ trên ảnh
mẫu trước, chưa so sánh cùng phí/biến thể. Mẫu Hshop rõ thông số hơn,
chưa có bằng chứng đo rằng chính xác/bền hơn mẫu rẻ hoặc chống nhiễu vượt
trội. Không đưa mẫu Hshop vào danh sách mua hiện tại.

Riêng mẫu Hshop, hướng đấu theo thông số công bố: VIN=3,3 V, GND chung, SDA/SCL sang Motion,
không cần thêm bộ chuyển mức cho bus này nếu module thực đúng mô tả. Cần
đối chiếu nhãn chân khi nhận, chưa gán GPIO ESP32. Kích thước 20 × 11 mm
chỉ khoảng 7,7% chiều dài xe 260 mm, phù hợp bố trí sơ bộ; tính thêm chân
header/gá/dây và giữ mặt quang thoáng. Shop ghi vùng đo 3–200 cm/FoV khoảng
25° và độ phân giải 1 mm; không hiểu 1 mm là sai số ±1 mm hay 2 m là tầm
đo luôn đạt. Driver Adafruit do shop dẫn là tham khảo Arduino, chưa phải
firmware ESP-IDF đã tích hợp/kiểm thử của AW-Car.

Mẫu trước từ ảnh Shopee: mục đang chọn ghi `VL53L0/1XV2 - Màu đỏ`, PCB cũng ghi
`VL53L0/1XV2`; giá trên ảnh 53.000đ, không phải giá đã kiểm tra trực tiếp.
Nhãn này chưa xác nhận chip là VL53L0X hay VL53L1X. Ưu tiên biến thể ghi rõ
**VL53L0X** (trang còn có lựa chọn “VL53L0X Màu Xanh/Màu đỏ”); cần shop xác
nhận đúng IC, không chọn theo màu. VL53L1X cũng dùng I²C nhưng driver/thư
viện không thay trực tiếp cho VL53L0X. Đây là cảm biến quang ToF, không phải
radar sóng vô tuyến dù shop dùng từ “radar”.

Mô tả chung của shop ghi nguồn 2,8–5 V, một đoạn khác chỉ dẫn cấp 5 V và
“I²C TTL 3,3–5 V”; chưa đủ xác nhận sơ đồ pull-up/chuyển mức của từng mẫu.
Hướng đấu ưu tiên sau khi xác nhận đúng breakout: VIN=3,3 V, GND chung,
SDA/SCL sang Motion ở mức 3,3 V. Không mặc định cấp VIN=5 V rồi nối thẳng
bus sang ESP32. GPIO1 là ngõ ngắt, XSHUT là ngõ shutdown/reset; chữ “không
kết nối” trong mô tả được hiểu là chưa dùng, không phải chân NC. Chỉ để hở
XSHUT khi breakout có kéo lên phù hợp; không tự kéo chân này lên 5 V.

Shop ghi kích thước 10,5 × 13,3 mm nhưng ảnh PCB có tai gá hai bên; chưa
chắc đây là kích thước ngoài toàn module. Mẫu có vẻ gọn so với xe 260 mm,
nhưng cần kích thước ngoài/khoảng cách lỗ khi làm gá. Các mốc 2 cm tối
thiểu và tầm đo theo màu/trong-ngoài trời là thông tin shop, chưa đo và
không dùng làm bảo đảm phát hiện/dừng xe.

Theo phân tải hiện tại, Motion ESP32-S3 đọc khoảng cách qua SDA/SCL và dùng
để giới hạn/dừng chuyển động; không cần đưa I²C của cảm biến qua FPGA.
Chỉ chốt breakout khi xác nhận cấp được từ rail 3,3 V và bus phía MCU ở
mức 3,3 V. Một số carrier có ổn áp/chuyển mức, không suy ra mọi module
VL53L0X đều giống nhau hoặc lấy điện áp cấp tối đa làm mức GPIO. Module
chuyển mức encoder đã chọn không mặc định phải dùng cho cảm biến này.

ST công bố đo tối đa 2 m; đây không phải khoảng cách bảo đảm trên mọi
vật/môi trường. Cần thử ánh sáng, bề mặt/vật nhỏ, điểm mù và thời gian đọc;
ngưỡng dừng phải theo tốc độ/quãng dừng thực. Một cảm biến phía trước
không bao phủ toàn bộ bề rộng xe 4WD, không thay cảm biến mép rơi/E-stop.

### Mẫu đã đánh giá: TCRT5000 hướng xuống phát hiện mép rơi

Đề xuất thử **2 module TCRT5000 dò line đơn có biến trở, ngõ DO và AO**,
ưu tiên bản bốn chân VCC/GND/DO/AO hỗ trợ nguồn 3,3 V. Không mua riêng đầu
quang rời hoặc thanh nhiều mắt. Từ khóa: `module TCRT5000 4 chân AO DO`.
Motion đọc GPIO DO, có thể đọc AO để hỗ trợ hiệu chuẩn; đây không phải
I²C/UART và không cần mở rộng khối đo encoder FPGA. Cần xác nhận mức ngõ
ra theo đúng module; không cấp module 5 V rồi nối OUT 5 V thẳng ESP32.

Ảnh Shopee chủ dự án gửi tiếp cho thấy module có nhãn VCC/GND/DO/AO,
đầu quang phản xạ và biến trở; mô tả ghi TCRT5000/LM393, nguồn 3,3–5 V,
dòng dưới 15 mA, kích thước 32 × 14 × 12 mm và vùng phát hiện 1–25 mm.
Đây là thông tin shop, chưa đo thực. Mẫu đúng nhóm cần thử; đề xuất 2 chiếc
trước trái/phải, chưa coi chủ dự án đã chọn/mua. Giá trên ảnh 16.850đ/chiếc,
bậc mua 2 ghi 15.850đ/chiếc (31.700đ nếu áp dụng), chưa phí giao hàng và
chưa kiểm tra giá giỏ thực.

Với mẫu này, hướng đấu theo mô tả là VCC=3,3 V, GND chung, mỗi DO sang
một GPIO Motion; AO chỉ nối ADC khi cần và đã kiểm tra dải điện áp/chân
ADC đúng board. Không coi AO là phép đo khoảng cách tuyến tính/chính xác:
tín hiệu phụ thuộc phản xạ bề mặt, độ cao, ánh sáng và dòng LED. Shop ghi
DO LOW khi phản xạ đủ, HIGH khi không có; cần kiểm chứng cực tính thực
rồi hiệu chuẩn ngưỡng. Không dùng mặc định HIGH=mép rơi/LOW=sàn hợp lệ
trước thử; sàn đen hoặc mất dây có thể gây đọc sai. Công bố “1–25 mm” và
“chống nhiễu tốt” chưa thay bài thử trên xe, không đổi kế hoạch gá thấp.

Ứng viên tham khảo Hshop HS0181C công bố nguồn 3,3–5 V, ngõ digital/analog,
biến trở và kích thước 32 × 14 mm; niêm yết 15.000đ/chiếc khi kiểm tra
28/10/2026, hai chiếc 30.000đ chưa giao hàng. Chưa xác nhận chọn/mua.

TCRT5000 đo phản xạ hồng ngoại, không đo khoảng cách sàn tuyệt đối.
Vishay nêu đỉnh đáp ứng khoảng 2,5 mm; dải 0,2–15 mm là điều kiện dòng
quang tương đối của cảm biến, không bảo đảm module phát hiện mép trên mọi
nền. Dự kiến thử đầu quang cách sàn khoảng 3–5 mm bằng gá hạ thấp; đây là
điểm bắt đầu hiệu chuẩn, không phải chiều cao đã kiểm chứng. Không gắn
thẳng trên tấm gầm cao vài cm và giả định vẫn đọc được.

Đặt hai đầu quang trước vệt tiếp xúc bánh trước trái/phải đủ khoảng đón
quãng dừng thực, quay xuống và tránh cạ sàn. Phải thử sàn sáng/tối/bóng,
ánh sáng, rung/nghiêng và mất dây; vạch đen có thể bị hiểu như mất sàn.
Hai đầu phía trước chỉ là phương án cho vùng chạy tiến đã kiểm chứng,
không bảo vệ toàn bộ khi lùi/quay tại chỗ. Nếu không bố trí được gá sát
sàn hoặc kết quả phản xạ không ổn định, đánh giá cảm biến khoảng cách
hướng xuống thay thế; chưa gọi tính năng chống rơi hoàn tất.

### Món đang đánh giá: pack pin cấp nguồn

**Cập nhật cấu hình đề xuất:** ưu tiên **2S1P / 2 cell 18650 xả cao** cho
bản đầu gọn/tiết kiệm; 2S2P / 4 cell là tùy chọn thêm dung lượng. Mục tiêu
pack/BMS 10 A liên tục thực, sạc Li-ion 2S 8,4 V CC/CV 1 A nếu pack cho
phép; đế cầu chì mini DC 32 V, chưa chốt viên bao nhiêu A khi chưa đo tải
và chọn dây. Chi tiết giả định, các rail và cách ghép ở
[phương án nguồn](power-plan.md); chưa coi chủ dự án đã chọn/mua cấu hình.

Ưu tiên mới nhất: **2S1P xả cao, cấp thẳng VM hai DRV8833; logic 5 V riêng**.
Motor TT là bản **9 V theo shop**, không bắt buộc cấp đủ 9 V; bỏ buck motor
6–6,5 V của phương án cũ. Đo lực khởi động/rẽ khi pin yếu, dòng kẹt/nhiệt trước nghiệm thu.

Ảnh tiếp theo có ba cell rời Hshop; ứng viên đề xuất là **2 Sunpower
2500 mAh 10C, màu cam ngoài trái**, 45.000đ/cell, 90.000đ tiền cell theo
giá kiểm tra ngày 28/10/2026. Shop ghi khoảng 18 A liên tục/đỉnh trên 25 A;
chưa có dữ liệu hãng đúng mã hoặc đo thực. Dự kiến 2S1P 7,4 V/2500 mAh,
đầy 8,4 V, không cộng thành 5000 mAh. Chưa xác nhận chủ dự án chọn/mua;
cần BMS/đóng pack/sạc/nguồn/cầu chì riêng, chi tiết ở phương án nguồn.

Nếu xác nhận bốn motor 6 V và muốn giữ rail 6 V: phương án hạn chế sụt
áp/đi dây, dòng quá độ khoảng 6–8 A để sàng lọc converter và headroom
pin 2S ở [phương án nguồn](power-plan.md). 2S2P chia dòng cell là tùy chọn,
không tự đổi lựa chọn 2S1P hoặc chốt BMS 10 A đủ mọi tình huống; cần đo
tải, mỗi motor giữ một cầu H riêng và không nối chung đầu ra driver.

Đề xuất đối chiếu **1 pack Li-ion 18650 2S hàn sẵn có BMS**, danh định
7,2/7,4 V tùy cell, đầy 8,4 V đối với cell chuẩn sạc 4,2 V. Từ khóa:
`pack pin 18650 2S 7.4V có BMS`. Mốc tìm ban đầu khoảng 2000–3000 mAh,
không phải dung lượng/thời gian chạy đã chốt; số nhánh song song phụ
thuộc dòng tải, cell, kích thước và ngân sách. Chưa xác nhận chọn/mua.

Cần ảnh nhãn/mã cell, cấu hình 2S1P/2S2P, thông số dòng xả liên tục và
đỉnh, BMS bảo vệ/cân bằng, đầu nối/kích thước/khối lượng và giá. Không
chốt khả năng cấp bốn motor từ số mAh hoặc dòng in riêng trên BMS; cell,
dây, mối nối và bộ nguồn phải cùng đáp ứng tải. Chưa đủ dữ liệu để chọn
định mức dòng pack, buck, cầu chì hay tính thời gian chạy.

Đường nguồn dự kiến tách nhánh logic 5 V và nhánh motor có điều áp/giới
hạn phù hợp motor thực, GND bố trí chung đúng. Không cấp 8,4 V vào chân
5 V/3V3 MCU hoặc trực tiếp motor TT chưa rõ định mức; không coi giảm duty
là thay cho nguồn motor phù hợp. Bộ hạ áp phải giữ rail trong toàn vùng
điện áp pin dưới tải; chốt ngưỡng pin yếu theo cell và headroom converter,
không chỉ thử lúc pin đầy. Sạc chọn đúng Li-ion 2S 8,4 V CC/CV và dòng
theo pack, BMS không thay bộ sạc. Chưa chọn module sạc/buck hoặc giá pin.

### Ưu tiên hiện tại: nguồn, driver, khóa an toàn và FPGA

Chủ dự án yêu cầu dừng bổ sung cảm biến và chuyển sang các phần trọng yếu.
Giữ mục tiêu hai TCRT5000 đã bàn, chưa suy ra đã mua/chọn mẫu từ câu chuyển
tiếp; chưa chọn thêm FSR402/SHT30. Phần đo dòng được chọn cùng thiết kế
nguồn khi rõ dòng tải, shunt và định mức, không mua theo tên INA219 chung.

**Món có thể đối chiếu ngay: 1 bộ nút E-stop đầu nấm đỏ, tự giữ khi nhấn,
xoay nhả, lỗ gá 22 mm, tối thiểu 1 tiếp điểm NC (thường đóng).** Có thêm
1 NO để báo trạng thái nếu giá phù hợp; không bắt buộc mua thêm NO. Từ
khóa tìm: `nút dừng khẩn cấp tự giữ xoay nhả 22mm 1NC`. Mua cả cụm tiếp
điểm, không chỉ đầu nút; không dùng nút nhấn nhả tức thời hoặc loại chỉ NO.

NC nằm trong đường cho phép phần cứng: nhấn nút/mở vòng làm gate khóa cả
hai DRV8833 độc lập MCU/UART/clock FPGA. Mạch gate/chốt lỗi và trạng thái
đứt dây còn cần thiết kế, không nối E-stop chỉ vào GPIO rồi chờ firmware.
Nhả nút không tự chạy lại, phải có phục hồi/ARM theo hợp đồng an toàn.
Chưa chốt cách cắt nguồn công suất, không cho dòng bốn motor qua tiếp điểm
khi chưa kiểm tra định mức DC/tải cảm. Đây là nút dừng qua gate, không thay
công tắc cách ly pin/cầu chì; ngắt driver cũng chưa bảo đảm xe dừng tức thì.

Loại lỗ gá 22 mm là kích thước lắp, không phải kích thước đầu nấm/thân.
Phải xem cả đường kính đầu và chiều sâu tiếp điểm để bố trí trên xe 260 mm.
Schneider XB2BS542C/XB7NS8442 chỉ làm tham chiếu chức năng 1 NC/xoay nhả,
không yêu cầu mua đúng hãng hoặc gán chứng nhận cho nút phổ thông khác.
Chưa xác nhận mẫu/giá hoặc mua E-stop, chưa có mạch gate thực đã kiểm thử.

Sau đó đối chiếu theo nhóm: pack pin/BMS/sạc phù hợp, bộ nguồn logic và
motor theo điện áp/dòng thực, cầu chì/dây/đầu nối và đường gate; hoàn tất
kiểm tra 2 DRV8833 với motor TT; board Tang Nano 9K vẫn là mục tiêu chưa
mua/chưa có fit/timing đúng chip. Không cấp motor từ chân nguồn ESP32.

## 4. Mua từng bước cùng chủ dự án

Mỗi lượt chỉ chốt một nhóm phụ thuộc liên quan. Chủ dự án gửi ảnh sản phẩm,
thông số và giá; đối chiếu cơ khí, điện áp, tín hiệu, dòng tải và ngân sách.
Sau khi chủ dự án chọn/mua, cập nhật bảng này; không đánh dấu đã mua chỉ vì
đã gửi một đường dẫn hoặc ảnh quảng cáo.

**Ưu tiên mới:** nguồn/truyền động/khóa an toàn/FPGA theo mục trên; không
tiếp tục mua thêm cảm biến ở lượt hiện tại. Danh sách dưới giữ các việc
tích hợp còn lại, không phải thứ tự mua bắt buộc.

1. **Hiện tại: chọn đường đo tốc độ cho bộ TT 4WD.** Đã nhận diện dạng motor
   và đã chốt dùng cả bốn bánh cố định. Cần ảnh cận trục gắn đĩa/motor thực,
   ảnh cảm biến đọc đĩa nếu có, thông số điện áp/RPM/dòng hoặc trang hàng.
   Ưu tiên hai V2 một OUT và chuyển mức 3,3 V theo yêu cầu đo tốc độ/chi phí;
   lập mode RTL/giao thức phù hợp, không gọi hai V2 là hai bộ A/B.
2. **Driver motor.** Sau khi biết motor và số motor thực dùng, kiểm tra dòng,
   điện áp, tản nhiệt và chân enable. Đang đánh giá 2 DRV8833 từ ảnh Hshop;
   cần xác nhận package và tải motor trước khi đổi trạng thái thành chốt mua.
3. **Gá encoder và hiệu chuẩn 4WD.** Không mua servo; kiểm tra gá, đường kính
   bánh, dấu chiều từng motor, hai vòng PID theo bên và giới hạn do trượt/kẹt.
4. **Nguồn và mạch an toàn.** Theo tải đã chọn, xác định pin/BMS/sạc/các rail,
   E-stop/gate/cầu chì và định mức. Không cấp motor qua chân nguồn MCU.
5. **FPGA.** Tiếp tục hồ sơ target9K, mua khi đủ điều kiện fit/timing/điện áp
   và ngân sách. Giữ an toàn và mục tiêu 9K như kế hoạch hiện tại.
6. **Âm thanh.** MAX98357A đã có; mẫu loa đang đánh giá là 4 Ω 3 W,
   Ø40 × cao 20 mm theo shop, chưa xác nhận mua; cần gá và thử giọng nói.
7. **Cảm biến còn thiếu.** Đã chọn **VL53L0X Màu Xanh, 1 module phía trước**,
   chưa xác nhận mua/nhận hàng hoặc kiểm thử.
   Đã đánh giá mẫu TCRT5000 với mục tiêu 2 chiếc; chưa xác nhận mua/nhận hàng.
   Dừng bổ sung cảm biến theo yêu cầu mới, để FSR402/SHT30 sau.
   MPU6050 đã có, không mua lại IMU.
8. **Đấu nối và tích hợp.** Hoàn thiện dây/connector/gá, thử từng khối trên
   bàn rồi mới thử xe; motherboard và DoA là các bước sau.

Ảnh chữ trên hai ESP32-S3 và hai mặt OLED là đầu vào cần bổ sung để lập bảng
chân/nguồn; không cần mua lại các board đang có trong lúc nhận diện bộ xe.

## 5. Nguồn và nhật ký quyết định

- 28/10/2026: chủ dự án xác nhận đã nạp Xiaozhi, OLED hiển thị với GPIO 41/42.
  File S3 ở root trùng từng byte với release v2.5.2 chính thức; đã tải snapshot
  source đúng commit để nghiên cứu, chưa tự build hoặc tích hợp Brain–Motion.
- 28/10/2026: chủ dự án xác nhận hai ESP32-S3 `R16N8` có Wi-Fi, OLED 0,96
  inch, Mic 441, MPU6050 và bộ cơ khí theo ảnh giao hàng; sau đó đính chính
  **OLED là I²C**. Ảnh là danh sách hàng, chưa phải ảnh pinout/mạch thực.
- 28/10/2026, ảnh bổ sung: bộ khung hai tầng 4WD với motor hộp số vàng dạng
  TT, đĩa rời, hộp pin/dây/gá trong ảnh sản phẩm; kích thước có các mốc khác
  nhau như bảng trên. Chủ dự án chọn **giữ nguyên 4WD, lái bằng tốc độ hai
  bên**. Servo/Ackermann đã ra khỏi danh sách mua bản đầu.
- 28/10/2026, chọn driver: chủ dự án đề xuất 2 DRV8833 theo ảnh Hshop;
  đủ số cầu H cho mỗi motor một kênh, chưa xác nhận package/tải hoặc đã mua.
- 28/10/2026, ảnh cận driver: có dấu hiệu marking `8833PW`, tạm chưa chốt
  mẫu module này; cần xác nhận bản thực trước khi áp định mức PWP/RTY.
- 28/10/2026, sau đối chiếu lại: chưa đọc chắc marking nên không loại
  module từ ảnh hoặc kết luận người bán sai. Giữ 2 DRV8833 dự kiến, shop
  công bố 1,5 A/kênh; đủ số kênh, chưa xác nhận tải. Chủ dự án xác nhận
  motor TT và gửi ảnh bốn motor trục đôi với đĩa đã gắn phía trong.
- 28/10/2026, bộ đọc: nhận ảnh encoder hồng ngoại V2, một OUT và nguồn/TTL
  5 V theo shop. Chủ dự án yêu cầu phù hợp FPGA/ESP32 hiện tại; chưa chọn
  mua hoặc đổi RTL, đang đối chiếu số pha, giao tiếp 3,3 V và gá cơ khí.
- 28/10/2026, ưu tiên chi phí: chủ dự án hỏi dùng một OUT, chỉ cần đo tốc độ
  và phải phù hợp FPGA/ESP32. Lập phương án hai V2 + chuyển mức + RTL xung
  đơn, đo chu kỳ khi ít xung và giao thức báo rõ mode; chưa viết code/mua.
- 28/10/2026, ưu tiên phổ biến/rẻ: chuyển đề xuất mua từ LVC125A rời sang
  module MOSFET 4 kênh HV/LV; ứng viên HS0666V niêm yết 10.000đ. Cần kiểm
  tra pin/mức/xung thực, chưa xác nhận đã mua hoặc tích hợp đạt.
- [Espressif: ESP32-S3 và Wi-Fi](https://www.espressif.com/en/products/socs/esp32-s3).
- 28/10/2026: đã chọn 1 module chuyển mức 4 kênh, chưa xác nhận nhận hàng;
  chủ dự án xác nhận **đã có MAX98357A**. Món kế tiếp là 1 loa thụ động
  4 Ω 3 W; chưa đánh dấu loa đã có hoặc đã mua.
- [Adafruit: MAX98357A, tải loa, nguồn, I²S và ngõ ra BTL](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/pinouts).
- 28/10/2026: sau khi đối chiếu loa, chuyển sang chọn 1 module VL53L0X I²C
  cho phía trước. Chưa xác nhận mua loa hoặc VL53L0X.
- [ST: VL53L0X ToF, I²C và tầm đo công bố](https://www.st.com/en/imaging-and-photonics-solutions/vl53l0x.html).
- 28/10/2026: chuyển sang đối chiếu pack 18650 2S có BMS, mục tiêu 1 pack;
  chưa chọn SKU/dòng xả/dung lượng cuối hoặc mua. Ý tưởng watchdog ngoài
  giám sát heartbeat để khóa gate/nhả relay đang được bàn, chưa chốt module
  hay thay E-stop; phục hồi không tự chạy lại vẫn áp dụng.
- [TI: thiết kế tham chiếu bộ pin robot 2S1P, 7,4 V/8,4 V tối đa](https://www.ti.com.cn/lit/ug/tidubq4a/tidubq4a.pdf): tham chiếu kiến trúc, không phải pack đã chọn.
- 28/10/2026: chủ dự án yêu cầu chuyển từ cảm biến sang các phần trọng yếu;
  tạm hoãn FSR402/SHT30, đề xuất đối chiếu 1 E-stop NC tự giữ xoay nhả,
  sau đó nguồn/gate/driver/FPGA. Chưa đánh dấu mua E-stop hoặc thêm cảm biến.
- [Schneider XB7NS8442: E-stop 22 mm, xoay nhả, 1 NC](https://www.se.com/ph/en/product/XB7NS8442/emergency-stop-%C3%B8-22-red-mushroom-head-%C3%B8-40-mm-turn-to-release-1-nc/): tham chiếu chức năng, không phải SKU đã chọn mua.
- 28/10/2026: sau khi chọn VL53L0X Màu Xanh, chuyển sang đánh giá 2 module
  TCRT5000 cho mép rơi phía trước; cần gá thấp và thử phản xạ, chưa chọn/mua.
- [Vishay: datasheet TCRT5000](https://www.vishay.com/docs/83760/tcrt5000.pdf): khoảng cách đỉnh đáp ứng/dải dòng quang tham chiếu.
- [Hshop: module TCRT5000 HS0181C](https://hshop.vn/cam-bien-do-line-don): nguồn, ngõ ra, kích thước/giá do shop công bố, chưa kiểm thử trên xe.
- 28/10/2026: chủ dự án xác nhận **chọn VL53L0X Màu Xanh** trên Shopee,
  mục tiêu 1 module phía trước, thay đề xuất Hshop TOF200C. Chưa xác nhận
  giá đúng biến thể/mua/nhận hàng; không dùng thông số breakout Hshop thay mẫu xanh.
- [Hshop: TOF200C VL53L0X, HS0201V](https://hshop.vn/cam-bien-khoang-cach-tof-laser-radar-vl53l0x): thông số/giá shop, chưa thay đo kiểm module thực.
- [Adafruit VL53L0X Arduino library](https://github.com/adafruit/Adafruit_VL53L0X): nguồn tham khảo phần mềm, chưa tích hợp vào AW-Car.
- [Pololu: carrier VL53L0X và chuyển mức theo VIN](https://www.pololu.com/product/2490): tham chiếu kỹ thuật carrier, không gán sơ đồ này cho module bán ở shop khác.
- [Espressif: datasheet WROOM-1/1U và mã N16R8](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.html).
- [Pololu: quadrature encoder với hai kênh A/B](https://www.pololu.com/docs/0J86/6.4).
- [WPILib: differential/skid-steer và nhóm motor mỗi bên](https://docs.wpilib.org/en/stable/docs/software/hardware-apis/motors/wpi-drive-classes.html).
- [WPILib: vận tốc thẳng/quay và khoảng cách hai vệt bánh](https://docs.wpilib.org/en/stable/docs/software/kinematics-and-odometry/differential-drive-kinematics.html).
- [TI: DRV8833, các package và dòng công bố](https://www.ti.com/product/DRV8833).
- [TI: datasheet DRV8833 Rev. E, logic/ngưỡng vào/sleep](https://www.ti.com/lit/ds/symlink/drv8833.pdf).
- [Hshop: module DRV8833 đang được đối chiếu](https://hshop.vn/mach-dieu-khien-dong-co-drv8833-dc-motor-driver): nguồn nhận diện module/chân theo ảnh, không thay datasheet IC hoặc sơ đồ breakout.
- [Adafruit 3777: mẫu TT và khuyến nghị DRV8833](https://www.adafruit.com/product/3777): chỉ làm ví dụ tham chiếu, không gán thông số cho motor chưa rõ SKU trong bộ AW-Car.
- [Microchip AN2434: một kênh và quadrature hai pha](https://onlinedocs.microchip.com/oxy/GUID-954122A4-C243-4CDD-AAB7-64D199581D04-en-US-5/GUID-96E15BCB-15F0-4DC6-876D-66EBF4B40CC7.html).
- [Espressif: datasheet ESP32-S3, DC Characteristics](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf): đối chiếu ngưỡng GPIO 3,3 V; không nối OUT 5 V trực tiếp.
- [TI SN74LVC125A](https://www.ti.com/product/SN74LVC125A): ứng viên buffer chuyển mức input 5 V/output 3,3 V, chưa chốt breakout hoặc sơ đồ thực.
- [Hshop HS0666V](https://hshop.vn/mach-chuyen-muc-tin-hieu-logic-4-kenh): module bốn MOSFET, nhãn HV/LV và giá kiểm tra ngày 28/10/2026; mã MOSFET chưa được nhà bán nêu.
- [SparkFun BOB-12009](https://www.sparkfun.com/sparkfun-logic-level-converter-bi-directional.html) và [sơ đồ BSS138](https://cdn.sparkfun.com/datasheets/BreakoutBoards/Logic_Level_Bidirectional.pdf): nguyên lý tham chiếu HV/LV.
- [Adafruit BSS138 bốn kênh](https://www.adafruit.com/product/757): tham chiếu dùng tín hiệu số tốc độ thấp, cần xét pull-up/tải/tốc độ thực.
- [TI TXS0108E, mục Recommended Operating Conditions/Input Driver/Output Load](https://www.ti.com/lit/ds/symlink/txs0108e.pdf): nguồn đối chiếu module trong ảnh tìm kiếm; chưa xác nhận phù hợp OUT của V2.
- [Sipeed: sơ đồ Tang Nano 9K 3672](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf): VCCO0/1/2=3,3 V, VCCO3=1,8 V; đối chiếu revision/pin thực trước đấu.
- [Kế hoạch phân tải](../docs/fpga-drive-plan.md) và
  [hợp đồng an toàn](../firmware/shared/fpga-safety.md) vẫn áp dụng.

Đã có ứng viên DRV8833 từ ảnh Hshop, chưa xác nhận đã mua. Các mục khác chưa
chốt SKU/giá. Chưa đo/kiểm thử các linh kiện đã có; tính tương thích được
xác nhận từng món trước khi chốt mua và đấu nối.
