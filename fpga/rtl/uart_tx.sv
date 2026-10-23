`timescale 1ns/1ps
`default_nettype none
module uart_tx #(
    parameter int CLK_HZ = 27000000,
    parameter int BAUD = 115200
) (
    input  logic clk,
    input  logic rst_n,
    input  logic [7:0] data,
    input  logic valid,
    output logic ready,
    output logic tx,
    output logic done
);
    localparam int BIT_CYCLES = (CLK_HZ + BAUD / 2) / BAUD;
    localparam int CW = (BIT_CYCLES > 1) ? $clog2(BIT_CYCLES) : 1;
    logic busy;
    logic [9:0] shift;
    logic [3:0] bit_index;
    logic [CW-1:0] timer;
    assign ready = !busy;
    assign tx = busy ? shift[0] : 1'b1;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0; shift <= '1; bit_index <= 0; timer <= 0; done <= 0;
        end else begin
            done <= 0;
            if (!busy) begin
                if (valid) begin
                    shift <= {1'b1, data, 1'b0};
                    busy <= 1;
                    bit_index <= 0;
                    timer <= BIT_CYCLES - 1;
                end
            end else if (timer != 0) timer <= timer - 1'b1;
            else if (bit_index == 9) begin
                busy <= 0;
                done <= 1;
            end else begin
                shift <= {1'b1, shift[9:1]};
                bit_index <= bit_index + 1'b1;
                timer <= BIT_CYCLES - 1;
            end
        end
    end
endmodule
`default_nettype wire
