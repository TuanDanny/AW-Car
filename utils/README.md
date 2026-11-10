# Công cụ

`awcarctl.py discover`, `info brain|motion`, `logs brain|motion --seconds 60`:
đọc quản trị trên STA, HTTPS3232; thêm `--ip` khi không tìm thấy .local.
`upload brain` nạp app vào slot không chạy, xác minh boot/ELF và health cục bộ;
Motion phải migration riêng trước. `test_ota_receiver.py` kiểm các ca từ chối,
truyền dở và reset, chỉ chạy trên bàn với `--vm-off`.

`migrate_motion_ota.py` chỉ dành lần USB chuyển từ layout legacy; đã bootstrap
thì chỉ upload app. Mỗi vùng bị ghi đều sao lưu trước, giữ factory/NVS/motioncfg.
Build sinh token/chứng chỉ riêng trong build/private/management-keys; giữ chúng
để dùng từ laptop, không commit. CLI pin đúng chứng chỉ, không dùng verify=false.

`probe_ap_boundary.py --ip <Motion-STA-IP>`: từ LAN router kiểm root và WS handshake
thật/giả Host/Origin AP; không gửi frame lái. Địa chỉ AP192.168.4.1 bị từ chối đầu vào.

`build_esp.py motion|brain`: build ESP-IDF, không nạp. `build_host.py`: native C++.
Các thư mục build, log thô, flash dump không đưa vào Git. Công cụ flash phải xác nhận
đúng manifest/board và trạng thái VM trước khi dùng; không tự dò rồi ghi mọi COM.

Chi tiết lệnh ở [build.md](../docs/build.md). `serial_log.py` chỉ đọc console,
không reset/gửi lệnh; phân biệt watchdog với panic. `check_wiring.py` đối chiếu
netlist XML xuất bằng KiCad với contract và CST thực. `program_fpga.py` mặc định
SRAM, Flash đòi hash/báo cáo SPI khớp. `simulator.py` dùng lõi C++ thật; `soak.py`
chỉ đo host. `generate_schematic.py` không ghi đè mặc định, giữ schematic cũ riêng.
