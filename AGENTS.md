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
  Phân tải ở `docs/fpga-drive-plan.md`; Tang Nano9K đã chạy bài LED thật theo
  người dùng. Target AW-Car/Gowin ở `fpga/targets/tang_nano9k`; người dùng đã cho phép
  và đã nạp SRAM AW-Car qua CLI ngày05/11, chưa thử công suất. STA dưới constraints không thay nghiệm thu gate/E-stop/motor.
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
- Ngoại lệ được người dùng giao05/11/2026: `feat/f01-tang-nano9k-target` ở worktree
  sạch riêng cho target Gowin, dựa FPGA7ab91b2 và đối chiếu main4cea85c LOCKED.
  Chỉ sửa workspace Gowin khi người dùng giao; không sửa CAD đang dở, thay Motion
  LOCKED hoặc tự merge FPGA vào main. Ngày06/11 người dùng giao hai mốc: lưu
  AW-Car vào Flash Tang và kiểm tra reset/mất liên kết ba board. Cho phép ghi
  đúng image đã audit/hash vào embedded Flash, giữ CRC/Security; không ghi khóa/
  OTP, user flash hoặc đổi firmware/NVS hai ESP32. Kiểm tra cả log ngữ nghĩa,
  không coi exit0 là PASS nếu Programmer in Verify Failed. Gate/E-stop chưa có.
- Yêu cầu tiếp ngày06/11: xử lý lỗi parser/Flash workflow. Cho phép sửa và
  nạp Motion LOCKED trên nhánh Motion hiện có, giữ NVS/motioncfg, không đổi
  firmware Brain hoặc mở driver; nhánh target lưu công cụ/báo cáo tích hợp.
  Không vô hiệu hóa CRC, deadline hoặc protection để đổi kết quả thành PASS.
- Không force-push main, bỏ qua hook/CI hoặc xóa thay đổi của người khác.
- Khi dọn nhánh cũ, kiểm tra phần đã merge và sao lưu commit/thay đổi còn lại
  trước khi xóa tham chiếu. Báo tên nhánh, commit đã push và kiểm tra khi bàn giao.

## Cấu trúc và phạm vi

- Yêu cầu07/11/2026: schematic KiCad trước, PCB sau khi chốt thành phần;
  module phải cắm rút, không hàn chết. Theo yêu cầu tiếp07/11, gộp thành một
  trang đấu nối chung ở `hardware/pcb/aw_car.kicad_sch`, project và thư viện
  cùng thư mục; bỏ concept PCB cũ và các sheet tách sau khi giữ bản phục hồi
  ngoài `hardware/pcb`. Layout KiCad sẽ cùng thư mục khi được giao triển khai.
  Dùng nhánh target hiện có, không sửa `hardware/cad` hoặc firmware đang chạy.
  Symbol GPIO/package chưa phải footprint module; không tự gán số pad/lỗ gá.
  Mô hình STBY generic chưa thay gate/E-stop/watchdog đầy đủ. Không suppress
  ERC hoặc coi bench PASS là quyền phát hành PCB/mở driver. Giữ chỉnh tay;
  generator phải từ chối ghi đè mặc định và sao lưu khi chủ động regenerate.

- Mỗi thư mục được quản lý trong Git có `README.md` giới thiệu ngắn và trạng thái.
- Root `README.md` là mục lục chính; `AGENTS.md` là nguồn quy tắc duy nhất.
- `firmware/brain`: âm thanh, Xiaozhi, OLED I²C, mạng. `firmware/motion`: PID và an toàn.
- `firmware/shared`: giao thức/kiểu dữ liệu chung, không phụ thuộc riêng một MCU.
- `fpga`: RTL đo encoder, PWM motor và watchdog; PID theo hai bên ở Motion. Viết RTL
  độc lập hãng; Quartus chỉ tham khảo cho chip Altera/Intel, Tang Nano dùng Gowin.
- Trong `fpga/rtl`, top triển khai duy nhất là `aw_car_top.sv` ở root,
  bọc lõi `drive_core.sv`; lõi vẫn được chọn làm top cho kiểm thử/tổng hợp riêng.
  Module con phân theo
  `common/`, `encoder/`, `pwm/`, `link/`, `safety/`, mỗi nhóm có README.
  Khi chuyển nguồn, cập nhật đường dẫn tổng hợp và runner tìm `.sv` đệ quy.
- Physical shell `fpga/targets/tang_nano9k/aw_car_nano9k.sv` chỉ thêm POR/mask
  reset và nối6 LED observer cho logical top trên; đây là top board của Gowin, không phải lõi truyền
  động thứ hai. Build target dùng SystemVerilog2017, không bỏ default_nettype
  none. Cổng module input dùng `wire logic` tường minh; tham số function/task
  giữ logic. Kiểm tra post-PnR encoder/STATUS để phát hiện tối ưu sai của tool.
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

## LED quan sát Nano9K

- 23 tín hiệu vật lý:17 chức năng giữ nguyên và6 LED active-low1,8V ở package
  10/11/13/14/15/16. FAULT > CONNECTED > WAITING; dùng cùng27MHz, không clock
  phụ hoặc phản hồi LED tới ARM/PWM/watchdog/gate. Chưa cấu hình/mất nguồn
  không thể hiển thị; mất clock có thể đứng hình. LED không thay E-stop.
