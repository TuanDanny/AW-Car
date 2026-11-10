`timescale 1ns/1ps
`default_nettype none
module encoder #(
    parameter int FILTER_CYCLES = 256
) (
    input wire logic clk, rst_n, pin_in,
    output logic [31:0] count, period_ticks, age_ticks,
    output logic seen
);
    localparam int FILTER_WIDTH = $clog2(FILTER_CYCLES + 1) > 0 ? $clog2(FILTER_CYCLES + 1) : 1;
    (* syn_keep = 1 *) logic meta_ff, sync_ff;
    logic candidate, filtered, initialized;
    logic [FILTER_WIDTH-1:0] stable_ticks;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            meta_ff <= 1'b0; sync_ff <= 1'b0;
        end else begin
            meta_ff <= pin_in; sync_ff <= meta_ff;
        end
    end
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            candidate <= 1'b0; filtered <= 1'b0; initialized <= 1'b0; stable_ticks <= '0;
            count <= '0; period_ticks <= '0; age_ticks <= '0; seen <= 1'b0;
        end else begin
            if (seen && age_ticks != 32'hffffffff) age_ticks <= age_ticks + 1'b1;
            if (sync_ff != candidate) begin
                candidate <= sync_ff;
                stable_ticks <= 1;
            end else if (stable_ticks < FILTER_CYCLES) begin
                stable_ticks <= stable_ticks + 1'b1;
            end else if (!initialized) begin
                // Establish the initial level without inventing a rising edge.
                initialized <= 1'b1;
                filtered <= candidate;
            end else if (filtered != candidate) begin
                filtered <= candidate;
                if (candidate) begin
                    count <= count + 1'b1; // unsigned wrap, independent of motor direction
                    period_ticks <= !seen ? 32'b0 :
                        (age_ticks == 32'hffffffff ? 32'hffffffff : age_ticks + 1'b1);
                    age_ticks <= '0;
                    seen <= 1'b1;
                end
            end
        end
    end
endmodule
