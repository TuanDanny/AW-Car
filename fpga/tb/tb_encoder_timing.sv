`timescale 1ns/1ps
module tb_encoder_timing;
    logic clk = 0;
    always #18.519 clk = !clk;
    logic rst_n = 0;
    logic valid;
    logic [31:0] left_count, right_count, left_snap, right_snap, stamp;
    logic [15:0] seq;
    logic [3:0] status;
    encoder_pair dut (.clk(clk), .rst_n(rst_n), .left_ab(2'b11), .right_ab(2'b10),
        .left_count(left_count), .right_count(right_count), .snapshot_valid(valid),
        .snapshot_left(left_snap), .snapshot_right(right_snap), .snapshot_time(stamp),
        .snapshot_seq(seq), .snapshot_status(status));
    integer cycles = 0;
    initial begin
        repeat (3) @(negedge clk); rst_n = 1;
        while (cycles < 810000) begin
            @(posedge clk); cycles = cycles + 1; #1;
            if (valid !== (cycles % 270000 == 0)) $fatal(1, "default snapshot period");
            if (valid && (stamp !== cycles - 1 || seq !== cycles / 270000 ||
                          left_snap !== 0 || right_snap !== 0 || status !== 12))
                $fatal(1, "default snapshot data");
        end
        $display("PASS tb_encoder_timing: default widths and 3 x 270000-clock periods");
        $finish;
    end
    initial begin #31000000; $fatal(1, "timeout tb_encoder_timing"); end
endmodule
