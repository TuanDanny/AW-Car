`timescale 1ns/1ps
module tb_drv8833_adapter;
    logic rst_n=0, enable=0, pwm_left=0, pwm_right=0;
    logic [1:0] direction=0;
    logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2;
    drv8833_adapter dut (.*);
    function automatic logic [1:0] expected(input logic allowed, input logic pwm, input logic dir);
        if (!allowed || !pwm) expected=2'b00;
        else case (dir)
            1'b0: expected=2'b10;
            1'b1: expected=2'b01;
            default: expected=2'bxx;
        endcase
    endfunction
    integer k;
    task automatic check;
        begin
            #1;
            if ({drv_left_in1,drv_left_in2}!==expected(rst_n && enable,pwm_left,direction[0]) ||
                {drv_right_in1,drv_right_in2}!==expected(rst_n && enable,pwm_right,direction[1]))
                $fatal(1,"DRV8833 truth table mismatch rst=%b enable=%b pwm=%b%b dir=%02b",
                       rst_n,enable,pwm_left,pwm_right,direction);
            if ({drv_left_in1,drv_left_in2}===2'b11 || {drv_right_in1,drv_right_in2}===2'b11)
                $fatal(1,"adapter requested active brake");
        end
    endtask
    initial begin
        // All known-value input combinations; no clock is present or needed.
        for (k=0;k<64;k=k+1) begin
            {rst_n,enable,pwm_left,pwm_right,direction}=6'(k); check;
        end
        rst_n=1; enable=1; pwm_left=1; pwm_right=1; direction=1; check;
        #0.123; enable=0; check;
        if ({drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2}!==0)
            $fatal(1,"asynchronous inhibit required a clock");
        enable=1; check; #0.123; rst_n=0; check;
        // A disabled adapter has no latch: changing direction/PWM stays off.
        for (k=0;k<16;k=k+1) begin
            {pwm_left,pwm_right,direction}=4'(k); check;
        end
        $display("COVER drv8833_adapter.input_combinations 64");
        $display("COVER drv8833_adapter.disabled_changes 16");
        $display("PASS tb_drv8833_adapter: TI drive/coast table, all combinations, reset/inhibit without clock");
        $finish;
    end
    initial begin #1000; $fatal(1,"timeout tb_drv8833_adapter"); end
endmodule
