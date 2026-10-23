`timescale 1ns/1ps
module tb_pwm_pair;
    reg clk = 0;
    always #5 clk = !clk;
    reg rst_n = 0, enable = 0, command_valid = 0;
    reg [15:0] duty_left = 0, duty_right = 0;
    wire left, right, start, rejected, applied;
    wire [15:0] active_left, active_right;
    pwm_pair #(.PERIOD_CYCLES(17)) dut (
        .clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(command_valid),
        .command_left(duty_left), .command_right(duty_right),
        .pwm_left(left), .pwm_right(right), .period_start(start),
        .command_rejected(rejected), .command_applied(applied),
        .active_left(active_left), .active_right(active_right));
    // Default 27MHz/1350-tick instance: validate exact HIGH counts and period.
    wire real_left, real_right, real_start, real_rejected, real_applied;
    wire [15:0] real_active_left, real_active_right;
    pwm_pair real_parameters (
        .clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(1'b1),
        .command_left(16'd675), .command_right(16'd1350),
        .pwm_left(real_left), .pwm_right(real_right), .period_start(real_start),
        .command_rejected(real_rejected), .command_applied(real_applied),
        .active_left(real_active_left), .active_right(real_active_right));
    integer slots = 0, highs_left = 0, highs_right = 0, periods = 0;
    integer real_slots = 0, real_high_left = 0, real_high_right = 0, real_periods = 0;
    integer period_left, period_right;
    reg measuring = 0, real_measuring = 0;
    reg previous_enable = 0;
    // Independent scoreboard counts observed output slots per whole period.
    always @(posedge clk) begin
        #1;
        if (!rst_n || !enable) begin
            measuring = 0; real_measuring = 0;
            if (left !== 0 || right !== 0) $fatal(1, "disabled PWM not zero");
        end else begin
            if ((^{left, right, active_left, active_right}) === 1'bx) $fatal(1, "unknown PWM");
            if (start) begin
                if (measuring) begin
                    if (slots != 17 || highs_left != period_left || highs_right != period_right)
                        $fatal(1, "period/high count mismatch %d %d/%d %d/%d",
                               slots, highs_left, period_left, highs_right, period_right);
                    periods = periods + 1;
                end
                measuring = 1; slots = 0; highs_left = 0; highs_right = 0;
                period_left = active_left; period_right = active_right;
            end
            if (measuring) begin
                if (active_left !== period_left || active_right !== period_right)
                    $fatal(1, "duty changed within a period");
                // Edge-aligned duty has no later rising pulse inside its period.
                if (left !== (slots < period_left) || right !== (slots < period_right))
                    $fatal(1, "unexpected PWM edge");
                slots = slots + 1; highs_left = highs_left + left; highs_right = highs_right + right;
            end
            if (real_start) begin
                if (real_measuring) begin
                    if (real_slots != 1350 || real_high_left != 675 || real_high_right != 1350)
                        $fatal(1, "default 1350/50%%/100%% timing");
                    real_periods = real_periods + 1;
                end
                real_measuring = 1; real_slots = 0; real_high_left = 0; real_high_right = 0;
            end
            real_slots = real_slots + 1;
            real_high_left = real_high_left + real_left;
            real_high_right = real_high_right + real_right;
        end
        previous_enable = enable;
    end
    task command(input integer l, input integer r);
        begin
            @(negedge clk); duty_left = l; duty_right = r; command_valid = 1;
            @(posedge clk); #2;
            if (rejected !== (!enable || l > 17 || r > 17)) $fatal(1, "range/enable rejection");
            @(negedge clk); command_valid = 0;
        end
    endtask
    task await_pair(input integer l, input integer r);
        integer wait_ticks;
        begin
            wait_ticks = 0;
            while ((active_left !== l || active_right !== r) && wait_ticks < 18) begin
                @(posedge clk); #2; wait_ticks = wait_ticks + 1;
            end
            if (active_left !== l || active_right !== r) $fatal(1, "pair command not committed");
            repeat (35) @(negedge clk);
        end
    endtask
    reg [31:0] random_state;
    integer i, seed, l, r;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_pwm_pair.vcd"); $dumpvars(0, tb_pwm_pair); end
        repeat (3) @(negedge clk); rst_n = 1;
        command(17, 17); // Commands received while disabled must be discarded.
        enable = 1;
        await_pair(0, 0);
        command(0, 17); await_pair(0, 17);
        command(1, 16); await_pair(1, 16);
        command(8, 9); await_pair(8, 9);
        command(17, 0); await_pair(17, 0);
        command(18, 9); await_pair(17, 0);
        command(1, 65535); await_pair(17, 0);
        // Queue several commands inside one period: only latest complete pair wins.
        wait (start); @(negedge clk);
        command(2, 15); command(3, 14); command(4, 13);
        await_pair(4, 13);
        for (seed = 1; seed <= 10; seed = seed + 1) begin
            random_state = seed;
            for (i = 0; i < 1000; i = i + 1) begin
                random_state = random_state ^ (random_state << 13);
                random_state = random_state ^ (random_state >> 17);
                random_state = random_state ^ (random_state << 5);
                l = random_state % 18; r = (random_state >> 8) % 18;
                command(l, r); await_pair(l, r);
            end
        end
        command(17, 17); await_pair(17, 17);
        // Falling inhibit must mask output without waiting for the next clock.
        #2; enable = 0; #1;
        if (left !== 0 || right !== 0) $fatal(1, "inhibit waited for boundary/clock");
        repeat (2) @(negedge clk); enable = 1;
        await_pair(0, 0); // No cached command after a sampled inhibit.
        command(8, 8); await_pair(8, 8);
        #2; rst_n = 0; #1;
        if (left !== 0 || right !== 0) $fatal(1, "reset did not mask PWM");
        if (periods < 10000 || real_periods < 3) $fatal(1, "insufficient period coverage");
        $display("PASS tb_pwm_pair: 10 seeds x 1000 pairs; bounds/atomic/registered edges/default timing");
        $finish;
    end
    initial begin #20000000; $fatal(1, "timeout tb_pwm_pair"); end
endmodule
