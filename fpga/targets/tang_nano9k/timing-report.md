# AW-Car Nano9K — timing và kiểm thử

Target GW1NR-9C / GW1NR-LV9QN88PC6/I5, Gowin1.9.11.03 Education. Báo cáo này
chỉ áp dụng AW-Car/physical shell cùng source hash trong build-report.json,
không dùng Fmax/slack của LED. Bitstream AW-Car chưa nạp board.

## Kết quả khảo sát sau route

RTL tham chiếu7ab91b2 với sửa net type/serializer và physical target của nhánh
này. Commit/source hash của build nghiệm thu cuối được ghi trong
`build/tang-nano9k/build-report.json`; artifact build không được commit.
Bảng này sẽ được đóng bằng snapshot JSON sau khi hoàn tất regression và build CLI.

| Chỉ số | Khảo sát target đầy đủ |
| --- | ---: |
| Clock constraint | 27MHz,37,037037ns |
| Actual Fmax | 41,091MHz |
| Worst setup slack (gồm I/O budget) | +11,700ns |
| Worst hold slack | +0,358ns |
| Worst recovery / removal slack | +27,645 / +1,866ns |
| TNS setup / hold | 0 /0ns |
| Setup / hold violated endpoints | 0 /0 |
| LUT4 / ALU | 1668 /311 |
| Logic cells | 1979/8640 |
| Logic FF / I/O FF | 1568 /4 |
| BRAM | 0 primitive |
| Logic / I/O latch | 0 /0 |
| I/O ports / buffers | 17/71 /17 |
| SDC active constraints | 9 |
| False-path sampler D pins | 4, exact names; không blanket cut |
| Unconstrained-path total | Không được tool format này xuất; ghi null |

Đây là timing dưới các giả định SDC trong [audit](hardware-audit.md), gồm
guardband0,2ns và ngân sách propagation một clock cho I/O. Không có clock ngoài
đồng bộ để công bố setup/hold giữa hai chip. GPIO mask/reset/metastability/gate
và biên nguồn vẫn cần review/đo độc lập. Tổng số unconstrained không được đổi
thành0 chỉ vì tool không in;17 boundary ports đã kiểm kê và exceptions tường minh.

## Bằng chứng chức năng sau mapping

Giữ netlist trước sửa trong build chẩn đoán: không có IBUF left_out/right_out.
Cùng test `tb_nano9k_mapped` trả FAIL encoder count0/0, mặc dù PnR exit0 và
timing FF có thể xanh. Bản sửa chọn byte bằng full-width shift khôi phục hai pad.
Mapped functional test với primitive Gowin PASS: bắt đầu resetHIGH để thử INIT/
POR, hai frame STATUSv2 đủ47byte/CRC, count3/5, period32, age khác0, reset/OFF.
Đây không phải timing simulation có SDF hoặc phép đo board.

## Các tầng nghiệm thu

| Tầng | Bằng chứng / phạm vi |
| --- | --- |
| Static pin/project audit | Checker17 cổng/điện áp/package/GPRJ; negative tests chống đổi bank/pin/false-path |
| RTL Icarus | 34 bench full-timing27MHz, report riêng; đang chạy lại nguồn sửa cuối |
| Native Motion + FPGA v2 | Peer main4cea85c,27MHz co-sim; chạy lại với serializer đã sửa |
| Gowin synth/PnR/STA | Khảo sát PASS dưới SDC; chạy CLI nghiệm thu sau cùng |
| Post-PnR mapped function | PASS như trên; counterexample cũ FAIL có chủ đích |
| Physical AW-Car | **NOT VERIFIED**; bài LED của người dùng là thiết kế khác |

Lượt benchmark hủy để sửa source không được tính PASS. Chỉ report full cuối và
hash khớp nguồn cuối được dùng khi chốt. Mạch gate/E-stop chưa có; không có quyền
nâng driver, thử VM hoặc tự merge FPGA vào main từ kết quả phần mềm này.
