`timescale 1ns/1ps
module diagnostic_case #(parameter int N=16)(output logic done=0);
    logic clk=0; always #5 clk=~clk;
    logic rst_n=0, receive_error=0, command_rejected=0, snapshot_dropped=0, pwm_rejected=0;
    logic snapshot_valid=1, motor_enable=0, interlock_active=0;
    logic request_left=0, request_right=0, raw_left=0, raw_right=0;
    logic [7:0] safety_state=0, flags;
    logic [31:0] left_count=0, right_count=0;
    logic critical_fault;
    runtime_diagnostics #(.SNAPSHOT_LIMIT(N),.ENCODER_LIMIT(N)) dut (.*);
    task automatic ticks(input integer n); repeat(n) @(negedge clk); endtask
    task automatic reset_monitor;
        rst_n=0; raw_left=0;raw_right=0;motor_enable=0;interlock_active=0;
        request_left=0;request_right=0;safety_state=0;snapshot_valid=1;
        receive_error=0;command_rejected=0;snapshot_dropped=0;pwm_rejected=0;
        ticks(2);rst_n=1;ticks(1);
        if(flags!==0 || critical_fault) $fatal(1,"diagnostic reset");
    endtask
    integer k;
    initial begin
        ticks(2);reset_monitor;
        ticks(N*3);
        if(flags) $fatal(1,"idle encoder produced warning");
        receive_error=1;command_rejected=1;snapshot_dropped=1;pwm_rejected=1;
        ticks(1);receive_error=0;command_rejected=0;snapshot_dropped=0;pwm_rejected=0;
        ticks(3);
        if(flags!==8'h47 || critical_fault) $fatal(1,"event warning latch or warning stopped motor");
        reset_monitor;
        motor_enable=1;request_left=1;
        ticks(N-1);if(flags) $fatal(1,"encoder warning early N=%0d",N);
        ticks(1);if(flags!==8'h10 || critical_fault) $fatal(1,"left encoder deadline N=%0d",N);
        request_left=0;request_right=1;
        ticks(N);if(flags!==8'h30) $fatal(1,"independent right warning");
        reset_monitor;motor_enable=1;request_left=1;request_right=1;
        for(k=0;k<30;k=k+1) begin
            // A count change every cycle (including wrap) prevents no-edge warnings.
            left_count=32'hfffffff0+k;right_count=k+1;ticks(1);
        end
        if(flags) $fatal(1,"count change/wrap falsely stale");
        interlock_active=1;ticks(N*3);
        if(flags) $fatal(1,"coast falsely stale");
        request_left=0;request_right=0;interlock_active=0;
        raw_left=1;raw_right=1;ticks(2);
        if(flags) $fatal(1,"valid raw PWM flagged");
        interlock_active=1;ticks(1);
        if(!flags[7] || !critical_fault) $fatal(1,"PWM during interlock undetected");
        raw_left=0;raw_right=0;interlock_active=0;ticks(2);
        if(!critical_fault) $fatal(1,"critical fault did not latch");
        reset_monitor;safety_state=6;ticks(1);
        if(!flags[7] || !critical_fault) $fatal(1,"illegal safety state undetected");
        reset_monitor;raw_right=1;ticks(1);
        if(!critical_fault) $fatal(1,"PWM without enable undetected");
        reset_monitor;snapshot_valid=0;
        ticks(N-1);if(flags) $fatal(1,"snapshot alarm early");
        ticks(1);if(flags!==8'h08 || !critical_fault) $fatal(1,"snapshot deadline");
        snapshot_valid=1;ticks(N+1);
        if(!critical_fault) $fatal(1,"snapshot fault auto-cleared");
        reset_monitor;
        $display("COVER diagnostics.N%0d.scenarios 12",N);done=1;
    end
endmodule
module tb_runtime_diagnostics;
    logic [4:0] done;
    diagnostic_case #(.N(1)) n1(done[0]);
    diagnostic_case #(.N(2)) n2(done[1]);
    diagnostic_case #(.N(16)) n16(done[2]);
    diagnostic_case #(.N(17)) n17(done[3]);
    diagnostic_case #(.N(64)) n64(done[4]);
    initial begin wait(&done);$display("PASS tb_runtime_diagnostics: boundaries, warnings, no-edge, wrap, interlock, invariant and reset");$finish;end
    initial begin #100000; $fatal(1,"diagnostics timeout");end
endmodule
