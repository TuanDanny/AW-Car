# Git hooks cục bộ

Bật cho từng clone bằng `git config --local core.hooksPath .githooks`.

- `pre-commit`: kiểm tra tên nhánh và cấu trúc/Markdown trong Git index.
- `pre-push`: chặn đẩy trực tiếp vào main; đưa thay đổi vào main qua PR.

Hooks là hàng rào trên máy đã bật, không thay thế ruleset GitHub hoặc build/test.
