# Bàn giao AW-Car — 04/11/2026

## Nhánh và checkout

- Brain/Xiaozhi/dashboard: `feat/f03-xiaozhi-ai`, checkout
  `C:/Users/tuand/.codex/worktrees/xiaozhi-ai/AW-Car`, [PR13](https://github.com/TuanDanny/AW-Car/pull/13).
- Motion: `codex/esp32-s3-motion`, checkout
  `C:/Users/tuand/.codex/worktrees/esp32-s3-motion/AW-Car`, [PR14](https://github.com/TuanDanny/AW-Car/pull/14).
- FPGA: `feat/f01-fpga-drive`, checkout `D:/Project/AW-Car`.
  Checkout `f01-speed-load-plan` đang detached cùng baseline RTL; không sửa
  Brain/Motion ở đó. Các thay đổi CAD/tài liệu đang dở tại checkout FPGA
  được giữ nguyên, chưa đưa vào hai nhánh firmware.
- Hai PR firmware giữ draft, chưa merge main. Firmware đang nạp có code
  Brain `d55e0b1`, Motion `89fd135`; các commit sau là báo cáo/tài liệu.

## Board và dây hiện tại

| Kết nối | Giá trị |
| --- | --- |
| Brain console | COM3, ESP32-S3 |
| Motion console | COM7, CH343, 115200 |
| Brain TX → Motion RX | GPIO17 → GPIO14 |
| Motion TX → Brain RX | GPIO13 → GPIO18 |
| GND logic | Nối chung hai board |
| GPIO17/18 trên Motion | Để trống, chủ dự án đo thông0–5Ω khi tháo nguồn/dây |
| OLED Brain SDA/SCL | GPIO41/42, I²C |
| INMP441 Brain WS/SCK/SD | GPIO4/5/6, L/R nối GND |
| MAX98357A Brain DIN/BCLK/LRC | GPIO7/15/16 |
| RGB Brain | GPIO48 |

Chân cùng số trên hai board là các tín hiệu riêng. UART2 Motion dành FPGA
TX15/RX16; bảng gate và mức điện áp ở [nhánh Motion](https://github.com/TuanDanny/AW-Car/blob/codex/esp32-s3-motion/hardware/motion-wiring.md).
Tang Nano9K đã có nhưng chưa nghiệm thu CST/PnR/STA và đường gate/motor.

## Kết quả và phần còn mở

Đã đọc monitor hai board, không dùng simulator làm bằng chứng phần cứng.
Lượt cuối210s: Brain STATUS20,1Hz/age≤49ms, lỗi parser1→1, HW errors0;
Motion nhận thêm34khung/442byte, parser/HW/queue/TX errors hoặc drops0.
STA Internet/AP DHCP, dashboard và Xiaozhi hoạt động đồng thời; có5STT và
10đoạn trả lời. Xem [báo cáo đã lọc](brain-motion-final-link-report.json).

Một client Close1000 rồi handshake mới xuất hiện trong lượt cuối. Lỗi1006/
send_failure trước đó chưa có nguyên nhân xác định, dù lượt cuối không
tăng send failure. Không coi lỗi này đã sửa dứt điểm. Loa phát được theo
xác nhận người dùng nhưng còn rè, nguồn chưa đo; phần tụ/âm thanh để sau.

Motion vẫn LOCKED/validated=false, driver và logical permit LOW. Chưa
nghiệm thu FPGA/gate/E-stop/motor hoặc latency toàn xe. ARM bị từ chối trên
bản này là đúng cấu hình; không bật driver để làm phép thử UART. Ưu tiên
phiên tới là chốt nối FPGA/gate rồi thử logic an toàn trước motor.

## Source, build và bản khôi phục

Đã fetch/đối chiếu hai nhánh firmware với origin: không thiếu tracked file,
không có source untracked cần push. Lockfile Brain, board profile, dashboard,
codec chung và Motion sdkconfig.defaults đều được quản lý trong Git.
`lang_config.h` là file sinh bởi CMake/gen_lang.py, không phải source bị thiếu.
Không đẩy sdkconfig riêng, mật khẩu, NVS, flash dump hoặc transcript lên Git.

Đã dọn18mục backup/build thử cũ (~1.012MiB), gồm flash/NVS cũ, stock build,
Motion enabled build và archive toolchain đã giải nén. Giữ SDK/toolchain,
managed_components, venv và build tăng dần hiện tại cho lần phát triển sau.

Một bộ khôi phục13file (~50MiB) ở cục bộ:
`C:/Users/tuand/.codex/worktrees/xiaozhi-ai/AW-Car/build/recovery-current/`.
`manifest-private.json` chứa SHA256 đã đối chiếu; app section trong merged
image khớp byte với binary đã kiểm thử. Có merged/app/ELF, sdkconfig riêng
và NVS/motioncfg từ lần nạp gần nhất cho cả hai board. Git ignore toàn bộ.

Các bản NVS này có thể cũ hơn cấu hình Wi-Fi được đổi sau lần nạp; đây
không phải dump mới đọc từ board. Trước lần nạp merged tại0x0000 tiếp theo,
đọc và giữ NVS/motioncfg mới nhất từ đúng board. Cách build tại
[Brain](../firmware/brain/README.md) và
[Motion](https://github.com/TuanDanny/AW-Car/blob/codex/esp32-s3-motion/firmware/motion/README.md).
Brain trên cặp board thật dùng `AWCAR_MOTION_IS_SIMULATED=n`; PC peer mặc
định `y`, không tự đổi chỉ để bỏ nhãn giả lập.

Kiểm tra mỗi lần bàn giao: `python tools/check_repo.py`,
`python -m unittest discover -s tests`, `git diff --check` và build/test phần
bị thay đổi. Theo dõi CI trên đúng head của PR; CI cấu trúc không thay
phép đo UART/FreeRTOS hoặc nghiệm thu phần cứng.
