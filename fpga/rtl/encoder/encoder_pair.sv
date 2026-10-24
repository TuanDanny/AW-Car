`timescale 1ns/1ps
`default_nettype none
module encoder_pair #(
    parameter int COUNT_WIDTH = 32,
    parameter int TIME_WIDTH = 32,
    parameter int SEQ_WIDTH = 16,
    parameter int FILTER_N = 3,
    parameter int SNAPSHOT_CYCLES = 270000,
    parameter int INVERT_LEFT = 0,
    parameter int INVERT_RIGHT = 0
) (
    input  logic clk,
    input  logic rst_n,
    input  logic [1:0] left_ab,
    input  logic [1:0] right_ab,
    output logic [COUNT_WIDTH-1:0] left_count,
    output logic [COUNT_WIDTH-1:0] right_count,
    output logic snapshot_valid,
    output logic [COUNT_WIDTH-1:0] snapshot_left,
    output logic [COUNT_WIDTH-1:0] snapshot_right,
    output logic [TIME_WIDTH-1:0] snapshot_time,
    output logic [SEQ_WIDTH-1:0] snapshot_seq,
    output logic [3:0] snapshot_status
);
    localparam int TIMER_WIDTH = (SNAPSHOT_CYCLES > 1) ? $clog2(SNAPSHOT_CYCLES) : 1;
    logic [1:0] left_filtered, right_filtered;
    logic left_valid, right_valid, left_error, right_error;
    logic left_ready, right_ready;
    logic [1:0] sticky_error;
    logic [TIMER_WIDTH-1:0] timer;
    logic [TIME_WIDTH-1:0] timestamp;
    input_sync_filter #(.FILTER_N(FILTER_N)) left_filter (
        .clk(clk), .rst_n(rst_n), .async_in(left_ab),
        .filtered(left_filtered), .valid(left_valid));
    input_sync_filter #(.FILTER_N(FILTER_N)) right_filter (
        .clk(clk), .rst_n(rst_n), .async_in(right_ab),
        .filtered(right_filtered), .valid(right_valid));
    quadrature_decoder #(.COUNT_WIDTH(COUNT_WIDTH), .INVERT(INVERT_LEFT)) left_decoder (
        .clk(clk), .rst_n(rst_n), .sample_valid(left_valid), .ab(left_filtered),
        .count(left_count), .invalid_event(left_error), .initialized(left_ready));
    quadrature_decoder #(.COUNT_WIDTH(COUNT_WIDTH), .INVERT(INVERT_RIGHT)) right_decoder (
        .clk(clk), .rst_n(rst_n), .sample_valid(right_valid), .ab(right_filtered),
        .count(right_count), .invalid_event(right_error), .initialized(right_ready));
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sticky_error <= 0;
            timer <= 0;
            timestamp <= 0;
            snapshot_valid <= 0;
            snapshot_left <= 0;
            snapshot_right <= 0;
            snapshot_time <= 0;
            snapshot_seq <= 0;
            snapshot_status <= 0;
        end else begin
            timestamp <= timestamp + 1'b1;
            sticky_error <= sticky_error | {right_error, left_error};
            snapshot_valid <= 1'b0;
            if (timer == SNAPSHOT_CYCLES - 1) begin
                timer <= 0;
                snapshot_valid <= 1'b1;
                snapshot_left <= left_count;
                snapshot_right <= right_count;
                snapshot_time <= timestamp;
                snapshot_seq <= snapshot_seq + 1'b1;
                snapshot_status <= {right_ready, left_ready, sticky_error};
            end else timer <= timer + 1'b1;
        end
    end
endmodule
`default_nettype wire
