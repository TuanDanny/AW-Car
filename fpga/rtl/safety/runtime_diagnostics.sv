`timescale 1ns/1ps
`default_nettype none
// Synthesizable checks, not simulation assertions. Sticky until FPGA reset.
// A quiet encoder is a warning, not proof of a failed motor or sensor.
module runtime_diagnostics #(
    parameter int SNAPSHOT_LIMIT = 540000,
    parameter int ENCODER_LIMIT = 13500000
) (
    input logic clk, rst_n,
    input logic receive_error, command_rejected, snapshot_dropped, pwm_rejected,
    input logic snapshot_valid, motor_enable, interlock_active,
    input logic request_left, request_right,
    input logic raw_left, raw_right,
    input logic [7:0] safety_state,
    input logic [31:0] left_count, right_count,
    output logic [7:0] flags,
    output logic critical_fault
);
    localparam int SW = SNAPSHOT_LIMIT > 1 ? $clog2(SNAPSHOT_LIMIT) : 1;
    localparam int EW = ENCODER_LIMIT > 1 ? $clog2(ENCODER_LIMIT) : 1;
    logic [SW-1:0] snapshot_age;
    logic [EW-1:0] left_age, right_age;
    logic [31:0] previous_left, previous_right;
    // Snapshot loss and an internal output invariant require reset/review.
    assign critical_fault = flags[7] || flags[3];
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            flags <= 0; snapshot_age <= 0; left_age <= 0; right_age <= 0;
            previous_left <= 0; previous_right <= 0;
        end else begin
            flags <= flags | {((raw_left || raw_right) &&
                              (!motor_enable || interlock_active)) || safety_state > 5,
                              pwm_rejected, 2'b00, 1'b0, snapshot_dropped,
                              command_rejected, receive_error};
            previous_left <= left_count; previous_right <= right_count;
            if (snapshot_valid) snapshot_age <= 0;
            else if (snapshot_age == SNAPSHOT_LIMIT - 1) flags[3] <= 1;
            else snapshot_age <= snapshot_age + 1'b1;
            if (!motor_enable || interlock_active || !request_left || left_count != previous_left)
                left_age <= 0;
            else if (left_age == ENCODER_LIMIT - 1) flags[4] <= 1;
            else left_age <= left_age + 1'b1;
            if (!motor_enable || interlock_active || !request_right || right_count != previous_right)
                right_age <= 0;
            else if (right_age == ENCODER_LIMIT - 1) flags[5] <= 1;
            else right_age <= right_age + 1'b1;
        end
    end
endmodule
`default_nettype wire
