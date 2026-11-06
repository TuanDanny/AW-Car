# Flash và liên kết ba board — 06/11/2026

Kiểm tra trên nhánh `feat/f01-tang-nano9k-target`, nền tài liệu09870cd,
implementation30d45ed. Người dùng giao hai mốc: lưu AW-Car sau mất nguồn và
kiểm tra reset/mất liên kết. Brain/Motion giữ firmware main4cea85c, Motion
LOCKED/validated0; gate/E-stop chưa có, không thử công suất.

## Nhận diện và đầu vào

- Tang: GW1NR-9C, ID0x1100481B, USB Debugger A/0/location529 tại lần scan này.
  Phải scan lại trước lần nạp sau; COM11 là USB UART, không phải địa chỉ JTAG.
- Brain COM3, Motion COM7. UART ứng dụng MotionTX15→TangRX25,
  TangTX26→MotionRX16, GND chung; BrainTX17→MotionRX14 và ngược TX13→RX18.
-24 file nguồn/constraint và4 artifact khớp SHA256 của báo cáo LED đã đạt.
  BitstreamSHA256: `23304499f5c36af116a5b78d1f75a73e17356bd0fb7024d83b81fc5f5b7092c2`.
  UserCode dự kiến0x00009EF7; CRC ON, SecurityBit ON, không đổi bitstream.
- STA/netlist dùng lại bằng chứng cùng artifact, không tuyên bố chạy lại36
  testbench. Các log console thô giữ private trong build vì có thể chứa mạng.

## Mốc1: lưu Flash

Gowin Programmer1.9.11.03 Education, operation6 `embFlash Erase,Program,Verify`.
Không dùng SPI Flash ngoài, không nạp `.fi`, không thao tác khóa/OTP. Đây là
ghi Flash được người dùng cho phép06/11, khác các lượt SRAM trước đó.

**Kết quả verify đọc lại: FAIL.** CLI trả native exit0 nhưng log có
`Verify Failed at 0` và `Verify Failed`; không gọi đây là verify PASS.
Programmer tiếp tục báo Program Finished, UserCode0x9EF7 và status0x3F020.
Giữ nguyên bảo vệ đọc lại; không tắt SecurityBit để che kết quả này.

Đã chạy operation1 `Reprogram`, là nạp lại cấu hình từ Flash vào SRAM theo
SUG502 trang15. Sau đó operation0 trả ID0x1100481B, UserCode0x9EF7 và
status0x3F020. UART STATUS hoạt động lại. Đây là bằng chứng reload/chức năng,
không phải so byte toàn bộ Flash. UG290 phần bảo vệ dữ liệu ghi rằng đọc
SRAM có security bị cấm và đọc Flash sau AUTOBOOT bị cấm; khả năng bảo vệ
liên quan tới lỗi verify được ghi riêng, chưa kết luận chỉ từ exit code.

Đã xóa riêng SRAM bằng operation24, giữ FPGA chưa cấu hình khoảng12s rồi
chạy operation1 mà không cung cấp file `.fs`. Motion báo fresh=false trong
cửa sổ chưa cấu hình, sau đó nhận snapshot mới và read codes vẫn0x9EF7/
0x3F020. Phép này xác nhận image Flash có thể tự nạp vào SRAM, chưa thay phép
mất nguồn thật. Lượt sau reload nhận17.013 frame/170,185s, khoảng99,968Hz.

**Power-cycle thật: PASS chức năng.** Người dùng xác nhận đã làm thao tác rút
USB cả ba board/chờ10s/cắm lại. Lượt sau chỉ scan và operation0 đọc mã, không
nạp SRAM, không Reprogram và không ghi Flash: ID0x1100481B, UserCode0x9EF7,
status0x3F020. Motion nhận STATUS mới, snapshot tăng và fresh=true. Như vậy
bản AW-Car tự khởi động từ Flash sau mất nguồn. Việc LED tắt hết/mất nguồn
dựa xác nhận người dùng; không có phép đo rail nguồn bằng oscilloscope.
Kết quả verify đọc lại FAIL ở lượt ghi ban đầu vẫn được giữ riêng.

## Mốc2: reset và mất liên kết

| Phép thử | Kết quả hiện có |
| --- | --- |
| FPGA→Motion trước lượt Flash | 3.500 frame v2/35s, khoảng100Hz; parser/HW errors0 ở lượt trước |
| Xóa SRAM/để trống12s, reload từ Flash | fresh=false rồi true, snapshot chạy lại; permit/duty giữ0 |
| Brain nhận Motion | STATUS khoảng20Hz, dữ liệu tiếp tục cập nhật |
| Giữ Motion reset8s rồi thả | Brain age lên6.693ms, STATUS dừng tăng; sau boot phục hồi, không tự ARM |
| Reset Brain USB-Serial-JTAG | Có boot reason0x15 và STATUS mới; Motion vẫn permit/duty0 |
| Rút TangTX26→MotionRX16 | fresh=false; snapshot/frame đứng yên; permit/duty0 |
| Nối lại TangTX26→MotionRX16 | fresh=true, snapshot/frame tăng; chốt Gate vẫn giữ, không tự ARM |
| Rút MotionTX13→BrainRX18 | Brain STATUS đứng yên, age vượt20s; Motion tiếp tục permit/duty0 |
| Nối lại MotionTX13→BrainRX18 | STATUS tăng lại, age về dưới150ms; Motion permit/duty0, không tự ARM |
| Motion→FPGA và ARM/recovery đầy đủ | Chưa có ACK/fixture; LOCKED và health/gate LOW không được nối giả để thử |

**Mốc2 là PARTIAL, chưa nghiệm thu ổn định hoàn toàn.** Lượt console tần
suất1Hz có tăng parser_errors phía Motion nhận FPGA. Đã giảm hỏi console
xuống mỗi5s; sau reload ổn định170,185s vẫn tăng5 parser_errors, HW errors0,
queue drops0. Vì lỗi có cả ngoài cửa sổ reconfigure/reset, không quy toàn bộ
cho việc nạp hoặc hỏi console. Chưa xác định timeout/parser, dây hay lập lịch;
không tăng deadline hay bỏ CRC để làm số lỗi biến mất. Cần chẩn đoán nguyên
nhân bằng counter nguyên nhân và/hoặc trace UART trước khi chốt mốc2.

404 mẫu console ở lượt trước đều có driver/logical permit readback0, duty0.
Brain UART errors0 trong các mẫu health đầy đủ. Có1 dòng Brain bị log khác
chen ngang nên thiếu trường; loại khỏi thống kê age, ghi số lượng trong JSON,
không thay dữ liệu thiếu bằng0. Chưa có Dashboard client trong lượt này.

Lượt sau power-cycle đã kiểm tra cả hai dây STATUS vật lý, rút/nối từng dây
theo xác nhận người dùng, không reset hay nạp để phục hồi. Khi TangTX26 bị
rút khỏi MotionRX16: count frame/snapshot đứng, fresh=false. Khi nối lại:
fresh=true, snapshot mới chạy tiếp. Khi MotionTX13 bị rút khỏi BrainRX18:
STATUS ở Brain đứng; age ghi nhận tới86.640ms trong cửa sổ mất dây. Nối lại
STATUS tăng, age dưới150ms. Motion vẫn nhận thêm frame hợp lệ từ Brain theo
chiều còn lại, HW/parser phía Brain–Motion0 ở các mẫu đọc. Chốt gate vẫn giữ,
không tự CLEAR/ARM. Tất cả dây UART đã được người dùng xác nhận nối lại.

Lỗi parser phía Motion nhận FPGA vẫn xuất hiện cả sau power-cycle; không
đánh dấu vấn đề này đã sửa nhờ ghi Flash. Lượt nối đủ cuối, số đo thời gian/
frame/lỗi và wrap sequence thực nằm trong `post_power_cycle` của JSON. Các
phép mất dây/phục hồi đạt hành vi trong LOCKED; mốc ổn định toàn liên kết vẫn
PARTIAL. Chưa thử điều khiển xe từ ARMED hay đo deadline cắt chân bằng analyzer.

Chốt lượt sau power-cycle:113 mẫu Motion, tổng517 mẫu hai lượt, tất cả
permit/duty0. Lượt nối đủ cuối16.514 frame/165,198s, khoảng99,965Hz; HW errors0,
queue/TX drops0, parser_errors tăng6→11. Brain age17–43ms, UART errors0.
Đã quan sát snapshot_seq wrap65509→474 giữa hai mẫu cách5,004s và fresh vẫn
true. Không thấy chữ ký panic/brownout trong log thu được. Đã đóng monitor,
ba board giữ nguyên image và dây kết nối; không tự CLEAR/ARM hoặc thay NVS.

Mẫu đo dùng console read-only `status`, `uart`, `config`, log COM3 và đồng hồ
đơn điệu trên PC. Quan sát `fresh`, sequence, lỗi, state, duty, driver_gpio và
logical_gpio. Log PC/console không thay logic analyzer, không đo được xung
permit ngắn hoặc deadline thực30ms từ khi frame cuối tới chân driver.

Tất cả phép thử ở LOCKED không chứng minh dừng từ ARMED. Reset/mất UART phải
giữ không tự ARM/MOVE; dữ liệu hồi phục không tự xóa chốt lỗi thiếu gate.
Encoder, GPIO recovery, gate/E-stop, PWM pad và motor chưa nghiệm thu.

## Nguồn và log

- Manual cài tại máy: SUG502-2.2.1E trang15, UG290-2.8.1E phần3/7/8.
- Hướng dẫn Sipeed: <https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/examples/led.html#other>.
- Log/operation/monitor riêng: `build/tang-nano9k/flash-link-20261106/`.
- Bằng chứng trước lượt này: `build/tang-nano9k/uart-bringup-20261106/link-check.json`.
- [JSON số đo đã lọc và hash log](../../../docs/fpga-flash-link-evidence.json).
- Lượt sau mất nguồn và rút/nối dây: `build/tang-nano9k/flash-link-20261106/post-powercycle-01/`.
- Kiểm tra repo,57 root Python tests và diff check đạt; không có thay đổi RTL.

Không tự push/merge; việc ghi Flash không thay source RTL, image hai ESP32,
NVS/motioncfg, cấu hình mạng hoặc quyền mở driver.


## Bổ sung: sửa UART và kiểm tra kết quả Programmer

Các số liệu/parser chưa đạt bên trên là lịch sử của firmware Motion cũ,
không bị ghi đè. Lượt sửa06/11 dùng nhánh Motion riêng, giữ Brain và RTL.
Đã tái hiện timeout từ API read có chờ của ESP-IDF, sửa read0 sau event;
sửa lấy đồng hồ sau dequeue để không bỏ nhầm event mới; sửa rediscovery khi
FPGA reset ở các pha seq/timestamp khác nhau. Chỉ rebaseline sau khi revoke,
STATUS stale và hai candidate session0 cùng tiến trong<30ms, không tự ARM.
Số đo và commit Motion cuối được bổ sung ở báo cáo sửa UART riêng.

`tools/gowin_programmer_result.py` phân tích log ngữ nghĩa cùng native exit.
Log operation6 trước đây được regression test phân loại `FAIL_VERIFY`, dù
configuration status hợp lệ, Program Finished và native exit0. Timeout,
output thiếu/cắt, wrong device/UserCode, status lỗi hoặc thiếu completion
đều không PASS. Op1 phải có op0 riêng sau reload, không suy VALID từ việc
Reprogram hoàn tất. Công cụ không chạy Programmer hoặc truy cập hardware.

Đường nạp đề xuất cho debugger Tang này dùng operation5 `embFlash
Erase,Program`, sau đó op0 kiểm ID/UserCode/status và quan sát UART. Sipeed
khuyến cáo tránh operation chứa Verify và dùng<=2,5MHz ở [troubleshooting
Programmer](https://wiki.sipeed.com/hardware/en/tang/common-doc/questions.html#Download-slowly).
Đây là hướng dẫn chọn workflow, **không chứng minh nguyên nhân chính xác**
của Verify Failed. UG290 có phân biệt đọc SRAM bị bảo vệ và chế độ đọc
embedded Flash; không khẳng định mọi embedded Flash verify đều bị security
chặn. Không tắt CRC/Security để làm đẹp kết quả.

Workflow op5 ghi `readback_verify=NOT_REQUESTED`; cấu hình VALID và UART
chạy không có nghĩa so byte Flash thành công. Lỗi verify đọc lại ở lượt
operation6 lịch sử vẫn là FAIL. Kết quả lượt workflow mới lưu riêng, không
nối nhiều operation vào một log rồi gọi chung là PASS.


Lượt workflow đã chạy trên board: scan lại USB Debugger A/0/location529,
đối chiếu SHA256 image, op0 trước nạp đạt; op5 hoàn tất7,99s, op0 sau nạp
đạt ID0x1100481B, UserCode0x00009EF7, status0x0003F020. CRC/Security giữ ON;
không OTP/key/userflash. Ba operation đều phân loại PASS trong đúng phạm vi,
`readback_verify=NOT_REQUESTED`. [JSON đã lọc và hash log](../../../docs/fpga-programmer-workflow-evidence.json).
78/78 root tests đạt, gồm21 test phân loại Programmer. Không chạy lại Gowin
synthesis/PnR/STA vì RTL/constraint/artifact không đổi trong lượt sửa này.


Chốt bản sửa Motion: `codex/esp32-s3-motion` commit `4af21b8`, đã nạp COM7,
NVS/PHY/motioncfg so byte không đổi. Bản cuối chạy62.072 frame/620,725s ở
100Hz, parser/HW/queue/TX/log drops0,125 mẫu Motion đều fresh và permit/duty0.
Giữ Motion reset8s làm Brain age lên6.510ms rồi phục hồi; reset Brain cũng
nhận lại STATUS. Ghi lại FPGA/op5 quan sát fresh=false→true. Reprogram từ
Flash ở pha counter tiếp theo quan sát seq14.130→354 và fresh phục hồi,
fault Gate1 vẫn giữ; có1 timeout partial33byte đúng lúc tái cấu hình,
không tăng tiếp trong65,079s sau đó. Không tự CLEAR/ARM/MOVE.

[JSON số đo sửa UART/queue/reboot](../../../docs/fpga-uart-repair-evidence.json)
ghi branch/commit/hash firmware, các phase riêng và giới hạn; báo cáo đầy đủ
ở `docs/motion-uart-receive-fix.md` trên nhánh Motion. Root Motion147 tests:
134 đạt,13 Web tests skip vì môi trường thiếu dependency. Hai core tích hợp
5/5checks và co-sim Motion+RTL thực27MHz6/6checks đạt. Không dùng các phép
LOCKED/console để nghiệm thu dừng từ ARMED, waveform pad hay motor thật.
Monitor đã đóng, dây đủ; thiếu gate/E-stop vẫn khóa đúng. Không đổi RTL,
Brain, protection hoặc nhánh main; source sửa và bằng chứng lưu ở hai nhánh
riêng, chưa push.
