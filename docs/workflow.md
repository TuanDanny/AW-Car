# Quy trình Git

`main -> feat/fXX-ten-ngan -> kiểm tra + review -> PR -> squash merge -> main`.
Mỗi tính năng một nhánh và một commit sau squash; lỗi/tài liệu/setup dùng
`fix/`, `docs/`, `chore/`. Quy tắc chi tiết và cách bảo toàn công việc đang
dở nằm ở [AGENTS.md](../AGENTS.md). F03 đang phát triển riêng trên
`feat/f03-xiaozhi-ai`; không trộn truyền động, FPGA hoặc nguồn vào nhánh này.

## Bắt đầu

Kiểm tra `git status`, bảo toàn thay đổi đang có rồi lấy main mới nhất:

```sh
git fetch origin
git switch -c feat/f01-drive origin/main
```

Tên trên là ví dụ; chọn mã tính năng đúng tác vụ. Khi lấy bản setup về lần đầu:

```sh
git config --local core.hooksPath .githooks
```

## Trước khi merge

- Một PR chỉ chứa phạm vi tính năng và sửa đổi cần thiết để tính năng hoạt động.
- Chạy kiểm tra ở [tools](../tools/README.md), build/test phần mã nguồn đã đổi
  khi có, và ghi rõ phần cần kiểm tra trên phần cứng.
- Review diff, xử lý lỗi, cập nhật nhánh nếu main thay đổi; chỉ squash merge khi
  các kiểm tra phù hợp đã đạt. Với tác vụ đang bàn bạc/setup, giữ nhánh để xem trước.
- Sau merge: `git fetch origin`, chuyển về main và `git pull --ff-only` khi cây
  làm việc sạch; nhánh tiếp theo bắt đầu từ main mới. Không sửa trực tiếp trên main.

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
