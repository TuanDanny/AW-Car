`timescale 1ns/1ps
module single_out_case #(parameter int FILTER_N=3) (output logic done=0);
    logic clk=0;
    always #5 clk=!clk;
    logic rst_n=0, left_out=1, right_out=0;
    logic [3:0] left_count, right_count, snapshot_left, snapshot_right, snapshot_seq;
    logic [7:0] snapshot_time;
    logic [3:0] snapshot_status;
    logic snapshot_valid;
    // Inversion belongs only to A/B mode and must not invent a sign here.
    encoder_pair #(.COUNT_WIDTH(4), .TIME_WIDTH(8), .SEQ_WIDTH(4), .FILTER_N(FILTER_N),
        .SNAPSHOT_CYCLES(7), .INVERT_LEFT(1), .INVERT_RIGHT(1)) dut (
        .clk(clk), .rst_n(rst_n), .left_ab(2'b10), .right_ab(2'b11),
        .left_out(left_out), .right_out(right_out), .left_count(left_count), .right_count(right_count),
        .snapshot_valid(snapshot_valid), .snapshot_left(snapshot_left), .snapshot_right(snapshot_right),
        .snapshot_time(snapshot_time), .snapshot_seq(snapshot_seq), .snapshot_status(snapshot_status));
    integer cycles=0, snapshots=0;
    logic [3:0] before_left, before_right;
    logic [31:0] frozen=0;
    always @(posedge clk) begin
        before_left=left_count; before_right=right_count;
        if (!rst_n) begin cycles=0; snapshots=0; frozen=0; end
        else begin
            cycles=cycles+1;
            #1;
            if (snapshot_valid !== (cycles%7==0)) $fatal(1,"single OUT snapshot cadence N=%0d",FILTER_N);
            if (snapshot_valid) begin
                snapshots=snapshots+1;
                if (snapshot_left!==before_left || snapshot_right!==before_right ||
                    snapshot_time!==8'(cycles-1) || snapshot_seq!==4'(snapshots))
                    $fatal(1,"single OUT atomic snapshot/wrap N=%0d",FILTER_N);
                if (snapshot_status[1:0]!==0) $fatal(1,"single OUT invented A/B error");
            end else if ({snapshot_status,snapshot_seq,snapshot_time,snapshot_right,snapshot_left} !== frozen)
                $fatal(1,"single OUT snapshot changed outside valid");
            frozen={snapshot_status,snapshot_seq,snapshot_time,snapshot_right,snapshot_left};
        end
    end
    task automatic settle;
        repeat(FILTER_N+9) @(negedge clk);
    endtask
    integer k, expected_left=0, expected_right=0;
    logic [31:0] random_state=32'h35a7201d;
    logic add_left, add_right;
    initial begin
        repeat(3) @(negedge clk); rst_n=1; settle;
        if (left_count!==0 || right_count!==0) $fatal(1,"initial HIGH counted as edge N=%0d",FILTER_N);
        repeat(20) @(negedge clk);
        if (snapshot_status!==12) $fatal(1,"single OUT initialization flags");
        if (FILTER_N>1) begin
            // Both a short HIGH and a short LOW must be rejected, otherwise a
            // false extra rising edge appears after the signal returns HIGH.
            #2; left_out=0; right_out=1;
            repeat(FILTER_N-1) @(negedge clk);
            #2; left_out=1; right_out=0;
            settle;
            if (left_count!==0 || right_count!==0) $fatal(1,"N-1 glitch counted N=%0d",FILTER_N);
        end
        left_out=0; right_out=0; settle;
        for (k=0;k<2000;k=k+1) begin
            random_state=random_state^(random_state<<13);
            random_state=random_state^(random_state>>17);
            random_state=random_state^(random_state<<5);
            add_left=random_state[1]; add_right=random_state[7];
            #2; left_out=add_left; #1; right_out=add_right;
            settle;
            expected_left=(expected_left+int'(add_left))&15;
            expected_right=(expected_right+int'(add_right))&15;
            if (left_count!==4'(expected_left) || right_count!==4'(expected_right))
                $fatal(1,"single OUT pulse mismatch N=%0d step=%0d",FILTER_N,k);
            // A held HIGH must not be counted more than once.
            settle;
            if (left_count!==4'(expected_left) || right_count!==4'(expected_right))
                $fatal(1,"held HIGH counted repeatedly");
            left_out=0; right_out=0; settle;
        end
        // Reset while HIGH also re-establishes the baseline without a pulse.
        #2; rst_n=0; left_out=1; right_out=1; #1;
        if (left_count!==0 || right_count!==0 || snapshot_valid!==0)
            $fatal(1,"single OUT asynchronous reset");
        repeat(3) @(negedge clk); rst_n=1; settle;
        if (left_count!==0 || right_count!==0) $fatal(1,"reset HIGH generated pulse");
        left_out=0; right_out=0; settle;
        left_out=1; right_out=1; settle;
        if (left_count!==1 || right_count!==1) $fatal(1,"first real pulse after reset missing");
        done=1;
    end
endmodule

module tb_encoder_single_out;
    logic [2:0] done;
    single_out_case #(.FILTER_N(1)) n1 (.done(done[0]));
    single_out_case #(.FILTER_N(3)) n3 (.done(done[1]));
    single_out_case #(.FILTER_N(5)) n5 (.done(done[2]));
    logic clk=0;
    always #5 clk=!clk;
    logic rst_n=0, sample_valid=0, pulse=1, initialized;
    logic [3:0] count;
    pulse_counter #(.COUNT_WIDTH(4)) unit_dut (.*);
    task automatic sample(input logic level, input logic valid_sample);
        @(negedge clk); pulse=level; sample_valid=valid_sample;
        @(posedge clk); #1;
    endtask
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        sample(1,0);
        if (count!==0 || initialized) $fatal(1,"invalid sample initialized counter");
        sample(1,1);
        if (count!==0 || !initialized) $fatal(1,"first HIGH must only initialize");
        sample(0,0); sample(1,1);
        if (count!==0) $fatal(1,"invalid LOW altered previous sample");
        sample(0,1); sample(1,0); sample(1,1);
        if (count!==1) $fatal(1,"edge across valid gap not counted exactly once");
        sample(0,0); sample_valid=0;
        wait (&done);
        $display("COVER encoder_single_out.random_pairs 6000");
        $display("COVER encoder_single_out.filter_configs 3");
        $display("PASS tb_encoder_single_out: one rising edge/pulse, N=1/3/5, startup/glitch/wrap/reset/snapshots");
        $finish;
    end
    initial begin #2000000; $fatal(1,"timeout tb_encoder_single_out"); end
endmodule
