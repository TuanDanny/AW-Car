`timescale 1ns/1ps
module tb_pwm_timing;
    reg clk = 0;
    always #18.519 clk = !clk;
    reg rst_n = 0, enable = 0, valid = 0;
    reg [15:0] l = 675, r = 1350;
    reg [1:0] requested_direction = 0;
    wire pl, pr, interlock, rejected;
    wire [1:0] direction;
    motor_pwm_pair dut (.clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(valid),
        .command_left(l), .command_right(r), .command_direction(requested_direction),
        .pwm_left(pl), .pwm_right(pr), .direction(direction),
        .interlock_active(interlock), .command_rejected(rejected));
    // Minimum supported parameters exercise width calculations and single-cycle waits.
    wire min_left, min_right, min_hold, min_rejected;
    wire [1:0] min_direction;
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
        for (i = 1; i <= 27000; i = i + 1) begin
            @(posedge clk); #1;
            if (pl || pr) $fatal(1, "PWM during 1ms zero wait");
            if (direction !== ((i < 27000) ? 0 : 3)) $fatal(1, "zero wait length");
            if (i >= 4 && (min_direction !== 3 || min_left !== 1 || min_right !== 0))
                $fatal(1, "single-cycle wait/period parameters");
        end
        for (i = 1; i <= 27; i = i + 1) begin
            @(posedge clk); #1;
            if (pl || pr || direction !== 3) $fatal(1, "PWM during 1us direction setup");
        end
        @(posedge clk); #1;
        if (!pl || !pr || interlock) $fatal(1, "pending pair not loaded after setup");
        $display("PASS tb_pwm_timing: 27MHz, 1350-slot period, 27000+27 waits; minimum parameters");
        $finish;
    end
    initial begin #2000000; $fatal(1, "timeout tb_pwm_timing"); end
endmodule
