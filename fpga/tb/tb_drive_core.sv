`timescale 1ns/1ps
module tb_drive_core #(parameter int SCALE = 10, parameter bit LONG_RUN = 1);
    localparam int HZ = 27000000 / SCALE;
    localparam real HALF_NS = 500000000.0 / HZ;
    localparam real BIT_NS = 1000000000.0 / 115200;
    logic clk=0, clock_running=1;
    always #(HALF_NS) if (clock_running) clk=!clk;
    logic arst_n=0, rx=1, tx;
    logic [1:0] left_ab=0, right_ab=0;
    logic motion_permit_async=0, recovery_req_async=0;
    logic safety_ok_async=1, gate_fault_n_async=0;
    logic pwm_left, pwm_right, fpga_permit, recovery_ack, gate_clear;
    logic [1:0] direction;
    logic [7:0] safety_state;
    logic [15:0] fault;
    drive_core #(.CLK_HZ(HZ), .PERIOD_CYCLES(1350/SCALE), .SNAPSHOT_CYCLES(270000/SCALE),
        .WATCHDOG_CYCLES(1350000/SCALE), .HANDSHAKE_CYCLES(6750000/SCALE),
        .CLEAR_CYCLES(135000/SCALE), .CLEAR_HOLD_CYCLES(2700/SCALE),
        .INTERBYTE_CYCLES(54000/SCALE), .FRAME_CYCLES(135000/SCALE),
        .ZERO_CYCLES(27000/SCALE), .SETUP_CYCLES((27/SCALE)>0 ? 27/SCALE : 1)) dut (.*);
    // Independent SET-dominant external latch: releasing E-stop/power never
    // clears it. Actual PCB circuit and electrical timing remain to be designed.
    always @(negedge safety_ok_async or posedge gate_clear) begin
        if (!safety_ok_async) gate_fault_n_async=0;
        else if (gate_clear && !motion_permit_async && !fpga_permit) gate_fault_n_async=1;
    end
    wire driver_enable = safety_ok_async && gate_fault_n_async && motion_permit_async && fpga_permit;
    integer left_phase=0, right_phase=0;
    function automatic logic [1:0] ab(input integer phase);
        case (phase & 3) 0: ab=0; 1: ab=1; 2: ab=3; 3: ab=2; endcase
    endfunction
    initial forever begin #250000; left_phase=left_phase+1; left_ab=ab(left_phase); end
    initial forever begin #500000; right_phase=right_phase-1; right_ab=ab(right_phase); end
    function automatic logic [15:0] crc_byte(input logic [15:0] c, input logic [7:0] b);
        logic [15:0] value;
        integer j;
        begin
            value=c ^ {b,8'd0};
            for(j=0;j<8;j=j+1) if(value[15]) value=(value<<1)^16'h1021; else value=value<<1;
            crc_byte=value;
        end
    endfunction
    logic [31:0] host_session=32'h12345678;
    integer seq=0;
    task automatic host_byte(input logic [7:0] b);
        integer j;
        begin
            rx=0; #(BIT_NS);
            for(j=0;j<8;j=j+1) begin rx=b[j]; #(BIT_NS); end
            rx=1; #(BIT_NS);
        end
    endtask
    task automatic frame(input logic [7:0] kind, input logic [15:0] number,
                         input logic [31:0] session_value, input integer dl, input integer dr,
                         input bit corrupt);
        logic [151:0] bytes;
        logic [15:0] c;
        integer length,j;
        begin
            length=kind==3 ? 6 : 0;
            bytes=0; bytes[7:0]=8'ha5; bytes[15:8]=8'h5a; bytes[23:16]=1;
            bytes[31:24]=kind; bytes[39:32]=length; bytes[71:40]=session_value; bytes[87:72]=number;
            bytes[119:104]=dl; bytes[135:120]=dr;
            c=16'hffff;
            for(j=2;j<11+length;j=j+1) c=crc_byte(c,bytes[j*8+:8]);
            if(corrupt) c=c^16'h8000;
            bytes[(11+length)*8+:16]=c;
            for(j=0;j<13+length;j=j+1) host_byte(bytes[j*8+:8]);
            repeat(12) @(negedge clk);
        end
    endtask
    task automatic send(input logic [7:0] kind, input integer dl, input integer dr);
        begin seq=seq+1; frame(kind,seq,host_session,dl,dr,0); end
    endtask
    task automatic recovery;
        begin
            motion_permit_async=0; recovery_req_async=0; #10000;
            recovery_req_async=1; wait(recovery_ack); #10000;
            recovery_req_async=0; wait(!recovery_ack); #6000000; // drain truncated UART/parser
            host_session=host_session+1; seq=0; send(1,0,0); #10000;
            if (!dut.session_active) $fatal(1,"HELLO not installed after GPIO recovery");
        end
    endtask
    task automatic clear_fault;
        begin
            recovery; send(5,0,0); #200000;
            if(safety_state!=0 || fault!=0 || driver_enable || dut.session_active)
                $fatal(1,"clear did not end DISARMED");
        end
    endtask
    logic [175:0] expected [0:65535];
    always @(posedge clk) if(dut.rst_n && !dut.context_load && dut.snapshot_valid && dut.snapshot_ready)
        expected[dut.snapshot_seq] = {dut.session_active ? dut.active_session : 32'd0,
            4'd0,dut.snapshot_status,fault,safety_state,dut.snapshot_seq,
            dut.snapshot_time,dut.snapshot_right,dut.snapshot_left};
    integer valid_frames=0, crc_discarded=0, pending_frames=0, high_ticks=0;
    integer stale_trips=0;
    logic monitor_stale=0, fresh_seen=0;
    logic [15:0] last_seq=0;
    logic [31:0] last_session=0;
    realtime last_fresh=0, stale_trip_time=0;
    task automatic record_sample(input logic [31:0] session_value, input logic [15:0] number);
        logic [15:0] delta;
        begin
            delta=number-last_seq;
            if(session_value==host_session &&
               (!fresh_seen || session_value!=last_session || (delta!=0 && delta<32768))) begin
                fresh_seen=1; last_session=session_value; last_seq=number; last_fresh=$realtime;
            end
        end
    endtask
    initial forever begin
        #1000000; // Motion safety task, 1 ms cadence, separate from FPGA clock
        if(monitor_stale && motion_permit_async && (!fresh_seen || $realtime-last_fresh>=30000000)) begin
            motion_permit_async=0; stale_trips=stale_trips+1;
            stale_trip_time=$realtime;
        end
    end
    logic [247:0] received=0;
    logic [7:0] observed;
    logic [15:0] received_crc;
    integer j,k;
    initial forever begin
        @(negedge tx); #(BIT_NS*1.5);
        for(j=0;j<8;j=j+1) begin observed[j]=tx; #(BIT_NS); end
        if(tx!==1) $fatal(1,"STATUS stop bit");
        received={observed,received[247:8]};
        if(received[15:0]==16'h5aa5 && received[39:16]==24'h128001) begin
            received_crc=16'hffff;
            for(k=2;k<29;k=k+1) received_crc=crc_byte(received_crc,received[k*8+:8]);
            if(received_crc==received[247:232]) begin
                if({received[71:40],received[231:88]} !== expected[received[87:72]])
                    $fatal(1,"torn/incorrect end-to-end STATUS snapshot");
                if(received[87:72] != received[199:184]) $fatal(1,"STATUS sequence mismatch");
                record_sample(received[71:40],received[87:72]); valid_frames=valid_frames+1;
                if(received[207:200]==2 && received[71:40]==host_session) pending_frames=pending_frames+1;
            end else crc_discarded=crc_discarded+1;
        end
    end
    always @(posedge clk) begin
        #1;
        if(fpga_permit && safety_state!=3) $fatal(1,"permit outside ARMED");
        if((pwm_left || pwm_right) && !fpga_permit) $fatal(1,"PWM without permission");
        if(direction!=0) $fatal(1,"forward-only policy");
        if(driver_enable && pwm_left) high_ticks=high_ticks+1;
        if(dut.status_sent && (received_crc!==received[247:232] || tx!==1 ||
            dut.status_session!==received[71:40] || dut.status_state!==received[207:200])) $fatal(1,"status_sent before full physical frame");
    end
    task automatic arm_and_run;
        integer before_pending, before_high, sample, left_high, right_high;
        begin
            recovery; before_pending=pending_frames; send(2,0,0);
            if(fpga_permit || pwm_left || pwm_right) $fatal(1,"ARM_ZERO drove motor");
            wait(recovery_ack);
            if(pending_frames<=before_pending) $fatal(1,"ACK before matching physical STATUS");
            if($signed(received[119:88])<=0 || $signed(received[151:120])>=0)
                $fatal(1,"encoder channels/forward-reverse counts wired incorrectly");
            motion_permit_async=1; #10000;
            if(safety_state!=3 || !fpga_permit) $fatal(1,"Motion permit failed to arm");
            before_high=high_ticks; send(3,(1350/SCALE)/2,1350/SCALE); #200000;
            if(high_ticks<=before_high || !driver_enable) $fatal(1,"valid UART command didn't drive PWM");
            left_high=0; right_high=0;
            // Any whole stable period must contain exactly the commanded HIGH
            // ticks on BOTH physical outputs, independent of the sampling phase.
            for(sample=0;sample<1350/SCALE;sample=sample+1) begin
                @(posedge clk); #1;
                if(pwm_left===1'b1) left_high=left_high+1;
                else if(pwm_left!==1'b0) $fatal(1,"unknown left PWM");
                if(pwm_right===1'b1) right_high=right_high+1;
                else if(pwm_right!==1'b0) $fatal(1,"unknown right PWM");
            end
            if(left_high!=(1350/SCALE)/2 || right_high!=1350/SCALE)
                $fatal(1,"top PWM duty pair mismatch: %0d/%0d",left_high,right_high);
        end
    endtask
    integer saved;
    realtime stop_time, frozen_fresh;
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_drive_core.vcd"); $dumpvars(0,tb_drive_core); end
        #2000; arst_n=1; #10000;
        if(fpga_permit || pwm_left || pwm_right) $fatal(1,"boot output");
        clear_fault; arm_and_run;
        // Malformed, duplicate, stale-session and out-of-range duty never refresh watchdog.
        saved=seq;
        frame(3,saved,host_session,1350/SCALE,1350/SCALE,0);
        frame(3,saved+1,host_session+9,0,0,0);
        frame(3,saved+1,host_session,0,0,1);
        frame(3,saved+1,host_session,1350/SCALE+1,0,0);
        #51000000;
        if(safety_state!=4 || !(fault & 1) || fpga_permit || pwm_left || pwm_right)
            $fatal(1,"UART invalid traffic refreshed watchdog");
        clear_fault; arm_and_run;
        // Short pulse at a clock-independent phase; release never reopens gate.
        #71; safety_ok_async=0; #10;
        if(driver_enable || fpga_permit || pwm_left || pwm_right) $fatal(1,"E-stop not asynchronous");
        safety_ok_async=1; #10000;
        if(driver_enable || gate_fault_n_async || safety_state!=4) $fatal(1,"E-stop release resumed");
        clear_fault; arm_and_run;
        // Reset with cached permit and UART frames: no GPIO recovery => no ARM.
        arst_n=0; #1000;
        if(fpga_permit || pwm_left || pwm_right) $fatal(1,"reset output");
        arst_n=1; #10000; send(1,0,0); send(2,0,0); send(3,1350/SCALE,1350/SCALE);
        if(fpga_permit || dut.session_active) $fatal(1,"cached UART/GPIO rearmed after reset");
        arm_and_run; monitor_stale=1;
        // Stop FPGA while PWM HIGH. Duplicate/reordered telemetry in the Motion
        // model must not refresh freshness even if a bridge keeps replaying it.
        wait(pwm_left && clk==0); clock_running=0; stop_time=$realtime; frozen_fresh=last_fresh;
        repeat(35) begin
            #1000000; record_sample(last_session,last_seq); record_sample(last_session,last_seq-1'b1);
        end
        if(stale_trips!=1 || motion_permit_async || driver_enable || $realtime-frozen_fresh<30000000)
            $fatal(1,"independent Motion stale inhibit failed");
        if(stale_trip_time-frozen_fresh<30000000 || stale_trip_time-frozen_fresh>31000000)
            $fatal(1,"Motion didn't inhibit within 30+1 ms of last new snapshot");
        if($realtime-stop_time>36000000) $fatal(1,"clock-stop test scheduling");
        // A power fault with stopped clock is still latched externally.
        safety_ok_async=0; #10; safety_ok_async=1; #1000;
        if(gate_fault_n_async || driver_enable) $fatal(1,"stopped-clock power latch");
        clock_running=1; #10000;
        if(safety_state!=4 || fpga_permit) $fatal(1,"clock resume restored old duty");
        monitor_stale=0; clear_fault; arm_and_run;
        if(LONG_RUN) begin
            monitor_stale=1;
            // End-to-end traffic over at least 2 s at the selected clock.
            while($realtime<2000000000) begin send(3,(1350/SCALE)/3,(1350/SCALE)*2/3); #8000000; end
            if(stale_trips!=1 || safety_state!=3) $fatal(1,"long-run link/motor stability");
        end
        send(4,0,0); #10000;
        if(fpga_permit || pwm_left || pwm_right || dut.session_active) $fatal(1,"DISABLE not applied");
        if(valid_frames<8 || dut.live_left==0 || dut.live_right==0) $fatal(1,"missing encoder telemetry");
        $display("PASS tb_drive_core: %0d Hz, %0.3f ms, %0d STATUS; UART/PWM/encoder, reset, E-stop, clock-stop/stale gate",
                 HZ,$realtime/1000000.0,valid_frames); $finish;
    end
    initial begin #2500000000; $fatal(1,"integrated timeout"); end
endmodule
