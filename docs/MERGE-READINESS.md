# MERGE-READINESS — Brain+Motion0.1 LOCKED

## Cập nhật phê duyệt release05/11

Chủ dự án đã duyệt push ứng viên và sau đó duyệt chốt main theo thứ tự Brain
rồi Motion, CI main sau merge, tag `v0.1-brain-motion-locked` khi đạt.
Ứng viên `a27a098` đã đạt **5/5job CI**, gồm139root Python,110tooling Xiaozhi
Ubuntu,9Node, ghép hai core/co-sim và22RTL/four synthesis. Bằng chứng:
[Brain CI](https://github.com/TuanDanny/AW-Car/actions/runs/41961239989),
[Repository CI](https://github.com/TuanDanny/AW-Car/actions/runs/41961240000).
Brain PR13 đã squash thành `e781c6b`; Motion áp dụng lại đúng cây đã review
trong worktree riêng, chỉ cập nhật metadata release. Xem
[nhật ký release](release-v0.1-brain-motion-locked.md) cho giai đoạn chốt.

Các mục bên dưới giữ nguyên **snapshot trước push** để kiểm toán; trạng thái
PENDING/không duyệt trong snapshot không thay nhật ký phê duyệt hiện tại.
HARDWARE NOT VERIFIED và driver LOCKED vẫn giữ nguyên.

Ngày05/11/2026 (Asia/Saigon). Ứng viên cục bộ `integration/brain-motion-v0.1`.
**Chưa đề xuất merge main:** còn chờ CI đúng ứng viên và bộ tooling Ubuntu.
Mục2.9 yêu cầu người dùng duyệt trước push/merge, nên chưa push nhánh ứng viên.
Không flash, reset, mở COM, erase NVS hoặc thay cấu hình hai board trong lượt này.

## 1. HEAD và provenance

| Vai trò | HEAD đã fetch/xác minh |
| --- | --- |
| main trước tích hợp | `094b37c3246fc9037dd2c94beb7f953d588e6f6f` |
| Brain — PR13 | `fe776f0ce808770a656a98aa4c0bf302bb57f5d7` |
| Motion — PR14 | `bc272552ccd22dcb53ee53c1a3d58b465758db92` |
| FPGA v2 — chỉ peer, không merge | `7ab91b2d6119af211453a1273e3dae978d8af286` |

Cả hai merge-base với main là094b37c. Nhánh mới từ origin/main, fast-forward
đến Brain, sau đó merge Motion với resolution rõ ràng; giữ toàn bộ parent/commit
để truy nguyên. Không sửa/push các nhánh nguồn hoặc worktree FPGA/CAD đang dở.
Source PR13 có1.966file; ZIP upstream pinned49b4380 khớp SHA256 đã công bố trong
UPSTREAM.md. Đã đối chiếu đủ1.740file:1.379nguyên byte,352chỉ trailing whitespace,
9khác gồm6patch code tích hợp,2metadata và1đổi indentation. Không thiếu file;
LICENSE MIT giữ nguyên.164file AW-Car thêm được phân loại/review theo scope.
Không gọi đây là kiểm chứng toàn bộ board stock hoặc mọi thuật toán vendor.

Đối chiếu trước/sau xác nhận HEAD và status của cả4worktree nguồn không đổi.
Worktree FPGA đang có30mục dirty; hash21file dirty còn tồn tại và trạng thái
9file đã xóa giữ nguyên. Không gom các thay đổi đó vào ứng viên.

## 2. Các mức bằng chứng

| Mức | Kết quả |
| --- | --- |
| Git resolution | PASS —12conflict đã giải quyết, không còn unmerged |
| Compile | PASS —Brain AW-Car và Motion LOCKED, ESP-IDF6.1, build mới trong worktree riêng |
| Host regression | PASS —139root Python,9Node, hai core production, protocol và co-sim v2 |
| Tooling Xiaozhi Windows | 105/110PASS, 5ERROR, 0SKIP —xem giới hạn riêng |
| GitHub CI tổ hợp | PENDING —chưa push theo yêu cầu; CI nhánh nguồn không thay CI ứng viên |
| Hardware | **HARDWARE NOT VERIFIED** cho binary tích hợp |

Các binary mới chỉ nằm trong build ignored, không nạp:

- Brain app SHA256 `45328b6a45bddd88bd5d9bd348347d49d29b8b9d9dc50e28a7accc15f8ebca7d`.
- Motion app SHA256 `100109657e3727ff66b6cdc29ca817712c95257090f511b5f1c4c6adbda3882d`.
- Build dùng cấu hình profile hiện có, đã bỏ giá trị override mật khẩu khỏi
  bản sao sdkconfig cục bộ. Không dùng NVS/device dump để build; không commit
  sdkconfig/build artifacts. Không khẳng định binary giống từng byte bản trên board.

## 3. Conflict và quyết định

Không dùng merge strategy ours/theirs hoặc bỏ test. Codec BM-v1 `.h/.cc`,
contract BM-v1 và policy LED có Git blob giống nhau trên cả hai nguồn và ứng viên.
Production Brain/Motion giữ nguyên code; chỉ cập nhật README hiện hành,
dependency dev PC, workflow và branch guard để hỗ trợ integration được yêu cầu.

| File | Resolution |
| --- | --- |
| `.github/workflows/README.md` | Document all four CI jobs plus Xiaozhi job, local versus GitHub proof and separate pinned FPGA peer. |
| `.github/workflows/ci.yml` | Keep full root/Node discovery, add current-checkout Brain+Motion integration, retain baseline FPGA22/synthesis4. Remove old pinned Brain peer; install dev lock; dispatch and integration push. |
| `AGENTS.md` | Unify three feature roles and explicit user-authorized temporary integration exception; forbid push/main merge and hardware operations before approval. |
| `README.md` | Replace contradictory branch snapshots with integration candidate overview, relative MCU links, LOCKED and v1 baseline/v2 peer distinction. |
| `docs/README.md` | Union Brain and Motion evidence links; add this readiness report. |
| `docs/workflow.md` | Keep three branches and hooks; describe auditable temporary integration, approvals and two-squash rollback. |
| `firmware/README.md` | Describe both complete ESP-IDF applications in one checkout, independent config/NVS and shared codecs. |
| `firmware/shared/README.md` | One BM-v1 codec and LED policy, explicit Motion FPGA v2; v1 only baseline regression. |
| `firmware/shared/fpga-safety.md` | Retain current two-permit v2 contract from Motion, including watchdog, clear deadline, stop ACK and driver wake; remove outdated AI v1 preface. |
| `tests/README.md` | Union all Brain/Web and Motion/core/codec/co-sim test instructions. |
| `tests/test_status_indicator.py` | Same policy/cache test plus Brain UI/tool removal regression; no test removed. |
| `tools/README.md` | Retain Brain and Motion tools, distinguish native core integration from board/RTL; no board tool executed. |

Thay đổi cần thiết ngoài12conflict: branch guard nhận integration/name nhưng
vẫn chặn main; giữ test hook. Workflow Brain hỗ trợ push integration. Nâng
aiohttp dev và thêm lock10package, sửa hướng dẫn RGB cũ trong README để khớp
code đã xóa. Không đổi CRC, session, sequence, epoch, STOP, watchdog, lease,
ARM, thuật toán core, pin mapping hoặc priority firmware.

## 4. Bảo toàn tính năng và test

| Nhóm | Bằng chứng trên ứng viên |
| --- | --- |
| Brain Manual/AI, STOP/neutral/ARM/CLEAR | test_brain_core và ghép production core; đổi mode/epoch, dead-man, TTL/challenge, ACK chính xác |
| Reset/reconnect/lệnh cũ | bốn ca reset/STOP mất lúc boot; sequence/session/epoch; không tự ARM/MOVE |
| AI context và audio/OLED/BOOT | VoiceGate và MCP guard giữ nguyên; toàn bộ source profile/audio như Brain HEAD; hardware chưa thử lại |
| HTTP/WS/auth | Web tests và I/O stub1000heartbeat; cookie/Origin/1controller, stale STATUS, close/reconnect, UI không phát lại MOVE |
| AP+STA và Wi-Fi ưu tiên | reconnect policy/backoff/DHCP; test ưu tiên lưu sau reboot; network source không đổi |
| Motion safety/driver | test_motion_core, drive_model/fpga_link, native integration; build ENABLE_DRIVER=n, validated clamp giữ khóa |
| Protocol | BM-v1 SET_TWIST20/STATUS30; FPGA v2 CMD19/STATUS47; CRC/version/length/range/seq/TTL và1000vector reference |
| WS2812 | một header policy chung, mask0x88ff, cache100000vòng, retry1s, không còn tool/UI RGB demo |

Không mất test: source Brain+Motion có union **139** test ID,
candidate giữ đủ **139**, missing0.9Node test đạt.
Hai core thật digest Brainbd274b66e833/Motione87c3de279a28d70 chạy5nhóm tích hợp;
FPGA vẫn là Python peer trong bài này. Bài riêng co-sim dùng RTL v2 thật qua
UART/GPIO27MHz,430ms thời gian mô phỏng,6nhóm: boot/status, handshake/wake,
duty, STOP hai permit, mất clock, CLEAR không tự ARM. Không có FPGA vật lý.
Smoke30s **thời gian ảo**,600lệnh/fault0; không gọi là soak30phút hoặc latency xe.

### Tooling Xiaozhi trên Windows

Đã chạy đủ110test, không xóa/bỏ qua test. Lượt PATH mặc định có12ERROR/1SKIP
do compiler/shell và cleanup. Sửa môi trường của riêng lệnh chạy (Git Bash+
LLVM-MinGW) còn **5ERROR WinError32/5** do TemporaryDirectory cleanup trước
restore cwd;105PASS/0SKIP. Code test/tooling vendor không thay đổi so với
Brain HEAD và lỗi cleanup đã được ghi từ baseline. Không đổi harness để tô xanh.
CI Ubuntu ứng viên phải xác nhận110test này trước đề nghị merge. Root139test
là suite khác và đạt hoàn toàn sau nâng dependency dev.

## 5. FPGA baseline và tách v2

Toàn bộ50file cây fpga/ giống main094b37c, không nhập RTL/CAD7ab91b2. Contract/
codec v2 từ Motion giữ trong shared; không fallback v1. Co-sim v2 dùng worktree
peer pinned riêng trong build ignored. Không chạy tool trong worktree FPGA đang dở.

- Hồi quy baseline: **PASS**, 22/22test, full-timing27MHz;
  đủ15/15module có bằng chứng tham gia bài PASS. Bài dài mô phỏng2.010,544ms,
  không thay phép đo board hoặc line/branch/toggle coverage.
- Bốn tổng hợp generic Gowin/Yosys encoder/pwm/link/drive: PASS.
- Mapping generic/mô phỏng không là CST/PnR/STA Nano9K hoặc nghiệm thu gate/motor.

## 6. Security, dependency và CI

Quét pattern trên1411file text tracked không phát hiện
private key/token/credential URL theo detector đã dùng. Không có .bin/.elf/rawlog/
sdkconfig/NVS/backup tracked;668binary là asset/ảnh đã đối chiếu nguồn, gồmOGG/EAF
và ảnh tài liệu. Đây không là bảo đảm không có mọi loại bí mật hoặc bug bảo mật.

Brain có74dependency locked/73component registry:10.853file khớp CHECKSUMS.
Motion có2dependency locked/1registry:30file khớp. Không đổi lockfile MCU,
không có hash mismatch. Mỗi ứng dụng có dependency graph riêng; SDK6.1 chung.
Motion ELF không chứa entrypoint init/start Wi-Fi hoặc Bluetooth đã kiểm.

Phát hiện aiohttp3.13.2 của simulator có advisory như
[GHSA-6mq8-rvhq-8wgg](https://github.com/aio-libs/aiohttp/security/advisories/GHSA-6mq8-rvhq-8wgg).
Ứng viên nâng lên3.14.5, khóa cả10package dev và kiểm lại139test/Web. OSV query
cho10phiên bản đang dùng không trả advisory tại thời điểm audit; không suy ra
MCU dependencies đã qua toàn bộ CVE/SAST. Chỉ gửi tên/phiên bản public lên API,
không gửi source, log, credential hoặc dữ liệu board.

LICENSE upstream nguyên vẹn. LVGL có LICENCE.txt;5package registry chỉ có
license trong manifest, chưa kèm notice file: 78/uart-uhci, 78/xiaozhi-fonts, espressif/dl_fft, espressif2022/esp_emote_assets, espressif2022/esp_emote_expression.
Không sửa package để giả notice; cần rà điều kiện/notice trước phân phối binary.
Các managed components và binary đều không đưa vào commit.

CI nguồn PASS trên đúng HEAD: Brain runs41932897613/41932897759, Motion
41932900079. PR13/14 vẫn draft, không có human review/inline thread đã gửi.
CI mới: structure/hook, root+Node discovery, hai core **cùng checkout**, v2 peer
pin riêng, baseline FPGA22/Yosys4; Xiaozhi tooling Ubuntu ở brain.yml. Giữ
permissions contents:read, action SHA pin và artifact report host đã lọc.
YAML đã parse và review; chưa có GitHub run ứng viên vì chưa push được duyệt.
API branch main hiện protected=false; local hook vẫn chặn push main. Không
tự sửa quyền/ruleset của repository trong audit này.

## 7. Rủi ro và điều kiện còn lại

- Chưa có CI ứng viên/Ubuntu tooling PASS; **không duyệt merge main lúc này**.
- Binary tích hợp chưa nạp theo đúng yêu cầu. Bằng chứng UART/AI/LED trước đây
  thuộc các source HEAD riêng, không thay nghiệm thu binary mới.
- Motion vẫn LOCKED; FPGA hardware/gate/E-stop/motor, nguồn loa/1006 cũ,
  tốc độ/quãng dừng, RAM/timing FreeRTOS/I2S/Wi-Fi thật chưa kiểm lại.
- Chưa chạy lại stock-board build matrix hoặc soak Wi-Fi/audio30phút.

## 8. Diff dự kiến và rollback

Toàn bộ diff review được trong worktree bằng `git diff origin/main..integration/brain-motion-v0.1`.
Phạm vi dự kiến2.013file thay đổi, gồm1.904file dưới Brain và22file dưới Motion;
cây fpga/ thay đổi0file.668binary là ảnh/asset, không phải firmware backup.
Patch đầy đủ lưu cục bộ ở build/merge-review/main-to-candidate.patch; không
commit patch lặp toàn bộ vendor source. JSON [merge-readiness.json](merge-readiness.json)
lưu HEAD, conflict, test/build/hash, dependency và giới hạn bằng chứng.

Sau khi được phép push ứng viên, chạy đủ5job GitHub và cập nhật report theo
đúng SHA. **Phê duyệt merge main là bước riêng.** Theo trình tự đã yêu cầu:

1. Squash Brain PR13; xác nhận main CI. Không flash hoặc mở driver.
2. Tạo worktree mới cho cập nhật Motion theo main mới, giữ worktree hiện tại;
   áp dụng lại resolution/CI/dev-security delta đã review, gồm lock dev mới.
   Không chỉ nhấn merge Motion cũ rồi giả định nó giống ứng viên.
3. Chạy lại cả tổ hợp/CI; so Git tree với ứng viên được duyệt, ngoài metadata
   báo cáo. Nếu HEAD/scope đổi phải review lại. Rồi mới squash Motion PR14.
4. Xác nhận CI main, đề xuất tag v0.1-brain-motion-locked; không tạo tag trước duyệt.
5. Giữ nhánh FPGA độc lập cho milestone hardware kế tiếp.

Rollback trước merge: giữ nhánh/worktree ứng viên, main không đổi. Sau merge,
mở nhánh/PR rollback, `git revert` squash Motion rồi squash Brain; chạy CI trước
merge rollback. Không reset --hard/clean/force-push main, không xóa công việc CAD
hoặc dùng rollback source làm lệnh flash thiết bị. Mốc khôi phục source là094b37c;
nếu main có công việc mới thì review revert để bảo toàn phần không liên quan.
