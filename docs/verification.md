# Kiểm chứng simplev1 — 10/11/2026

**Checkpoint quản trị mới:** [management-checkpoint.json](../data/management-checkpoint.json)
ghi hai app đã nạp/đọc ngược, tìm bằng .local/IP, log HTTPS và xác thực trên board.
Chủ dự án xác nhận Manual/STOP/OLED/AI vẫn bình thường khi đọc log. Chưa có OTA;
không chuyển kết quả log/metadata thành nghiệm thu cập nhật hoặc độ trễ toàn xe.

**Nhánh AP+STA/OTA đang phát triển:** xem [checkpoint](../data/apsta-checkpoint.json)
và [cổng kiểm thử](ota-network-plan.md). Mốc skeleton dưới đây là baseline cũ;
không dùng số đo đó để đánh dấu AP+STA/OTA mới PASS.
Đã build hai ESP, 10 bài unittest (1 bỏ qua), 17 browser test trên mô phỏng.
Motion đã nạp/đọc ngược app `simplev1-9441bc362b38`, giữ NVS/partition/motioncfg.
Brain chỉ build lại; chưa nạp thay firmware Brain. Có bản sửa IPv4-mapped IPv6
sau khi chủ dự án báo dashboard bị chặn nhầm. Đang chờ thử điện thoại/router/latency;
chưa kích hoạt migration, management log hoặc OTA.

Mốc hiện tại: source cho ba board đã build và nạp; Manual/AI có duty đúng dấu và
ACK SPI trên phần cứng thật. Các lượt log đầu giữ VM ngắt; sau đó người dùng cấp
**VM USB khoảng5V, chưa motor** và đo được bốn chiều đúng trên cầuB cả hai DRV.
Không có PIN/ARM/Gate handshake cũ. Không coi mốc này là xe đã chạy hoặc nghiệm thu
nguồn2S/PID.

## Build và kiểm thử phần mềm

| Phần | Bằng chứng | Kết quả |
| --- | --- | --- |
| Lõi C++ dùng chung | 49.180 assertion,12.000 vector SPI ngẫu nhiên,1.024 frame UART; seed731 | Đạt |
| Session AI | 127 kiểm tra trực tiếp `AiContext`; callback cũ sau STOP/mode/reconnect | Đạt |
| Python độc lập | CRC/packing đối chiếu C++, bit corruption, cấu trúc | Đạt; browser opt-in được chạy riêng |
| Browser | 17/17 ca trên native C++ simulator, desktop/mobile;31,601s | Đạt |
| Soak host | 1.800,046s;28.768 lệnh;0 bị từ chối; kết thúcManual0 | Đạt phạm vi host |
| RTL | tb_pwm_encoder, tb_spi, tb_nano9k, tb_watchdog đủ13,5triệu clock/500ms | 4/4 đạt |
| Gowin | Synthesis, PnR, STA27MHz, pin/bank/POR/2FF/latch audit | Đạt |
| Netlist sau PnR | Mô phỏng functional với primitive Gowin thật | Đạt, không SDF; timing xét bằng STA |
| KiCad | Xuất SVG/PDF/netlist native; xem A3;87pin và9đường CST đối chiếu | Đạt đấu nối logic; chưa PCB/ERC nguồn |

STA routed: Fmax57,767MHz; setup slack nhỏ nhất19,726ns, hold0,508ns;
setup/hold vi phạm0, TNS0. Chỉ một clock27MHz. Không dùng Fmax để suy độ trễ xe.

Soak localhost ACK: p50 0,5971ms; p95 1,2895ms; p99 1,4793ms; max21,3885ms.
Đây là client↔host, **không phải ESP/SPI/motor**. Runner đã lưu đủ báo cáo1800s
nhưng lần đầu lỗi in Unicode trên console cp1252 sau khi lưu; đã sửa cách in và
chạy smoke8s exit0. Không đổi lỗi console đó thành một lần chạy1800s mới.

## Firmware và Flash thật

| Board | Build đang nạp | SHA-256 app |
| --- | --- | --- |
| Brain COM3 | `simplev1-e8adbccbfcf0` | `4940a899cc720e6265bacfbd4308a9b73ff70dfdbf35beba9cf0f5b236dad714` |
| Motion COM7 | `simplev1-3196afc4efb1` | `30772cbf1014ddf8a5adb3e302204415669353ecf823f10ca3f2182e7db8c35d` |

Hai app đọc ngược SHA đúng. Giữ partition table/NVS; Brain giữ otadata, Motion
giữ motioncfg cũ. So sánh phần bảo tồn thực hiện khi app chưa chạy lại; NVS có thể
được thư viện cập nhật bình thường sau boot. Assets Brain269.890byte, SHA
`7034fc1a926ec88297cba70f58397fadc40f103e083eda92d7c7050f55938112`.

Lượt điều khiển/10phút watchdog dùng buildbcb8d4099453/71f28a456828; sau đó chỉ
chuẩn hóa whitespace/LF để hook kiểm tra đầy đủ bản nhập. Hai image ở bảng là
rebuild cùng hành vi từ source đã chuẩn hóa, được nạp/readback lại; không thay
logic điều khiển hoặc cấu hình audio giữa hai lượt.

Tang JTAGGW1NR-9C `0x1100481B`: SRAM đã thử trước, sau đó ghi embedded Flash và
ra lệnh Reprogram từ Flash. UserCode`0x0000A6C1`, status`0x0003F020`; CRC/Security
ON. Bitstream SHA`64212c9aa7f73ec7779f27e3f2fd48f7b7e3a62ae9eee3a9dffc78a0ecb4cf43`.
Không xóa khóa/OTP/user flash. ReadCodes và reload đạt; **không byte-readback FPGA**.

## Web, UART và SPI trên ba board

Người dùng mở Web do Motion host, không PIN; đối chiếu các số duty hiển thị với
console Motion (Web lấy chính snapshot đó), cùng `applied_seq` tăng từ FPGA.

| Thao tác30% | Trái | Phải | Kiểm trên board |
| --- | ---: | ---: | --- |
| Manual tiến | +405 | +405 | Đã thấy log |
| Manual lùi | −405 | −405 | Đã thấy log |
| Manual quay trái | −405 | +405 | Đã thấy log |
| Manual quay phải | +405 | −405 | Đã thấy log |
| AI tiến | +405 | +405 | Đã thấy tool và log |
| AI lùi | −405 | −405 | Log bản cuối có `action=backward`, SPI còn liên kết |
| AI quay trái | −405 | +405 | Tool/log/Web khớp; người dùng xác nhận |
| AI quay phải | +405 | −405 | Tool/log/Web khớp; người dùng xác nhận |
| Nhả/hết thời lượng | 0 | 0 | Đã thấy released/ai_complete |

AI trái/phải khoảng1s rồi về0; không xếp hàng. Lượt đầu ởManual bị từ chối đúng;
sau khi chọnAI và bắt đầu nghe mới, backend có session thật và tool được thực thi.
Giữ tiếng Trung, BOOT/Web nghe, mic, loa, OLED. Người dùng xác nhận OLED/AI vẫn
bình thường sau bản vá cuối. Lượt log sau đó đã có AI lùi−405/−405; AI tiến ở
60/80/100% có duty810/1080/1350. Người dùng chọn giữ tốc độ riêng từng lệnh,
không nêu tốc độ thì30%, không lưu mặc định mới qua câu tiếp theo.

Lượt DMM cuối ởManual100%, đỏBO1/đenBO2, không motor:

| Lệnh | DRV trái | DRV phải |
| --- | ---: | ---: |
| Tiến | +5,1V | khoảng+5,1V |
| Lùi | −5,1V | khoảng−5,1V |
| Quay trái | −5,1V | khoảng+5,1V |
| Quay phải | +5,1V | khoảng−5,1V |

Trái là số người dùng đọc; phải người dùng xác nhận đúng bốn giá trị dự kiến,
không chép từng số riêng. Lần trái0V ban đầu không tái hiện khi giữ nút lâu hơn;
nguyên nhân ban đầu chưa kết luận. Kết quả này xác nhận đường Manual đầy đủ tới
cầuH-B thật, không thay đo cầuA hoặc PWM30%. Người dùng còn xác nhận đã thử AI
và đo điện áp hoạt động đúng, nhưng chưa chép số đo riêng theo từng câu thoại.
Dữ liệu ở
`data/drv-5v-measurements.json`.

Mẫu cuối52 input: Motion timestamp nhận yêu cầu → ngay trước gọi API SPI:
p50 **248µs**, p95 **384µs**, p99/max **1.577µs**. Mẫu nhỏ này đạt mục tiêu ban đầu
5/10ms, chưa phải benchmark1.000lệnh Web trên ESP hoặc độ trễ toàn xe.
Tách driver waking1ms và đổi chiều40ms khỏi số submit này. SPI32byte ở1MHz mất
256µs trên dây; ACK trong RX là giao dịch trước.

Sau rebuild/readback cuối, người dùng tiếp tục thử Manual tới99% (duty1337/1337)
rồi nhả0. Motion ghi tổng **1.062input đã nhận**: cửa sổ256mẫu gần nhất p50
256µs, p95 **459µs**, p99 **1.671µs**; max toàn mẫu **2.627µs**. Số lấy trực tiếp
trên ESP trong task log nền, không phải localhost. Lần đọc20s cuối chỉ bao phủ
đoạn cuối phiên; không có trace từng input của toàn1.062mẫu. Đây chưa phải soak
30phút trên thiết bị. Xem `data/bench-1000-commands.json`.

## Các lỗi phát hiện và giới hạn

- Brain100Hz: `pdMS_TO_TICKS(5)` bằng0 khiến UART worker có thể spin không chờ.
  Đã ép tối thiểu1tick, không đổi tick/audio/priority hoặc tắt watchdog. OLED dùng
  I1 theo [mẫu Espressif](https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/examples/i2c_oled/main/i2c_oled_example_main.c),
  bỏ chuyển RGB565 không cần thiết. Log sau sửa:0watchdog/0panic, hơn4.000refresh,
  refresh max khoảng57,5ms; trước đó có watchdog lặp. Không coi backtrace nằm ởLVGL
  là bằng chứng duy nhất cho nguyên nhân. Xem [TWDT Espressif](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/api-reference/system/wdts.html).
- Trong506s cửa sổ trước nạpFlash:3frame SPI không hợp lệ,3ACK sau đó lệch;
  bị loại, liên kết phục hồi, không có lỗi API SPI. Chưa xác định nguồn vật lý của
  các frame lỗi; không tuyên bố bus hoàn toàn sạch. Một lỗi UART xuất hiện quanh
  lần Brain reset/nạp; sau đó không tăng trong lượt điều khiển.
- Lúc chủ động nạp/reloadFlash Tang, lỗi frame tăng vì FPGA đang cấu hình. Đây là
  một cửa sổ riêng: đã thấy link0→1, duty vẫn0, không phát lại mục tiêu cũ. Không
  trộn các lỗi có chủ đích này vào số liệu vận hành trước nạp.
- Chỉ một encoder thật ởP28, chưa gắn trục/đo vòng: RTL đã test xung, chưa nghiệm
  thu encoder trên bitstream mới bằng quay đúng vòng hoặc PID. PID giữ tắt.
- Đã đo cực tính cầuB haiDRV trên simplev1 ở100%; chưa đo cầuA/PWM bằng dụng cụ
  bắt xung hoặc điện áp30% có tải trở. Chưa motor, pin2S, giới hạn dòng, hiệu chuẩn,
  E-stop/gate vật lý. Kết quả cầuH bản cũ không được tính là phép đo mới.
- 30phút/28.768lệnh là host; soak30phút trên ESP thật vẫn còn lại. Bộ đếm thực
  đã vượt1.000input nhưng chưa có trace đầy đủ cho mọi input hoặc thời gian toàn xe.

## Nâng cấp AP+STA / OTA ngày10/11/2026

Nhánh `codex/simplev1-ota` giữ main/skeleton nguyên mốc đã duyệt. Manual vẫn
chỉ interface AP; probe từ router bị từ chối kể cả giả Host/Origin. Hai board
có HTTPS3232/mDNS và log RAM lấy mẫu. User đã xác nhận Manual/STOP, OLED và AI
bình thường khi đọc log, và hồi quy sau OTA Brain. Uploader dùng Python theo
lựa chọn tiếp của user; không ghi Arduino IDE là đã tương thích.

Brain và Motion đã nhận app qua OTA, kiểm build/ELF và boot VALID; đã thử sai
project/SHA, body bị ngắt, reset giữa truyền và bản health cố ý lỗi để rollback
thật. Motion migration USB giữ factory/NVS/motioncfg/PHY byte-for-byte, bản sao
vùng ghi giữ riêng. Log cập nhật ghi maintenance1, duty0/0, GPIO10LOW; input
pad được bật để đọc mức chân. Bản cuối không có cờ cố ý lỗi health.

Mốc này không thay SPI/FPGA/audio/PID/timeout500ms và không nghiệm thu motor/2S.
Cặp lỗi SPI frame/ACK rải rác có từ trước vẫn phải cách ly; không che cờ lỗi.
26test host (browser opt-in được skip trong discovery), 18ca browser riêng,
52.273assertion native và127context Brain đạt; cả hai firmware build được.
Soak ESP30phút/A-B và độ trễ điện thoại→PWM vẫn chưa được coi là đạt.
Xem `data/brain-ota-checkpoint.json`, `data/motion-ota-checkpoint.json` và
[hướng dẫn dùng](ota-usage.md).

## Sửa giữ nút và thời lượng AI

Người dùng báo giữ nút chập chờn trên bản OTA trước; không coi lượt nghiệm thu
đó là UI PASS dù log đã nhận đúng hướng. Đã tái hiện một nguyên nhân: client tự
hủy giữ khi bufferedAmount chỉ bận60ms. Bản sửa bỏ lần lặp khi bận ngắn, hủy giữ
nếu tắc liên tục150ms, tránh xếp MOVE/STATUS và bớt ghi DOM từ ACK lặp. Nhả/STOP
và deadline500ms không đổi. AI mặc định3giây ở cả schema Brain và Control Motion,
câu có thời gian riêng vẫn100..3000ms.

26test host và22test browser đạt; gồm tái hiện trước/sau, giữ touch3giây, tắc dài
không replay và default3giây. Hai ESP đã build/nạp, Motion readback khớp SHA,
Brain boot VALID. Xem `data/web-hold-fix-checkpoint.json`; phản hồi điện thoại
thật và log AI mới được ghi riêng, không suy từ simulator.

## Danh sách bằng chứng skeleton

`data/bench-manual.json`, `bench-ai.json`, `bench-final.json`,
`bench-flash-recovery.json` chỉ giữ command/ACK/error/latency; không có câu nói,
SSID/mật khẩu thật, MAC, NVS hay raw console. Báo cáo build/soak/FPGA và wiring
được lưu trong `data`. Log thô, backup và image nằm ở `build/private`/`build`,
không vào Git. Theo yêu cầu chốt prototype v1, main dùng nội dung simplev1; các
nhánh khác lưu phục hồi cục bộ rồi xóa. Worktree cũ giữ file ở trạng thái detached.
