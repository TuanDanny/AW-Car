# Milestone v0.1-brain-motion-locked

Mốc phần mềm Brain+Motion LOCKED theo phê duyệt05/11/2026. Git tag chỉ được
đặt trên main sau khi CI main cuối đạt; source trên board không đổi trong release.
Không có firmware binary/NVS/raw log hoặc credential được phát hành kèm tag.

## Nguồn và bằng chứng trước release

| Vai trò | Commit |
| --- | --- |
| main trước milestone | 094b37c3246fc9037dd2c94beb7f953d588e6f6f |
| Brain đã review | fe776f0ce808770a656a98aa4c0bf302bb57f5d7 |
| Motion đã review | bc272552ccd22dcb53ee53c1a3d58b465758db92 |
| Ứng viên tích hợp | a27a098c733fa487b20fbaaca2c6743eadacdbd0 |
| Brain squash PR13 | e781c6bc70cb995c2f4cc00a80d2b529b3066612 |
| FPGA v2 chỉ dùng làm peer | 7ab91b2d6119af211453a1273e3dae978d8af286 |

Ứng viên đạt5/5job CI:139root Python,110Xiaozhi tooling Ubuntu,9Node,
hai core production/co-sim v2,22bài RTL full-timing27MHz và4bài tổng hợp generic.
[Brain CI](https://github.com/TuanDanny/AW-Car/actions/runs/41961239989),
[Repository CI](https://github.com/TuanDanny/AW-Car/actions/runs/41961240000).
Build ESP-IDF6.1 cho Brain AW-Car/Motion LOCKED đã đạt ở cùng code/config
được ghi trong [báo cáo merge](MERGE-READINESS.md), không phải build MCU trên CI.

## Trình tự chốt và cách đối chiếu

1. Squash Brain PR13; giữ parent main094b37c và tree Brainfe776f0.
2. Ghép main mới vào Motion ở worktree riêng. Trước metadata release, toàn bộ
   tree được so giống hệt a27a098. Áp dụng resolution/CI/dev lock đã review,
   không chọn ours/theirs toàn bộ protocol hoặc bỏ test.
3. Đối chiếu runtime/config/lock/codec/dashboard/RTL không đổi so với a27a098,
   chạy lại host checks và CI PR14. Chỉ squash Motion khi CI tổ hợp đạt.
4. Chạy lại CI trên main sau Motion squash, xác nhận không có thay đổi main
   ngoài phạm vi được duyệt; rồi tạo annotated tag v0.1-brain-motion-locked.

Main SHA sau cùng được xác định bằng Git tag, không ghi SHA tự tham chiếu trong
commit này. Hai squash commit có thể tra ở [PR13](https://github.com/TuanDanny/AW-Car/pull/13)
và [PR14](https://github.com/TuanDanny/AW-Car/pull/14). CI cuối tra theo đúng SHA
tag tại [Actions main](https://github.com/TuanDanny/AW-Car/actions?query=branch%3Amain).
Phải dùng run event push/main ở SHA sau merge, không lấy PR synthetic merge làm
bằng chứng CI main. Các kết quả sau commit này được ghi trong Git tag và log CI.

## Phạm vi ổn định

Brain giữ Xiaozhi/AP+STA, mic/OLED/loa/BOOT, Dashboard Manual/AI, auth/Origin/
WebSocket và phục hồi không tự ARM. Motion giữ hai UART13/14 và15/16, lease,
STOP/neutral/CLEAR, hai đường permit và source driver mặc định LOCKED.
BM-v1/FPGA v2, CRC/session/sequence/epoch/deadline không đổi. WS2812 GPIO48
chỉ báo trạng thái; code demo RGB AI/Web đã xóa trước mốc này. Dev simulator
aiohttp3.14.5 và lock10package giữ bản đã test trong ứng viên.

Toàn bộ cây fpga/ giữ baseline main094b37c; FPGA v2 chỉ là peer riêng khi co-sim,
không nhập RTL/CAD hoặc công việc chưa commit của worktree FPGA. Không force-push,
không reset/clean worktree nguồn và không tự xóa nhánh phát triển.

## Giới hạn phần cứng và rollback

**HARDWARE NOT VERIFIED cho binary tích hợp.** Không flash/reset/mở COM, erase
NVS hoặc nâng quyền driver trong quy trình release. Bằng chứng UART/AI/LED trước
đó thuộc các source branch riêng. FPGA gate/E-stop/motor, PnR/STA Nano9K, nguồn
loa/rè và lỗi1006 cũ chưa được nghiệm thu bởi tag này. PID/cảm biến ở mốc sau.

Nếu cần rollback source, mở PR `git revert` squash Motion rồi squash Brain,
chạy CI và review để bảo toàn thay đổi khác sau milestone. Không reset/force-push
main hoặc di chuyển tag đã công bố. Rollback source không tự flash thiết bị.
