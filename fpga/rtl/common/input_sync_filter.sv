`timescale 1ns/1ps
`default_nettype none
module input_sync_filter #(
    parameter int WIDTH = 2,
    parameter int FILTER_N = 3
) (
    input  logic clk,
    input  logic rst_n,
    input  logic [WIDTH-1:0] async_in,
    output logic [WIDTH-1:0] filtered,
    output logic valid
);
    localparam int CW = ((FILTER_N + 1) > 1) ? $clog2(FILTER_N + 1) : 1;
    (* ASYNC_REG = "TRUE" *) logic [WIDTH-1:0] meta_ff, sync_ff;
    logic [1:0] ready;
    logic [WIDTH-1:0] candidate;
    logic [CW-1:0] stable;
    always_ff @(posedge clk or negedge rst_n) begin
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
