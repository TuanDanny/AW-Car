# Hoàn thiện schematic trước layout carrier

Rà lại ngày 07/11/2026 trên `feat/f04-pcb-schematic`, nền `6348fd0`.
Mở project hiện tại tại `hardware/pcb/aw_car.kicad_pro` trong worktree
`aw-car-pcb/AW-Car`; bản ở worktree `tang-nano9k-target` là bản lưu trước khi
tách nhánh. Nếu đang chỉnh tay ở bản lưu, giữ thay đổi đó để đối chiếu trước
khi chuyển sang project hiện tại.

## Điểm xuất phát

Schematic một trang A3 có 60 phần tử/68 net. Đã có dây UART/GPIO, nguồn
qua ba jumper RUN/DEBUG, bốn cầu H độc lập, audio/OLED và tụ ứng viên.
Module cắm rút; C301–C304 lắp tại motor, không đặt lên carrier.
Chủ dự án đã chọn đặt xưởng làm PCB, tự hàn và ưu tiên SMD; gate nằm trên
carrier, jumper RUN/DEBUG dạng header/cầu nối rút được ở mặt sau. Đã gán
ứng viên footprint cho8 tụ và3 jumper; chưa có layout hoặc footprint/đầu
nối vật lý được duyệt. [Phân bổ đồ có sẵn](awcar-passive-reuse.md) giữ rõ
điện áp/điện môi tụ còn thiếu.

Lượt kiểm tra sau bổ sung đồ rời: 98/98 unittest đạt, KiCad ERC 0 vi phạm và checker
netlist đạt 10 nhóm contract. Đây là kiểm chứng source/kết nối; chưa kiểm
nguồn thực, dòng tải, cơ khí hay gate hoàn chỉnh. Không suy ra sẵn sàng sản xuất.

## Những phần cần hoàn thiện trên schematic

Yêu cầu mới về ngắt VM, bật logic khi sạc và đo pin được chốt ở
[contract nguồn/E-stop/sạc/đo pin](awcar-power-safety-requirements.md).
Đầu vào DSN hiện cùng VM_MOTOR là một điểm phải sửa, không dùng topology
hiện tại như bằng chứng logic còn hoạt động khi E-stop.

| Phần | Có trong source | Cần chốt trước footprint/layout |
| --- | --- | --- |
| Gate/E-stop | J9 là interface chờ thay bằng mạch trên carrier; Q101/Q102 và Q111/Q112 là tầng STBY ứng viên | Thêm ngắt cấp VM và tách logic, linh kiện chốt lỗi/giám sát độc lập, đường E-stop và trình tự clear |
| Nguồn pack | J30 nhận đầu ra pack đã bảo vệ, F1 còn `RATING_TBD` | Mã cell, cấu hình pack/BMS, đầu sạc, dòng khởi động/kẹt; sau đó chọn cầu chì/dây/đầu nối |
| Nguồn logic/loa | U11 DSN mục tiêu 5 V, JP1/2/3 tách từng controller | Đo DSN ở tải thực, đường USB trên đúng board và cấp ngược qua tín hiệu khi một board mất nguồn |
| Sạc khi bật logic | Chưa có khối sạc/chia tải trong source | Đầu vào sạc, chuyển nguồn logic, BMS và sạc phù hợp cell; dự toán/đo tải và liên động motor |
| Điện áp pack | Chưa có mạch đo/GPIO ADC trong source | Đo đúng pack qua mạch chia áp/lọc/bảo vệ, calibration và ngưỡng cảnh báo; chưa thêm tự khóa motor bởi cảnh báo này |
| Nguồn cảm biến | `5V_SENSOR_SOURCE_TBD`, `3V3_SENSORS_TBD` | Nguồn cụ thể và ngân sách dòng; hiện chưa nối các net này tới nguồn thực |
| I2C Motion | J20/J21 nối tới J24 bằng `SENSOR_SDA_TBD`/`SENSOR_SCL_TBD` | GPIO SDA/SCL trên Motion, nguồn pull-up và mức điện áp của từng module |
| Hai TCRT5000 | J22/J23, qua U10 tới J24 | GPIO Motion, thứ tự chân module thực, cực tính DO và điều kiện phát hiện; AO chưa sử dụng |
| Hai encoder | U7/U8 OUT qua U9 tới Tang package 27/28 | Mã module, mức OUT, nguồn và tải/pull-up thực; chọn đúng vỏ IC chuyển mức |
| ESP32/Tang | U1/U2/U3 dùng ID GPIO/package logic | Số chân/header, khoảng cách hai hàng, chiều cắm, vùng USB/anten và gá đỡ trên đúng board |
| Hai driver | U4/U5, mỗi motor một cầu H | Header thực, IC thực, STBY có nối nSLEEP/pull-up nào; dòng và nhiệt của module |
| Cáp/giắc/tụ | Chức năng và giá trị tụ ứng viên đã có | Kiểu giắc, số chân, chiều cực, vỏ linh kiện và kích thước thực trước gán pad |

GPIO17/18 của **Motion** đã hỏng theo phép đo của chủ dự án, tiếp tục để
trống. Hai UART đang dùng: Brain TX17 → Motion RX14, Motion TX13 → Brain
RX18; Motion TX15 → Tang package25, Tang package26 → Motion RX16. Mức
logic theo contract là 3,3 V; số package Tang không phải số thứ tự lỗ header.

## Trình tự tiếp tục

1. Chốt họ đầu nối dây còn mở, đối chiếu đồ rời đang có và kích thước
   module. Vị trí gate/cách hàn/jumper đã được trả lời; giữ DSN cấp 5 V,
   VM trực tiếp 2S, jumper riêng từng board, module cắm rút và tụ motor
   ngoài carrier. Chừa chỗ tiếp cận cầu nối và đầu hàn phía dưới PCB.
2. Hoàn thiện nguồn/gate/cảm biến trên chính schematic A3. Chủ dự án xác
   nhận chưa có nút E-stop, cần chọn cùng mạch gate. Gate cần sơ đồ
   mạch thực; không dùng khối J9 hoặc một cổng AND như bằng chứng đã có
   watchdog/chốt lỗi. Thiết kế giám sát mất clock phải chỉ rõ tín hiệu được
   giám sát; permit tĩnh không chứng minh FPGA còn chạy.
3. Lập bảng chân **vật lý** cho từng socket/giắc từ board thực hoặc bản vẽ
   đúng revision. Với mỗi hàng ghi: ref, pin module, pad socket, net, mức
   điện áp và nguồn xác nhận. Chưa rõ một trường thì chưa gán footprint đó.
4. Chọn mã linh kiện/vỏ/định mức còn thiếu; thử nguồn và gate trên bàn.
   E-stop ngắt khả năng tạo lực motor, giữ logic hoạt động; nhả E-stop hoặc
   có lại nguồn không tự chạy. Phân biệt khóa nSLEEP/thả trôi với cắt VM.
5. Khi schematic và linh kiện được chốt mới đo không gian/gá trên xe,
   đặt outline và layout `hardware/pcb/aw_car.kicad_pcb`. DRC, ERC và kiểm
   kê pad/net phải đạt trước xuất file sản xuất.

## Bằng chứng cần lưu cho lần nghiệm thu tiếp

- Ảnh hoặc bản vẽ đúng revision của board/module; số đo header, chiều cắm
  và hướng USB. Không suy kích thước từ hình quảng cáo.
- Mã cell/BMS/sạc, đo DSN không tải/có tải và dòng motor ở điều kiện thử
  được kiểm soát; chưa ấn định cầu chì chỉ dựa vào chữ 1,5 A của driver.
- Xác nhận STBY/nSLEEP và pull-up thực; thử khóa khi reset/mất nguồn từng
  board, FPGA chưa cấu hình/mất clock, E-stop và phục hồi có chủ đích.
- Thử jumper đúng quy trình: tắt nguồn khi đổi; DEBUG mở jumper board đó
  trước USB, RUN chỉ đóng khi USB đã tháo. Chưa có chọn nguồn tự động.

Nguồn đầu vào và giới hạn đã chốt ở
[design inputs](awcar-schematic-design-inputs.json),
[thiết kế lọc nguồn](awcar-a3-filter-design.md) và
[hợp đồng an toàn](../firmware/shared/fpga-safety.md).
