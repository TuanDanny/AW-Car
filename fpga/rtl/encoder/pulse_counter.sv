`timescale 1ns/1ps
`default_nettype none
// One OUT measures rotation magnitude only, including coasting/unpowered motion.
// The input must already be synchronized and filtered in this clock domain.
module pulse_counter #(
    parameter int COUNT_WIDTH = 32
) (
    input  logic clk,
    input  logic rst_n,
    input  logic sample_valid,
    input  logic pulse,
    output logic [COUNT_WIDTH-1:0] count,
    output logic initialized
);
    logic previous;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 0;
            previous <= 0;
            initialized <= 0;
        end else if (sample_valid) begin
            // An initial HIGH is a baseline, not a measured rising edge.
            if (initialized && pulse && !previous) count <= count + 1'b1;
            previous <= pulse;
            initialized <= 1;
        end
    end
endmodule
`default_nettype wire
