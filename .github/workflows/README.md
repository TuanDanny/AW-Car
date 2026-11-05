# Workflows

`ci.yml` chạy PR main, push main/integration/** hoặc workflow_dispatch:

- `structure-and-rules`: repository, nhánh và whitespace; chỉ chạy test công cụ.
- `host-regression`: toàn bộ root Python tests, production Brain/Motion core,
  Web/auth/network/LED/protocol và Node dashboard; cài cùng dependencies dev.
- `motion-peer-integration`: ghép hai MCU core trong chính checkout được review,
  co-sim FPGA v2 từ commit7ab91b2 riêng, không dùng RTL v1 baseline làm v2.
- `fpga-simulation`: giữ hồi quy22testbench/full-timing và4script Yosys của main;
  không sửa RTL trong milestone firmware.

`brain.yml` chạy công cụ build/release Xiaozhi trên Ubuntu24.04/Python3.13,
tránh nhầm lỗi harness Windows với regression firmware. Artifact chỉ lấy report
host đã lọc, không có raw log/NVS/backup/credential. Không checkout Brain peer cũ
cho phép thử tích hợp. SDK build Brain/Motion được ghi riêng trong MERGE-READINESS;
CI host/synthesis generic không thay ESP-IDF build, PnR/STA hoặc test board.

Integration cục bộ chưa push thì không có CI run GitHub; phải báo PENDING,
không lấy CI xanh của PR nguồn làm CI của tổ hợp. Chỉ push sau chủ dự án duyệt.
