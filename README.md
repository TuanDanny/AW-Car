# AW-Car

Xe TT4WD dùng hai ESP32-S3, Tang Nano9K và một INMP441; hai nhóm motor trái/phải,
lái bằng tốc độ hai bên, không servo. Brain giữ Xiaozhi/Web/âm thanh/OLED;
Motion giữ quyền truyền động; FPGA phát PWM/đọc encoder. DoA để nâng cấp.

Tác giả: **TuanDanny**. Cộng tác viên: **Minh Nho** và **Nhan Duc**.

## Ứng viên milestone0.1 — Brain+Motion LOCKED

Nhánh `integration/brain-motion-v0.1` chuẩn bị từ main094b37c, Brainfe776f0
và Motionbc27255. Chưa push/merge main, chưa flash/reset board trong lượt review.
[MERGE-READINESS](docs/MERGE-READINESS.md) là nơi chốt test/build/CI/rollback;
Git merge clean, compile, host PASS và hardware verified là các mức khác nhau.

- Brain: Dashboard Manual/AI, sáu hướng, authentication/WebSocket, AP+STA,
  Xiaozhi tiếng Trung, INMP441/MAX98357A/OLED I²C, phục hồi reset Motion và
  lưu Wi-Fi ưu tiên. STOP/đổi mode/mất liên kết thu quyền, không tự ARM/MOVE.
- Motion: BM-v1, hai UART, vòng hở/kích đề-pa/chờ đảo, lease và gate riêng.
  **ENABLE_DRIVER=n, validated=0**; PID/cảm biến để mốc sau.
- WS2812 GPIO48 hai board chỉ báo trạng thái; code RGB demo AI/Web đã xóa.
  Brain xanh lá không chứng minh Motion/motor đã sẵn sàng hoặc được ARM.

Source riêng trước tích hợp đã thử UART hai ESP ~20Hz, dashboard/AP+STA/
Xiaozhi và màu LED; [report trước merge](docs/status-led-report.json).
Lỗi1006 cũ chưa rõ nguyên nhân, loa còn rè/nguồn chưa đo. **Không lấy bằng
chứng đó thay nghiệm thu binary tích hợp. HARDWARE NOT VERIFIED cho ứng viên này.**

## FPGA tách milestone

Toàn bộ cây `fpga/` giữ nguyên origin/main094b37c, chưa nhập RTL từ nhánh FPGA.
Motion bắt buộc [protocol v2](firmware/shared/fpga-protocol-v2.md), STATUS34/
frame47byte/encoder một OUT mỗi bên. RTL v1 baseline ở checkout này chỉ để
hồi quy; không dùng để ghép Motion. Co-sim v2 dùng peer7ab91b2 riêng trong build.
Tang Nano9K đã có; CST/PnR/STA, gate/E-stop, motor/dòng/nhiệt/quãng dừng còn
phải nghiệm thu. Số đếm một OUT không cho biết chiều quay thực.

## Mục lục

| Thư mục | Vai trò |
| --- | --- |
| [Brain](firmware/brain/README.md) | ESP-IDF6.1, Xiaozhi, Web, audio/OLED/mạng |
| [Motion](firmware/motion/README.md) | ESP-IDF6.1, hai UART, core và adapter an toàn |
| [Shared](firmware/shared/README.md) | Một codec BM-v1, một codec FPGA v2, policy LED |
| [Dashboard](dashboard/README.md) | Manual/AI, transcript/telemetry và simulator |
| [FPGA](fpga/README.md) | RTL baseline main; phát triển v2 ở nhánh FPGA |
| [Hardware](hardware/README.md) | Linh kiện, nguồn, cơ khí và bảng dây |
| [Docs](docs/README.md) | Contract, kế hoạch, báo cáo |
| [Tests](tests/README.md) | Root/host, Web, protocol và co-sim |
| [Tools](tools/README.md) | Build host, kiểm tra, giả lập và board tooling |

[AGENTS.md](AGENTS.md) là nguồn quy tắc; [workflow](docs/workflow.md) quy định
audit/duyệt merge. Giữ nhánh FPGA/CAD đang dở tại chỗ. Thiết kế gốc ở
[issue1](https://github.com/TuanDanny/AW-Car/issues/1),
[phân tải](docs/fpga-drive-plan.md), [rà soát](docs/issue-1-technical-review.md),
[linh kiện](hardware/components.md), [khóa gate](firmware/shared/fpga-safety.md).

## Kiểm tra cục bộ, không tác động thiết bị

```sh
python tools/check_repo.py --feature-branch
python -m unittest discover -s tests -v
node --test dashboard/control.test.mjs dashboard/connection.test.mjs
python tools/motion_brain_integration.py --brain-root .
git diff --check
```

Build từng firmware theo README riêng. Không chạy công cụ board/flash/reset
trong review này. Không commit sdkconfig riêng, credential, raw log, NVS hay
build output. Chỉ đề xuất tag v0.1-brain-motion-locked sau duyệt và CI main đạt.
