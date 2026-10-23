`timescale 1ns/1ps
module tb_frame_tx;
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0, flush = 0, snapshot_valid = 0;
    logic snapshot_ready, snapshot_dropped, byte_valid, byte_ready = 0;
    logic [7:0] byte_data;
    logic [31:0] session = 32'h12345678, snapshot_left = 32'h10203040;
    logic [31:0] snapshot_right = 32'hffeeddcc, snapshot_time = 32'h56789abc;
    logic [15:0] snapshot_seq = 16'h4321, fault = 16'h100;
    logic [3:0] snapshot_status = 12;
    logic [7:0] safety_state = 2;
    frame_tx dut (.*);
    logic [255:0] vectors [0:6];
    logic [255:0] expected;
    logic [7:0] held_data;
    logic was_stalled = 0;
    integer count = 0, drops = 0;
    logic check_bytes = 1;
    always @(posedge clk) begin
        if (rst_n && !flush) begin
            if (was_stalled && (!byte_valid || byte_data !== held_data)) $fatal(1, "TX changed under backpressure");
            if (byte_valid && byte_ready && check_bytes) begin
                if (byte_data !== expected[count*8 +: 8]) $fatal(1, "snapshot/CRC byte %d corrupt", count);
                count = count + 1;
                if (count == 31) count = 0;
            end
        end
        was_stalled = rst_n && !flush && byte_valid && !byte_ready;
        held_data = byte_data;
        #1;
        if (snapshot_dropped) drops = drops + 1;
    end
    task automatic submit;
        begin
            @(negedge clk); snapshot_valid = 1;
            @(negedge clk); snapshot_valid = 0;
        end
    endtask
    integer i, j, saved;
    logic [31:0] rng = 32'h63529a8b;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_frame_tx.vcd"); $dumpvars(0, tb_frame_tx); end
        $readmemh("../../firmware/shared/fpga-vectors.hex", vectors); expected = vectors[6];
        repeat (3) @(negedge clk); rst_n = 1;
        submit;
        // Every source field changes while the frozen frame is stalled.
        session = 0; snapshot_left = 1; snapshot_right = 2; snapshot_time = 3;
        snapshot_seq = 4; snapshot_status = 5; safety_state = 6; fault = 7;
        submit;
        if (drops != 1) $fatal(1, "busy snapshot not reported");
        repeat (50) @(negedge clk);
        for (i = 0; i < 500 && !snapshot_ready; i = i + 1) begin
            rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
            byte_ready = rng[0]; @(negedge clk);
        end
        byte_ready = 0;
        if (!snapshot_ready || count != 0) $fatal(1, "TX failed to finish under random stalls");
        // Flush/reset at each serializer position must discard the pending frame.
        check_bytes = 0;
        for (j = 0; j < 31; j = j + 1) begin
            submit;
            byte_ready = 1;
            repeat (j) @(negedge clk);
            byte_ready = 0; flush = 1; snapshot_valid = 1;
            @(posedge clk); #1;
            if (byte_valid || snapshot_ready) $fatal(1, "flush did not mask interface");
            @(negedge clk); flush = 0; snapshot_valid = 0;
            @(posedge clk); #1;
            if (!snapshot_ready || byte_valid) $fatal(1, "flush retained old frame");
            submit; byte_ready = 1;
            repeat (j) @(negedge clk);
            byte_ready = 0; rst_n = 0;
            @(negedge clk); rst_n = 1;
            if (!snapshot_ready || byte_valid) $fatal(1, "reset retained old frame");
        end
        // A new coherent snapshot still serializes correctly after all aborts.
        session = 32'h12345678; snapshot_left = 32'h10203040; snapshot_right = 32'hffeeddcc;
        snapshot_time = 32'h56789abc; snapshot_seq = 16'h4321; snapshot_status = 12;
        safety_state = 2; fault = 16'h100; count = 0; check_bytes = 1;
        submit; byte_ready = 1;
        repeat (32) @(negedge clk);
        if (!snapshot_ready || count != 0) $fatal(1, "TX recovery frame missing");
        $display("PASS tb_frame_tx: shared STATUS vector, frozen snapshot, backpressure/drop, flush/reset at all 31 positions");
        $finish;
    end
    initial begin #100000; $fatal(1, "frame TX timeout"); end
endmodule
