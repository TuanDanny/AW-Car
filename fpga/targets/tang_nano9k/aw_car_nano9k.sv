`timescale 1ns/1ps
`default_nettype none
// Physical shell only. Declaration initialization maps to Gowin configuration
// reset; an external, independently default-OFF driver gate is still required.
module aw_car_nano9k #(
    parameter int POR_CYCLES = 1024
) (
    input wire logic clk, arst_n, rx,
    input wire logic left_out, right_out,
    input wire logic motion_permit_async, recovery_req_async,
    input wire logic safety_ok_async, gate_fault_n_async,
    output logic tx,
    output logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2,
    output logic fpga_permit, recovery_ack, gate_clear
);
    localparam int POR_WIDTH = (POR_CYCLES > 1) ? $clog2(POR_CYCLES) : 1;
    logic [POR_WIDTH-1:0] por_count = '0;
    logic por_ready = 1'b0;
    logic core_arst_n;
    logic raw_left_in1, raw_left_in2, raw_right_in1, raw_right_in2;
    logic raw_permit, raw_ack, raw_clear;

    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin
            por_count <= '0;
            por_ready <= 1'b0;
        end else if (!por_ready) begin
            if (por_count == POR_CYCLES - 1) por_ready <= 1'b1;
            else por_count <= por_count + 1'b1;
        end
    end
    assign core_arst_n = arst_n && por_ready;
    aw_car_top core (
        .clk(clk), .arst_n(core_arst_n), .rx(rx),
        .left_out(left_out), .right_out(right_out),
        .motion_permit_async(motion_permit_async), .recovery_req_async(recovery_req_async),
        .safety_ok_async(safety_ok_async), .gate_fault_n_async(gate_fault_n_async),
        .tx(tx), .drv_left_in1(raw_left_in1), .drv_left_in2(raw_left_in2),
        .drv_right_in1(raw_right_in1), .drv_right_in2(raw_right_in2),
        .fpga_permit(raw_permit), .recovery_ack(raw_ack), .gate_clear(raw_clear)
    );
    // Also mask the board boundary during POR / an asynchronous button reset.
    assign drv_left_in1 = core_arst_n && raw_left_in1;
    assign drv_left_in2 = core_arst_n && raw_left_in2;
    assign drv_right_in1 = core_arst_n && raw_right_in1;
    assign drv_right_in2 = core_arst_n && raw_right_in2;
    assign fpga_permit = core_arst_n && raw_permit;
    assign recovery_ack = core_arst_n && raw_ack;
    assign gate_clear = core_arst_n && raw_clear;
endmodule
`default_nettype wire
