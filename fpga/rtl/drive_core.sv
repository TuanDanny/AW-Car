`timescale 1ns/1ps
`default_nettype none
// Logical top with DRV8833 drive/coast mapping. Board wrapper must supply POR,
// pin/clock/I/O constraints and a default-off independent hardware gate.
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
    parameter int ZERO_CYCLES = 1080000,
    parameter int SETUP_CYCLES = 27,
    parameter int FILTER_N = 3,
    parameter int ENCODER_STALE_CYCLES = CLK_HZ / 2,
    parameter bit ALLOW_REVERSE = 1,
    parameter bit ENCODER_SINGLE_OUT = 1,
    parameter int PROTOCOL_VERSION = ENCODER_SINGLE_OUT ? 2 : 1,
    parameter bit INVERT_LEFT = 0,
    parameter bit INVERT_RIGHT = 0
) (
    input wire logic clk, arst_n, rx,
    input wire logic [1:0] left_ab, right_ab,
    input wire logic encoder_left_out, encoder_right_out,
    input wire logic motion_permit_async, recovery_req_async,
    input wire logic safety_ok_async, gate_fault_n_async,
    output logic tx, pwm_left, pwm_right,
    output logic [1:0] direction,
    output logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2,
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
    logic [7:0] snapshot_status_ext;
    logic [31:0] snapshot_left_period, snapshot_right_period;
    logic [31:0] snapshot_left_age, snapshot_right_age;
    logic raw_left, raw_right, interlock_active;
    logic output_allowed, clear_request;
    logic [15:0] safety_fault;
    logic [7:0] diagnostic_flags;
    logic diagnostic_stop;
    assign fault = safety_fault | {diagnostic_flags, 8'b0};
    reset_sync reset_release (.clk(clk), .arst_n(arst_n), .rst_n(rst_n));
    // Async assertion captures short LOW pulses; release needs clock edges.
    reset_sync safety_capture (.clk(clk), .arst_n(arst_n && safety_ok_async), .rst_n(safety_ok));
    reset_sync gate_capture (.clk(clk), .arst_n(arst_n && gate_fault_n_async), .rst_n(gate_ok));
    reset_sync permit_capture (.clk(clk), .arst_n(arst_n && motion_permit_async), .rst_n(motion_permit));
    input_sync_filter #(.WIDTH(2), .FILTER_N(1)) control_sync (
        .clk(clk), .rst_n(rst_n), .async_in({motion_permit_async, recovery_req_async}),
        .filtered(controls), .valid(inputs_valid));
    generate
        if (ENCODER_SINGLE_OUT && PROTOCOL_VERSION == 2) begin : g_single_out
            pulse_encoder_pair #(.FILTER_N(FILTER_N), .SNAPSHOT_CYCLES(SNAPSHOT_CYCLES)) encoders (
                .clk(clk), .rst_n(rst_n), .left_out(encoder_left_out), .right_out(encoder_right_out),
                .left_count(live_left), .right_count(live_right), .snapshot_valid(snapshot_valid),
                .snapshot_left(snapshot_left), .snapshot_right(snapshot_right),
                .snapshot_time(snapshot_time), .snapshot_seq(snapshot_seq),
                .snapshot_status(snapshot_status_ext),
                .snapshot_left_period(snapshot_left_period), .snapshot_right_period(snapshot_right_period),
                .snapshot_left_age(snapshot_left_age), .snapshot_right_age(snapshot_right_age));
            assign snapshot_status = 4'd0; // v1 status not exposed in v2 mode
        end else begin : g_quadrature
            encoder_pair #(.FILTER_N(FILTER_N), .SNAPSHOT_CYCLES(SNAPSHOT_CYCLES),
                           .SINGLE_OUT(ENCODER_SINGLE_OUT), .INVERT_LEFT(INVERT_LEFT), .INVERT_RIGHT(INVERT_RIGHT)) encoders (
                .clk(clk), .rst_n(rst_n), .left_ab(left_ab), .right_ab(right_ab),
                .left_out(encoder_left_out), .right_out(encoder_right_out),
                .left_count(live_left), .right_count(live_right), .snapshot_valid(snapshot_valid),
                .snapshot_left(snapshot_left), .snapshot_right(snapshot_right),
                .snapshot_time(snapshot_time), .snapshot_seq(snapshot_seq),
                .snapshot_status(snapshot_status));
            assign snapshot_status_ext = 8'd0;
            assign snapshot_left_period = 32'd0;
            assign snapshot_right_period = 32'd0;
            assign snapshot_left_age = 32'd0;
            assign snapshot_right_age = 32'd0;
        end
    endgenerate
    fpga_link #(.CLK_HZ(CLK_HZ), .BAUD(BAUD), .PERIOD_CYCLES(PERIOD_CYCLES),
                .ALLOW_REVERSE(ALLOW_REVERSE), .INTERBYTE_CYCLES(INTERBYTE_CYCLES),
               .FRAME_CYCLES(FRAME_CYCLES),
               .PROTOCOL_VERSION(PROTOCOL_VERSION), .ENCODER_SINGLE_OUT(ENCODER_SINGLE_OUT)) link (
        .clk(clk), .rst_n(rst_n), .rx(rx), .tx(tx), .context_load(context_load),
        .session_active(session_active), .active_session(active_session), .sequence_base(sequence_base),
        .command_enable(command_enable), .hello_request(hello_request), .arm_zero_request(arm_zero_request),
        .disable_request(disable_request), .clear_fault_request(clear_fault_request),
        .command_valid(command_valid), .command_rejected(command_rejected), .event_session(event_session),
        .event_sequence(event_sequence), .command_left(command_left), .command_right(command_right),
        .command_direction(command_direction), .receive_error(receive_error),
        .snapshot_valid(snapshot_valid), .snapshot_ready(snapshot_ready), .snapshot_dropped(snapshot_dropped),
        .snapshot_left(snapshot_left), .snapshot_right(snapshot_right), .snapshot_time(snapshot_time),
        .snapshot_seq(snapshot_seq), .snapshot_status(snapshot_status),
        .snapshot_status_ext(snapshot_status_ext),
        .snapshot_left_period(snapshot_left_period), .snapshot_right_period(snapshot_right_period),
        .snapshot_left_age(snapshot_left_age), .snapshot_right_age(snapshot_right_age),
        .safety_state(safety_state), .fault(fault),
        .status_sent(status_sent), .status_session(status_session), .status_state(status_state));
    generate if (PROTOCOL_VERSION == 2) begin : g_diagnostics
        runtime_diagnostics #(.SNAPSHOT_LIMIT(2 * SNAPSHOT_CYCLES),
                              .ENCODER_LIMIT(ENCODER_STALE_CYCLES)) monitor (
            .clk(clk), .rst_n(rst_n), .receive_error(receive_error),
            .command_rejected(command_rejected), .snapshot_dropped(snapshot_dropped),
            .pwm_rejected(pwm_rejected), .snapshot_valid(snapshot_valid),
            .motor_enable(motor_enable), .interlock_active(interlock_active),
            .request_left(command_left != 0), .request_right(command_right != 0),
            .raw_left(raw_left), .raw_right(raw_right), .safety_state(safety_state),
            .left_count(live_left), .right_count(live_right),
            .flags(diagnostic_flags), .critical_fault(diagnostic_stop));
    end else begin : g_no_diagnostics
        assign diagnostic_flags = 0;
        assign diagnostic_stop = 0;
    end endgenerate
    safety_fsm #(.WATCHDOG_CYCLES(WATCHDOG_CYCLES), .HANDSHAKE_CYCLES(HANDSHAKE_CYCLES),
                 .CLEAR_CYCLES(CLEAR_CYCLES), .CLEAR_HOLD_CYCLES(CLEAR_HOLD_CYCLES)) safety (
        .clk(clk), .rst_n(rst_n), .inputs_valid(inputs_valid), .motion_permit(motion_permit),
        .recovery_req(controls[0]), .safety_ok(safety_ok && !diagnostic_stop), .gate_ok(gate_ok),
        .hello_request(hello_request), .arm_zero_request(arm_zero_request),
        .disable_request(disable_request), .clear_fault_request(clear_fault_request),
        .command_valid(command_valid), .pwm_rejected(pwm_rejected),
        .event_session(event_session), .event_sequence(event_sequence), .status_sent(status_sent),
        .status_session(status_session), .status_state(status_state), .context_load(context_load),
        .session_active(session_active), .active_session(active_session), .sequence_base(sequence_base),
        .command_enable(command_enable), .motor_enable(motor_enable), .motor_command(motor_command),
        .recovery_ack(recovery_ack), .gate_clear(clear_request), .safety_state(safety_state), .fault(safety_fault));
    motor_pwm_pair #(.PERIOD_CYCLES(PERIOD_CYCLES), .ZERO_CYCLES(ZERO_CYCLES),
                     .SETUP_CYCLES(SETUP_CYCLES)) motors (
        .clk(clk), .rst_n(rst_n), .enable(motor_enable), .command_valid(motor_command),
        .command_left(command_left), .command_right(command_right), .command_direction(command_direction),
        .pwm_left(raw_left), .pwm_right(raw_right), .direction(direction),
        .interlock_active(interlock_active), .command_rejected(pwm_rejected));
    assign output_allowed = arst_n && rst_n && safety_ok_async && gate_fault_n_async &&
                            motion_permit_async && motor_enable && !diagnostic_stop;
    assign fpga_permit = output_allowed;
    assign gate_clear = clear_request && arst_n && safety_ok_async &&
                        !motion_permit_async && !recovery_req_async;
    assign pwm_left = raw_left && output_allowed;
    assign pwm_right = raw_right && output_allowed;
    drv8833_adapter driver_pins (
        .rst_n(arst_n && rst_n), .enable(output_allowed),
        .pwm_left(pwm_left), .pwm_right(pwm_right), .direction(direction),
        .drv_left_in1(drv_left_in1), .drv_left_in2(drv_left_in2),
        .drv_right_in1(drv_right_in1), .drv_right_in2(drv_right_in2));
endmodule
`default_nettype wire
