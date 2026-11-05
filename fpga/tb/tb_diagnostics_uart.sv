`timescale 1ns/1ps
module tb_diagnostics_uart;
    logic clk=0;always #5 clk=~clk;
    logic arst_n=0,rx=1,tx,left_out=0,right_out=0;
    logic motion_permit_async=0,recovery_req_async=0,safety_ok_async=1,gate_fault_n_async=1;
    logic pwm_left,pwm_right,fpga_permit,recovery_ack,gate_clear;
    logic drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2;
    logic [1:0] direction;logic [7:0] safety_state;logic [15:0] fault;
    logic [5:0] leds_n;
    aw_car_top #(.CLK_HZ(800000),.BAUD(100000),.PERIOD_CYCLES(16),
        .SNAPSHOT_CYCLES(1000),.WATCHDOG_CYCLES(10000),.HANDSHAKE_CYCLES(50000),
        .CLEAR_CYCLES(16),.CLEAR_HOLD_CYCLES(3),.ZERO_CYCLES(8),.SETUP_CYCLES(2),
        .ENCODER_STALE_CYCLES(2000)) dut(.*);
    // Verification observes core diagnostics without consuming board pins.
    assign pwm_left=dut.core.pwm_left;
    assign pwm_right=dut.core.pwm_right;
    assign direction=dut.core.direction;
    assign safety_state=dut.core.safety_state;
    assign fault=dut.core.fault;
    task automatic ticks(input integer n);repeat(n) @(negedge clk);endtask
    function automatic logic [15:0] crc_byte(input logic [15:0] c,input logic [7:0] b);
        logic [15:0] x;integer k;
        begin x=c^{b,8'b0};for(k=0;k<8;k=k+1)x=x[15]?(x<<1)^16'h1021:x<<1;crc_byte=x;end
    endfunction
    task automatic host_byte(input logic [7:0] b);
        integer k;begin rx=0;ticks(8);for(k=0;k<8;k=k+1)begin rx=b[k];ticks(8);end rx=1;ticks(8);end
    endtask
    task automatic frame(input integer kind,seq,input logic [31:0] session,input bit bad);
        logic [151:0] b;logic [15:0] c;integer len,k;
        begin
            len=kind==3?6:0;b=0;b[15:0]=16'h5aa5;b[23:16]=2;b[31:24]=8'(kind);
            b[39:32]=8'(len);b[71:40]=session;b[87:72]=16'(seq);
            b[119:104]=8;b[135:120]=8;c=16'hffff;
            for(k=2;k<11+len;k=k+1)c=crc_byte(c,b[k*8+:8]);
            b[(11+len)*8+:16]=bad?c^16'h1:c;
            for(k=0;k<13+len;k=k+1)host_byte(b[k*8+:8]);ticks(8);
        end
    endtask
    logic [375:0] received=0;logic [7:0] observed;
    logic [15:0] crc,seen_fault=0;integer i,j,frames=0;
    initial forever begin
        @(negedge tx);ticks(12);
        for(i=0;i<8;i=i+1)begin observed[i]=tx;ticks(8);end
        if(tx!==1)$fatal(1,"diagnostic UART stop");
        received={observed,received[375:8]};
        if(received[39:0]==40'h2280025aa5)begin
            crc=16'hffff;for(j=2;j<45;j=j+1)crc=crc_byte(crc,received[j*8+:8]);
            if(crc==received[375:360])begin seen_fault=seen_fault|received[223:208];frames=frames+1;end
        end
    end
    initial begin
        ticks(4);arst_n=1;ticks(12);
        recovery_req_async=1;ticks(12);if(!recovery_ack)$fatal(1,"recovery ack");
        recovery_req_async=0;ticks(12);frame(1,1,32'h12345678,0);frame(2,2,32'h12345678,0);
        wait(recovery_ack);motion_permit_async=1;ticks(12);
        frame(3,3,32'h12345678,0);ticks(32);
        if(!fpga_permit || safety_state!=3)$fatal(1,"failed to ARM before diagnostics");
        frame(1,4,32'h12345678,1); // actual bad-CRC traffic
        frame(3,4,32'h87654321,0); // actual wrong-session command
        frame(3,4,32'h12345678,0);ticks(4000);
        if((seen_fault&16'h0300)!=16'h0300 || !fpga_permit)
            $fatal(1,"warning missing over UART or warning disabled drive");
        // Inject a defined internal invariant violation, not a claimed real bug.
        force dut.core.raw_left=1'b1;force dut.core.interlock_active=1'b1;ticks(3);
        if(fpga_permit || pwm_left || pwm_right || drv_left_in1 || drv_left_in2 || drv_right_in1 || drv_right_in2)
            $fatal(1,"internal invariant did not lock actual driver pins");
        release dut.core.raw_left;release dut.core.interlock_active;ticks(5000);
        if(!seen_fault[15] || safety_state!=4)$fatal(1,"critical diagnostic not reported/latching");
        frame(1,5,32'h12345678,0);frame(2,6,32'h12345678,0);
        frame(5,7,32'h12345678,0);frame(3,8,32'h12345678,0);
        if(fpga_permit || !fault[15])$fatal(1,"UART cleared critical latch without reset");
        arst_n=0;ticks(3);arst_n=1;ticks(12);
        if(fault[15:8]!=0)$fatal(1,"reset did not clear diagnostic history");
        force dut.core.snapshot_valid=1'b0;ticks(2010);
        if(!fault[11] || fpga_permit)$fatal(1,"snapshot watchdog did not inhibit");
        release dut.core.snapshot_valid;ticks(5000);
        if(!seen_fault[11])$fatal(1,"snapshot fault missing after telemetry resumes");
        if(frames<3)$fatal(1,"no CRC-valid diagnostic STATUS");
        $display("COVER diagnostics_uart.frames %0d",frames);
        $display("PASS tb_diagnostics_uart: real bad CRC/session, warn vs stop, injected PWM/snapshot faults and reset");$finish;
    end
    initial begin #2000000;$fatal(1,"diagnostic UART timeout");end
endmodule
