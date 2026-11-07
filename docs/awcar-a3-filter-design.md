# Schematic A3 và lọc nguồn AW-Car

Chốt trao đổi07/11/2026: giữ một trang A3 ngang, input bên trái, output
bên phải, nguồn trên và GND dưới. Chân hai chiều như SDA giữ ký hiệu hai
chiều, đặt theo nhóm giao tiếp. Các số GPIO/package vẫn là ID logic; chưa
gán footprint/pad header. Các module tiếp tục cắm rút.

## Nguồn và jumper đã chọn

Pin2S qua BMS/cầu chì/công tắc rồi chia nhánh: VM trực tiếp đến hai DRV8833;
DSN6000AUD chỉnh **5,0V** cấp MAX98357A và ba controller. Chưa đo điện áp,
tải/nhiệt DSN hoặc chốt BMS/sạc/cầu chì. Không đổi nhánh motor thành buck.

| Jumper | Nhánh RUN từ DSN | Khi debug USB board đó |
| --- | --- | --- |
| JP1 | Brain5V | Mở JP1 trước khi cắm USB Brain |
| JP2 | Motion5V | Mở JP2 trước khi cắm USB Motion |
| JP3 | Tang5V | Mở JP3 trước khi cắm USB Tang |

Đổi jumper khi tắt nguồn. RUN: USB tháo, jumper lắp. DEBUG: jumper của board
đó tháo, board nhận nguồn USB; amp vẫn dùng DSN nếu pin đang bật. Board khác
không cắm USB có thể nhận DSN qua jumper riêng. Đây là **cách chọn nguồn
thủ công**, không có OR-ing/chống cấp ngược tự động: không được vừa lắp
jumper vừa cắm USB board tương ứng. Cần kiểm tra board thực và khả năng
cấp nguồn ngược qua GPIO khi cấp nguồn lệch trước khi nghiệm thu.

## Tụ đề xuất ban đầu

Tụ nguồn trên carrier, sát đầu cắm module. Tụ motor gắn ngay hai cực từng
motor, **không đưa vào layout carrier**; vẫn nằm trong schematic/BOM để
thể hiện đầy đủ lắp ráp. Dây loa và motor dự kiến tối đa20cm, chưa chốt bố trí.

| Ref | Chức năng | Giá trị ứng viên | Vị trí lắp |
| --- | --- | --- | --- |
| C201 | Bypass nguồn MAX | 100nF,50V, không phân cực | Carrier,5V–GND sát amp |
| C202 | Decoupling nguồn MAX | 10µF,10V, gốm X7R | Carrier,5V–GND sát amp |
| C203 | Bulk nguồn MAX | 220µF,10V, điện phân | Carrier, cực+ ở5V |
| C211/C221 | Bypass VM hai driver | 100nF,50V, không phân cực | Carrier,VM–GND mỗi driver |
| C212/C222 | Decoupling VM | 10µF,25V, gốm X7R | Carrier,VM–GND mỗi driver |
| C213/C223 | Bulk VM | 470µF,25V, điện phân | Carrier, cực+ ởVM mỗi driver |
| C301–C304 | Nhiễu chổi than | 100nF,50V, không phân cực | Ngoài carrier, giữa hai cực từng motor |

ADI khuyến nghị bypass MAX98357A bằng100nF và10µF; đường nguồn dài có thể
cần thêm bulk. C203=220µF là **ứng viên của dự án**, không phải trị số bắt
buộc của hãng. Cần đối chiếu tụ đã có trên module và đo nguồn5V khi phát
âm thanh. Tụ không khắc phục được nguồn thiếu dòng kéo dài hoặc clipping
do gain/âm lượng. [Datasheet MAX98357A, tr.33](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf).

TI khuyến nghị bypass10µF sát VM của IC. Bulk hệ thống phụ thuộc tải, dây,
nguồn và chế độ phanh, cần đo thực; C213/C223=470µF là ứng viên. Tụ trên
carrier không thay thế tụ sát chân IC đã thuộc module. Mã tụ, điện dung
hiệu dụng khi có DC bias, ESR, dòng ripple và dòng nạp ban đầu còn phải
chọn/đo. Tụ25V không tạo bảo vệ quá áp cho IC driver.
[DRV8833, mục9.1 và10.1](https://www.ti.com/lit/ds/symlink/drv8833.pdf).

Pololu hướng dẫn dùng tụ gốm100nF sát cực motor để giảm nhiễu. Motor quay
hai chiều yêu cầu tụ **không phân cực**. Kiểm tra tụ đã có trên motor để
tránh lắp trùng; xoắn cặp dây motor và đi xa mic/I2S/UART khi bố trí xe.
[Pololu: Dealing with Motor Noise](https://www.pololu.com/docs/0J15/9).

## Điện trở và cuộn lọc

Giữ các điện trở tầng STBY hiện có; chưa thêm điện trở nối tiếp đường công
suất hoặc RC snubber chưa có số đo. Phiên bản cơ bản giữ MAX98357A nối BTL
trực tiếp loa4Ω/3W, chưa thêm L/FB. ADI cho phép filterless; tài liệu eval
gợi ý đánh giá ferrite khi dây loa dài hơn khoảng30cm. Dây20cm vẫn cần thử
nhiễu trên xe, không suy ra đã đạt EMI. Hai đầu loa tiếp tục là OUTP/OUTN,
không nối đầu loa vào GND. Không mắc diode một chiều qua motor đảo chiều.
[MAX98357 eval, mục Filterless/EMI](https://www.analog.com/media/en/technical-documentation/data-sheets/max98357devwlp-max98357evsyswlp.pdf).

## Kiểm chứng và phần còn mở

KiCad netlist/ERC kiểm kết nối, cực tụ, nguồn qua jumper và bốn tụ motor
được đánh dấu `exclude_from_board`. Test hướng chân đọc chính thư viện
native; test bỏ nhãn rồi xuất netlist xác nhận dây tín hiệu nối thật.
ERC0 không chứng minh quy trình jumper, nguồn5V, EMI hoặc độ ổn định vật lý.

Batch ngspice hiện chỉ mô phỏng tầng STBY generic. Chưa mô phỏng đáp ứng
DSN, loa/class-D, tụ vừa thêm, chổi than, nhiệt hoặc gate hoàn chỉnh. Phép
đo tiếp theo: kiểm DSN5V không tải/có tải, VM/5V khi khởi động motor và phát
loa, inrush, nhiệt/tải driver, nguồn USB khi mở/đóng jumper đúng quy trình.
Footprint, connector, gate/E-stop và nguồn pack vẫn chưa phát hành PCB.
