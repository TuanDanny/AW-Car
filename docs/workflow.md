# Quy trình Git

Giai đoạn hiện tại dùng `main` ổn định và hai nhánh phát triển:

| Nhánh | Phần việc |
| --- | --- |
| `feat/f01-fpga-drive` | FPGA, truyền động, giao tiếp Motion–FPGA và tài liệu liên quan |
| `feat/f03-xiaozhi-ai` | AI/Xiaozhi, âm thanh, OLED và tài liệu liên quan |

Dùng lại nhánh phù hợp cho sửa lỗi, tài liệu và tối ưu; theo dõi từng bước
bằng task/commit. Quy tắc ở [AGENTS.md](../AGENTS.md).

## Bắt đầu

Kiểm tra `git status`, bảo toàn thay đổi đang có rồi lấy thông tin mới nhất:

```sh
git fetch origin
git switch feat/f01-fpga-drive
```

Nếu nhánh đang được dùng ở worktree khác, làm trong worktree đó. Khi làm AI,
dùng `feat/f03-xiaozhi-ai`. Không tự tạo thêm nhánh cho mỗi task. Lần setup đầu:

```sh
git config --local core.hooksPath .githooks
```

## Trước khi merge

- Một PR bàn giao một mốc của FPGA hoặc AI, với diff và kiểm tra rõ ràng.
- Chạy kiểm tra ở [tools](../tools/README.md), build/test phần mã nguồn đã đổi
  khi có, và ghi rõ phần cần kiểm tra trên phần cứng.
- Review diff, xử lý lỗi, cập nhật nhánh nếu main thay đổi; chỉ squash merge khi
  các kiểm tra phù hợp đã đạt. Với tác vụ đang bàn bạc/setup, giữ nhánh để xem trước.
- Sau merge: lấy main mới rồi đồng bộ vào hai nhánh phát triển khi cây làm việc
  sạch. Không sửa trực tiếp trên main.

## Dọn nhánh cũ

Các PR encoder/PWM/UART/watchdog/tối ưu đã squash vào main. Kiểm tra nội dung
và sao lưu lịch sử trước khi bỏ tên nhánh cũ. Thay đổi phần cứng/CAD chưa
commit ở checkout khác phải được giữ nguyên, không tự gộp vào bản đã nghiệm thu.

## Mức bảo vệ

- `AGENTS.md`: hướng dẫn công cụ tự đọc và tự kiểm tra; không phải khóa Git.
- Hooks cục bộ: chặn commit trên main/sai tên nhánh và push trực tiếp lên main;
  pre-commit kiểm tra nội dung **đã stage**. Mỗi bản clone phải bật hooks riêng.
- CI `Repository checks / structure-and-rules`: kiểm tra cấu trúc và test công
  cụ trên PR/main; hiện chưa build firmware vì chưa có mã nguồn.

**Chưa cấu hình bảo vệ nhánh trên GitHub.** Khi đưa setup lên GitHub, đặt ruleset
cho main: yêu cầu PR, chỉ squash merge, yêu cầu status check `structure-and-rules`,
chặn force-push/xóa main và áp dụng cho người có quyền bỏ qua khi phù hợp.
Hooks có thể bị bỏ qua; chính ruleset phía GitHub mới chặn push/merge sai từ mọi máy.
