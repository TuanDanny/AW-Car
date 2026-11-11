# Triển khai động tác cơ bản — source ứng viên

Ngày12/11/2026, nhánh `codex/motion-primitives-sim`, nền prototype-v2 `85a0094`.
Chủ dự án chốt dùng cả Web/AI; khi lùi, trái/phải là hướng đầu xe xoay.
Độ cong bản đầu cố định: ga bên trong bằng50% bên ngoài. Không thêm màn hình
chỉnh thuật toán, chạy tròn/số8 tự động, PID hay cảm biến ở mốc này.

## Phần đã sửa

- `esp/shared/include/simple/primitives.hpp`: ánh xạ 10 động tác và envelope
  mũ tùy chọn. Không heap, không đợi, không tạo task/timer mới.
- `Control` vẫn sở hữu deadline/STOP/đổi mode/đổi chiều/wake. Envelope chạy
  sau các kiểm tra đó; refresh20Hz không kích lại boost. Khi đổi chiều có
  neutral40ms và wake ít nhất1ms trước lần boost mới.
- Bốn ID0..4 giữ nguyên; thêm ID5..10. UART vẫn AiMove8byte/MotionState28byte,
  CRC/session-context/generation giữ nguyên. SPI32byte và toàn bộ RTL giữ nguyên.
- Web giữ bốn nút/WASD đã nghiệm thu. Thêm một nhóm thu gọn chứa sáu nút mới,
  dùng lại logic giữ/nhả/backpressure/neutral; đóng nhóm khi giữ cũng neutral.
  Không thêm phím tắt mới hoặc tự nối lại/phát lại lệnh.
- Brain dùng cùng parser tên action; vẫn một tool `self.car.move`, mặc định
  30%/3giây, mỗi câu độc lập. Context cloud và STOP ưu tiên như nền đã có.
- STATUS Web thêm `startup`, chỉ quan sát cấu hình. Không cho AI bật boost,
  ghi PWM tùy ý hoặc bỏ giới hạn thời gian.

Tại30%: tiến rẽ trái=+203/+405, tiến rẽ phải=+405/+203;
lùi đầu xoay trái=−405/−203, lùi đầu xoay phải=−203/−405;
pivot trái=0/+405, pivot phải=+405/0. Một tick sai số do lượng tử là bình thường.
Duty0 ở một bên không khóa cơ khí bánh bên đó; chưa hứa bán kính/góc chính xác.

## Đề-pa: có source, mặc định tắt

`idf.py menuconfig` → AW-Car experimental startup:

| Cấu hình | Mặc định | Ý nghĩa |
| --- | --- | --- |
| SIMPLE_STARTUP_ENABLED | n | Giữ duty trực tiếp như nền nghiệm thu |
| SIMPLE_STARTUP_GAIN_PERCENT | 100 khi bật | Hệ số100%=không boost; chưa gán số motor giả |
| SIMPLE_STARTUP_TAU_MS | 100 khi bật | Hằng số thời gian phần mềm, chưa hiệu chuẩn |

Ví dụ test167%/100ms chỉ chạy trên host, không chọn làm mặc định xe.
Với targetL/R không đổi, dùng gain chung có giới hạn sao cho không bên nào
vượt1350. Sau5*tau chốt đúng target; không có đuôi khi STOP/nhả/timeout.
Khi đổi ga đang chạy, cập nhật trực tiếp theo lệnh mới mà không tái kích timer;
không hứa profile trơn nếu người dùng chủ động thay target đột ngột.

Khi tắt không tính hàm mũ. Khi bật, chỉ tính một expf mỗi tick trong khoảng
đề-pa, không lọc toàn bộ đường input và không delay lệnh. Độ trễ trên ESP32
và dòng khởi động phải đo sau nạp; không suy từ thời gian host.
Envelope nhận biết phiên xuất lệnh0→khác0, không đo được trục đã đứng yên.
Chưa bật trên xe trước khi đo motor/tải/dòng. Nút nhả/STOP không phải phanh
cơ khí, quán tính vẫn có thể làm bánh tiếp tục quay.

## Đối chiếu và hồi quy

`test/test_primitives_native.py` gọi đúng C++ firmware qua ctypes:

- Toàn bộ11action (gồm neutral) ×101 mức ga, so số hữu tỷ Python làm tròn
  half-away-from-zero; không chỉ chép bảng output C++.
- Manual và AI cho mọi action; timeout500ms, AI3giây và trạng thái default
  startup tắt. Hết hạn về0, không xếp hàng.
- Envelope C++ so Python ở các thời điểm đều và lệch tick, hai chiều,
  quay tại chỗ, pivot và bão hòa; sai số cho phép≤0,501tick do lượng tử.
- Refresh không re-kick; STOP/release/mode/maintenance/link/cloud/deadline
  đều hủy; đổi chiều40ms +wake trước lần boost tiếp theo.

Host C++ bổ sung roundtrip tên/ID, AiMove/MotionState cho11action; mọi ID11..255
bị từ chối. Bộ SPI/UART fuzz cũ và Brain context cũ giữ nguyên assertion.

Browser dùng core C++ thật, không có mô hình phân xử JS khác. Ca27–30 bổ sung
6nút ở0/30/100%, giữ/nhả/đóng nhóm không replay, AI/generation cũ và touchCancel.
Bộ26ca cũ giữ nguyên hành vi. Lần đầu hai ca mới bấm vùng nút bị STOP dock
che; fixture đã cuộn giữa màn hình và hit-test đích, không đổi logic điều khiển
để che lỗi. Việc đóng/mở nhóm chẩn đoán cũng được làm rõ trong phép thử.

Tool build host tái dùng DLL bất biến theo hash source/compiler/options,
tránh ghi đè DLL Windows đang nạp. Biên dịch file tạm rồi đổi tên nguyên tử;
không áp dụng cache này vào flash/OTA hoặc bỏ kiểm tra source firmware.

Kết quả cuối và hash firmware build: `data/motion-primitives-verification.json`.
Các ảnh browser trong `build/primitives-browser/`, không có thông tin Wi-Fi thật.

| Kiểm tra đã chạy | Kết quả |
| --- | --- |
| Unit discovery | 54test, 1skip browser opt-in; không fail/error |
| Browser chạy riêng | 30/30PASS, gồm26ca cũ và4ca mới |
| Native C++ / Brain context | 52.872assertion /127check PASS |
| Đối chiếu action/ga C++–Python | 1.111tổ hợp khớp |
| Envelope C++–Python | max0,494235tick, giới hạn0,501tick |
| Build Brain | PASS, simplev1-84ddf7614fa1 |
| Build Motion, startup tắt | PASS, simplev1-8303ca707d06 |
| Hash source / build ID | Khớp cả2board sau build cuối |
| Repo structure / diff check | PASS |

Đã xem ảnh expanded-group desktop/mobile; không tràn ngang ở390px. Chưa đo
độ trễ phần cứng hoặc thử giọng nói cloud trên bản mới. Bộ31,416giây tròn/số8
ở hồ sơ nghiên cứu vẫn chỉ là mô phỏng, không có runner tương ứng trong firmware.

## Chạy và triển khai sau review

```powershell
python utils/build_host.py
python -m unittest discover -s test
python utils/check_repo.py
python utils/build_esp.py motion
python utils/build_esp.py brain
# Terminal riêng, dùng Python có aiohttp/Playwright:
python utils/simulator.py --port 8794
python test/browser/test_dashboard.py --port 8794 --output build/primitives-browser
git diff --check
```

Wire layout và GPIO không đổi; không phải đi dây lại. Không cần nạp lại FPGA.
Source ứng viên chưa phải firmware đang chạy trên3board. Trước khi nạp cần
VM ngắt, đúng board/manifest và giữ khóa quản trị của bản đã nghiệm thu;
không dùng key mới sinh cho build offline để vô tình thay danh tính OTA.

Mốc tiếp: thử tín hiệu không motor cho các action mới, kiểm hồi quy giọng nói
thật và giữ/nhả trên điện thoại. Sau đó mới đo motor để chọn có dùng đề-pa hay
không. Chưa merge main, chưa gọi motor/nguồn2S đã nghiệm thu từ build/mô phỏng.
