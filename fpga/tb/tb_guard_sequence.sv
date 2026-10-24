`timescale 1ns/1ps
module tb_guard_sequence;
    logic clk=0;
    always #5 clk=!clk;
    logic rst_n=0, context_load=0, session_active=1, command_enable=1, frame_valid=0;
    logic [31:0] active_session=32'h89abcdef, frame_session=32'h89abcdef;
    logic [15:0] sequence_base=16'hbabe, frame_sequence=0;
    logic [7:0] frame_type=3;
    logic [47:0] frame_payload=0;
    logic hello_request, arm_zero_request, disable_request, clear_fault_request, command_valid, rejected;
    logic [31:0] event_session;
    logic [15:0] event_sequence, command_left, command_right;
    logic [1:0] command_direction;
    command_guard dut(.*);
    integer distance, accepted=0, rejected_count=0, control_bit;
    task automatic reload;
        begin
            @(negedge clk); frame_valid=0; context_load=1;
            @(negedge clk); context_load=0;
        end
    endtask
    task automatic offer(input logic expected);
        begin
            frame_valid=1; @(posedge clk); #1;
            if(command_valid!==expected || rejected!==!expected)
                $fatal(1,"sequence classification delta=%0d seq=%h",distance,frame_sequence);
            if({hello_request,arm_zero_request,disable_request,clear_fault_request}!==0)
                $fatal(1,"CMD produced management request");
            if(expected) accepted=accepted+1; else rejected_count=rejected_count+1;
            @(negedge clk); frame_valid=0;
        end
    endtask
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_guard_sequence.vcd"); $dumpvars(0,tb_guard_sequence); end
        repeat(2) @(negedge clk); rst_n=1;
        // Independent modular distance rule, including every wrap and half-range boundary.
        for(distance=0;distance<65536;distance=distance+1) begin
            reload; frame_sequence=16'(sequence_base+distance);
            offer(distance>=1 && distance<=32767);
            // The immediately repeated accepted sequence must never commit twice.
            if(distance>=1 && distance<=32767) offer(0);
        end
        frame_sequence=sequence_base+1;
        // Walk invalid isolated flags/direction/reserved bits, then retry
        // the same sequence with the legal zero payload.
        for(control_bit=0;control_bit<16;control_bit=control_bit+1) begin
            reload; frame_payload=48'd1<<control_bit; offer(0);
            frame_payload=0; offer(1);
        end
        reload; frame_payload={16'd1,16'd2049,16'd0}; offer(0);
        frame_payload={16'd1350,16'd675,16'd0}; offer(1);
        if(command_left!==675 || command_right!==1350) $fatal(1,"full-width duty check");
        // Context invalidation on the same edge as a valid command has priority.
        @(negedge clk); context_load=1; frame_valid=1;
        @(posedge clk); #1;
        if(command_valid || rejected || command_left || command_right || command_direction)
            $fatal(1,"context collision retained duty");
        $display("COVER guard.sequence_distances 65536");
        $display("COVER guard.duplicate_retries 32767");
        $display("COVER guard.invalid_control_bits 16");
        $display("PASS tb_guard_sequence: all modulo distances, duplicates, control bits, full-width duty/context");
        $finish;
    end
    initial begin #5000000; $fatal(1,"sequence sweep timeout"); end
endmodule
