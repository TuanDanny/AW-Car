`timescale 1ns/1ps
`default_nettype none
module quadrature_decoder #(
    parameter integer COUNT_WIDTH = 32,
    parameter integer INVERT = 0
) (
    input  wire clk,
    input  wire rst_n,
    input  wire sample_valid,
    input  wire [1:0] ab,
    output reg [COUNT_WIDTH-1:0] count,
    output reg invalid_event,
    output reg initialized
);
    reg [1:0] previous;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 0;
            previous <= 0;
            initialized <= 0;
            invalid_event <= 0;
        end else begin
            invalid_event <= 0;
            if (sample_valid) begin
                previous <= ab;
                initialized <= 1'b1;
                if (initialized) begin
                    case ({previous, ab})
                        4'b0001, 4'b0111, 4'b1110, 4'b1000:
                            if (INVERT != 0) count <= count - 1'b1;
                            else count <= count + 1'b1;
                        4'b0010, 4'b1011, 4'b1101, 4'b0100:
                            if (INVERT != 0) count <= count + 1'b1;
                            else count <= count - 1'b1;
                        4'b0011, 4'b1100, 4'b0110, 4'b1001:
                            invalid_event <= 1'b1;
                        default: begin end
                    endcase
                end
            end
        end
    end
endmodule
`default_nettype wire
