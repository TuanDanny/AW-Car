`timescale 1ns/1ps
`default_nettype none
module pwm_pair #(
    parameter integer PERIOD_CYCLES = 1350,
    parameter integer DUTY_WIDTH = 16
) (
    input  wire clk,
    input  wire rst_n,
    input  wire enable,
    input  wire command_valid,
    input  wire [DUTY_WIDTH-1:0] command_left,
    input  wire [DUTY_WIDTH-1:0] command_right,
    output wire pwm_left,
    output wire pwm_right,
    output wire period_start,
    output reg command_rejected,
    output reg command_applied,
    output reg [DUTY_WIDTH-1:0] active_left,
    output reg [DUTY_WIDTH-1:0] active_right
);
    function integer bits_for;
        input integer value;
        integer v;
        begin
            v = value - 1; bits_for = 0;
            while (v > 0) begin bits_for = bits_for + 1; v = v >> 1; end
            if (bits_for == 0) bits_for = 1;
        end
    endfunction
    localparam integer PHASE_WIDTH = bits_for(PERIOD_CYCLES);
    reg [PHASE_WIDTH-1:0] phase;
    reg [DUTY_WIDTH-1:0] shadow_left, shadow_right;
    reg pending;
    reg pwm_left_ff, pwm_right_ff;
    wire in_range = command_left <= PERIOD_CYCLES && command_right <= PERIOD_CYCLES;
    wire accept = command_valid && in_range && enable;
    wire boundary = phase == PERIOD_CYCLES - 1;
    wire [PHASE_WIDTH-1:0] next_phase = boundary ? 0 : phase + 1'b1;
    wire [DUTY_WIDTH-1:0] next_left = accept ? command_left : pending ? shadow_left : active_left;
    wire [DUTY_WIDTH-1:0] next_right = accept ? command_right : pending ? shadow_right : active_right;
    // Registered PWM avoids glitches from a binary counter/comparator carry.
    // enable is a synchronous safety permission; its falling level also masks IO immediately.
    assign pwm_left = rst_n && enable && pwm_left_ff;
    assign pwm_right = rst_n && enable && pwm_right_ff;
    assign period_start = enable && phase == 0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= PERIOD_CYCLES - 1;
            shadow_left <= 0; shadow_right <= 0;
            active_left <= 0; active_right <= 0;
            pending <= 0;
            pwm_left_ff <= 0; pwm_right_ff <= 0;
            command_rejected <= 0; command_applied <= 0;
        end else begin
            command_rejected <= command_valid && (!enable || !in_range);
            command_applied <= 0;
            if (!enable) begin
                phase <= PERIOD_CYCLES - 1;
                shadow_left <= 0; shadow_right <= 0;
                active_left <= 0; active_right <= 0;
                pending <= 0;
                pwm_left_ff <= 0; pwm_right_ff <= 0;
            end else begin
                phase <= next_phase;
                if (accept) begin
                    shadow_left <= command_left; shadow_right <= command_right;
                    pending <= 1;
                end
                if (boundary) begin
                    active_left <= next_left; active_right <= next_right;
                    pending <= 0;
                    command_applied <= accept || pending;
                    pwm_left_ff <= next_left != 0;
                    pwm_right_ff <= next_right != 0;
                end else begin
                    pwm_left_ff <= next_phase < active_left;
                    pwm_right_ff <= next_phase < active_right;
                end
            end
        end
    end
endmodule
`default_nettype wire
