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

`--staged` kiểm tra snapshot trong Git index; `--feature-branch` kiểm tra tên
nhánh hiện tại, hoặc nhận tên nhánh làm đối số khi CI checkout detached HEAD.
CI chạy kiểm tra cấu trúc và test công cụ; đây chưa phải kiểm thử tính năng xe.

`run_fpga_tests.py` biên dịch/chạy testbench Icarus/VVP, dừng khi compile lỗi,
simulation lỗi hoặc timeout; build/VCD trong `fpga/build/` không commit.
Chạy `python tools/run_fpga_tests.py --help`. Cần Icarus/VVP trong PATH hoặc
truyền đường dẫn bằng `--iverilog`/`--vvp`; Python không cần package ngoài.

Tổng hợp sơ bộ: `yosys -s fpga/synth_encoder.ys` và
`yosys -s fpga/synth_pwm.ys`, chạy từ root sau khi tạo `fpga/build/`. Có thể
dùng YoWASP-Yosys trong venv cục bộ thay binary Yosys; bản đã xác minh là
`yowasp-yosys==0.70.0.0.post1259`. Đây là dependency công cụ tùy chọn cho máy
phát triển; CI cài Yosys hệ thống. Kết quả chưa bao gồm place-and-route/timing.
