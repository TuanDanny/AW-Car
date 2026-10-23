# Workflows

`ci.yml` chạy trên PR vào main và khi main nhận thay đổi: kiểm tra README,
quy tắc tên nhánh PR và test công cụ bằng Python. Không cần dependency ngoài.

Khi có firmware/Dashboard, thêm job build/test tương ứng; job cấu trúc đạt
không chứng minh tính năng xe đã hoạt động.
