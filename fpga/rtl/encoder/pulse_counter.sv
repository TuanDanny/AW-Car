`timescale 1ns/1ps
`default_nettype none
// Single OUT pulse encoder: count rising edges, never infer physical direction.
// Input is already synchronized/filtered; the first valid level only establishes
// the baseline (including a HIGH boot level, which must not invent an edge).
module pulse_counter #(
    parameter int COUNT_WIDTH = 32,
    parameter int TIME_WIDTH = 32
) (
    input  logic clk,
    input  logic rst_n,
    input  logic sample_valid,
    input  logic pulse,
    output logic [COUNT_WIDTH-1:0] count,
    output logic [TIME_WIDTH-1:0] period_ticks,
    output logic [TIME_WIDTH-1:0] age_ticks,
    output logic initialized,
    output logic edge_seen,
    output logic period_valid
);
    localparam logic [TIME_WIDTH-1:0] NO_EDGE = {TIME_WIDTH{1'b1}};
    logic previous;
    logic rising;
    assign rising = sample_valid && initialized && !previous && pulse;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= '0;
            period_ticks <= '0;
            age_ticks <= NO_EDGE;
            initialized <= 1'b0;
            edge_seen <= 1'b0;
            period_valid <= 1'b0;
            previous <= 1'b0;
        end else begin
            if (sample_valid) begin
                previous <= pulse;
                initialized <= 1'b1;
            end
            if (rising) begin
                count <= count + 1'b1;
                // age is zero on the previous rising edge; add current tick.
                if (edge_seen && age_ticks != NO_EDGE) begin
                    period_ticks <= age_ticks + 1'b1;
                    period_valid <= 1'b1;
                end else begin
                    period_ticks <= '0;
                    period_valid <= 1'b0;
                end
                edge_seen <= 1'b1;
                age_ticks <= '0;
            end else if (edge_seen) begin
                if (age_ticks == NO_EDGE - 1'b1) begin
                    // Stop claiming a fresh period when the age counter saturates.
                    age_ticks <= NO_EDGE;
                    period_valid <= 1'b0;
                    edge_seen <= 1'b0;
                end else if (age_ticks != NO_EDGE) begin
                    age_ticks <= age_ticks + 1'b1;
                end
            end
        end
    end
endmodule
`default_nettype wire
