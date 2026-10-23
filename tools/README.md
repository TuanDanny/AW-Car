# Công cụ phát triển

Python 3.10+ và Git, không cần cài thư viện Python ngoài.

```sh
python tools/check_repo.py
python -m unittest discover -s tests
git diff --check
```

`check_repo.py` kiểm tra `AGENTS.md`, README của mọi thư mục có file được quản
lý và các file Markdown: UTF-8, nội dung, khoảng trắng cuối dòng, newline cuối file.
File untracked chưa bị ignore cũng được kiểm tra; file build bị ignore không tính.

`--staged` kiểm tra snapshot trong Git index; `--feature-branch` kiểm tra tên
nhánh hiện tại, hoặc nhận tên nhánh làm đối số khi CI checkout detached HEAD.
CI chạy kiểm tra cấu trúc và test công cụ; đây chưa phải kiểm thử tính năng xe.
