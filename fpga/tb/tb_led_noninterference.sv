`timescale 1ns/1ps
module tb_led_noninterference;
    logic clk=0; always #18.5185 clk=~clk; // One nominal 27 MHz clock.
    logic arst_n=0,rx=1,left_out=0,right_out=0;
    logic motion_permit_async=0,recovery_req_async=0,safety_ok_async=1,gate_fault_n_async=1;
    wire tx,drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2;
    wire fpga_permit,recovery_ack,gate_clear;
    wire [5:0] leds_n;
    wire ref_tx,ref_l1,ref_l2,ref_r1,ref_r2,ref_permit,ref_ack,ref_clear;
    wire [7:0] ref_state;
    wire [15:0] ref_fault;
    wire ref_pwm_l,ref_pwm_r;
    wire [1:0] ref_direction;
    // Protocol is real UART/v2. Timers/baud are explicitly shortened for a
    // cycle-for-cycle observer miter, not a second physical timing sign-off.
    aw_car_top #(.BAUD(2700000),.PERIOD_CYCLES(16),.SNAPSHOT_CYCLES(700),
        .WATCHDOG_CYCLES(30000),.HANDSHAKE_CYCLES(100000),.CLEAR_CYCLES(600),
        .CLEAR_HOLD_CYCLES(30),.INTERBYTE_CYCLES(1000),.FRAME_CYCLES(10000),
        .ZERO_CYCLES(40),.SETUP_CYCLES(3),.FILTER_N(1),.LED_HALF_CYCLES(7)) dut(.*);
    drive_core #(.BAUD(2700000),.PERIOD_CYCLES(16),.SNAPSHOT_CYCLES(700),
        .WATCHDOG_CYCLES(30000),.HANDSHAKE_CYCLES(100000),.CLEAR_CYCLES(600),
        .CLEAR_HOLD_CYCLES(30),.INTERBYTE_CYCLES(1000),.FRAME_CYCLES(10000),
        .ZERO_CYCLES(40),.SETUP_CYCLES(3),.FILTER_N(1)) reference_core (
        .clk(clk),.arst_n(arst_n),.rx(rx),.left_ab(2'b00),.right_ab(2'b00),
        .encoder_left_out(left_out),.encoder_right_out(right_out),
        .motion_permit_async(motion_permit_async),.recovery_req_async(recovery_req_async),
        .safety_ok_async(safety_ok_async),.gate_fault_n_async(gate_fault_n_async),
        .tx(ref_tx),.drv_left_in1(ref_l1),.drv_left_in2(ref_l2),
        .drv_right_in1(ref_r1),.drv_right_in2(ref_r2),.fpga_permit(ref_permit),
        .recovery_ack(ref_ack),.gate_clear(ref_clear),.safety_state(ref_state),.fault(ref_fault),
        .pwm_left(ref_pwm_l),.pwm_right(ref_pwm_r),.direction(ref_direction)
    );
    integer comparisons=0,led_changes=0,pwm_ticks=0;
    logic [5:0] previous_led=6'b111111;
    always @(negedge clk) begin
        #1;
        if (arst_n) begin
            if ({tx,drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2,fpga_permit,recovery_ack,gate_clear}
                !== {ref_tx,ref_l1,ref_l2,ref_r1,ref_r2,ref_permit,ref_ack,ref_clear})
                $fatal(1,"observer changed UART/DRV8833/permit/recovery outputs");
            if ({dut.core.safety_state,dut.core.fault,dut.core.pwm_left,dut.core.pwm_right,dut.core.direction}
                !== {ref_state,ref_fault,ref_pwm_l,ref_pwm_r,ref_direction})
                $fatal(1,"observer changed Safety/PWM state");
            comparisons++;
            if (leds_n!=previous_led) led_changes++;
            if (ref_pwm_l || ref_pwm_r) pwm_ticks++;
        end
        previous_led=leds_n;
    end
    task automatic ticks(input integer n); repeat(n) @(negedge clk); endtask
    function automatic logic [15:0] crc_byte(input logic [15:0] c,input logic [7:0] b);
        logic [15:0] x;
        begin
            x=c^{b,8'b0};
            for(int i=0;i<8;i++) x=x[15] ? (x<<1)^16'h1021 : x<<1;
            return x;
        end
    endfunction
    logic [31:0] session_id=32'h12345670;
    integer seq=0;
    task automatic packet(input logic [7:0] kind,input logic [1:0] direction,
                          input integer dl,input integer dr,input bit corrupt=0);
        logic [151:0] data;
        logic [15:0] crc;
        integer length;
        begin
            seq++;
            length=kind==3 ? 6 : 0;
            data=0;data[15:0]=16'h5aa5;data[23:16]=2;data[31:24]=kind;
            data[39:32]=8'(length);data[71:40]=session_id;data[87:72]=16'(seq);
            data[103:96]={6'd0,direction};data[119:104]=16'(dl);data[135:120]=16'(dr);
            crc=16'hffff;
            for(int i=2;i<11+length;i++) crc=crc_byte(crc,data[i*8+:8]);
            data[(11+length)*8+:16]=corrupt ? crc^16'h8000 : crc;
            for(int i=0;i<13+length;i++) begin
                rx=0;ticks(10);
                for(int j=0;j<8;j++) begin rx=data[i*8+j];ticks(10);end
                rx=1;ticks(10);
            end
            ticks(15);
        end
    endtask
    task automatic arm;
        begin
            session_id++;motion_permit_async=0;recovery_req_async=0;ticks(20);
            recovery_req_async=1;wait(recovery_ack);ticks(5);
            recovery_req_async=0;wait(!recovery_ack);ticks(1100);
            packet(1,0,0,0);wait(ref_state==1);
            packet(2,0,0,0);wait(recovery_ack);ticks(5);
            motion_permit_async=1;wait(ref_state==3);ticks(8);
            if(leds_n!==6'b111110) $fatal(1,"connected indicator not LED1 only");
        end
    endtask
    initial begin
        #1;arst_n=1;#1;arst_n=0;ticks(8);arst_n=1;ticks(50);
        if(led_changes<4) $fatal(1,"waiting LED was not exercised");
        arm();packet(3,0,8,12);ticks(80);
        packet(3,0,16,16,1);ticks(30); // CRC fault is not a motor command.
        packet(3,1,4,10);ticks(120); // Reversal/interlock while observer runs.
        packet(4,0,0,0);wait(ref_state==0);motion_permit_async=0;ticks(40);
        arm();packet(3,2,10,5);ticks(31000); // Real watchdog expiration.
        if(ref_state!=4 || !(ref_fault&1) || leds_n!==0 || fpga_permit)
            $fatal(1,"watchdog must outrank connected/waiting and remain OFF");
        arst_n=0;motion_permit_async=0;ticks(8);arst_n=1;ticks(20);
        arm();packet(3,3,12,12);ticks(40);
        #3;safety_ok_async=0;#2;
        if({fpga_permit,drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2}!==0)
            $fatal(1,"LED integration affected asynchronous stop");
        ticks(12);
        if(leds_n!==0 || ref_state!=4) $fatal(1,"safety fault LED priority");
        if(comparisons<30000 || pwm_ticks<100) $fatal(1,"miter lacked active control evidence");
        $display("COVER led_noninterference.compared_cycles %0d",comparisons);
        $display("COVER led_noninterference.active_pwm_ticks %0d",pwm_ticks);
        $display("PASS tb_led_noninterference: cycle-exact Safety/UART/PWM/permit without observer, CRC reject, reversal, STOP, watchdog, async E-stop");
        $finish;
    end
    initial begin #10000000;$fatal(1,"LED noninterference timeout");end
endmodule
