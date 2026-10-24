# Công cụ phát triển

Python 3.10+ và Git, không cần cài thư viện Python ngoài.

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
kết quả22 bài, module RTL thực được Icarus elaborate trong từng bài PASS,
số ca `COVER`, SHA256 nguồn và compiler. Runner fail nếu thiếu module hoặc
marker PASS dù simulator trả mã0; báo cáo ghi cả lỗi/ca chạy chưa xong.
Đây là kiểm tra module tham gia mô phỏng, chưa đo line/branch/toggle coverage.
CI bật yêu cầu này và lưu JSON kể cả khi regression thất bại.

`fpga_protocol.py` dùng `binascii.crc_hqx` và layout little-endian làm reference
độc lập RTL. Chạy `python tools/fpga_protocol.py` để đối chiếu vector chung;
`--write-vectors` chỉ để ghi lại fixture khi chủ động đổi đặc tả. Testbench
đọc `firmware/shared/fpga-vectors.hex`; unit test phát hiện fixture lệch reference.

Tổng hợp sơ bộ: `yosys -s fpga/synth_encoder.ys`,
`yosys -s fpga/synth_pwm.ys`, `yosys -s fpga/synth_link.ys`,
`yosys -s fpga/synth_drive.ys`, chạy từ root sau
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
