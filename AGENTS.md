# Quy tắc làm việc AW-Car

## Trước khi sửa

- Đọc README ở root, README của thư mục liên quan và yêu cầu đang thực hiện.
- Kiểm tra `git status` và nhánh hiện tại; giữ nguyên thay đổi không thuộc tác vụ.
- Bản đầu: 2 ESP32-S3, 1 FPGA, 1 INMP441; DoA dành cho nâng cấp.
  Dùng khung TT 4WD, hai nhóm motor trái/phải, không dùng servo lái.
  Encoder bản đầu dùng một OUT mỗi bên: RTL đếm cạnh lên không dấu;
  không suy chiều đo từ lệnh motor. Giữ A/B là mode tùy chọn.
  Bản một OUT mặc định dùng protocol v2 (STATUS 34 byte, frame 47 byte),
  có period/age; v1 chỉ để tương thích/hồi quy, phải chọn phiên bản tường minh.
  V2: fault[7:0] là lỗi Safety, fault[15:8] là diagnostic sticky. Chỉ các cờ
  snapshot stall/invariant (mask 0x8800) yêu cầu reset; không coi mọi cảnh báo
  encoder/RX là lỗi tự khóa. ESP32 vẫn phải timeout STATUS độc lập.
  Nhánh AI giữ lịch sử source và không tự kéo toàn bộ RTL sang.
  Phân tải ở `docs/fpga-drive-plan.md`; đã có Tang Nano 9K theo xác nhận
  03/11/2026, chưa xác nhận fit/timing đúng chip. Không đổi mục tiêu về 1K.
- Trao đổi và báo cáo bằng tiếng Việt, ngắn gọn; nêu giả định ảnh hưởng thiết kế.

## Nhánh và merge

- `main` luôn là bản ổn định; tạo nhánh trước khi sửa, không commit/push trực tiếp.
- Theo quyết định cập nhật 03/11/2026, dùng ba nhánh phát triển:
  `feat/f01-fpga-drive` cho FPGA/truyền động và tài liệu liên quan;
  `feat/f03-xiaozhi-ai` cho AI/Xiaozhi, âm thanh, OLED và tài liệu liên quan;
  `codex/esp32-s3-motion` tách từ main cho firmware Motion, hai UART và gate.
- Theo yêu cầu05/11/2026, cho phép nhánh tạm `integration/brain-motion-v0.1`
  từ origin/main để audit Brain+Motion. Không flash/reset, không đổi driver,
  không push bản tích hợp hoặc merge main trước khi chủ dự án duyệt.
- Chủ dự án đã duyệt chốt milestone05/11: squash Brain PR13 trước, cập nhật
  Motion PR14 theo main trong worktree riêng, kiểm CI tổ hợp trước squash
  Motion; chạy CI main cuối rồi tạo tag `v0.1-brain-motion-locked`.
  Worktree tạm `codex/motion-release-v0.1` chỉ phục vụ cập nhật PR14; giữ
  nguyên worktree nguồn/FPGA/CAD. Không flash/reset hoặc mở driver trong release.
- Dùng lại nhánh đúng phần việc; không tạo thêm nhánh cho từng module, bản sửa
  lỗi, ghi chú hoặc lần tối ưu. Theo dõi các bước nhỏ bằng task và commit.
- Ngày06/11 người dùng giao xử lý lỗi UART FPGA→Motion đã bắt trên board.
  Dùng lại `codex/esp32-s3-motion`, cho phép thêm chẩn đoán/sửa và nạp Motion
  COM7 khi vẫn ENABLE_DRIVER=n/validated0; sao lưu và so byte NVS/motioncfg.
  Brain/image FPGA giữ nguyên; tài liệu tích hợp ở nhánh target Nano9K riêng.
  Không tăng hạn parser, bỏ CRC hoặc nối giả health để làm lỗi biến mất.
- Giữ thay đổi chưa commit của checkout khác tại chỗ; không đưa công việc
  phần cứng/CAD đang dở vào một commit chỉ để dọn tên nhánh.
- Nhánh FPGA giữ nền `origin/main` mới nhất đã chứa các PR RTL; giữ nguyên
  lịch sử và bản source đã thử của nhánh AI. Chỉ đồng bộ thay đổi chung cần thiết.
- Hoàn tất kiểm tra và review rồi mở PR vào `main`; dùng **squash merge**.
  Chỉ merge một mốc đã nghiệm thu; sau đó đồng bộ main về các nhánh đang dùng.
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
- Trong nhánh FPGA, top triển khai duy nhất là `aw_car_top.sv` ở root,
  bọc lõi `drive_core.sv`; lõi vẫn là top kiểm thử/tổng hợp riêng. Checkout
  Integration và các nhánh firmware giữ RTL baseline main; FPGA v2 dùng
  checkout peer cố định riêng để co-sim, không kéo RTL/CAD vào merge MCU.
  Module con phân theo
  `common/`, `encoder/`, `pwm/`, `link/`, `safety/`, mỗi nhóm có README.
  Khi chuyển nguồn, cập nhật đường dẫn tổng hợp và runner tìm `.sv` đệ quy.
- Toàn bộ mã HDL của dự án, gồm RTL và testbench, bắt buộc dùng **SystemVerilog
  với đuôi `.sv`**; không thêm nguồn `.v`, `.vh`, `.svh`, `.vhd` hoặc `.vhdl`.
  RTL dùng `logic`, `always_ff`/`always_comb` đúng vai trò; tổng hợp bằng
  Yosys/Gowin và mô phỏng bằng Icarus. Build bật chế độ SystemVerilog; khi đổi tên
  file, cập nhật mọi script/danh sách nguồn và chạy lại mô phỏng/tổng hợp.
- `dashboard`: giao diện Web; `hardware`: BOM/nguồn/sơ đồ/PCB; `docs`: kế hoạch.
- Brain/dashboard: hai mode Manual/AI, nguồn lệnh độc quyền; neutral giữ ARM,
  STOP bỏ ARM. Host simulator phải dùng chính control core C++, không dựng
  bản sao phân xử bằng JS. Mọi số đo giả lập phải ghi rõ môi trường.
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
