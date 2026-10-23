`timescale 1ns/1ps
`default_nettype none
module fpga_link #(
    parameter int CLK_HZ = 27000000,
    parameter int BAUD = 115200,
    parameter int PERIOD_CYCLES = 1350,
    parameter bit ALLOW_REVERSE = 0,
    parameter int INTERBYTE_CYCLES = 54000,
    parameter int FRAME_CYCLES = 135000
) (
    input  logic clk,
    input  logic rst_n,
    input  logic rx,
    output logic tx,
    input  logic context_load,
    input  logic session_active,
    input  logic [31:0] active_session,
    input  logic [15:0] sequence_base,
    input  logic command_enable,
    output logic hello_request,
    output logic arm_zero_request,
    output logic disable_request,
    output logic clear_fault_request,
    output logic command_valid,
    output logic command_rejected,
    output logic [31:0] event_session,
    output logic [15:0] event_sequence,
    output logic [15:0] command_left,
    output logic [15:0] command_right,
    output logic [1:0] command_direction,
    output logic receive_error,
    input  logic snapshot_valid,
    output logic snapshot_ready,
    output logic snapshot_dropped,
    input  logic [31:0] snapshot_left,
    input  logic [31:0] snapshot_right,
    input  logic [31:0] snapshot_time,
    input  logic [15:0] snapshot_seq,
    input  logic [3:0] snapshot_status,
    input  logic [7:0] safety_state,
    input  logic [15:0] fault
);
    logic [7:0] rx_byte, tx_byte, kind;
    logic rx_valid, framing_error, break_error, frame_valid, tx_valid, tx_ready, tx_done;
    logic [31:0] session;
    logic [15:0] frame_seq;
    logic [47:0] payload;
    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) receiver (
        .clk(clk), .rst_n(rst_n), .rx(rx), .data(rx_byte), .valid(rx_valid),
        .framing_error(framing_error), .break_error(break_error));
    frame_rx #(.INTERBYTE_CYCLES(INTERBYTE_CYCLES), .FRAME_CYCLES(FRAME_CYCLES)) parser (
        .clk(clk), .rst_n(rst_n), .flush(context_load), .byte_data(rx_byte),
        .byte_valid(rx_valid), .byte_error(framing_error || break_error),
        .frame_valid(frame_valid), .frame_error(receive_error), .frame_type(kind),
        .frame_session(session), .frame_sequence(frame_seq), .frame_payload(payload));
    command_guard #(.PERIOD_CYCLES(PERIOD_CYCLES), .ALLOW_REVERSE(ALLOW_REVERSE)) guard (
        .clk(clk), .rst_n(rst_n), .context_load(context_load), .session_active(session_active),
        .active_session(active_session), .sequence_base(sequence_base), .command_enable(command_enable),
        .frame_valid(frame_valid), .frame_type(kind), .frame_session(session),
        .frame_sequence(frame_seq), .frame_payload(payload), .hello_request(hello_request),
        .arm_zero_request(arm_zero_request), .disable_request(disable_request),
        .clear_fault_request(clear_fault_request), .command_valid(command_valid), .rejected(command_rejected),
        .event_session(event_session), .event_sequence(event_sequence),
        .command_left(command_left), .command_right(command_right), .command_direction(command_direction));
    frame_tx serializer (
        .clk(clk), .rst_n(rst_n), .flush(context_load), .snapshot_valid(snapshot_valid),
        .snapshot_ready(snapshot_ready), .snapshot_dropped(snapshot_dropped),
        .session(session_active ? active_session : 32'd0), .snapshot_left(snapshot_left),
        .snapshot_right(snapshot_right), .snapshot_time(snapshot_time), .snapshot_seq(snapshot_seq),
        .snapshot_status(snapshot_status), .safety_state(safety_state), .fault(fault),
        .byte_valid(tx_valid), .byte_ready(tx_ready), .byte_data(tx_byte));
    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) transmitter (
        .clk(clk), .rst_n(rst_n), .data(tx_byte), .valid(tx_valid),
        .ready(tx_ready), .tx(tx), .done(tx_done));
endmodule
`default_nettype wire
