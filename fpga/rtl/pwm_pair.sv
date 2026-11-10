`timescale 1ns/1ps
`default_nettype none
module pwm_pair (
    input wire logic clk, rst_n, enable,
    input wire logic signed [15:0] target_left, target_right,
    output logic left_in1, left_in2, right_in1, right_in2
);
    // 27MHz / 1350 = 20kHz. No derived or gated clocks.
    logic [10:0] phase;
    logic signed [15:0] active_left, active_right, next_left, next_right;
    logic [15:0] left_magnitude, right_magnitude;
    always_comb begin
        next_left = enable ? target_left : 16'sd0;
        next_right = enable ? target_right : 16'sd0;
        // A single complete neutral PWM period prevents overlap at reversal.
        // Mechanical 40ms and last-nonzero sign memory belong to Motion only.
        if (active_left != 0 && next_left != 0 && active_left[15] != next_left[15]) next_left = 0;
        if (active_right != 0 && next_right != 0 && active_right[15] != next_right[15]) next_right = 0;
        left_magnitude = active_left[15] ? -active_left : active_left;
        right_magnitude = active_right[15] ? -active_right : active_right;
    end
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= '0; active_left <= '0; active_right <= '0;
            left_in1 <= 1'b0; left_in2 <= 1'b0; right_in1 <= 1'b0; right_in2 <= 1'b0;
        end else begin
            if (phase == 11'd1349) phase <= '0;
            else phase <= phase + 1'b1;
            if (!enable) begin
                active_left <= '0; active_right <= '0;
                left_in1 <= 1'b0; left_in2 <= 1'b0; right_in1 <= 1'b0; right_in2 <= 1'b0;
            end else if (phase == 11'd1349) begin
                active_left <= next_left; active_right <= next_right;
                left_in1 <= next_left > 0; left_in2 <= next_left < 0;
                right_in1 <= next_right > 0; right_in2 <= next_right < 0;
            end else begin
                left_in1 <= active_left > 0 && ({1'b0, phase} + 12'd1) < left_magnitude;
                left_in2 <= active_left < 0 && ({1'b0, phase} + 12'd1) < left_magnitude;
                right_in1 <= active_right > 0 && ({1'b0, phase} + 12'd1) < right_magnitude;
                right_in2 <= active_right < 0 && ({1'b0, phase} + 12'd1) < right_magnitude;
            end
        end
    end
endmodule
