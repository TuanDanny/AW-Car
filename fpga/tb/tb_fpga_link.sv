`timescale 1ns/1ps
module tb_fpga_link;
    // Real 27 MHz parameters, host bit period at exactly 115200 baud.
    localparam real HOST_BIT_NS = 1000000000.0 / 115200.0;
    logic clk = 0;
    always #18.519 clk = !clk;
    logic rst_n = 0, rx = 1, tx;
    logic context_load = 0, session_active = 0, command_enable = 0;
    logic [31:0] active_session = 32'h12345678;
    logic [15:0] sequence_base = 16'h1232;
    logic hello_request, arm_zero_request, disable_request, clear_fault_request;
    logic command_valid, command_rejected, receive_error;
    logic [31:0] event_session;
    logic [15:0] event_sequence, command_left, command_right;
    logic [1:0] command_direction;
    logic snapshot_valid = 0, snapshot_ready, snapshot_dropped;
    logic [31:0] snapshot_left = 32'h10203040, snapshot_right = 32'hffeeddcc, snapshot_time = 32'h56789abc;
    logic [15:0] snapshot_seq = 16'h4321, fault = 16'h100;
    logic [3:0] snapshot_status = 12;
    logic [7:0] safety_state = 2;
    fpga_link dut (.*);
    logic [255:0] vectors [0:6];
    integer commands = 0, hellos = 0, arms = 0, disables = 0, rejected = 0, errors = 0, drops = 0;
    always @(posedge clk) begin
        #1;
        if (command_valid) begin
            if (!command_enable || !session_active || command_left !== 675 || command_right !== 1350 ||
                command_direction !== 0 || event_session !== active_session || event_sequence !== 16'h1234)
                $fatal(1, "end-to-end command mismatch");
            commands = commands + 1;
        end
        if (hello_request) hellos = hellos + 1;
        if (arm_zero_request) arms = arms + 1;
        if (disable_request) disables = disables + 1;
        if (command_rejected) rejected = rejected + 1;
        if (receive_error) errors = errors + 1;
        if (snapshot_dropped) drops = drops + 1;
    end
    task automatic host_byte(input logic [7:0] value);
        integer i;
        begin
            rx = 0; #(HOST_BIT_NS);
            for (i = 0; i < 8; i = i + 1) begin rx = value[i]; #(HOST_BIT_NS); end
            rx = 1; #(HOST_BIT_NS);
        end
    endtask
    task automatic host_frame(input logic [255:0] frame);
        integer i;
        begin
            for (i = 0; i < frame[255:248]; i = i + 1) host_byte(frame[i*8 +: 8]);
            repeat (10) @(negedge clk);
        end
    endtask
    integer tx_bytes = 0, i;
    logic [7:0] observed;
    initial forever begin
        @(negedge tx);
        #(HOST_BIT_NS * 1.5);
        for (i = 0; i < 8; i = i + 1) begin
            observed[i] = tx;
            #(HOST_BIT_NS);
        end
        if (tx !== 1 || observed !== vectors[6][tx_bytes*8 +: 8])
            $fatal(1, "physical STATUS/stop byte %d mismatch", tx_bytes);
        tx_bytes = tx_bytes + 1;
    end
    logic [255:0] corrupt;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_fpga_link.vcd"); $dumpvars(0, tb_fpga_link); end
        $readmemh("../../firmware/shared/fpga-vectors.hex", vectors);
        repeat (4) @(negedge clk); rst_n = 1;
        #123;
        host_frame(vectors[0]);
        host_frame(vectors[1]);
        if (hellos != 1 || arms != 0 || commands != 0) $fatal(1, "boot/HELLO granted authority");
        // Future safety controller is explicitly modelled by the testbench.
        @(negedge clk); session_active = 1; context_load = 1;
        @(negedge clk); context_load = 0;
        host_frame(vectors[1]);
        if (arms != 1) $fatal(1, "authorized ARM_ZERO event missing");
        command_enable = 1;
        fork
            begin
                @(negedge clk); snapshot_valid = 1;
                @(negedge clk); snapshot_valid = 0;
                snapshot_left = 0; snapshot_right = 0; snapshot_time = 0; snapshot_seq = 0;
                snapshot_status = 0; safety_state = 0; fault = 0;
                repeat (100) @(negedge clk);
                snapshot_valid = 1; @(negedge clk); snapshot_valid = 0;
            end
            begin
                corrupt = vectors[2]; corrupt[18*8 +: 8] = corrupt[18*8 +: 8] ^ 1;
                host_frame(corrupt);
                if (commands != 0 || errors != 1) $fatal(1, "bad CRC reached command output");
                host_frame(vectors[2]);
            end
        join
        host_frame(vectors[2]); // Duplicate must not refresh a future watchdog.
        host_frame(vectors[4]);
        if (commands != 1 || tx_bytes != 31 || drops != 1 || disables != 1 || rejected != 2)
            $fatal(1, "link event counts cmd=%d tx=%d drop=%d disable=%d rejected=%d",
                   commands, tx_bytes, drops, disables, rejected);
        // Default 2ms parser interbyte timeout after an actual UART prefix.
        host_byte(8'ha5); host_byte(8'h5a); host_byte(1);
        #2100000;
        if (errors != 2) $fatal(1, "default 2ms timeout missing");
        host_frame(vectors[4]);
        if (disables != 2) $fatal(1, "link did not recover after truncation");
        // Valid bytes remain <2ms apart but the entire frame exceeds 5ms.
        for (i = 0; i < 13; i = i + 1) begin
            host_byte(vectors[0][i*8 +: 8]); #500000;
        end
        if (errors != 3 || hellos != 1) $fatal(1, "default 5ms whole-frame timeout missing");
        host_frame(vectors[4]);
        if (disables != 3) $fatal(1, "whole-frame timeout did not recover");
        $display("PASS tb_fpga_link: 27MHz/115200 full duplex, shared wire vectors, CRC/duplicate rejection, frozen STATUS, timeout/recovery");
        $finish;
    end
    initial begin #40000000; $fatal(1, "link timeout"); end
endmodule
