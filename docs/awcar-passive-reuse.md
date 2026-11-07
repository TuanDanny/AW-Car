# Tận dụng linh kiện rời đã có

Chủ dự án xác nhận ngày 07/11/2026: các linh kiện trong ảnh là **linh kiện
rời**; điện áp chịu đựng/điện môi/mã tụ **chưa rõ**. Số lượng dưới đây lấy
theo danh sách ký hiệu trên ảnh, chưa kiểm đếm độc lập.

| Đồ có sẵn | Số lượng theo ảnh | Dành cho schematic AW-Car | Trạng thái |
| --- | --- | --- | --- |
| 100 nF, SMD 0805 | 5 | C9/C10 lọc nguồn U9/U10; C201 nguồn loa; C211/C221 VM hai driver | Đủ 5 vị trí về giá trị/kích thước; chờ xác nhận định mức |
| 10 µF, SMD 1206 | 4 | C202 nguồn loa; C212/C222 VM hai driver | Dành 3, còn 1 dự phòng; chờ xác nhận định mức và điện dung khi có DC bias |
| 1 kΩ, SMD 0805 | 5 | Chưa có vị trí khớp trong tầng STBY hiện tại | Giữ dự phòng, không đổi điện trở mạch chỉ để dùng hết |
| 10 Ω, SMD 0805 | 1 | Chưa có nhu cầu trong schematic hiện tại | Giữ dự phòng; không tự chèn vào đường nguồn motor/loa |
| R8 ghi DNP | 0 linh kiện được xác nhận | Không phân bổ | DNP là vị trí không lắp, không phải trị số điện trở |

Các tên C1/C2/… trên ảnh chỉ là nhãn kiểm kê gốc. Ví dụ **C9 trên ảnh là
10 µF**, còn **C9 của AW-Car là 100 nF**; không đổi C9 của AW-Car thành
10 µF do trùng tên. Ánh xạ từng chiếc được lưu trong
[dữ liệu kiểm kê](awcar-passive-stock.json).

## Điều kiện dùng tụ

Đã gán footprint **ứng viên** trong KiCad cho 8 tụ trên carrier:
`Capacitor_SMD:C_0805_2012Metric` và
`Capacitor_SMD:C_1206_3216Metric`. Kích thước vỏ tương ứng là
2,0 × 1,25 mm và 3,2 × 1,6 mm theo thư viện KiCad cài trên máy. Đây không
phải xác nhận điện áp/điện môi hay cho phép lắp các tụ chưa rõ mã vào nguồn.

Giữ yêu cầu schematic hiện hành: C202 ở rail 5 V có yêu cầu 10 V;
C212/C222 ở VM có yêu cầu 25 V; C201/C211/C221 có yêu cầu 50 V.
`Voltage_Rating` trên schematic là **yêu cầu thiết kế**, không phải thông
số đã biết của hàng tồn. Metadata `Stock_Status` ghi rõ chưa được xác nhận.
C9/C10 ở rail 3,3 V cũng cần đối chiếu thông số hàng thực.

Nếu tụ 10 µF đang có chỉ chịu 6,3 V hoặc 10 V, không phân bổ chúng vào VM
theo yêu cầu 25 V hiện tại. Nếu xác nhận được mã khác, review lại định mức
theo rail và quá độ trước khi sửa yêu cầu. Không đo ra 10 µF rồi suy ra tụ
chịu được bao nhiêu V. Điện dung hiệu dụng của tụ gốm điện môi hằng số cao
còn thay đổi theo điện áp DC; cần mã hàng/đồ thị để đánh giá.
[Murata: đặc tính DC bias](https://www.murata.com/en-us/support/faqs/capacitor/ceramiccapacitor/char/0005).

Cặp 100 nF + 10 µF phù hợp hướng bypass nguồn MAX98357A đang dùng;
carrier không thay tụ sát IC trên module. Bulk motor cần đánh giá theo
nguồn/tải/dây, không thể đổi 470 µF thành 10 µF chỉ vì có sẵn.
[ADI MAX98357A](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf),
[TI DRV8833, mục 9.1/10.1](https://www.ti.com/lit/ds/symlink/drv8833.pdf).

C203 220 µF, C213/C223 470 µF, bốn tụ sát motor C301–C304 và các điện trở
47 kΩ/10 kΩ/100 kΩ hiện chưa được ảnh này xác nhận là đã có. Năm tụ 100 nF
được dành cho carrier trước; chưa phân bổ trùng chúng cho motor. Tụ sát
motor vẫn ngoài carrier, cần cách gá chịu rung và định mức phù hợp.

## Lắp ráp và jumper đã chốt

- Đặt xưởng gia công PCB, chủ dự án tự hàn; ưu tiên SMD. Không phải bo tự
  ăn mòn một mặt. Số lớp/công nghệ/kích thước sẽ chốt ở bước layout.
- Gate an toàn sẽ nằm **trên carrier chung**. J9 hiện vẫn là khối giao
  tiếp chờ thay bằng mạch gate/chốt/watchdog thực, chưa có gate hoàn chỉnh.
  Chủ dự án chưa có nút E-stop; cần chọn nút/tiếp điểm cùng mạch này.
- JP1/JP2/JP3 dùng **chân cắm và cầu nối rút được ở mặt sau**, dự kiến header
  1×2 bước 2,54 mm. Header xuyên lỗ là ứng viên để thuận tiện tự hàn và
  thao tác rút/cắm; cần chừa khoảng hở dưới carrier, đầu hàn và đường tiếp cận.
- Thuộc tính mặt sau trên schematic là yêu cầu bố trí. Chỉ khi có layout
  mới xác nhận footprint thật đã được đặt/lật sang mặt sau.
- RUN/DEBUG giữ quy trình đã chọn: đổi khi tắt nguồn, mở jumper board đó
  trước khi cắm USB, chỉ lắp lại khi USB đã tháo. Chưa có chọn nguồn tự động.

Tham khảo [trình tự hoàn thiện schematic](awcar-pcb-next-stage.md) và
[thiết kế tụ/jumper](awcar-a3-filter-design.md).
