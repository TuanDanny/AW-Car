`timescale 1ns/1ps
`default_nettype none
module frame_tx #(
    parameter bit ENCODER_SINGLE_OUT = 0,
    parameter int PROTOCOL_VERSION = 1
) (
    input  logic clk,
    input  logic rst_n,
    input  logic flush,
    input  logic snapshot_valid,
    output logic snapshot_ready,
    output logic snapshot_dropped,
    input  logic [31:0] session,
    input  logic [31:0] snapshot_left,
    input  logic [31:0] snapshot_right,
    input  logic [31:0] snapshot_time,
    input  logic [15:0] snapshot_seq,
    input  logic [3:0] snapshot_status,
    input  logic [7:0] snapshot_status_ext,
    input  logic [31:0] snapshot_left_period,
    input  logic [31:0] snapshot_right_period,
    input  logic [31:0] snapshot_left_age,
    input  logic [31:0] snapshot_right_age,
    input  logic [7:0] safety_state,
    input  logic [15:0] fault,
    output logic byte_valid,
    input  logic byte_ready,
    output logic [7:0] byte_data,
    output logic byte_last,
    output logic [31:0] frame_session,
    output logic [7:0] frame_state
);
    logic busy;
    localparam int STATUS_LENGTH = (PROTOCOL_VERSION == 2) ? 34 : 18;
    localparam int LAST_BYTE = 12 + STATUS_LENGTH;
    logic [5:0] index;
    logic [31:0] frozen_session;
    logic [271:0] payload;
    logic [15:0] crc, next_crc;
    assign snapshot_ready = !busy && !flush;
    assign byte_valid = busy && !flush;
    assign byte_last = byte_valid && index == LAST_BYTE;
    assign frame_session = frozen_session;
    assign frame_state = payload[119:112];
    function automatic logic [7:0] select_byte(input logic [5:0] idx,
            input logic [31:0] session_value, input logic [271:0] sample,
            input logic [15:0] checksum);
        begin
            select_byte = 0;
            case (idx)
                0: select_byte = 8'ha5;
                1: select_byte = 8'h5a;
                2: select_byte = PROTOCOL_VERSION;
                3: select_byte = 8'h80;
                4: select_byte = STATUS_LENGTH;
                5, 6, 7, 8: select_byte = session_value[(idx-5)*8 +: 8];
                9, 10: select_byte = sample[96+(idx-9)*8 +: 8];
                default: begin
                    if (idx == 11 + STATUS_LENGTH)
                        select_byte = checksum[7:0];
                    else if (idx == 12 + STATUS_LENGTH)
                        select_byte = checksum[15:8];
                    else if (idx >= 11 && idx < 11 + STATUS_LENGTH)
                        select_byte = sample[(idx-11)*8 +: 8];
                end
            endcase
        end
    endfunction
    assign byte_data = select_byte(index, frozen_session, payload, crc);
    crc16_byte crc_step (.crc(crc), .data(byte_data), .next_crc(next_crc));
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0; index <= 0; payload <= 0; frozen_session <= 0;
            crc <= 16'hffff; snapshot_dropped <= 0;
        end else begin
            snapshot_dropped <= snapshot_valid && !snapshot_ready;
            if (flush) begin busy <= 0; index <= 0; crc <= 16'hffff; end
            else if (snapshot_valid && snapshot_ready) begin
                if (PROTOCOL_VERSION == 2)
                    payload <= {snapshot_right_age, snapshot_left_age,
                                snapshot_right_period, snapshot_left_period,
                                snapshot_status_ext, fault, safety_state,
                                snapshot_seq, snapshot_time, snapshot_right, snapshot_left};
                else
                    payload <= {{128{1'b0}}, {3'b000, ENCODER_SINGLE_OUT, snapshot_status}, fault,
                                safety_state, snapshot_seq, snapshot_time,
                                snapshot_right, snapshot_left};
                frozen_session <= session;
                busy <= 1; index <= 0; crc <= 16'hffff;
            end else if (byte_valid && byte_ready) begin
                if (index >= 2 && index < 11 + STATUS_LENGTH) crc <= next_crc;
                if (index == LAST_BYTE) begin busy <= 0; index <= 0; end
                else index <= index + 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
