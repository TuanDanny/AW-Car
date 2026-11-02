`timescale 1ns/1ps
module tb_drive_maneuvers;
    localparam int PERIOD=1350, ZERO=1080000, SETUP=27, WATCHDOG=1350000;
    localparam real HALF_NS=500000000.0/27000000;
    localparam real BIT_NS=1000000000.0/115200;
    logic clk=0;
    always #(HALF_NS) clk=!clk;
    logic arst_n=0, rx=1, tx;
    logic encoder_left_out=1, encoder_right_out=0;
    logic motion_permit_async=0, recovery_req_async=0;
    logic safety_ok_async=1, gate_fault_n_async=1;
    logic pwm_left, pwm_right, fpga_permit, recovery_ack, gate_clear;
    logic drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2;
    logic [1:0] direction;
    logic [7:0] safety_state;
    logic [15:0] fault;
    // No parameter overrides: exercise the actual 27 MHz hardware defaults,
    // including reverse enabled, single OUT, 20 kHz PWM and 50 ms watchdog.
    aw_car_top dut (.left_out(encoder_left_out), .right_out(encoder_right_out), .*);
    // Verification observes core diagnostics without consuming board pins.
    assign pwm_left=dut.core.pwm_left;
    assign pwm_right=dut.core.pwm_right;
    assign direction=dut.core.direction;
    assign safety_state=dut.core.safety_state;
    assign fault=dut.core.fault;
    always @(negedge safety_ok_async or posedge gate_clear) begin
        if (!safety_ok_async) gate_fault_n_async=0;
        else if (gate_clear && !motion_permit_async && !fpga_permit) gate_fault_n_async=1;
    end
    function automatic logic [15:0] crc_byte(input logic [15:0] c, input logic [7:0] b);
        logic [15:0] value;
        integer i;
        begin
            value=c^{b,8'd0};
            for (i=0;i<8;i=i+1) value=value[15] ? (value<<1)^16'h1021 : value<<1;
            crc_byte=value;
        end
    endfunction
    logic [31:0] host_session=32'h8a17d300;
    integer seq=0, accepted=0, rejected=0;
    task automatic host_byte(input logic [7:0] value);
        integer i;
        begin
            rx=0; #(BIT_NS);
            for (i=0;i<8;i=i+1) begin rx=value[i]; #(BIT_NS); end
            rx=1; #(BIT_NS);
        end
    endtask
    task automatic frame(input logic [7:0] kind, input logic [15:0] number,
                         input logic [7:0] dir, input integer dl, input integer dr,
                         input bit corrupt);
        logic [151:0] data;
        logic [15:0] crc;
        integer length,i;
        begin
            length=kind==3 ? 6 : 0;
            data=0; data[15:0]=16'h5aa5; data[23:16]=2;
            data[31:24]=kind; data[39:32]=8'(length);
            data[71:40]=host_session; data[87:72]=number;
            data[103:96]=dir; data[119:104]=16'(dl); data[135:120]=16'(dr);
            crc=16'hffff;
            for (i=2;i<11+length;i=i+1) crc=crc_byte(crc,data[i*8+:8]);
            data[(11+length)*8+:16]=corrupt ? crc^16'h8000 : crc;
            for (i=0;i<13+length;i=i+1) host_byte(data[i*8+:8]);
            repeat(12) @(negedge clk);
        end
    endtask
    task automatic send(input logic [7:0] kind, input logic [7:0] dir,
                        input integer dl, input integer dr);
        begin seq=seq+1; frame(kind,16'(seq),dir,dl,dr,0); end
    endtask
    task automatic recovery;
        begin
            motion_permit_async=0; recovery_req_async=0; #10000;
            recovery_req_async=1; wait(recovery_ack); #10000;
            recovery_req_async=0; wait(!recovery_ack); #6000000;
            host_session=host_session+1; seq=0; send(1,0,0,0); #10000;
            if (!dut.core.session_active) $fatal(1,"maneuvers recovery HELLO");
        end
    endtask
    task automatic arm;
        begin
            recovery; send(2,0,0,0);
            if (fpga_permit || pwm_left || pwm_right) $fatal(1,"ARM_ZERO generated PWM");
            wait(recovery_ack);
            motion_permit_async=1; #10000;
            if (safety_state!=3 || !fpga_permit) $fatal(1,"maneuvers failed to arm");
        end
    endtask
    task automatic clear_fault;
        begin
            recovery; send(5,0,0,0); #200000;
            if (safety_state!=0 || fault[7:0]!=0 || fpga_permit) $fatal(1,"maneuvers clear failed");
        end
    endtask
    integer cycles=0, quiet_ticks=0, direction_tick=-1000000, last_change_cmd=-1000000;
    integer last_valid_command_tick=0, watchdog_deadlines=0, reversal_refreshes=0;
    logic watchdog_reported=0;
    logic [1:0] previous_direction=0;
    always @(posedge clk) begin
        cycles=cycles+1;
        if (dut.core.motor_command) last_valid_command_tick=cycles;
        if (dut.core.motor_command && !dut.core.interlock_active && dut.core.command_direction!=direction)
            last_change_cmd=cycles;
        if (dut.core.command_valid) accepted=accepted+1;
        if (dut.core.command_rejected) rejected=rejected+1;
        #1;
        if (!arst_n || !fault[0]) watchdog_reported=0;
        else if (!watchdog_reported) begin
            if (cycles-last_valid_command_tick!=WATCHDOG)
                $fatal(1,"coast/setup paused or extended the command watchdog");
            watchdog_reported=1; watchdog_deadlines=watchdog_deadlines+1;
        end
        if ((pwm_left || pwm_right) && (!fpga_permit || safety_state!=3))
            $fatal(1,"maneuvers PWM without ARMED/permit");
        if ({drv_left_in1,drv_left_in2}===2'b11 || {drv_right_in1,drv_right_in2}===2'b11)
            $fatal(1,"unexpected DRV8833 brake command");
        if ((!fpga_permit || dut.core.interlock_active) &&
            {drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2}!==4'b0)
            $fatal(1,"DRV8833 pins active during inhibit/interlock");
        if (direction!=previous_direction && fpga_permit) begin
            if (pwm_left || pwm_right || quiet_ticks<ZERO-1 || cycles-last_change_cmd<ZERO)
                $fatal(1,"direction changed without complete zero interval");
            direction_tick=cycles;
        end
        if (fpga_permit && (pwm_left || pwm_right) && cycles-direction_tick<SETUP)
            $fatal(1,"PWM before direction setup complete");
        previous_direction=direction;
        if (pwm_left || pwm_right) quiet_ticks=0; else quiet_ticks=quiet_ticks+1;
    end
    logic [303:0] expected [0:65535];
    always @(posedge clk) if (dut.core.rst_n && !dut.core.context_load && dut.core.snapshot_valid && dut.core.snapshot_ready)
        expected[dut.core.snapshot_seq]={dut.core.session_active ? dut.core.active_session : 32'd0,
            dut.core.snapshot_right_age,dut.core.snapshot_left_age,
            dut.core.snapshot_right_period,dut.core.snapshot_left_period,
            dut.core.snapshot_status_ext,fault,safety_state,dut.core.snapshot_seq,
            dut.core.snapshot_time,dut.core.snapshot_right,dut.core.snapshot_left};
    logic [375:0] received=0;
    logic [7:0] observed;
    logic [15:0] received_crc;
    logic [31:0] observed_left=0, observed_right=0;
    integer valid_status=0, i,j;
    initial forever begin
        @(negedge tx); #(BIT_NS*1.5);
        for (i=0;i<8;i=i+1) begin observed[i]=tx; #(BIT_NS); end
        if (tx!==1) $fatal(1,"maneuvers STATUS stop bit");
        received={observed,received[375:8]};
        if (received[15:0]==16'h5aa5 && received[39:16]==24'h228002) begin
            received_crc=16'hffff;
            for (j=2;j<45;j=j+1) received_crc=crc_byte(received_crc,received[j*8+:8]);
            if (received_crc==received[375:360]) begin
                if ({received[71:40],received[359:88]} !== expected[received[87:72]])
                    $fatal(1,"maneuvers STATUS snapshot mismatch");
                if ((received[231:224] & 8'h9c)!==8'h1c)
                    $fatal(1,"single OUT v2 mode/ready/unknown direction flags");
                observed_left=received[119:88]; observed_right=received[151:120];
                valid_status=valid_status+1;
            end
        end
    end
    integer expected_left=0, expected_right=0;
    task automatic pulses(input integer nl, input integer nr);
        integer p;
        begin
            for (p=0;p<nl || p<nr;p=p+1) begin
                @(negedge clk); #3; encoder_left_out=0; encoder_right_out=0;
                repeat(12) @(negedge clk);
                #3; encoder_left_out=(p<nl); encoder_right_out=(p<nr);
                repeat(12) @(negedge clk);
            end
            encoder_left_out=0; encoder_right_out=0; repeat(12) @(negedge clk);
            expected_left=expected_left+nl; expected_right=expected_right+nr;
            if (dut.core.live_left!==32'(expected_left) || dut.core.live_right!==32'(expected_right))
                $fatal(1,"single OUT count must increase regardless of commanded direction");
        end
    endtask
    integer cases=0;
    // Independent H-bridge truth-table decoder, not the adapter equations.
    function automatic integer bridge_drive(input logic [1:0] pins);
        case (pins)
            2'b00: bridge_drive=0;
            2'b10: bridge_drive=1;
            2'b01: bridge_drive=-1;
            default: bridge_drive=1000000;
        endcase
    endfunction
    task automatic measure(input logic [1:0] dir, input integer dl, input integer dr);
        integer n, left_high, right_high, left_drive, right_drive;
        begin
            if (direction!==dir || !fpga_permit) $fatal(1,"wrong direction/permit for requested maneuver");
            left_high=0; right_high=0; left_drive=0; right_drive=0;
            for (n=0;n<2*PERIOD;n=n+1) begin
                @(posedge clk); #2;
                if ((^{pwm_left,pwm_right})===1'bx) $fatal(1,"unknown physical PWM output");
                left_high=left_high+int'(pwm_left); right_high=right_high+int'(pwm_right);
                left_drive=left_drive+bridge_drive({drv_left_in1,drv_left_in2});
                right_drive=right_drive+bridge_drive({drv_right_in1,drv_right_in2});
            end
            if (left_high!=2*dl || right_high!=2*dr || direction!==dir)
                $fatal(1,"duty mismatch dir=%0d expected=%0d/%0d measured=%0d/%0d",
                       dir,dl,dr,left_high/2,right_high/2);
            if (left_drive!=(dir[0] ? -2*dl : 2*dl) ||
                right_drive!=(dir[1] ? -2*dr : 2*dr))
                $fatal(1,"DRV8833 signed drive/coast ticks mismatch dir=%02b",dir);
        end
    endtask
    task automatic maneuver(input logic [1:0] dir, input integer dl, input integer dr);
        integer before_accepted, refresh_index, expected_accepts;
        logic changing_direction;
        begin
            before_accepted=accepted; expected_accepts=1;
            changing_direction=(direction!=dir);
            send(3,{6'b0,dir},dl,dr);
            if (changing_direction) begin
                // Fresh desired commands about every 10 ms must refresh the
                // lease without restarting the 40 ms zero interval forever.
                for (refresh_index=0;refresh_index<3;refresh_index=refresh_index+1) begin
                    #8000000; send(3,{6'b0,dir},dl,dr);
                    expected_accepts=expected_accepts+1; reversal_refreshes=reversal_refreshes+1;
                end
                #12000000;
            end else #200000;
            if (accepted!=before_accepted+expected_accepts) $fatal(1,"valid maneuver rejected");
            measure(dir,dl,dr); cases=cases+1;
            $display("CASE dir=%02b L=%0d/1350 R=%0d/1350: exact HIGH ticks PASS",dir,dl,dr);
        end
    endtask
    integer d, before_accepted, before_rejected;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_drive_maneuvers.vcd"); $dumpvars(0,tb_drive_maneuvers); end
        #2000; arst_n=1; #10000;
        if (pwm_left || pwm_right || fpga_permit || dut.core.live_left || dut.core.live_right)
            $fatal(1,"boot or initial HIGH output/count");
        pulses(5,9); arm;
        for (d=0;d<4;d=d+1) begin
            maneuver(2'(d),0,0);
            maneuver(2'(d),1,1);
            maneuver(2'(d),337,1012);
            maneuver(2'(d),675,1350);
            maneuver(2'(d),1080,270);
            maneuver(2'(d),1350,1350);
            if (d==3) begin
                pulses(3,7);
                wait(observed_left==32'(expected_left) && observed_right==32'(expected_right));
            end
        end
        maneuver(0,0,1350); // turn left about the stationary left wheels
        maneuver(0,1350,0); // turn right about the stationary right wheels
        // DISABLE cancels an outstanding reversal; waiting past the original
        // zero deadline must not resurrect its cached direction/duty.
        send(3,1,1350,1350); #8000000;
        if (!dut.core.interlock_active || direction!=0 || pwm_left || pwm_right)
            $fatal(1,"40ms reversal failed to stay blank before DISABLE");
        send(4,0,0,0); #41000000;
        if (safety_state!=0 || fault[7:0]!=0 || fpga_permit || pwm_left || pwm_right ||
            drv_left_in1 || drv_left_in2 || drv_right_in1 || drv_right_in2)
            $fatal(1,"DISABLE during coast replayed pending command");
        arm;
        // Active reverse must retain the previous pair on invalid UART traffic.
        maneuver(3,900,450); before_accepted=accepted; before_rejected=rejected;
        frame(3,16'(seq+1),8'h04,0,0,0);
        frame(3,16'(seq+2),3,PERIOD+1,0,0);
        frame(3,16'(seq+3),3,0,0,1);
        if (accepted!=before_accepted || rejected!=before_rejected+2)
            $fatal(1,"invalid direction/duty/CRC accepted");
        measure(3,900,450);
        #51000000;
        if (safety_state!=4 || !(fault&1) || fpga_permit || pwm_left || pwm_right)
            $fatal(1,"reverse invalid traffic refreshed watchdog or failed to stop");
        clear_fault; arm; maneuver(1,1350,1350);
        // Releasing E-stop must never restore the spin command.
        #71; safety_ok_async=0; #10;
        if (pwm_left || pwm_right || fpga_permit ||
            drv_left_in1 || drv_left_in2 || drv_right_in1 || drv_right_in2)
            $fatal(1,"spin E-stop not asynchronous");
        safety_ok_async=1; #10000;
        if (safety_state!=4 || fpga_permit || gate_fault_n_async) $fatal(1,"E-stop release resumed spin");
        clear_fault; arm; maneuver(2,1350,1350);
        // Reset with Motion permit cached HIGH must not replay a reverse command.
        #7; arst_n=0; #10;
        if (pwm_left || pwm_right || fpga_permit ||
            drv_left_in1 || drv_left_in2 || drv_right_in1 || drv_right_in2)
            $fatal(1,"spin reset not asynchronous");
        #1000; arst_n=1; #10000;
        send(1,0,0,0); send(2,0,0,0); send(3,3,1350,1350);
        if (fpga_permit || dut.core.session_active || pwm_left || pwm_right)
            $fatal(1,"cached UART/GPIO rearmed after spin reset");
        arm; maneuver(3,1350,1350); send(4,0,0,0); #10000;
        if (fpga_permit || pwm_left || pwm_right || dut.core.session_active)
            $fatal(1,"DISABLE failed while reversing");
        if (valid_status<10) $fatal(1,"missing single OUT UART telemetry");
        $display("COVER drive_maneuvers.numeric_cases %0d",cases);
        $display("COVER drive_maneuvers.drv8833_pin_cases %0d",cases);
        $display("COVER drive_maneuvers.reversal_refreshes %0d",reversal_refreshes);
        $display("COVER drive_maneuvers.disable_during_coast 1");
        $display("COVER drive_maneuvers.watchdog_deadlines %0d",watchdog_deadlines);
        $display("COVER drive_maneuvers.direction_combinations 4");
        $display("COVER drive_maneuvers.physical_status %0d",valid_status);
        $display("PASS tb_drive_maneuvers: 27MHz defaults, exact PWM/direction, OUT telemetry, interlock and safety");
        $finish;
    end
    initial begin #1000000000; $fatal(1,"timeout tb_drive_maneuvers"); end
endmodule
