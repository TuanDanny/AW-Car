`timescale 1ns/1ps
module tb_encoder_pair;
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0;
    logic [1:0] left_ab = 3, right_ab = 3;
    logic [7:0] left_count, right_count, snap_left, snap_right, snap_time;
    logic [3:0] snap_seq, snap_status;
    logic snap_valid;
    encoder_pair #(.COUNT_WIDTH(8), .TIME_WIDTH(8), .SEQ_WIDTH(4),
        .FILTER_N(3), .SNAPSHOT_CYCLES(7), .INVERT_RIGHT(1)) dut (
        .clk(clk), .rst_n(rst_n), .left_ab(left_ab), .right_ab(right_ab),
        .left_count(left_count), .right_count(right_count),
        .snapshot_valid(snap_valid), .snapshot_left(snap_left), .snapshot_right(snap_right),
        .snapshot_time(snap_time), .snapshot_seq(snap_seq), .snapshot_status(snap_status));
    task settle;
        begin repeat (10) @(negedge clk); end
    endtask
    function [1:0] phase_value(input integer index);
        case (index % 4)
            0: phase_value = 0;
            1: phase_value = 1;
            2: phase_value = 3;
            3: phase_value = 2;
        endcase
    endfunction
    integer cycles = 0, snapshots = 0;
    logic [7:0] before_left, before_right, before_time;
    logic [3:0] before_seq;
    logic [7:0] last_left = 0, last_right = 0, last_time = 0;
    logic [3:0] last_seq = 0;
    // Scoreboard checks old-value snapshot semantics on every clock.
    always @(posedge clk) begin
        before_left = left_count; before_right = right_count;
        before_time = cycles & 255; before_seq = snapshots & 15;
        if (!rst_n) begin cycles = 0; snapshots = 0; end
        else begin
            cycles = cycles + 1;
            #1;
            if (snap_valid !== ((cycles % 7) == 0)) $fatal(1, "snapshot cadence");
            if (snap_valid) begin
                snapshots = snapshots + 1;
                if (snap_left !== before_left || snap_right !== before_right ||
                    snap_time !== before_time || snap_seq !== (snapshots & 15))
                    $fatal(1, "snapshot atomicity/time/sequence mismatch");
            end else if (snap_left !== last_left || snap_right !== last_right ||
                         snap_time !== last_time || snap_seq !== last_seq)
                $fatal(1, "snapshot changed outside valid");
            if ((^{left_count, right_count, snap_left, snap_right, snap_seq}) === 1'bx)
                $fatal(1, "unknown encoder outputs");
            last_left = snap_left; last_right = snap_right;
            last_time = snap_time; last_seq = snap_seq;
        end
    end
    logic [31:0] random_state;
    integer seed, k, li = 2, ri = 2, expected_left = 0, expected_right = 0;
    integer dl, dr;
    initial begin
        if ($test$plusargs("waves")) begin
            $dumpfile("tb_encoder_pair.vcd"); $dumpvars(0, tb_encoder_pair);
        end
        repeat (3) @(negedge clk); rst_n = 1;
        settle();
        if (left_count !== 0 || right_count !== 0) $fatal(1, "startup counted phase");
        // One sampled clock of noise must not change the accepted pair.
        #2; left_ab = 2; @(negedge clk); #2; left_ab = 3;
        settle();
        if (left_count !== 0) $fatal(1, "glitch changed count");
        for (seed = 1; seed <= 10; seed = seed + 1) begin
            random_state = seed;
            for (k = 0; k < 10000; k = k + 1) begin
                random_state = random_state ^ (random_state << 13);
                random_state = random_state ^ (random_state >> 17);
                random_state = random_state ^ (random_state << 5);
                dl = random_state[0] ? 1 : -1; dr = random_state[3] ? 1 : -1;
                li = (li + dl + 4) % 4; ri = (ri + dr + 4) % 4;
                expected_left = (expected_left + dl) & 255;
                expected_right = (expected_right - dr) & 255;
                // Change away from clock edge to exercise asynchronous phase.
                #2; left_ab = phase_value(li); #1; right_ab = phase_value(ri);
                settle();
                if (left_count !== expected_left[7:0] || right_count !== expected_right[7:0])
                    $fatal(1, "seed %d transition %d: count mismatch", seed, k);
            end
        end
        // Invalid two-bit jump: no invented steps; subsequent legal phase recovers.
        #2; left_ab = ~left_ab; right_ab = ~right_ab;
        settle();
        if (left_count !== expected_left[7:0] || right_count !== expected_right[7:0])
            $fatal(1, "invalid jump counted");
        repeat (10) @(negedge clk);
        if (snap_status[1:0] !== 3 || snap_status[3:2] !== 3)
            $fatal(1, "sticky/ready status missing");
        $display("PASS tb_encoder_pair: 10 seeds x 10000 transitions/wheel; snapshots and wrap");
        $finish;
    end
    initial begin #20000000; $fatal(1, "timeout tb_encoder_pair"); end
endmodule
