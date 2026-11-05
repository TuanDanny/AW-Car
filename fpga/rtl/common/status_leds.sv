`timescale 1ns/1ps
`default_nettype none
// Read-only observer. No control/permit outputs and no derived clock.
module status_leds #(
    parameter int BLINK_HALF_CYCLES = 13500000
) (
    input wire logic clk, rst_n,
    input wire logic [7:0] safety_state,
    input wire logic [15:0] fault,
    output logic [5:0] leds_n
);
    localparam int CW = BLINK_HALF_CYCLES > 1 ? $clog2(BLINK_HALF_CYCLES) : 1;
    logic [CW-1:0] count;
    logic dark_half;
    logic failed, waiting;
    // Safety errors and only the two fatal diagnostics outrank connection.
    assign failed = |(fault & 16'h88ff) || safety_state >= 4;
    assign waiting = safety_state == 0 && !failed;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin count <= 0; dark_half <= 0; end
        else if (!waiting) begin count <= 0; dark_half <= 0; end
        else if (count == BLINK_HALF_CYCLES - 1) begin
            count <= 0; dark_half <= !dark_half;
        end else count <= count + 1'b1;
    end
    always_comb begin
        leds_n = 6'b111111; // Active-low; all OFF during reset/POR.
        if (rst_n) begin
            if (failed) leds_n = 6'b000000;
            else case (safety_state)
                0: leds_n = dark_half ? 6'b111111 : 6'b111110;
                1, 2, 3: leds_n = 6'b111110;
                default: leds_n = 6'b000000;
            endcase
        end
    end
endmodule
`default_nettype wire
