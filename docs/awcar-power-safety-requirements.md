# Nguồn, E-stop, sạc khi bật logic và đo pin

Quyết định chủ dự án ngày07/11/2026, trên `feat/f04-pcb-schematic`:

| Hạng mục | Yêu cầu đã chọn |
| --- | --- |
| E-stop | Cắt nguồn nhánh motor **và** khóa hai driver; logic/OLED/Dashboard vẫn có nguồn |
| Sạc | Có thể sạc pack trong khi bật phần logic |
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

Những điểm còn chờ người dùng chọn:

- Đầu vào adapter DC hay USB-C/PD, hay để chọn phương án gọn/tiết kiệm.
- Cắm/rút sạc có cần giữ logic liên tục không reset, hay được phép reset
  về trạng thái khóa. Chưa hứa chuyển nguồn không gián đoạn khi chưa chọn
  mạch, dự toán tải và đo sụt áp.

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
| Pin đầy/gần ngưỡng yếu, tải logic/loa thay đổi | Dòng pin/kết thúc sạc/nhiệt đúng thiết kế, không chỉ quan sát đèn báo sạc |
| ADC so với đồng hồ, E-stop và sạc đang cắm | Vẫn đo đúng pack; cắt VM không bị báo nhầm pin0V, không lấy nhầm áp adapter |
| Motion tắt nguồn trong khi pack/sạc còn điện | Không cấp ngược hoặc vượt giới hạn đầu vào qua đường đo |

Tiếp tục thực hiện trên schematic A3 sau khi chốt khối nguồn/ngắt/sạc;
layout vẫn chờ schematic, linh kiện, header và kích thước thực được xác nhận.
