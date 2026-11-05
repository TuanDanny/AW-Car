# Quy trình Git

Giai đoạn hiện tại giữ `main` ổn định và ba nhánh phát triển:

| Nhánh | Phần việc |
| --- | --- |
| `feat/f01-fpga-drive` | RTL, encoder, PWM, liên kết FPGA và tài liệu |
| `feat/f03-xiaozhi-ai` | Brain, Xiaozhi, Web, âm thanh và OLED |
| `codex/esp32-s3-motion` | Motion, hai UART, truyền động và khóa driver |

Nhánh Motion tạo từ main `094b37c` theo yêu cầu 03/11/2026; giữ PR Brain #13
draft. Dùng lại nhánh cho sửa lỗi/tối ưu; theo dõi bước nhỏ bằng commit.
Quy tắc duy nhất nằm ở [AGENTS.md](../AGENTS.md).

## Làm việc

Kiểm tra `git status`, bảo toàn thay đổi hiện có, `git fetch origin`, rồi
làm trong worktree của nhánh phù hợp. Không tạo thêm nhánh cho từng module.
Lần đầu clone bật `git config --local core.hooksPath .githooks`.

Chỉ đồng bộ hợp đồng/codec cần thiết giữa các nhánh. Motion giữ nền main;
co-sim dùng checkout FPGA v2 riêng, không kéo CAD hoặc cả lịch sử AI vào.
Brain giữ nguyên source và lịch sử đã thử. Không sửa trực tiếp main.

## Bàn giao và merge

- Chạy repo checks, unit tests, build phần đổi và review diff.
- Ghi đúng phiên bản hai peer, bằng chứng và phần phần cứng chưa thử.
- Mở PR vào main; chỉ **squash merge** mốc đã được nghiệm thu. Mốc đang
  setup hoặc còn thiếu phần cứng giữ draft, không tự merge.
- Sau merge đồng bộ main về các nhánh đang dùng khi cây làm việc sạch.
- Dọn nhánh phải kiểm tra/sao lưu phần chưa merge; không xóa công việc CAD
  hoặc thay đổi chưa commit của checkout khác.

Hooks kiểm tra snapshot staged và tên nhánh, chặn commit/push main; mỗi
clone phải bật riêng. CI kiểm cấu trúc, host tests và hồi quy RTL; không thay
build firmware hay đo trên xe. Không bỏ qua hook/CI hoặc force-push main.
Ruleset phía GitHub cần được xác minh riêng khi nghiệm thu merge.

## Tích hợp milestone Brain+Motion LOCKED

Theo yêu cầu05/11, nhánh tạm `integration/brain-motion-v0.1` từ origin/main
chuẩn bị tổ hợp Brain rồi Motion; giữ commit gốc và merge resolution truy nguyên.
Audit tất cả worktree, pin HEAD và peer v2, giữ nguyên RTL/CAD/dirty source.
Chạy host/regression/build trong worktree riêng; không flash/reset trong review.
Không push integration hoặc merge main trước duyệt. Khi được phép công bố ứng viên,
CI chạy trên push integration/** và PR main; CI chưa chạy phải ghi PENDING.

Phê duyệt merge main là bước riêng: squash Brain PR trước, đồng bộ Motion trong
worktree mới theo main mới, chạy CI lại rồi mới squash Motion PR. So sánh cây cuối
với ứng viên đã duyệt, không dùng Git merge clean làm bằng chứng firmware.
Rollback bằng PR `git revert` các squash commit theo thứ tự Motion rồi Brain;
không reset/force-push main. Tag milestone chỉ đề xuất sau CI main đạt.
