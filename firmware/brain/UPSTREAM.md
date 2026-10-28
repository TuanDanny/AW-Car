# Nguồn Xiaozhi và baseline F03

Ngày đối chiếu: 28/10/2026.

- Kho: https://github.com/78/xiaozhi-esp32
- Tag: v2.5.2.
- Commit: 49b4380b3faa0ceadd28a3e78aaf0f311c46c57e.
- Release: https://github.com/78/xiaozhi-esp32/releases/tag/v2.5.2
- Variant: bread-compact-wifi-128x64, target esp32s3.
- ESP-IDF trong release manifest: 6.1.0.
- LICENSE upstream được giữ nguyên; component ngoài kho có điều khoản riêng.

## Đối chiếu binary

Đã tải v2.5.2_bread-compact-wifi-128x64.zip từ release, kiểm tra SHA-256 ZIP
khớp digest API GitHub và SHA256SUMS của release. ZIP chỉ chứa merged-binary.bin.
So sánh toàn bộ byte bên trong với merged-binary-esp32s3.bin ở checkout gốc
của chủ dự án: trùng hoàn toàn.

| Dữ liệu | Kết quả |
| --- | --- |
| Kích thước binary | 8.949.609 byte |
| SHA-256 binary | 933f2219153b0e2e22ce3833ecf3091631bbffb7181a963a1f7cf011c65533be |
| SHA-256 ZIP firmware | c591d3d6ab98cb82f1c920b07a5a886f806c5d8d3aff7bcd50c44717c37d538e |
| SHA-256 ZIP source theo commit | f32183298a86e35f6c3d4d81e28d900bb79ba281f199e4e7c3d2995cb1c48a4c |

Đây là source mà upstream công bố cho release trùng binary local, không phải
mã decompile. Chưa tái tạo build giống từng byte với release. Ngày 29/10/2026
đã đọc flash trước nạp, tự build và chạy tới màn hình kích hoạt; xem
[bằng chứng build/nạp](docs/aw-car-windows.md). Firmware dựng sẵn, ELF,
NVS và file build không được commit.

## Cách nhập source vào AW-Car

- Nhập snapshot đầy đủ 1.740 file; không thêm nested Git repo/submodule.
- Giữ cấu hình và logic nguồn upstream; chỉ chuẩn hóa khoảng trắng cuối
  dòng/EOF và thụt dòng theo kiểm tra Git của AW-Car. Asset giữ nguyên byte.
- README.md upstream đổi tên README.upstream.md để README.md giới thiệu F03.
- AGENTS.md upstream chuyển thành UPSTREAM-DEVELOPMENT.md dạng tham khảo;
  AGENTS.md của AW-Car ở root vẫn là nguồn quy tắc duy nhất.
- Thêm README mục lục cho các thư mục upstream còn thiếu, chuẩn hóa khoảng
  trắng/newline của Markdown theo kiểm tra repo AW-Car. Một ReadMe.md được
  đổi thành README.md để đúng quy ước tên trên Linux.
- Bỏ dòng ignore dependencies.lock của upstream để lần build sau có thể
  lưu phiên bản dependency đã giải quyết. Chưa có lockfile được dựng giả.
- Các workflow nằm dưới firmware/brain/.github là bản tham khảo upstream;
  GitHub chỉ chạy workflow của AW-Car ở .github/workflows tại root.

Các lần nâng upstream phải ghi tag/commit mới, so diff và chạy host test,
build/kiểm thử phần cứng tương ứng; không thay source âm thầm bằng main mới nhất.

## Giới hạn kiểm thử tại máy Windows

Lượt đầu chạy đủ 110 host test: 11 lỗi, 1 bỏ qua. Lỗi gồm dọn thư mục tạm
khi test còn đứng trong thư mục đó (WinError 32), đọc UTF-8 theo locale
Windows và thiếu compiler c++. Chạy lại UTF-8 gặp Bash chuyển qua WSL và
không hoàn tất, đã dừng tiến trình thử đó. Đây chưa phải kết quả host test
đạt trên Windows. Cần chạy bộ này trên Linux hoặc xử lý tương thích Windows
trước khi kết luận baseline đầy đủ đạt; không thay test bằng kết quả giả.

Mốc kiểm tra đầu chưa có ESP-IDF. Ngày 29/10/2026 đã cài ESP-IDF 6.1,
compile thành công với response file, lưu dependencies.lock, nạp và kiểm
tra boot qua COM3. Việc này không khắc phục các lỗi host test Windows đã
nêu và chưa nghiệm thu chất lượng thu/phát âm hoặc hội thoại AI.
