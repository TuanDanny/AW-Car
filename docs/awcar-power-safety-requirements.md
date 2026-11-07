# Nguồn, E-stop, sạc khi bật logic và đo pin

Quyết định chủ dự án ngày07/11/2026, trên `feat/f04-pcb-schematic`:

| Hạng mục | Yêu cầu đã chọn |
| --- | --- |
| E-stop | Cắt nguồn nhánh motor **và** khóa hai driver; logic/OLED/Dashboard vẫn có nguồn |
| Sạc | Có thể sạc pack trong khi bật phần logic |
| Nguồn sạc | Adapter DC rời, người triển khai chọn mẫu phù hợp/dễ mua |
| Chuyển nguồn | Cắm/rút adapter phải giữ Brain/OLED/Dashboard hoạt động liên tục, không reset |
| Pin yếu | Đo điện áp pack, hiển thị và cảnh báo; chưa yêu cầu thêm tự khóa motor do cảnh báo pin yếu |

Nhả E-stop, rút sạc, có lại nguồn hoặc khôi phục liên kết không tự ARM hay
phát lại lệnh cũ. BMS và các bảo vệ mất nguồn/lỗi an toàn đã có vẫn độc lập
với chức năng cảnh báo pin yếu mới.

## Đối chiếu bản schematic hiện tại

Native source ở mốc `c72a26e` vẫn là bản nối dây trước các yêu cầu này:

| Phần tử/chân | Net đang có |
| --- | --- |
| J30.1, F1.1 | `PACK_PROTECTED_PLUS` |
| F1.2, SW1.1 | `PACK_FUSED` |
| SW1.2, hai driver VM, U11.IN+ | `VM_MOTOR` |
| U11.OUT+ | `5V_DSN_TARGET` |

**DSN lấy nguồn từ `VM_MOTOR`: nếu cắt rail này để E-stop thì logic cũng
mất nguồn.** Vì thế chưa thể dùng sơ đồ hiện tại để đáp ứng E-stop vừa chốt.
J9 cũng mới là interface; chưa có mạch ngắt VM/chốt/watchdog, charger/load
sharing hoặc mạch đo pin. ERC0 và mô phỏng tầng STBY cũ không xác minh các
chức năng mới này. Tài liệu này chốt yêu cầu, chưa thay thế schematic thực.

## Tách hai nhánh nguồn

- Nhánh motor nhận điện từ **pack2S đã bảo vệ**, qua bảo vệ dòng và phần
  tử ngắt công suất điều khiển bởi mạch an toàn. E-stop vừa ngắt nhánh này
  vừa ép trạng thái khóa driver, không đợi UART, MCU hoặc clock FPGA.
- Nhánh logic cấp đầu vào DSN từ đường nguồn riêng, phía ngoài đường
  ngắt motor. E-stop không cắt đường nuôi logic. Công tắc tổng vẫn cần
  được phân biệt rõ với E-stop; không tự đổi SW1 thành E-stop rồi mất
  chức năng công tắc tổng.
- Quy trình jumper RUN/DEBUG của ba board với USB giữ nguyên. Chuyển
  nguồn giữa sạc và pin ở phía nguồn hệ thống là phần việc khác, không
  tự thay cho việc mở JP1/JP2/JP3 khi cắm USB board tương ứng.
- Khi có nguồn sạc, khối quản lý nguồn phải nuôi tải logic và sạc pin
  theo đúng giới hạn nguồn/pack. Không nối đầu adapter chưa xác định hoặc
  rail SYS của charger trực tiếp vào VM của hai driver.
- Trị số cầu chì, dòng/ngưỡng/nhiệt linh kiện ngắt, chiều chặn dòng,
  điện áp quá độ và xử lý năng lượng motor khi ngắt còn phải thiết kế/đo.
  Tụ VM có thể vẫn giữ điện sau khi ngắt đường cấp; không coi tiếp điểm
  hở hoặc khóa nSLEEP là phép đo VM đã về0V/bánh đã dừng.

TI mô tả nSLEEP LOW khóa cầu H; bulk nguồn motor phụ thuộc tải/nguồn/dây
và cần kiểm chứng hệ thống. Đây là cơ sở phân biệt khóa driver với ngắt
đường cấp VM. [DRV8833, mục7.3.4 và9.1](https://www.ti.com/lit/ds/symlink/drv8833.pdf).

## Sạc đồng thời với tải logic

Hướng thiết kế là có **power-path/load-sharing**: quản lý đường cấp cho
tải riêng với đường nạp pin, hoặc một cấu trúc tương đương đã được kiểm
chứng. Không mặc định rằng nối song song một bộ sạc CC/CV thông thường,
pin và tải sẽ giữ được đúng kết thúc sạc, nhiệt và dòng pin.

Ví dụ tài liệu kỹ thuật về kiến trúc này là TI BQ25672: có các cổng
nguồn vào/SYS/BAT và quản lý NVDC. Đây **chỉ là nguồn tham khảo nguyên lý**,
chưa chọn IC/module này cho AW-Car; vỏ QFN4×4mm và yêu cầu mạch ngoại vi
cần cân nhắc với tự hàn/chi phí. DSN đang được dành cho đầu ra5V logic,
không được tính là khối sạc2S trong kiến trúc này.
[TI BQ25672](https://www.ti.com/lit/ds/symlink/bq25672.pdf).

Chủ dự án đã chọn **adapter DC rời** và **giữ logic liên tục khi cắm/rút**.
Đây là yêu cầu nghiệm thu; chưa phải kết quả đã đo. Không còn cần hỏi lại
hai lựa chọn này. Mã adapter/charger và linh kiện chuyển nguồn vẫn phải
được chọn, kiểm dung sai và thử trên tải thực.

### Adapter và phương án ưu tiên để phát triển tiếp

Mục tiêu chọn mua ban đầu: **adapter ổn áp12VDC,3A liên tục,36W**, đầu
ra5,5×2,1mm, cực dương ở tâm, loại đóng vỏ hoàn chỉnh. Jack đầu vào carrier
phải khớp đầu cắm và có định mức phù hợp; chưa gán footprint từ tên jack.
Adapter cấp vào mạch nguồn/sạc, **không nối trực tiếp vào pack hoặc VM**.
Thông số này là mục tiêu do người triển khai chọn theo yêu cầu; chưa chọn
SKU, chưa xác nhận chất lượng/ripple hoặc đã mua. Ví dụ nơi xem loại12V3A:
[nguồn adapter12V3A](https://linhkiendientutphcm.com/nguon-adapter-12v-3a).

Bao công suất dùng để sàng lọc, toàn bộ là **giả định thiết kế**, chưa đo:

| Phần | Giả định tính | Công suất đầu vào dự trù |
| --- | --- | --- |
| Logic/âm thanh | 5V×3A, hiệu suất DSN tạm lấy80% | 18,75W |
| Sạc2S | 8,4V×1A, hiệu suất sạc tạm lấy85% | Khoảng9,88W |
| Mạch phụ | Bao dự phòng ban đầu | 0,5W |
| Tổng | Khoảng29,13W | Khoảng2,43A ở12V; dư khoảng6,87W so với36W danh định |

3A không phải tải logic đã đo hoặc khả năng DSN được xác nhận. 1A sạc chỉ
là trường hợp tính bao; dòng sạc thực phải theo mã cell/BMS/nhiệt. Sụt áp
dây, dung sai adapter, nhiệt và tải xung còn phải kiểm, có thể cần đổi mức
nguồn hoặc dòng sạc. Không lấy dòng in trên cuộn/IC của DSN làm dòng ra
liên tục ở5V. Tận dụng DSN nếu đo tải/nhiệt/quá độ đạt yêu cầu.

Hướng đơn giản ưu tiên để review: adapter chia hai đường, một đường vào
**charger buck2S** thích hợp với đầu vào12V thực kể cả dung sai, đường kia
vào hệ thống logic qua diode/MOSFET quản lý chiều dòng; pack được cấp bù
cho logic khi mất adapter. Đường motor vẫn chỉ lấy từ pack qua mạch ngắt
riêng. Chuyển nguồn làm bằng phần cứng, không đợi firmware hoặc UART.

Nguyên lý chia tải bằng P-MOS/diode có trong Microchip AN1149. Mạch tham
khảo của hãng dùng **một cell**; chỉ dùng để tham khảo nguyên lý, không
sao chép trị số/điện áp hoặc IC sạc1S sang2S/12V. Cần kiểm chiều diode thân
MOS, VGS ở mọi trạng thái, RDS(on) tại điện áp gate nhỏ nhất dưới tải,
nhiệt, khả năng cấp ngược qua charger, adapter sụt áp và chuyển tiếp khi
cắm/rút. Chưa chốt mã MOS/diode hoặc gọi mạch ứng viên là đạt không reset.
[Microchip AN1149](https://ww1.microchip.com/downloads/en/AppNotes/01149a.pdf).

TP5100 là một **ứng viên module sạc2S để nghiên cứu**, không phải món đã
chốt mua. Datasheet hãng có chế độ4,2/8,4V; cần kiểm kỹ dải làm việc và
dung sai nguồn thực, chọn đúng mode2S, điện trở đặt dòng, TS/nhiệt, reverse
leakage và chất lượng module. Không lấy giới hạn tuyệt đối18V làm dải
vận hành, hoặc dùng board chỉ mang cùng tên như bằng chứng có power-path.
[Top Power TP5100](https://www.toppwr.com/uploadfile/file/20240913/66e3a293b3c42.pdf).

Giả định thiết kế ban đầu: **khi cắm sạc thì motor bị khóa**, chỉ phần
logic hoạt động. Đây là quy tắc đề xuất để đáp ứng nhu cầu đã nêu, cần
ghi vào contract và thực hiện liên động trước khi nghiệm thu; không
khẳng định firmware/mạch hiện tại đã thực hiện. Rút sạc không tự ARM.
BMS/sạc/cell/nguồn đầu vào chưa chọn; chưa ấn định dòng sạc hoặc điện áp
adapter chỉ từ chữ18650.

## Đo điện áp và cảnh báo

- Đo **điện áp pack đã bảo vệ**, không lấy điện áp VM sau phần ngắt motor
  hoặc điện áp SYS/adapter để giả làm điện áp pin. Không đi dây đo làm
  bypass đường bảo vệ của BMS.
- Hướng ưu tiên là mạch chia áp/lọc/bảo vệ vào ADC Motion rồi gửi
  `battery_mv` về Brain. GPIO, giá trị R/C, mã/vỏ và nguồn reference còn
  chốt; chưa thay firmware hoặc gán GPIO mới trong bước ghi yêu cầu này.
- Tính điện áp đầu vào ADC ở điện áp pack lớn nhất, dung sai, quá độ và
  tình huống Motion mất nguồn. Thiết kế phải xét dòng cấp ngược vào board
  tắt nguồn; không chỉ tính chia áp ở trạng thái chạy bình thường.
- Dùng calibration, lọc phù hợp và so sánh với đồng hồ thực. Ngưỡng cảnh
  báo có hysteresis/thời gian xác nhận để tránh nhấp nháy khi khởi động
  motor; ngưỡng cụ thể chờ mã cell và số đo dưới tải.
- Báo giá trịV/mV và trạng thái pin yếu; không biến điện áp thành phần
  trăm dung lượng chính xác khi chưa có mô hình/hiệu chuẩn. Dữ liệu chưa
  đo/sai/quá cũ hiện "Chưa có dữ liệu", không thay bằng0V giả.

[Espressif ADC ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/adc.html).

## Những ca phải thử sau khi có mạch

| Ca thử | Kết quả cần xác nhận |
| --- | --- |
| E-stop khi motor được cho phép | Khóa driver bằng đường cứng và ngắt cấp VM; logic vẫn chạy; ghi thời gian/điện áp thực |
| Nhả E-stop, reset một board, FPGA mất clock | Không tự cấp quyền motor; phải clear/ARM đúng contract |
| Cắm sạc trong các trạng thái | Liên động motor theo contract đã chốt; logic nhận nguồn phù hợp, không nối nhầm adapter vào VM |
| Rút sạc | Hành vi logic theo lựa chọn chuyển nguồn; motor không tự ARM |
| Chuyển adapter ↔ pin có tải | Uptime các board liên tục, không có boot/brownout mới; Dashboard không mất kết nối do reset nguồn; đo5V/3,3V tại chân board bằng oscilloscope |
| Pin đầy/gần ngưỡng yếu, tải logic/loa thay đổi | Dòng pin/kết thúc sạc/nhiệt đúng thiết kế, không chỉ quan sát đèn báo sạc |
| ADC so với đồng hồ, E-stop và sạc đang cắm | Vẫn đo đúng pack; cắt VM không bị báo nhầm pin0V, không lấy nhầm áp adapter |
| Motion tắt nguồn trong khi pack/sạc còn điện | Không cấp ngược hoặc vượt giới hạn đầu vào qua đường đo |

Tiếp tục thực hiện trên schematic A3 sau khi chốt khối nguồn/ngắt/sạc;
layout vẫn chờ schematic, linh kiện, header và kích thước thực được xác nhận.

Điều kiện thử chuyển nguồn: pack đang nối, còn đủ điện và BMS chưa ngắt;
thử lúc pin đầy/gần ngưỡng vận hành, loa/Wi-Fi tải cao, cắm/rút nhanh và
adapter tăng/giảm chậm. Datasheet linh kiện và UART log không thay phép đo
rail thực. Không reset là tiêu chí kết quả trên các board, không chỉ tên
"seamless" hoặc có tụ lớn trong sơ đồ.
