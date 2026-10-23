`timescale 1ns/1ps
`default_nettype none
// Logical top only. Board wrapper must supply POR, pin/clock constraints,
// default-off independent gate and driver-specific direction/brake mapping.
module drive_core #(
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
    parameter int ZERO_CYCLES = 27000,
    parameter int SETUP_CYCLES = 27,
    parameter int FILTER_N = 3,
    parameter bit ALLOW_REVERSE = 0,
    parameter bit INVERT_LEFT = 0,
    parameter bit INVERT_RIGHT = 0
) (
    input logic clk, arst_n, rx,
    input logic [1:0] left_ab, right_ab,
    input logic motion_permit_async, recovery_req_async,
    input logic safety_ok_async, gate_fault_n_async,
    output logic tx, pwm_left, pwm_right,
    output logic [1:0] direction,
    output logic fpga_permit, recovery_ack, gate_clear,
    output logic [7:0] safety_state,
    output logic [15:0] fault
);
    logic rst_n, inputs_valid, safety_ok, gate_ok, motion_permit;
    logic [1:0] controls;
    logic context_load, session_active, command_enable, motor_enable, motor_command;
    logic [31:0] active_session, event_session, status_session;
    logic [15:0] sequence_base, event_sequence, command_left, command_right;
    logic [1:0] command_direction;
    logic hello_request, arm_zero_request, disable_request, clear_fault_request;
    logic command_valid, command_rejected, receive_error, pwm_rejected;
    logic status_sent;
    logic [7:0] status_state;
    logic snapshot_valid, snapshot_ready, snapshot_dropped;
    logic [31:0] snapshot_left, snapshot_right, snapshot_time, live_left, live_right;
    logic [15:0] snapshot_seq;
    logic [3:0] snapshot_status;
    logic raw_left, raw_right, interlock_active;
    logic output_allowed, clear_request;
    reset_sync reset_release (.clk(clk), .arst_n(arst_n), .rst_n(rst_n));
    // Async assertion captures short LOW pulses; release needs clock edges.
    reset_sync safety_capture (.clk(clk), .arst_n(arst_n && safety_ok_async), .rst_n(safety_ok));
    reset_sync gate_capture (.clk(clk), .arst_n(arst_n && gate_fault_n_async), .rst_n(gate_ok));
    reset_sync permit_capture (.clk(clk), .arst_n(arst_n && motion_permit_async), .rst_n(motion_permit));
    input_sync_filter #(.WIDTH(2), .FILTER_N(1)) control_sync (
        .clk(clk), .rst_n(rst_n), .async_in({motion_permit_async, recovery_req_async}),
        .filtered(controls), .valid(inputs_valid));
    encoder_pair #(.FILTER_N(FILTER_N), .SNAPSHOT_CYCLES(SNAPSHOT_CYCLES),
                   .INVERT_LEFT(INVERT_LEFT), .INVERT_RIGHT(INVERT_RIGHT)) encoders (
        .clk(clk), .rst_n(rst_n), .left_ab(left_ab), .right_ab(right_ab),
        .left_count(live_left), .right_count(live_right), .snapshot_valid(snapshot_valid),
        .snapshot_left(snapshot_left), .snapshot_right(snapshot_right), .snapshot_time(snapshot_time),
        .snapshot_seq(snapshot_seq), .snapshot_status(snapshot_status));
    fpga_link #(.CLK_HZ(CLK_HZ), .BAUD(BAUD), .PERIOD_CYCLES(PERIOD_CYCLES),
                .ALLOW_REVERSE(ALLOW_REVERSE), .INTERBYTE_CYCLES(INTERBYTE_CYCLES),
                .FRAME_CYCLES(FRAME_CYCLES)) link (
        .clk(clk), .rst_n(rst_n), .rx(rx), .tx(tx), .context_load(context_load),
        .session_active(session_active), .active_session(active_session), .sequence_base(sequence_base),
        .command_enable(command_enable), .hello_request(hello_request), .arm_zero_request(arm_zero_request),
        .disable_request(disable_request), .clear_fault_request(clear_fault_request),
        .command_valid(command_valid), .command_rejected(command_rejected), .event_session(event_session),
        .event_sequence(event_sequence), .command_left(command_left), .command_right(command_right),
        .command_direction(command_direction), .receive_error(receive_error),
        .snapshot_valid(snapshot_valid), .snapshot_ready(snapshot_ready), .snapshot_dropped(snapshot_dropped),
        .snapshot_left(snapshot_left), .snapshot_right(snapshot_right), .snapshot_time(snapshot_time),
        .snapshot_seq(snapshot_seq), .snapshot_status(snapshot_status), .safety_state(safety_state), .fault(fault),
        .status_sent(status_sent), .status_session(status_session), .status_state(status_state));
    safety_fsm #(.WATCHDOG_CYCLES(WATCHDOG_CYCLES), .HANDSHAKE_CYCLES(HANDSHAKE_CYCLES),
                 .CLEAR_CYCLES(CLEAR_CYCLES), .CLEAR_HOLD_CYCLES(CLEAR_HOLD_CYCLES)) safety (
        .clk(clk), .rst_n(rst_n), .inputs_valid(inputs_valid), .motion_permit(motion_permit),
        .recovery_req(controls[0]), .safety_ok(safety_ok), .gate_ok(gate_ok),
        .hello_request(hello_request), .arm_zero_request(arm_zero_request),
        .disable_request(disable_request), .clear_fault_request(clear_fault_request),
        .command_valid(command_valid), .pwm_rejected(pwm_rejected),
        .event_session(event_session), .event_sequence(event_sequence), .status_sent(status_sent),
        .status_session(status_session), .status_state(status_state), .context_load(context_load),
        .session_active(session_active), .active_session(active_session), .sequence_base(sequence_base),
        .command_enable(command_enable), .motor_enable(motor_enable), .motor_command(motor_command),
        .recovery_ack(recovery_ack), .gate_clear(clear_request), .safety_state(safety_state), .fault(fault));
    motor_pwm_pair #(.PERIOD_CYCLES(PERIOD_CYCLES), .ZERO_CYCLES(ZERO_CYCLES),
                     .SETUP_CYCLES(SETUP_CYCLES)) motors (
        .clk(clk), .rst_n(rst_n), .enable(motor_enable), .command_valid(motor_command),
        .command_left(command_left), .command_right(command_right), .command_direction(command_direction),
        .pwm_left(raw_left), .pwm_right(raw_right), .direction(direction),
        .interlock_active(interlock_active), .command_rejected(pwm_rejected));
    assign output_allowed = arst_n && rst_n && safety_ok_async && gate_fault_n_async &&
                            motion_permit_async && motor_enable;
    assign fpga_permit = output_allowed;
    assign gate_clear = clear_request && arst_n && safety_ok_async &&
                        !motion_permit_async && !recovery_req_async;
    assign pwm_left = raw_left && output_allowed;
    assign pwm_right = raw_right && output_allowed;
endmodule
`default_nettype wire
