# Công cụ phát triển

Python 3.10+ và Git, không cần cài thư viện Python ngoài.

`generate_awcar_schematic.py` sinh một trang KiCad A1 có dây tín hiệu nối
trực tiếp, từ manifest trong `docs/awcar-schematic-parts.json`; nhúng symbol
passive/BJT từ thư viện KiCad cài tại máy. Mặc định từ chối ghi đè source
đã có; `--overwrite` sao lưu trước vào build, không dùng để ghi đè chỉnh tay
chưa review. `check_awcar_schematic.py` kiểm netlist XML KiCad với contract
UART/GPIO/audio/driver và đối chiếu toàn bộ44 phần tử/69 net;
`simulate_awcar_clamps.py` dùng ngspice DLL mô phỏng
R/Q đọc từ netlist đó. Không có lệnh COM/flash/ARM hoặc phát hành PCB.
Cách mở/chạy và giới hạn mô hình ở [KiCad](../hardware/pcb/README.md).
Source trực tiếp ở `hardware/pcb`; `--output build/kicad-candidate` tạo bản
thử để review mà không chạm chỉnh tay. Không còn project simulation riêng;
runner batch đọc chính netlist xuất từ schematic chung.

`build_tang_nano9k.py` audit pin/điện áp/GPRJ/SDC, chạy RTL regression, Gowin
synthesis/PnR/STA và tùy chọn test netlist thật với primitive Gowin. Dùng
`--audit-only` cho checker không cần chạy compiler; lệnh đầy đủ và giới hạn ở
[target](../fpga/targets/tang_nano9k/README.md). Script không flash/mở COM/ARM.
Output/hash/report ở build ignored. Missing metric unconstrained ghi null,
không biến thành0; pin drift, latch, timing âm hoặc pad/sampler bị mất đều fail.

`gowin_programmer_result.py` chỉ phân loại log đã thu, không chạy Programmer
hoặc mở COM/JTAG. API `analyze_programmer_result(stdout, stderr="", returncode=...,
operation_index=..., expected_usercode=None, timed_out=False, output_truncated=False)`
trả dict JSON; CLI ví dụ:

```sh
python tools/gowin_programmer_result.py --log flash-program.log --returncode 0 --operation-index 6 --expected-usercode 0x9EF7
```

Hỗ trợ op0/1/2/5/6, thêm `--stderr-log`, `--timed-out`, `--truncated` khi cần.
Exit0 chỉ khi đạt đủ tiêu chí; lỗi Error/Failed thắng Finished/exit0. Thiếu
`Finished.`, readout hoặc capture bị cắt/timeout đều chưa đạt. Op0 cần ID
0x1100481B; op0/2/5/6 cần UserCode và status không lỗi CRC/lệnh/ID/timeout,
VLD/DONE/READY/POR/Security ON. `configuration_status=VALID` chỉ nói về các
bit status đã đọc, không chứng minh CRC bật trong image hay so byte Flash.
Op1 completed vẫn configuration UNKNOWN/chưa đạt, cần phân tích op0 kế tiếp.
`readback_verify=NOT_REQUESTED` cho op0/1/2/5; op6 chỉ PASSED khi log có marker
verify thành công tường minh. Không suy nguyên nhân Verify Failed từ security.
API nhận một lượt chạy, từ chối header sai op/nhiều lượt ghép chung; caller
phải báo capture bị cắt/timeout đã biết.

```sh
python tools/check_repo.py
python -m unittest discover -s tests
git diff --check
```

`check_repo.py` kiểm tra `AGENTS.md`, README của mọi thư mục có file được quản
lý và các file Markdown: UTF-8, nội dung, khoảng trắng cuối dòng, newline cuối file.
File untracked chưa bị ignore cũng được kiểm tra; file build bị ignore không tính.
Mã HDL bắt buộc dùng SystemVerilog, đuôi `.sv`; đuôi `.v`, `.vh`, `.svh`,
`.vhd`, `.vhdl` và biến thể viết hoa bị chặn, kể cả trong snapshot đã stage.

`--staged` kiểm tra snapshot trong Git index; `--feature-branch` kiểm tra tên
nhánh hiện tại, hoặc nhận tên nhánh làm đối số khi CI checkout detached HEAD.
CI chạy kiểm tra cấu trúc và test công cụ; đây chưa phải kiểm thử tính năng xe.

`run_fpga_tests.py` biên dịch/chạy testbench Icarus/VVP, dừng khi compile lỗi,
simulation lỗi hoặc timeout; build/VCD trong `fpga/build/` không commit.
Runner lấy đệ quy toàn bộ `.sv` trong `fpga/rtl/`, gồm top tại root và các
nhóm module con; bật chế độ SystemVerilog `-g2012`. Không lấy model/testbench
ngoài cây `rtl/` vào danh sách nguồn RTL.
Chạy `python tools/run_fpga_tests.py --help`. Cần Icarus/VVP trong PATH hoặc
truyền đường dẫn bằng `--iverilog`/`--vvp`; Python không cần package ngoài.
`--full-timing --timeout 1800` chạy cả bài top>=2s tại27MHz; mặc định bài dài
dùng2,7MHz và thêm bài lỗi27MHz. CI bật full-timing, không dùng số liệu scaled
để xác nhận timing vật lý.

`--report fpga/build/regression-report.json --require-module-coverage` ghi
kết quả34 bài, module RTL thực được Icarus elaborate trong từng bài PASS,
số ca `COVER`, SHA256 nguồn và compiler. Runner fail nếu thiếu module hoặc
marker PASS dù simulator trả mã0; báo cáo ghi cả lỗi/ca chạy chưa xong.
Đây là kiểm tra module tham gia mô phỏng, chưa đo line/branch/toggle coverage.
CI bật yêu cầu này và lưu JSON kể cả khi regression thất bại.

`fpga_protocol.py` dùng `binascii.crc_hqx` và layout little-endian làm reference
độc lập RTL. Chạy `python tools/fpga_protocol.py` để đối chiếu vector chung;
`--write-vectors` chỉ để ghi lại fixture khi chủ động đổi đặc tả. Testbench
đọc `firmware/shared/fpga-vectors.hex` (v1) và `fpga-vectors-v2.hex` (v2);
unit test phát hiện fixture lệch reference. `encode_frame(..., version=2)`
tạo frame v2 tường minh, không tự coi STATUS18 byte là v2.

Tổng hợp sơ bộ: `yosys -s fpga/synth_encoder.ys`,
`yosys -s fpga/synth_pwm.ys`, `yosys -s fpga/synth_link.ys`,
`yosys -s fpga/synth_drive.ys`, `yosys -s fpga/synth_aw_car.ys`, chạy từ root sau
khi tạo `fpga/build/`. Có thể
dùng YoWASP-Yosys trong venv cục bộ thay binary Yosys; bản đã xác minh là
`yowasp-yosys==0.70.0.0.post1259`. Đây là dependency công cụ tùy chọn cho máy
phát triển; CI cài Yosys hệ thống. Kết quả chưa bao gồm place-and-route/timing.

`check_fpga_equivalence.py` so sánh PWM/motor PWM/command guard/safety với một
revision Git trước tối ưu. Bản baseline phải có trong lịch sử local:

```sh
python tools/check_fpga_equivalence.py --base 821cfae --yosys <yosys>
```

Tool tạo bản nguồn/miter/log trong `fpga/build/equivalence/`, không sửa RTL.
Yosys SAT temporal induction chứng minh đầu ra và quan hệ trạng thái; các
invariant là assertion được chứng minh, không giả định từ người gọi. Có14
trường hợp, gồm tham số mặc định, duty power-of-two và timer nhỏ/hold>=clear.
Reset bất đồng bộ được chuẩn hóa bằng async2sync; vẫn phải mô phỏng reset và
đo CDC/reset/timing trên board. Đây là phép so sánh phục vụ refactor f11,
chạy riêng cục bộ; CI chạy regression Icarus/tổng hợp. Khi chủ động đổi chức
năng, phải xem lại baseline/observation, không coi bản cũ là đặc tả mới.

`generate_fpga_v4_diagrams.py` là generator sơ đồ tham chiếu được giữ từ
checkout thiết kế. Chỉ chạy trên bản sao: nhãn cũ và chỉnh tay của sơ đồ
không được phép ghi đè ngược lên RTL/tài liệu protocol hiện tại.

`generate_fpga_v2_review_block.py` giữ bản generator sơ đồ review v2 độc lập;
không chạy để ghi đè các chỉnh sửa sơ đồ trong tác vụ hợp nhất.

`fpga_protocol.py --decode-status HEX` xác thực và giải mã47 byte STATUS v2,
phân loại lỗi Safety/cảnh báo/diagnostic cần reset; không tự cấp quyền chạy xe.
