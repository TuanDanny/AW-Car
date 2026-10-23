`include "fpga/tb/tb_drive_core.sv"
`timescale 1ns/1ps
module tb_drive_defaults;
    tb_drive_core #(.SCALE(1), .LONG_RUN(0)) scenario ();
endmodule
