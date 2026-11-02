`timescale 1ns/1ps
// Exercise the actual 24-bit encoder timeout, not only shortened parameters.
module tb_diagnostics_default_timeout;
    logic clk=0;always #18.519 clk=~clk;
    logic rst_n=0,receive_error=0,command_rejected=0,snapshot_dropped=0,pwm_rejected=0;
    logic snapshot_valid=0,motor_enable=0,interlock_active=0;
    logic request_left=0,request_right=0,raw_left=0,raw_right=0;
    logic [7:0] safety_state=3,flags;
    logic [31:0] left_count=0,right_count=0;
    logic critical_fault;
    logic [18:0] heartbeat=0;
    runtime_diagnostics dut(.*);
    always @(posedge clk) begin
        if(!rst_n) begin heartbeat<=0;snapshot_valid<=0;end
        else if(heartbeat==269999)begin heartbeat<=0;snapshot_valid<=1;end
        else begin heartbeat<=heartbeat+1'b1;snapshot_valid<=0;end
    end
    initial begin
        repeat(4)@(negedge clk);rst_n=1;
        repeat(3)@(negedge clk);motor_enable=1;request_left=1;raw_left=1;
        repeat(13499999)@(negedge clk);
        if(flags!==0 || critical_fault)$fatal(1,"default timeout early or normal heartbeat rejected");
        @(negedge clk);
        if(flags!==8'h10 || critical_fault)$fatal(1,"default 13500000-tick no-edge threshold");
        left_count=1;request_left=0;repeat(3)@(negedge clk);
        if(flags!==8'h10)$fatal(1,"history did not persist after encoder recovered");
        $display("COVER diagnostics.default_encoder_timeout_ticks 13500000");
        $display("PASS tb_diagnostics_default_timeout: nominal 27MHz, 500ms encoder warning, healthy 10ms snapshots");$finish;
    end
    initial begin #510000000;$fatal(1,"default diagnostic timeout");end
endmodule
