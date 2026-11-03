# Workflows

`ci.yml` chạy trên PR vào main và khi main nhận thay đổi: kiểm tra README,
quy tắc tên nhánh PR và test công cụ bằng Python. Job `fpga-simulation` cài
Icarus/Yosys trên Ubuntu24.04 rồi chạy
`python tools/run_fpga_tests.py --full-timing --timeout 1800` và bốn script
tổng hợp trong `fpga/`, gồm top hoàn chỉnh. Bài top dài chạy>=2s tại27MHz; compile, testbench lỗi, timeout hoặc lỗi
`check -assert` đều làm CI thất bại. Version được in trong log.

Gowin mapping generic chưa phải báo cáo fit/timing sau route trên chip cụ thể.

Job `motion-peer-integration` biên dịch core/codec Motion C++ thật, ghép
Brain và RTL v2 từ hai commit cố định trong `build/peers/`. Không dùng RTL
v1 baseline của checkout Motion để kiểm v2. Report/hash được lưu artifact;
smoke 30s thời gian ảo không thay soak paced30phút cục bộ. Không upload
backup/NVS/flash/log board. Build ESP-IDF ghi tại báo cáo Motion, chưa có job
MCU SDK; CI host/cấu trúc không chứng minh tính năng trên xe.
