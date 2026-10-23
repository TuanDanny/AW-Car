`timescale 1ns/1ps
`default_nettype none
module frame_rx #(
    parameter int INTERBYTE_CYCLES = 54000,
    parameter int FRAME_CYCLES = 135000
) (
    input  logic clk,
    input  logic rst_n,
    input  logic flush,
    input  logic [7:0] byte_data,
    input  logic byte_valid,
    input  logic byte_error,
    output logic frame_valid,
    output logic frame_error,
    output logic [7:0] frame_type,
    output logic [31:0] frame_session,
    output logic [15:0] frame_sequence,
    output logic [47:0] frame_payload
);
    localparam int GW = (INTERBYTE_CYCLES > 1) ? $clog2(INTERBYTE_CYCLES) : 1;
    localparam int FW = (FRAME_CYCLES > 1) ? $clog2(FRAME_CYCLES) : 1;
    typedef enum logic [2:0] {SYNC0, SYNC1, BODY, CRC_LO, CRC_HI} state_t;
    state_t state;
    logic [GW-1:0] gap_count;
    logic [FW-1:0] age_count;
    logic [3:0] index;
    logic [2:0] length;
    logic [15:0] crc, next_crc;
    logic [7:0] received_crc_lo;
    logic timeout_due, bad_header;
    assign timeout_due = state != SYNC0 &&
        (gap_count == INTERBYTE_CYCLES - 1 || age_count == FRAME_CYCLES - 1);
    assign bad_header = (index == 0 && byte_data != 1) ||
        (index == 1 && (byte_data < 1 || byte_data > 5)) ||
        (index == 2 && byte_data != ((frame_type == 3) ? 6 : 0));
    crc16_byte crc_step (.crc(crc), .data(byte_data), .next_crc(next_crc));
    // Fields are staging registers; only frame_valid authorizes consumption.
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= SYNC0; gap_count <= 0; age_count <= 0; index <= 0; length <= 0;
            crc <= 16'hffff; received_crc_lo <= 0;
            frame_valid <= 0; frame_error <= 0; frame_type <= 0;
            frame_session <= 0; frame_sequence <= 0; frame_payload <= 0;
        end else begin
            frame_valid <= 0; frame_error <= 0;
            if (state != SYNC0) begin
                gap_count <= gap_count + 1'b1;
                age_count <= age_count + 1'b1;
            end
            if (flush || byte_error) begin
                state <= SYNC0; gap_count <= 0; age_count <= 0;
                frame_error <= byte_error;
            end else if (timeout_due || (byte_valid && state == BODY && bad_header)) begin
                frame_error <= 1;
                if (byte_valid && byte_data == 8'ha5) state <= SYNC1;
                else state <= SYNC0;
                gap_count <= 0; age_count <= 0;
            end else if (byte_valid) begin
                gap_count <= 0;
                case (state)
                    SYNC0: if (byte_data == 8'ha5) begin
                        state <= SYNC1; age_count <= 0;
                    end
                    SYNC1: if (byte_data == 8'h5a) begin
                        state <= BODY; index <= 0; crc <= 16'hffff;
                        frame_session <= 0; frame_sequence <= 0; frame_payload <= 0;
                    end else begin
                        if (byte_data == 8'ha5) state <= SYNC1;
                        else state <= SYNC0;
                        age_count <= 0;
                    end
                    BODY: begin
                        crc <= next_crc;
                        index <= index + 1'b1;
                        case (index)
                            1: frame_type <= byte_data;
                            2: length <= byte_data[2:0];
                            3, 4, 5, 6: frame_session[(index-3)*8 +: 8] <= byte_data;
                            7, 8: frame_sequence[(index-7)*8 +: 8] <= byte_data;
                            9, 10, 11, 12, 13, 14: frame_payload[(index-9)*8 +: 8] <= byte_data;
                            default: begin end
                        endcase
                        if (index == 8 + length) state <= CRC_LO;
                    end
                    CRC_LO: begin received_crc_lo <= byte_data; state <= CRC_HI; end
                    CRC_HI: begin
                        if ({byte_data, received_crc_lo} == crc) frame_valid <= 1;
                        else frame_error <= 1;
                        // A failed CRC's final byte may also begin the next preamble.
                        if ({byte_data, received_crc_lo} != crc && byte_data == 8'ha5)
                            state <= SYNC1;
                        else state <= SYNC0;
                        age_count <= 0;
                    end
                    default: state <= SYNC0;
                endcase
            end
        end
    end
endmodule
`default_nettype wire
