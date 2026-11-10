`timescale 1ns/1ps
`default_nettype none
module status_leds #(
    parameter int HALF_PERIOD_CYCLES = 13500000
) (
    input wire logic clk, rst_n, connected,
    output logic [5:0] leds_n
);
    localparam int WIDTH = HALF_PERIOD_CYCLES > 1 ? $clog2(HALF_PERIOD_CYCLES) : 1;
    logic [WIDTH-1:0] ticks;
    logic blink;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ticks <= '0; blink <= 1'b0; end
        else if (connected) begin ticks <= '0; blink <= 1'b0; end
        else if (ticks == HALF_PERIOD_CYCLES - 1) begin ticks <= '0; blink <= !blink; end
        else ticks <= ticks + 1'b1;
    end
    assign leds_n = !rst_n ? 6'b111111 : {5'b11111, !(connected || blink)};
endmodule
