`timescale 1ns/1ps
`default_nettype none
// Two independent single-OUT encoders. Count/period/age/status all snapshot
// atomically every SNAPSHOT_CYCLES; direction is explicitly NOT observable.
module pulse_encoder_pair #(
    parameter int COUNT_WIDTH = 32,
    parameter int TIME_WIDTH = 32,
    parameter int SEQ_WIDTH = 16,
    parameter int FILTER_N = 3,
    parameter int SNAPSHOT_CYCLES = 270000
) (
    input  logic clk,
    input  logic rst_n,
    input  logic left_out,
    input  logic right_out,
    output logic [COUNT_WIDTH-1:0] left_count,
    output logic [COUNT_WIDTH-1:0] right_count,
    output logic snapshot_valid,
    output logic [COUNT_WIDTH-1:0] snapshot_left,
    output logic [COUNT_WIDTH-1:0] snapshot_right,
    output logic [TIME_WIDTH-1:0] snapshot_time,
    output logic [SEQ_WIDTH-1:0] snapshot_seq,
    output logic [7:0] snapshot_status,
    output logic [TIME_WIDTH-1:0] snapshot_left_period,
    output logic [TIME_WIDTH-1:0] snapshot_right_period,
    output logic [TIME_WIDTH-1:0] snapshot_left_age,
    output logic [TIME_WIDTH-1:0] snapshot_right_age
);
    localparam int TIMER_WIDTH = (SNAPSHOT_CYCLES > 1) ? $clog2(SNAPSHOT_CYCLES) : 1;
    logic left_filtered, right_filtered, left_valid, right_valid;
    logic left_initialized, right_initialized, left_edge_seen, right_edge_seen;
    logic left_period_valid, right_period_valid;
    logic [TIME_WIDTH-1:0] live_left_period, live_right_period;
    logic [TIME_WIDTH-1:0] live_left_age, live_right_age;
    logic [TIMER_WIDTH-1:0] timer;
    logic [TIME_WIDTH-1:0] timestamp;

    input_sync_filter #(.WIDTH(1), .FILTER_N(FILTER_N)) left_filter (
        .clk(clk), .rst_n(rst_n), .async_in(left_out),
        .filtered(left_filtered), .valid(left_valid));
    input_sync_filter #(.WIDTH(1), .FILTER_N(FILTER_N)) right_filter (
        .clk(clk), .rst_n(rst_n), .async_in(right_out),
        .filtered(right_filtered), .valid(right_valid));
    pulse_counter #(.COUNT_WIDTH(COUNT_WIDTH), .TIME_WIDTH(TIME_WIDTH)) left_encoder (
        .clk(clk), .rst_n(rst_n), .sample_valid(left_valid), .pulse(left_filtered),
        .count(left_count), .period_ticks(live_left_period), .age_ticks(live_left_age),
        .initialized(left_initialized), .edge_seen(left_edge_seen),
        .period_valid(left_period_valid));
    pulse_counter #(.COUNT_WIDTH(COUNT_WIDTH), .TIME_WIDTH(TIME_WIDTH)) right_encoder (
        .clk(clk), .rst_n(rst_n), .sample_valid(right_valid), .pulse(right_filtered),
        .count(right_count), .period_ticks(live_right_period), .age_ticks(live_right_age),
        .initialized(right_initialized), .edge_seen(right_edge_seen),
        .period_valid(right_period_valid));

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            timer <= '0;
            timestamp <= '0;
            snapshot_valid <= 1'b0;
            snapshot_left <= '0;
            snapshot_right <= '0;
            snapshot_time <= '0;
            snapshot_seq <= '0;
            snapshot_status <= '0;
            snapshot_left_period <= '0;
            snapshot_right_period <= '0;
            snapshot_left_age <= '0;
            snapshot_right_age <= '0;
        end else begin
            timestamp <= timestamp + 1'b1;
            snapshot_valid <= 1'b0;
            if (timer == SNAPSHOT_CYCLES - 1) begin
                timer <= '0;
                snapshot_valid <= 1'b1;
                snapshot_left <= left_count;
                snapshot_right <= right_count;
                snapshot_time <= timestamp;
                snapshot_seq <= snapshot_seq + 1'b1;
                // v2: bit4 SINGLE_OUT, bit2/3 initialized, bit0/1 period valid,
                // bit5/6 first rising edge seen, bit7 direction-known=0.
                snapshot_status <= {1'b0, right_edge_seen, left_edge_seen, 1'b1,
                                    right_initialized, left_initialized,
                                    right_period_valid, left_period_valid};
                snapshot_left_period <= live_left_period;
                snapshot_right_period <= live_right_period;
                snapshot_left_age <= live_left_age;
                snapshot_right_age <= live_right_age;
            end else timer <= timer + 1'b1;
        end
    end
endmodule
`default_nettype wire
