`timescale 1ns/1ps
module tb_pwm_timing;
    logic clk = 0;
    always #18.519 clk = !clk;
    logic rst_n = 0, enable = 0, valid = 0;
    logic [15:0] l = 675, r = 1350;
    logic [1:0] requested_direction = 0;
    logic pl, pr, interlock, rejected;
    logic [1:0] direction;
    motor_pwm_pair dut (.clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(valid),
        .command_left(l), .command_right(r), .command_direction(requested_direction),
        .pwm_left(pl), .pwm_right(pr), .direction(direction),
        .interlock_active(interlock), .command_rejected(rejected));
    logic thirty_left, thirty_right, thirty_hold, thirty_rejected;
    logic [1:0] thirty_direction;
    motor_pwm_pair #(.ZERO_CYCLES(810000)) thirty_ms (
        .clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(valid),
        .command_left(l), .command_right(r), .command_direction(requested_direction),
        .pwm_left(thirty_left), .pwm_right(thirty_right), .direction(thirty_direction),
        .interlock_active(thirty_hold), .command_rejected(thirty_rejected));
    // Minimum supported parameters exercise width calculations and single-cycle waits.
    logic min_left, min_right, min_hold, min_rejected;
    logic [1:0] min_direction;
    motor_pwm_pair #(.PERIOD_CYCLES(1), .ZERO_CYCLES(1), .SETUP_CYCLES(1)) minimum (
        .clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(valid),
        .command_left(16'd1), .command_right(16'd0), .command_direction(requested_direction),
        .pwm_left(min_left), .pwm_right(min_right), .direction(min_direction),
        .interlock_active(min_hold), .command_rejected(min_rejected));
    integer i, high_count;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_pwm_timing.vcd"); $dumpvars(0, tb_pwm_timing); end
        repeat (3) @(negedge clk); rst_n = 1;
        @(negedge clk); enable = 1; valid = 1;
        @(posedge clk); #1;
        if (!pl || !pr || min_left !== 1 || min_right !== 0) $fatal(1, "first PWM slot");
        @(negedge clk); valid = 0;
        high_count = 1;
        for (i = 1; i < 1350; i = i + 1) begin
            @(posedge clk); #1;
            high_count = high_count + pl;
            if (pl !== (i < 675) || pr !== 1 || min_left !== 1 || min_right !== 0)
                $fatal(1, "27MHz PWM duty edges");
        end
        if (high_count != 675) $fatal(1, "27MHz HIGH slot count");
        @(posedge clk); #1;
        if (!pl || !pr) $fatal(1, "20kHz period boundary");
        @(negedge clk); valid = 1; requested_direction = 3;
        @(posedge clk); #1;
        if (!interlock || pl || pr || min_left) $fatal(1, "direction did not blank");
        @(negedge clk); valid = 0;
        for (i = 1; i <= 1080000; i = i + 1) begin
            @(posedge clk); #1;
            if (pl || pr) $fatal(1, "PWM during 40ms zero wait");
            if (direction !== ((i < 1080000) ? 0 : 3)) $fatal(1, "zero wait length");
            if (thirty_direction !== ((i < 810000) ? 0 : 3)) $fatal(1,"30ms zero wait length");
            if (i<=810027) begin
                if (thirty_left || thirty_right) $fatal(1,"30ms PWM before zero/setup complete");
            end else if (thirty_right!==1 ||
                thirty_left!==(((i-810028)%1350)<675) || thirty_hold)
                $fatal(1,"30ms duty/resume after exact zero/setup deadline");
            if (i >= 4 && (min_direction !== 3 || min_left !== 1 || min_right !== 0))
                $fatal(1, "single-cycle wait/period parameters");
        end
        for (i = 1; i <= 27; i = i + 1) begin
            @(posedge clk); #1;
            if (pl || pr || direction !== 3) $fatal(1, "PWM during 1us direction setup");
        end
        @(posedge clk); #1;
        if (!pl || !pr || interlock) $fatal(1, "pending pair not loaded after setup");
        $display("COVER pwm_timing.zero_30ms_ticks 810000");
        $display("COVER pwm_timing.zero_40ms_ticks 1080000");
        $display("PASS tb_pwm_timing: 27MHz, 1350-slot period, 30/40ms zero plus 27 setup ticks; minimum parameters");
        $finish;
    end
    initial begin #42000000; $fatal(1, "timeout tb_pwm_timing"); end
endmodule
