`timescale 1ns/1ps
module tb_motor_pwm_pair;
    reg clk = 0;
    reg clock_running = 1;
    always #5 if (clock_running) clk = !clk;
    reg rst_n = 0, enable = 0, valid = 0;
    reg [15:0] left_command = 0, right_command = 0;
    reg [1:0] direction_command = 0;
    wire left, right, interlock, rejected;
    wire [1:0] direction;
    motor_pwm_pair #(.PERIOD_CYCLES(17), .ZERO_CYCLES(5), .SETUP_CYCLES(3)) dut (
        .clk(clk), .rst_n(rst_n), .enable(enable), .command_valid(valid),
        .command_left(left_command), .command_right(right_command),
        .command_direction(direction_command), .pwm_left(left), .pwm_right(right),
        .direction(direction), .interlock_active(interlock), .command_rejected(rejected));
    integer zero_ticks = 0, since_direction = 100, changes = 0;
    reg [1:0] previous_direction = 0;
    always @(posedge clk) begin
        #1;
        if (!rst_n || !enable) begin zero_ticks = 0; since_direction = 100; end
        else begin
            if (interlock && (left || right)) $fatal(1, "PWM active during interlock");
            if (direction != previous_direction) begin
                if (zero_ticks < 5 || left || right) $fatal(1, "direction changed before zero interval");
                since_direction = 0; changes = changes + 1;
            end else since_direction = since_direction + 1;
            if ((left || right) && since_direction < 3) $fatal(1, "direction setup interval too short");
            if (!left && !right) zero_ticks = zero_ticks + 1;
            else zero_ticks = 0;
        end
        previous_direction = direction;
    end
    task command(input integer l, input integer r, input [1:0] d);
        begin
            @(negedge clk); left_command = l; right_command = r; direction_command = d; valid = 1;
            @(posedge clk); #2;
            if (rejected !== (!enable || l > 17 || r > 17)) $fatal(1, "wrapper rejection");
            @(negedge clk); valid = 0;
        end
    endtask
    task measure(input integer l, input integer r);
        integer i, hl, hr;
        begin
            repeat (50) @(negedge clk);
            hl = 0; hr = 0;
            for (i = 0; i < 17; i = i + 1) begin
                @(negedge clk); hl = hl + left; hr = hr + right;
            end
            if (hl != l || hr != r) $fatal(1, "motor pair duty mismatch %d/%d %d/%d", hl,l,hr,r);
        end
    endtask
    integer delay_ticks;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_motor_pwm_pair.vcd"); $dumpvars(0, tb_motor_pwm_pair); end
        repeat (3) @(negedge clk); rst_n = 1;
        command(17, 17, 3); enable = 1; measure(0, 0);
        command(17, 17, 0); measure(17, 17);
        command(9, 4, 1); measure(9, 4);
        if (direction !== 1) $fatal(1, "direction request missing");
        command(8, 8, 2);
        repeat (2) @(negedge clk);
        command(3, 14, 3); // New command during zero wait supersedes whole pair.
        measure(3, 14);
        if (direction !== 3) $fatal(1, "old pending direction replayed");
        command(18, 2, 0); measure(3, 14);
        if (direction !== 3) $fatal(1, "invalid command changed direction");
        command(17, 0, 0);
        repeat (5) @(negedge clk);
        command(0, 17, 1); // Supersede while direction setup is pending.
        measure(0, 17);
        if (direction !== 1) $fatal(1, "setup replacement lost");
        // Disable at every phase of a direction change; never resurrect queued duty.
        for (delay_ticks = 0; delay_ticks <= 10; delay_ticks = delay_ticks + 1) begin
            command(17, 17, 0); measure(17, 17);
            command(17, 17, 3);
            repeat (delay_ticks) @(negedge clk);
            #2; enable = 0; #1;
            if (left || right) $fatal(1, "disable did not mask motor PWM");
            repeat (2) @(negedge clk); enable = 1;
            measure(0, 0);
            if (direction !== 0) $fatal(1, "disable did not discard pending direction");
        end
        // Reset each interlock phase, then re-enable without new command.
        for (delay_ticks = 0; delay_ticks <= 10; delay_ticks = delay_ticks + 1) begin
            command(17, 17, 3);
            repeat (delay_ticks) @(negedge clk);
            #2; rst_n = 0; #1;
            if (left || right || direction !== 0) $fatal(1, "reset motor outputs");
            repeat (2) @(negedge clk); rst_n = 1;
            measure(0, 0);
        end
        // The permission's falling level must mask PWM even if this clock stops.
        command(17, 17, 0); measure(17, 17);
        @(negedge clk); clock_running = 0;
        #2; enable = 0; #1;
        if (left || right) $fatal(1, "inhibit failed with stopped PWM clock");
        #20; clock_running = 1;
        repeat (2) @(negedge clk); enable = 1;
        measure(0, 0);
        command(17, 17, 0); measure(17, 17);
        @(negedge clk); clock_running = 0;
        #2; rst_n = 0; #1;
        if (left || right || direction !== 0) $fatal(1, "async reset with stopped clock");
        #20; clock_running = 1;
        repeat (2) @(negedge clk); rst_n = 1;
        measure(0, 0);
        if (changes < 4) $fatal(1, "missing direction coverage");
        $display("PASS tb_motor_pwm_pair: zero/setup, latest pair, invalid, disable/reset each phase");
        $finish;
    end
    initial begin #200000; $fatal(1, "timeout tb_motor_pwm_pair"); end
endmodule
