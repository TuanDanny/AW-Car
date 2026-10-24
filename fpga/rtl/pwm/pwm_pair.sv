`timescale 1ns/1ps
`default_nettype none
module pwm_pair #(
    parameter int PERIOD_CYCLES = 1350,
    parameter int DUTY_WIDTH = 16
) (
    input  logic clk,
    input  logic rst_n,
    input  logic enable,
    input  logic command_valid,
    input  logic [DUTY_WIDTH-1:0] command_left,
    input  logic [DUTY_WIDTH-1:0] command_right,
    output logic pwm_left,
    output logic pwm_right,
    output logic period_start,
    output logic command_rejected,
    output logic command_applied,
    output logic [DUTY_WIDTH-1:0] active_left,
    output logic [DUTY_WIDTH-1:0] active_right
);
    localparam int PHASE_WIDTH = (PERIOD_CYCLES > 1) ? $clog2(PERIOD_CYCLES) : 1;
    // Duty includes PERIOD_CYCLES itself (100%), even for power-of-two periods.
    localparam int VALUE_WIDTH = (PERIOD_CYCLES > 1) ? $clog2(PERIOD_CYCLES + 1) : 1;
    logic [PHASE_WIDTH-1:0] phase;
    logic [VALUE_WIDTH-1:0] shadow_left, shadow_right;
    logic [VALUE_WIDTH-1:0] active_left_value, active_right_value;
    logic pending;
    logic pwm_left_ff, pwm_right_ff;
    logic in_range, accept, boundary;
    logic [PHASE_WIDTH-1:0] next_phase;
    logic [VALUE_WIDTH-1:0] next_left, next_right;
    assign active_left = active_left_value;
    assign active_right = active_right_value;
    assign in_range = command_left <= PERIOD_CYCLES && command_right <= PERIOD_CYCLES;
    assign accept = command_valid && in_range && enable;
    assign boundary = phase == PERIOD_CYCLES - 1;
    assign next_phase = boundary ? 0 : phase + 1'b1;
    assign next_left = accept ? VALUE_WIDTH'(command_left) : pending ? shadow_left : active_left_value;
    assign next_right = accept ? VALUE_WIDTH'(command_right) : pending ? shadow_right : active_right_value;
    // Registered PWM avoids glitches from a binary counter/comparator carry.
    // enable is a synchronous safety permission; its falling level also masks IO immediately.
    assign pwm_left = rst_n && enable && pwm_left_ff;
    assign pwm_right = rst_n && enable && pwm_right_ff;
    assign period_start = enable && phase == 0;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= PERIOD_CYCLES - 1;
            shadow_left <= 0; shadow_right <= 0;
            active_left_value <= 0; active_right_value <= 0;
            pending <= 0;
            pwm_left_ff <= 0; pwm_right_ff <= 0;
            command_rejected <= 0; command_applied <= 0;
        end else begin
            command_rejected <= command_valid && (!enable || !in_range);
            command_applied <= 0;
            if (!enable) begin
                phase <= PERIOD_CYCLES - 1;
                shadow_left <= 0; shadow_right <= 0;
                active_left_value <= 0; active_right_value <= 0;
                pending <= 0;
                pwm_left_ff <= 0; pwm_right_ff <= 0;
            end else begin
                phase <= next_phase;
                if (accept) begin
                    shadow_left <= VALUE_WIDTH'(command_left); shadow_right <= VALUE_WIDTH'(command_right);
                    pending <= 1;
                end
                if (boundary) begin
                    active_left_value <= next_left; active_right_value <= next_right;
                    pending <= 0;
                    command_applied <= accept || pending;
                    pwm_left_ff <= next_left != 0;
                    pwm_right_ff <= next_right != 0;
                end else begin
                    pwm_left_ff <= next_phase < active_left_value;
                    pwm_right_ff <= next_phase < active_right_value;
                end
            end
        end
    end
endmodule
`default_nettype wire
