# Quy tắc làm việc AW-Car

## Trước khi sửa

- Đọc README ở root, README của thư mục liên quan và yêu cầu đang thực hiện.
- Kiểm tra `git status` và nhánh hiện tại; giữ nguyên thay đổi không thuộc tác vụ.
- Bản đầu: 2 ESP32-S3, 1 FPGA, 1 INMP441; DoA dành cho nâng cấp.
  Dùng khung TT 4WD, hai nhóm motor trái/phải, không dùng servo lái.
  Encoder một OUT là kế hoạch; RTL hiện có A/B chưa hỗ trợ mode mới.
  Phân tải ở `docs/fpga-drive-plan.md`; board mục tiêu Tang Nano 9K, chưa mua
  và chưa xác nhận fit/timing đúng chip. Tối ưu RTL không đổi mục tiêu về 1K.
- Trao đổi và báo cáo bằng tiếng Việt, ngắn gọn; nêu giả định ảnh hưởng thiết kế.

## Nhánh và merge

- `main` luôn là bản ổn định; tạo nhánh trước khi sửa, không commit/push trực tiếp.
- Theo quyết định 30/10/2026, giai đoạn hiện tại chỉ dùng hai nhánh phát triển:
  `feat/f01-fpga-drive` cho FPGA/truyền động và tài liệu liên quan;
  `feat/f03-xiaozhi-ai` cho AI/Xiaozhi, âm thanh, OLED và tài liệu liên quan.
- Dùng lại nhánh đúng phần việc; không tạo thêm nhánh cho từng module, bản sửa
  lỗi, ghi chú hoặc lần tối ưu. Theo dõi các bước nhỏ bằng task và commit.
- Giữ thay đổi chưa commit của checkout khác tại chỗ; không đưa công việc
  phần cứng/CAD đang dở vào một commit chỉ để dọn tên nhánh.
- Nhánh FPGA giữ nền `origin/main` mới nhất đã chứa các PR RTL; giữ nguyên
  lịch sử và bản source đã thử của nhánh AI. Chỉ đồng bộ thay đổi chung cần thiết.
- Hoàn tất kiểm tra và review rồi mở PR vào `main`; dùng **squash merge**.
  Chỉ merge một mốc đã nghiệm thu; sau đó đồng bộ main về hai nhánh đang dùng.
- Tác vụ đang bàn bạc/setup chỉ chuẩn bị nhánh để xem trước, chưa merge.
- Không force-push main, bỏ qua hook/CI hoặc xóa thay đổi của người khác.
- Khi dọn nhánh cũ, kiểm tra phần đã merge và sao lưu commit/thay đổi còn lại
  trước khi xóa tham chiếu. Báo tên nhánh, commit đã push và kiểm tra khi bàn giao.

## Cấu trúc và phạm vi

- Mỗi thư mục được quản lý trong Git có `README.md` giới thiệu ngắn và trạng thái.
- Root `README.md` là mục lục chính; `AGENTS.md` là nguồn quy tắc duy nhất.
- `firmware/brain`: âm thanh, Xiaozhi, OLED I²C, mạng. `firmware/motion`: PID và an toàn.
- `firmware/shared`: giao thức/kiểu dữ liệu chung, không phụ thuộc riêng một MCU.
- `fpga`: RTL đo encoder, PWM motor và watchdog; PID theo hai bên ở Motion. Viết RTL
  độc lập hãng; Quartus chỉ tham khảo cho chip Altera/Intel, Tang Nano dùng Gowin.
- Trong `fpga/rtl`, top logic `drive_core.sv` ở root; module con phân theo
  `common/`, `encoder/`, `pwm/`, `link/`, `safety/`, mỗi nhóm có README.
  Khi chuyển nguồn, cập nhật đường dẫn tổng hợp và runner tìm `.sv` đệ quy.
- Toàn bộ mã HDL của dự án, gồm RTL và testbench, bắt buộc dùng **SystemVerilog
  với đuôi `.sv`**; không thêm nguồn `.v`, `.vh`, `.svh`, `.vhd` hoặc `.vhdl`.
  RTL dùng `logic`, `always_ff`/`always_comb` đúng vai trò; tổng hợp bằng
  Yosys/Gowin và mô phỏng bằng Icarus. Build bật chế độ SystemVerilog; khi đổi tên
  file, cập nhật mọi script/danh sách nguồn và chạy lại mô phỏng/tổng hợp.
- `dashboard`: giao diện Web; `hardware`: BOM/nguồn/sơ đồ/PCB; `docs`: kế hoạch.
- `tests`: kiểm thử; `tools`: công cụ phát triển. Chỉ thêm thư mục con khi cần.
- Không thêm framework, dependency hay mã firmware giả để lấp khung thư mục.
- Không commit bí mật, thông tin Wi-Fi, file build; giữ lockfile của dependency.

## Kiểm tra trước khi bàn giao

- Chạy `python tools/check_repo.py` và `python -m unittest discover -s tests`.
- Chạy `git diff --check` và xem diff; cập nhật README khi đổi vai trò/cách dùng.
- Khi có mã nguồn: chạy build/test đúng phần bị đổi; CI cấu trúc không thay thế
  build firmware, test giao thức hoặc phép đo an toàn trên xe.
- Motion phải dừng độc lập khi mất lệnh/lỗi an toàn, có đường khóa driver ngoài
  giao tiếp FPGA. FPGA mặc định không cho chạy khi boot/reset/mất lệnh hợp lệ.
  AI/Web không ghi PWM trực tiếp; E-stop không phụ thuộc MCU hay clock FPGA.
- Báo rõ đã đổi gì, kiểm tra nào đạt/chưa chạy và rủi ro còn lại. Không gọi
  tính năng là hoàn tất nếu chưa có bằng chứng kiểm thử phù hợp.
