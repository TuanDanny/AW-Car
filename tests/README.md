# Kiểm thử

`test_awcar_schematic.py` chạy KiCad CLI thật để round-trip schematic,
kiểm contract và negative cases: sai UART, nối GND loa BTL, chập hai cầu H,
bỏ chuyển mức encoder, nối rail3V3, STBY nối VM, đảo chân transistor, chập
I2C cảm biến và nối tắt cầu chì. Bài xóa nhãn rồi xuất lại bằng KiCad xác nhận
dây tín hiệu thật sự nối pin với pin, không chỉ dùng nhãn ở các khối tách.
Các ca mới chặn bypass jumper, đảo tụ điện phân, tụ phân cực qua motor,
đưa tụ motor lên carrier và sai định mức tụ bulk. Khổ giấy A3 và hướng
input/output/nguồn/GND được kiểm trên source native.
Nếu thiếu KiCad CLI thì ghi SKIP; không gọi ERC hoặc mô phỏng phần cứng là
đạt từ các unit test này. Schematic vẫn là bản review chưa có quyền đi PCB.

Hiện có test công cụ kiểm tra kho: README thư mục, snapshot đã stage, file ignore,
tên nhánh và hook chặn commit/push vào main. Test dùng kho Git tạm, không push
lên GitHub. Chạy bằng `python -m unittest discover -s tests`.
Kiểm tra đuôi HDL bắt buộc `.sv` cho cả RTL/testbench, cả worktree và index;
netlist trong build đã ignore không bị áp quy tắc nguồn.

Chưa có test firmware/phần cứng. Khi thêm tính năng, đặt test tương ứng tại đây
hoặc trong project MCU nếu bộ test ESP-IDF yêu cầu, rồi ghi lệnh chạy thực tế.

`test_tang_nano9k.py` kiểm đủ17 cổng và negative cases: đổi pin/bank/điện áp,
pin trùng, GPRJ bỏ source, blanket false-path và report thiếu dữ liệu. Không
cần Gowin hoặc board để chạy unit tests. Mapped functional test riêng nằm tại
target Nano9K và dùng netlist thật sau PnR; không biến unit PASS thành hardware PASS.

`test_fpga_runner.py` kiểm tra runner không bỏ qua compile lỗi, mã lỗi simulator
hoặc timeout; kiểm tra đường dẫn tool tương đối và môi trường subprocess.
Đồng thời kiểm tra compiler nhận đủ nguồn `.sv`, tùy chọn SystemVerilog và
`--full-timing` thực sự chọn clock danh định cho bài top2s.
Nguồn thử gồm top ở root, module lồng nhiều cấp và helper ngoài `rtl/` để
phát hiện runner bỏ sót thư mục con hoặc lấy nhầm nguồn testbench.
Test thêm registry đủ testbench, inventory module bỏ qua comment/trùng tên,
kiểu module từ VVP, marker PASS, JSON/hash và failure khi module mới chưa có
bài kiểm thử. Module của test lỗi không được tính là đã có bằng chứng PASS.
Test RTL thực nằm ở [fpga/tb](../fpga/tb/README.md), chạy riêng
bằng `python tools/run_fpga_tests.py` và được yêu cầu trong CI.

`test_fpga_protocol.py` kiểm tra layout/endianness, CRC chuẩn và vector Motion–
FPGA chung; reference dùng thư viện Python thay vì gọi lại hàm CRC của RTL.

`test_fpga_protocol.py` có cả v1/v2, kiểm tra field offset/CRC/độ dài và
từ chối phối nhầm STATUS18/34 byte. `test_aw_car_cad.py` và
`test_awcar_pcb_sources.py` kiểm project một trang, thư viện cục bộ và bảo vệ
source chỉnh tay khi chạy generator. Test concept PCB cũ đã bỏ cùng concept;
CAD cơ khí không thay đổi. Các kiểm tra này không chứng minh lắp vừa hoặc
sơ đồ điện an toàn trên xe thực.
