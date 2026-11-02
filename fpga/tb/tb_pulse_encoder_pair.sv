`timescale 1ns/1ps
module tb_pulse_encoder_pair;
    logic clk=0;
    always #5 clk=~clk;
    logic rst_n=0, left_out=1, right_out=1;
    logic [7:0] left_count, right_count, snapshot_left, snapshot_right, snapshot_time;
    logic [3:0] snapshot_seq;
    logic [7:0] snapshot_status;
    logic [7:0] snapshot_left_period, snapshot_right_period;
    logic [7:0] snapshot_left_age, snapshot_right_age;
    logic snapshot_valid;
    pulse_encoder_pair #(.COUNT_WIDTH(8), .TIME_WIDTH(8), .SEQ_WIDTH(4),
        .FILTER_N(3), .SNAPSHOT_CYCLES(7)) dut (.*);

    task automatic ticks(input integer n);
        repeat(n) @(negedge clk);
    endtask
    task automatic pulse_left;
        begin
            left_out=0; ticks(9);
            left_out=1; ticks(9);
        end
    endtask
    task automatic pulse_right;
        begin
            right_out=0; ticks(9);
            right_out=1; ticks(9);
        end
    endtask
    integer snapshot_count=0;
    logic [7:0] captured_left, captured_right, captured_time;
    logic [7:0] captured_lp, captured_rp, captured_la, captured_ra;
    logic [7:0] captured_status;
    // Captured snapshot must use the same pre-edge values for ALL fields.
    always @(posedge clk) if (rst_n) begin
        captured_left = left_count; captured_right = right_count;
        captured_time = dut.timestamp;
        captured_lp = dut.live_left_period; captured_rp = dut.live_right_period;
        captured_la = dut.live_left_age; captured_ra = dut.live_right_age;
        captured_status = {1'b0, dut.right_edge_seen, dut.left_edge_seen,
                          1'b1, dut.right_initialized, dut.left_initialized,
                          dut.right_period_valid, dut.left_period_valid};
        #1;
        if (snapshot_valid) begin
            snapshot_count=snapshot_count+1;
            if ({snapshot_left,snapshot_right,snapshot_time,snapshot_left_period,
                 snapshot_right_period,snapshot_left_age,snapshot_right_age,snapshot_status}
                !== {captured_left,captured_right,captured_time,captured_lp,
                     captured_rp,captured_la,captured_ra,captured_status})
                $fatal(1,"single-OUT atomic snapshot mismatch");
        end
    end
    integer i;
    initial begin
        ticks(3); rst_n=1;
        ticks(16);
        if (left_count!==0 || right_count!==0 || !snapshot_status[4])
            $fatal(1,"initial HIGH invented pulses or wrong mode");
        // A pulse shorter than FILTER_N must be rejected.
        left_out=0; ticks(1); left_out=1; ticks(12);
        if (left_count!==0) $fatal(1,"glitch counted");
        pulse_left();
        if (left_count!==1 || right_count!==0 || dut.left_period_valid!==0 ||
            dut.live_left_age === 8'hff)
            $fatal(1,"first rising edge/age invalid");
        pulse_left();
        pulse_right();
        pulse_right();
        if (left_count!==2 || right_count!==2 || !dut.left_period_valid ||
            !dut.right_period_valid || dut.live_left_period!==18 ||
            dut.live_right_period!==18)
            $fatal(1,"period/count not measured independently");
        // Saturation means stale period becomes invalid, not wrap to a new speed.
        ticks(300);
        if (dut.live_left_age!==8'hff || dut.left_period_valid ||
            dut.left_edge_seen)
            $fatal(1,"age saturation/period expiry");
        pulse_left();
        if (left_count!==3 || dut.left_period_valid)
            $fatal(1,"first after timeout must reestablish period baseline");
        pulse_left();
        if (left_count!==4 || !dut.left_period_valid)
            $fatal(1,"period did not recover after timeout");
        // Counter wrap on every single rising edge, no negative quadrature steps.
        for (i=0;i<253;i=i+1) pulse_left();
        if (left_count!==8'd1) $fatal(1,"single channel count wrap failed");
        if (snapshot_count<500 || snapshot_seq===4'bxxxx)
            $fatal(1,"missing snapshots");
        $display("PASS tb_pulse_encoder_pair: HIGH boot, filter glitch, independent edges, period/age, timeout, wrap, atomic snapshots");
        $finish;
    end
    initial begin #500000; $fatal(1,"pulse pair timeout"); end
endmodule
