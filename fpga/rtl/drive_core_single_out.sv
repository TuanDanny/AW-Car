`timescale 1ns/1ps
`default_nettype none
// FPGA logical top for the actual two single-OUT IR encoders.
// No unused quadrature GPIOs are exposed at the board boundary.
// Version 2 UART frames only: Motion must explicitly implement v2 decoding.
module drive_core_single_out #(
    parameter int CLK_HZ = 27000000,
    parameter int BAUD = 115200,
    parameter int PERIOD_CYCLES = 1350,
    parameter int SNAPSHOT_CYCLES = 270000,
    parameter int WATCHDOG_CYCLES = 1350000,
    parameter int HANDSHAKE_CYCLES = 6750000,
    parameter int CLEAR_CYCLES = 135000,
    parameter int CLEAR_HOLD_CYCLES = 2700,
    parameter int INTERBYTE_CYCLES = 54000,
    parameter int FRAME_CYCLES = 135000,
    parameter int ZERO_CYCLES = 1080000,
    parameter int SETUP_CYCLES = 27,
    parameter int FILTER_N = 3,
    parameter bit ALLOW_REVERSE = 1
) (
    input logic clk, arst_n, rx,
    input logic left_out, right_out,
    input logic motion_permit_async, recovery_req_async,
    input logic safety_ok_async, gate_fault_n_async,
    output logic tx, pwm_left, pwm_right,
    output logic [1:0] direction,
    output logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2,
    output logic fpga_permit, recovery_ack, gate_clear,
    output logic [7:0] safety_state,
    output logic [15:0] fault
);
    drive_core #(
        .CLK_HZ(CLK_HZ), .BAUD(BAUD), .PERIOD_CYCLES(PERIOD_CYCLES),
        .SNAPSHOT_CYCLES(SNAPSHOT_CYCLES), .WATCHDOG_CYCLES(WATCHDOG_CYCLES),
        .HANDSHAKE_CYCLES(HANDSHAKE_CYCLES), .CLEAR_CYCLES(CLEAR_CYCLES),
        .CLEAR_HOLD_CYCLES(CLEAR_HOLD_CYCLES), .INTERBYTE_CYCLES(INTERBYTE_CYCLES),
        .FRAME_CYCLES(FRAME_CYCLES), .ZERO_CYCLES(ZERO_CYCLES),
        .SETUP_CYCLES(SETUP_CYCLES), .FILTER_N(FILTER_N),
        .ALLOW_REVERSE(ALLOW_REVERSE), .ENCODER_SINGLE_OUT(1), .PROTOCOL_VERSION(2)
    ) core (
        .clk(clk), .arst_n(arst_n), .rx(rx),
        .left_ab(2'b00), .right_ab(2'b00),
        .encoder_left_out(left_out), .encoder_right_out(right_out),
        .motion_permit_async(motion_permit_async),
        .recovery_req_async(recovery_req_async),
        .safety_ok_async(safety_ok_async), .gate_fault_n_async(gate_fault_n_async),
        .tx(tx), .pwm_left(pwm_left), .pwm_right(pwm_right),
        .direction(direction), .fpga_permit(fpga_permit),
        .drv_left_in1(drv_left_in1), .drv_left_in2(drv_left_in2),
        .drv_right_in1(drv_right_in1), .drv_right_in2(drv_right_in2),
        .recovery_ack(recovery_ack), .gate_clear(gate_clear),
        .safety_state(safety_state), .fault(fault)
    );
endmodule
`default_nettype wire
