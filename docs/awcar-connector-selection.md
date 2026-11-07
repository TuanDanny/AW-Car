# Đề xuất giắc cắm và dây bấm sẵn

Ngày07/11/2026, chủ dự án ưu tiên giắc cắm kiểu dây bấm sẵn trong ảnh
`codex-clipboard-1a848bdb-cff8-4989-aeed-89e23a6a0c9b.png`.
Ảnh cho thấy hai nửa đều có dây; chưa có thước đo/mã sản phẩm để xác nhận
series, bước chân, cỡ dây hoặc định mức. Các họ dưới đây là **đề xuất mua**,
chưa phải nhận dạng chắc chắn món trong ảnh hoặc footprint được duyệt.

Chốt tiếp theo ảnh `codex-clipboard-f0c4d23a-b784-4f31-9eb9-f7949a8487c9.png`:
**đế có vỏ nhựa hàn trực tiếp lên carrier**, đầu dây ghép đôi cắm/rút khỏi
đế này. Đây là yêu cầu nối dây–bo. Khi mua gọi rõ "đế giắc hàn PCB + dây
bấm sẵn tương ứng"; không xác định mã hàng chỉ từ chữ đực/cái của shop.
Ảnh cận cảnh chưa đủ xác nhận series, bước chân hoặc định mức. Hướng đứng/
ngang và phần nhô ra khỏi bo còn chốt theo bố trí thực tế.

## Danh sách để hỏi shop

Một **bộ nối dây–PCB** gồm một đầu dây đã bấm/vỏ giắc, đầu còn lại để đấu
vào ngoại vi và một đế giắc cùng loại hàn lên carrier. Gói hai giắc dây–dây
như ảnh có thể chưa kèm đế hàn PCB; cần hỏi rõ shop. Mua đầu dây và đế cùng
họ, cùng bước chân và cùng số chân để kiểm lắp trước khi chốt pad.

| Vị trí hiện tại | Đề xuất | Số bộ tối thiểu theo sơ đồ hiện tại |
| --- | --- | --- |
| J4 loa | XH,2P, dây bấm sẵn15–20cm; cặp dây loa xoắn, chọn cỡ dây/tiếp điểm đủ dòng | 1 |
| U7/U8 encoder | XH,3P, dây bấm sẵn15–20cm | 2 |
| J1 OLED, J20 MPU6050, J21 VL53L0X, J22/J23 TCRT5000 | XH,4P, dây bấm sẵn15–20cm | 5 |
| J2 INMP441 | XH,6P, dây ngắn khoảng15cm | 1 |
| J5–J8, mỗi motor một cầu H riêng | VH3,96mm,2P, dây bấm sẵn và đế PCB đồng bộ | 4 |
| J30 đầu ra pack2S đã bảo vệ | XT30 dây + đầu tương thích hàn PCB thuộc họ XT30PW | 1 cặp |

Đây là kế hoạch harness theo số chân logic hiện có. J22/J23 có4 chân,
chân analog không dùng; nếu muốn đổi sang giắc3P thì sửa contract/symbol
trước khi giảm số dây. Mỗi loại có thể mua thêm1 bộ dự phòng. Chưa tính
đầu nối E-stop, gá DSN hoặc thay đổi cổng khi thiết kế gate hoàn chỉnh.
ESP32/Tang vẫn dùng socket cắm board theo quyết định trước, không cần mua
một bó dây riêng cho các đường đã đi trực tiếp trên carrier.

Cổng I2C và TCRT cùng4P nhưng khác tín hiệu/nguồn; cùng số chân không có
nghĩa cắm thay cho nhau. In tên cổng và pin1 lên silkscreen, lập bảng thứ
tự dây từng ngoại vi; không xác định cực nguồn chỉ từ màu dây trong ảnh.

## Bước chân, định mức và footprint

JST XH chính hãng có bước chân **2,50mm**; shop trong nước có sản phẩm mang
tên **XH2.54**. Không lấy tên thương mại đó làm bằng chứng cùng kích thước:
đối chiếu bản vẽ/đo đế thật rồi mới chọn footprint2,50 hoặc2,54mm. Không xác
nhận tương thích giữa đầu dây generic và đế JST chỉ từ ảnh.
[Datasheet JST XH](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf),
[ví dụ tên hàng trong nước](https://icdayroi.com/connector-xh2-54mm).

XH chính hãng công bố3A với dâyAWG22; số đó không tự áp dụng cho dây mảnh,
tiếp điểm hoặc giắc generic trong ảnh. Vì dòng khởi động/kẹt motor và dòng
pack chưa đo, chưa dùng gói cáp mảnh không rõ mã cho nhánh công suất.
VH là ứng viên lớn hơn: bước3,96mm, định mức phụ thuộc đầu tiếp điểm/đế/dây;
ví dụ10A của hãng gắn điều kiệnAWG16 và đế tiêu chuẩn. Không coi mọi bộ dây
ghi "VH/KF396" là cùng khả năng tải.
[JST VH](https://www.jst-mfg.com/product/index.php?lang=2&series=262).

XT30/XT30PW có nhiều phiên bản; cần chọn đúng nửa ghép đôi, hướng lắp,
pinout và bản vẽ của món mua. Dùng họ riêng cho pin giúp phân biệt với cổng
loa/cảm biến. Chưa chọn mã chân/pad cụ thể hoặc định mức dòng cho J30.
[AMASS XT30PW](https://www.china-amass.net/xt30pw-m-product/).

Ưu tiên đế có vỏ định hướng, xuyên lỗ, dễ tự hàn và chịu thao tác cắm/rút;
tụ/trở/IC vẫn ưu tiên SMD. Chưa áp yêu cầu jumper mặt sau sang mọi đầu nối:
vị trí giắc sẽ theo hướng đi dây và khoảng hở USB/anten ở bước layout.

## Ví dụ nơi xem hình/tên mua

- [Dây bấm sẵn và đầu chuyển XH tại Điện tử Đức Huy](https://dientuduchuy.com/collections/day-bus-day-testboard-jack-day-dien).
- [Đế/vỏ/cos XH tại IC ĐÂY RỒI](https://icdayroi.com/connector-xh2-54mm).

Hai link để xem kiểu hàng, không chứng minh các món của hai shop ghép vừa
nhau. Giá/variant/chất lượng dây và tình trạng hàng cần kiểm tra đúng món
khi đặt; chưa ghi giá cố định hoặc xác nhận đã mua.
