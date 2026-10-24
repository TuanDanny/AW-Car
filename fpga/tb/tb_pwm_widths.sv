`timescale 1ns/1ps
// Exercise inclusive duty width and reject high-bit aliases before narrowing.
module pwm_width_case #(parameter int PERIOD = 16) (output logic done = 0);
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0, enable = 0, command_valid = 0;
    logic [15:0] command_left = 0, command_right = 0;
    logic pwm_left, pwm_right, period_start, command_rejected, command_applied;
    logic [15:0] active_left, active_right;
    pwm_pair #(.PERIOD_CYCLES(PERIOD)) dut (.*);
    logic motor_left, motor_right, motor_rejected, interlock;
    logic [1:0] direction;
    motor_pwm_pair #(.PERIOD_CYCLES(PERIOD), .ZERO_CYCLES(1), .SETUP_CYCLES(1)) motor (
        .clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(command_valid),
        .command_left(command_left), .command_right(command_right), .command_direction(2'b00),
        .pwm_left(motor_left), .pwm_right(motor_right), .direction(direction),
        .interlock_active(interlock), .command_rejected(motor_rejected));

    task automatic offer(input integer left, input integer right, input logic reject);
        @(negedge clk); command_left = left; command_right = right; command_valid = 1;
        @(posedge clk); #1;
        if (command_rejected !== reject || motor_rejected !== reject)
            $fatal(1, "period %0d: full-width rejection failed", PERIOD);
        @(negedge clk); command_valid = 0;
    endtask
    task automatic measure(input integer left, input integer right);
        integer ticks, highs_left, highs_right;
        // Allow the pending pair to commit, then observe a complete PWM period.
        repeat (PERIOD + 1) @(negedge clk);
        while (!period_start) @(negedge clk);
        if (active_left !== left || active_right !== right)
            $fatal(1, "period %0d: duty truncated or invalid command committed", PERIOD);
        highs_left = 0; highs_right = 0;
        for (ticks = 0; ticks < PERIOD; ticks = ticks + 1) begin
            if (pwm_left !== motor_left || pwm_right !== motor_right)
                $fatal(1, "period %0d: motor wrapper duty differs", PERIOD);
            if (pwm_left !== (ticks < left) || pwm_right !== (ticks < right))
                $fatal(1, "period %0d: wrong edge or full-scale duty", PERIOD);
            highs_left = highs_left + pwm_left; highs_right = highs_right + pwm_right;
            @(negedge clk);
        end
        if (highs_left != left || highs_right != right)
            $fatal(1, "period %0d: wrong HIGH tick count", PERIOD);
    endtask
    initial begin
        repeat (3) @(negedge clk); rst_n = 1; enable = 1;
        offer(PERIOD, PERIOD, 0); measure(PERIOD, PERIOD);
        offer(1, 0, 0); measure(1, 0);
        if (PERIOD < 65535) begin
            offer(PERIOD + 1, 0, 1); measure(1, 0);
            // With 11-bit storage, 2049 would alias to a valid duty of one.
            if (PERIOD < 2049) begin offer(2049, 0, 1); measure(1, 0); end
            offer(0, 65535, 1); measure(1, 0);
        end
        enable = 0; @(negedge clk); enable = 1; measure(0, 0);
        done = 1;
    end
endmodule

module tb_pwm_widths;
    wire [3:0] done;
    pwm_width_case #(.PERIOD(16)) power_four (.done(done[0]));
    pwm_width_case #(.PERIOD(1350)) nominal (.done(done[1]));
    pwm_width_case #(.PERIOD(2048)) power_eleven (.done(done[2]));
    pwm_width_case #(.PERIOD(65535)) full_input_width (.done(done[3]));
    initial begin
        wait (&done);
        $display("PASS tb_pwm_widths: periods 16/1350/2048/65535, full duty, high-bit aliases, disable");
        $finish;
    end
    initial begin #10000000; $fatal(1, "PWM width timeout"); end
endmodule
