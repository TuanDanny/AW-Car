# Tài liệu

[Schematic KiCad đấu nối chung](../hardware/pcb/README.md): một trang A3,
source trực tiếp trong `hardware/pcb`; layout chờ chốt thành phần. Dữ liệu
tham chiếu ở [design inputs](awcar-schematic-design-inputs.json),
[manifest60 phần tử/68 net](awcar-schematic-parts.json),
[thiết kế lọc nguồn/jumper](awcar-a3-filter-design.md) và
[báo cáo kiểm chứng](awcar-schematic-verification.json).

[Hoàn thiện schematic trước layout](awcar-pcb-next-stage.md): các ref/net
còn mở, thông số module thực cần xác nhận và thứ tự chốt nguồn/gate/giắc.

[Ảnh schematic A3](awcar-schematic-a3.png) và
[SVG phóng to](awcar-schematic-a3.svg) xuất từ bản KiCad đã kiểm thử;
giữ đồng bộ khi sửa source trong `hardware/pcb`.

- [Flash và kiểm tra reset/liên kết ba board06/11](../fpga/targets/tang_nano9k/flash-link-report.md),
  [JSON số đo](fpga-flash-link-evidence.json): reload Flash và reset LOCKED
  và power-cycle/ngắt dây đã thử; verify lịch sử FAIL; bổ sung công cụ phân loại và bản sửa Motion ở báo cáo.
- [LED trạng thái Nano9K và bằng chứng không can thiệp điều khiển](../fpga/targets/tang_nano9k/status-leds-report.md),
  [JSON nguồn và kết quả](fpga-status-led-evidence.json): source30d45ed,
  đã nạp SRAM/quan sát FAULT; chưa nghiệm thu gate/motor.

Lưu yêu cầu, quyết định kỹ thuật và kết quả thử nghiệm.

- [Giai đoạn2 Tang Nano9K/Gowin](../fpga/targets/tang_nano9k/README.md): hardware
  audit, pinout17 tín hiệu, source/constraints/build CLI, STA, risk register và
  bring-up không VM. Bài LED thật đã đạt; AW-Car và gate/E-stop chưa nghiệm thu.

Mốc đồng bộ 02/11/2026: `feat/f01-fpga-drive` là nguồn FPGA chung,
[protocol v2](../firmware/shared/fpga-protocol-v2.md) dùng STATUS34/frame47.
Các sơ đồ/cơ khí concept được giữ để tiếp tục chỉnh; nhãn v1 hoặc số module cũ
trong trang lịch sử không thay thế cổng/tham số RTL hiện tại.

- [Kiểm tra binary Xiaozhi ở root](xiaozhi-binary-review.md): nhận diện hai
  bản ESP32-S3/ESP32, metadata, flash, checksum/hash và GPIO upstream tham khảo.
  Bản S3 trùng từng byte với release v2.5.2; đã tải source đúng commit và đánh
  giá khả thi dịch ngược. Người dùng xác nhận OLED chạy ở GPIO 41/42;
  chưa tích hợp firmware Brain–Motion của AW-Car.

- [Ghép bộ đọc một OUT với FPGA/ESP32](single-channel-encoder-plan.md):
  phương án giảm chi phí cho V2, chuyển mức 5 V -> 3,3 V, đếm/đo chu kỳ
  xung, protocol nhận biết mode và giới hạn không đo được chiều thực.
  Đã triển khai RTL FPGA v2/mô phỏng; chưa có firmware Motion v2 hay kiểm thử phần cứng.

- [Kiểm kê và kế hoạch mua từng linh kiện](../hardware/components.md): mốc
  ngày 28/10/2026 theo đồ chủ dự án đã có; hai ESP32-S3 có Wi-Fi, OLED I²C,
  INMP441, MPU6050 và bộ xe. Đối chiếu ảnh/thông số từng món trước chọn mua.

Các sơ đồ draw.io/PNG dưới đây là bản tham chiếu ngày 24/10, còn chữ TFT và
servo/Ackermann cũ; chưa phản ánh quyết định dùng TT 4WD ngày 28/10. Dùng bảng linh kiện và
Mermaid trong README/kế hoạch phân tải cho trạng thái hiện tại; giữ các file
sơ đồ cũ để chỉnh/xuất lại cùng nhau sau khi chốt cơ khí và pinout.

- [Sơ đồ AW-Car/FPGA v4 — 6 trang](AW_Car_FPGA_Modular_IO_v4.drawio): giữ cả ba
  trang V3 làm tham chiếu, bổ sung sơ đồ hệ thống, flow điều khiển giọng nói
  Xiaozhi và flow điều khiển thủ công qua Dashboard; mũi tên đánh thứ tự dữ
  liệu đến từng nhóm RTL và vòng phản hồi encoder/STATUS/PID. Các bước
  Brain–Motion/Web/Xiaozhi điều khiển xe và adapter/gate là thiết kế dự kiến;
  không coi firmware hoặc mạch công suất đã hoàn tất. Có thể dựng lại bằng
  `python tools/generate_fpga_v4_diagrams.py` chỉ trên bản sao riêng: script cũ
  còn nhãn A/B và có thể ghi đè chỉnh sửa V4 hiện tại của chủ dự án.
- [Sơ đồ FPGA module hóa v3](AW_Car_FPGA_Modular_IO_v3.drawio): ba trang Draw.io
  có thể chỉnh sửa gồm cổng INPUT/OUTPUT chính xác của `drive_core.sv`, đường
  tín hiệu giữa các subsystem và cây phân cấp đủ 15 module RTL; adapter DRV8833,
  gate an toàn và encoder V2 một OUT được đánh dấu là chưa hoàn thiện.

- [Phân công ESP32–FPGA](aw-car-processor-map.png): ảnh tham chiếu,
  file draw.io gốc tương ứng chưa có trong kho;
  gồm [chức năng từng bộ xử lý](aw-car-processor-map.png) và
  [luồng lệnh, phản hồi, đường khóa driver](aw-car-control-flow.png).
  Bản cũ còn ghi PID/PWM servo ở Motion; encoder/PWM motor/watchdog ở FPGA.
  Bản hiện tại đã bỏ servo, dùng TT 4WD theo hai bên. Firmware và mạch thực
  chưa triển khai, chưa có timing đúng chip.
- [Sơ đồ tư duy AW-Car](aw-car-overview.png): ảnh tham chiếu,
  file draw.io gốc tương ứng chưa có trong kho;
  phân cấp bộ xử lý, cơ điện, an toàn, triển khai và ba học phần.
  [Ảnh xem nhanh](aw-car-overview.png) được xuất từ draw.io; khi đổi sơ đồ,
  xuất lại ảnh để hai bản khớp nhau. Sơ đồ ghi Nano 9K là board mục tiêu đã chốt;
  chưa xác nhận fit/timing đúng chip hoặc hoạt động trên phần cứng.
- [Rà soát issue #1](issue-1-technical-review.md): kiến trúc, lỗi thiết kế cần
  tránh, phạm vi 1 mic và lộ trình nghiệm thu; ghi chú F01 về giữ tốc độ,
  kích đề-pa, quãng đường và mã Gray.
- [Quy trình Git](workflow.md): nhánh tính năng, squash merge và bảo vệ main.
- [Kế hoạch FPGA và toàn hệ thống](fpga-drive-plan.md): quyết định mới nhất,
  FPGA phát PWM motor, phân tải, công cụ và các điều kiện nghiệm thu.
- [Thiết kế và kiểm thử RTL](fpga-rtl-design-test-plan.md): module, ca thử,
  luồng Icarus/Gowin không cần Quartus và điều kiện chọn board trước khi mua.

Quy tắc dành cho agent nằm ở [AGENTS.md](../AGENTS.md); không sao chép thành
nhiều bộ quy tắc khác nhau.

[Sơ đồ review RTL v2](AW_Car_FPGA_RTL_Block_Review_v2.drawio) và
[ảnh xem](AW_Car_FPGA_RTL_Block_Review_v2_preview.png) được giữ từ bản
thiết kế mới xuất hiện trong lúc hợp nhất. Đây là bản review để tiếp tục
đối chiếu, không thay danh sách cổng/tham số RTL đã kiểm thử.

[Nghiệm thu và chẩn đoán Tang Nano9K](fpga-bringup-diagnostics.md):
điều kiện trước nạp, ma trận thử trên bàn, nguồn/chân/timing chưa xác nhận và
log lỗi v2 cho ESP32.
