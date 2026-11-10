`timescale 1ns/1ps
`default_nettype none
// Board shell: configuration-initialized POR and an asynchronous S2 output mask.
module simplev1_nano9k #(
    parameter int POR_CYCLES = 1024
) (
    input wire logic clk, arst_n,
    input wire logic spi_mosi, spi_sclk, spi_cs_n,
    input wire logic enc_left, enc_right,
    output logic spi_miso,
    output logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2,
    output logic [5:0] leds_n
);
    localparam int WIDTH = POR_CYCLES > 1 ? $clog2(POR_CYCLES) : 1;
    logic [WIDTH-1:0] por_ticks = '0;
    logic por_ready = 1'b0;
    wire logic core_reset_n = arst_n && por_ready;
    logic left1, left2, right1, right2;
    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin por_ticks <= '0; por_ready <= 1'b0; end
        else if (!por_ready) begin
            if (por_ticks == POR_CYCLES - 1) por_ready <= 1'b1;
            else por_ticks <= por_ticks + 1'b1;
        end
    end
    simplev1_core core (
        .clk(clk), .arst_n(core_reset_n), .spi_mosi(spi_mosi), .spi_sclk(spi_sclk),
        .spi_cs_n(spi_cs_n), .spi_miso(spi_miso), .enc_left(enc_left), .enc_right(enc_right),
        .drv_left_in1(left1), .drv_left_in2(left2), .drv_right_in1(right1),
        .drv_right_in2(right2), .leds_n(leds_n)
    );
    assign drv_left_in1 = core_reset_n && left1;
    assign drv_left_in2 = core_reset_n && left2;
    assign drv_right_in1 = core_reset_n && right1;
    assign drv_right_in2 = core_reset_n && right2;
endmodule
