# Tài liệu tham chiếu FPGA

Lưu các mốc tài liệu đã chốt cùng nguồn và hash để tra cứu trong nhánh FPGA.
Kết quả kiểm thử chỉ áp dụng source commit được nêu trong từng báo cáo.

- [Tang Nano 9K — hướng dẫn Gowin, pinout và audit](tang_nano9k/README.md).
- [Báo cáo timing và kiểm thử Nano9K](tang_nano9k/timing-report.md): mốc
  implementation `17a0ccb`, tài liệu `697c4fa`, ngày 05/11/2026.
- [Build và nạp SRAM trên Tang thật bằng CLI](tang_nano9k/sram-run-2026-11-05.md):
  bổ sung sau bản chụp timing; ghi cả lỗi readback do SecurityBit và lượt SRAM
  Program/CRC thành công. Chưa nghiệm thu UART/encoder/gate/motor thật.

Đây là bản tài liệu tham chiếu. Source/constraints/project target tiếp tục ở
`feat/f01-tang-nano9k-target`; việc thêm tài liệu không ghép target vào RTL
của nhánh này hoặc thay trạng thái nghiệm thu phần cứng.
