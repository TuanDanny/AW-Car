`timescale 1ns/1ps
`default_nettype none
module input_sync_filter #(
    parameter integer WIDTH = 2,
    parameter integer FILTER_N = 3
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [WIDTH-1:0] async_in,
    output reg  [WIDTH-1:0] filtered,
    output reg valid
);
    function integer bits_for;
        input integer value;
        integer v;
        begin
            v = value - 1;
            bits_for = 0;
            while (v > 0) begin bits_for = bits_for + 1; v = v >> 1; end
            if (bits_for == 0) bits_for = 1;
        end
    endfunction
    localparam integer CW = bits_for(FILTER_N + 1);
    (* ASYNC_REG = "TRUE" *) reg [WIDTH-1:0] meta_ff, sync_ff;
    reg [1:0] ready;
    reg [WIDTH-1:0] candidate;
    reg [CW-1:0] stable;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            meta_ff <= 0;
            sync_ff <= 0;
            ready <= 0;
            candidate <= 0;
            stable <= 0;
            filtered <= 0;
            valid <= 0;
        end else begin
            meta_ff <= async_in;
            sync_ff <= meta_ff;
            ready <= {ready[0], 1'b1};
            if (ready[1]) begin
                if (FILTER_N == 1) begin
                    filtered <= sync_ff;
                    valid <= 1'b1;
                end else if (sync_ff != candidate) begin
                    candidate <= sync_ff;
                    stable <= 1;
                end else if (stable < FILTER_N) begin
                    stable <= stable + 1'b1;
                    if (stable == FILTER_N - 1) begin
                        filtered <= sync_ff;
                        valid <= 1'b1;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
