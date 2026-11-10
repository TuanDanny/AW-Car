`timescale 1ns/1ps
`default_nettype none
module simplev1_core #(
    parameter int WATCHDOG_CYCLES = 13500000,
    parameter int ENCODER_FILTER_CYCLES = 256,
    parameter int LED_HALF_CYCLES = 13500000
) (
    input wire logic clk, arst_n,
    input wire logic spi_mosi, spi_sclk, spi_cs_n,
    input wire logic enc_left, enc_right,
    output logic spi_miso,
    output logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2,
    output logic [5:0] leds_n
);
    localparam int WATCHDOG_WIDTH = WATCHDOG_CYCLES > 1 ? $clog2(WATCHDOG_CYCLES) : 1;
    logic [1:0] reset_release;
    wire logic rst_n = reset_release[1];
    logic command_valid;
    logic [15:0] command_seq, applied_seq;
    logic signed [15:0] command_left, command_right, target_left, target_right;
    logic [WATCHDOG_WIDTH-1:0] watchdog_ticks;
    logic timed_out, left_seen, right_seen;
    logic [31:0] left_count, right_count, left_period, right_period, left_age, right_age;
    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) reset_release <= '0;
        else reset_release <= {reset_release[0], 1'b1};
    end
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            applied_seq <= '0; target_left <= '0; target_right <= '0;
            watchdog_ticks <= '0; timed_out <= 1'b1;
        end else if (command_valid) begin
            // Atomic committed setpoints. Physical outputs latch at the next PWM boundary.
            applied_seq <= command_seq;
            target_left <= command_left; target_right <= command_right;
            watchdog_ticks <= '0; timed_out <= 1'b0;
        end else if (!timed_out) begin
            if (watchdog_ticks == WATCHDOG_CYCLES - 1) begin
                timed_out <= 1'b1;
                target_left <= '0; target_right <= '0;
            end else watchdog_ticks <= watchdog_ticks + 1'b1;
        end
    end
    spi32 link (
        .clk(clk), .rst_n(rst_n), .cs_n(spi_cs_n), .sclk(spi_sclk), .mosi(spi_mosi),
        .status_flags({5'b0, right_seen, left_seen, timed_out}), .applied_seq(applied_seq),
        .left_count(left_count), .right_count(right_count), .left_period(left_period),
        .right_period(right_period), .left_age(left_age), .right_age(right_age),
        .miso(spi_miso), .command_valid(command_valid), .command_seq(command_seq),
        .command_left(command_left), .command_right(command_right)
    );
    encoder #(.FILTER_CYCLES(ENCODER_FILTER_CYCLES)) left_encoder (
        .clk(clk), .rst_n(rst_n), .pin_in(enc_left), .count(left_count),
        .period_ticks(left_period), .age_ticks(left_age), .seen(left_seen)
    );
    encoder #(.FILTER_CYCLES(ENCODER_FILTER_CYCLES)) right_encoder (
        .clk(clk), .rst_n(rst_n), .pin_in(enc_right), .count(right_count),
        .period_ticks(right_period), .age_ticks(right_age), .seen(right_seen)
    );
    pwm_pair pwm (
        .clk(clk), .rst_n(rst_n), .enable(!timed_out),
        .target_left(target_left), .target_right(target_right),
        .left_in1(drv_left_in1), .left_in2(drv_left_in2),
        .right_in1(drv_right_in1), .right_in2(drv_right_in2)
    );
    status_leds #(.HALF_PERIOD_CYCLES(LED_HALF_CYCLES)) observer (
        .clk(clk), .rst_n(rst_n), .connected(!timed_out), .leds_n(leds_n)
    );
endmodule
