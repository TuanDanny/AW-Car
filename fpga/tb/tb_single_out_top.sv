`timescale 1ns/1ps
module tb_single_out_top;
    logic clk=0; always #18.519 clk=~clk; // Physical 27 MHz nominal clock
    logic arst_n=0, rx=1, tx;
    logic left_out=1, right_out=1;
    logic motion_permit_async=0, recovery_req_async=0;
    logic safety_ok_async=1, gate_fault_n_async=0;
    logic pwm_left,pwm_right,fpga_permit,recovery_ack,gate_clear;
    logic [1:0] direction;
    logic drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2;
    logic [7:0] safety_state;
    logic [15:0] fault;
    drive_core_single_out #(.SNAPSHOT_CYCLES(32),
        .HANDSHAKE_CYCLES(270), .CLEAR_CYCLES(135),
        .CLEAR_HOLD_CYCLES(27)) dut (.*);
    task automatic ticks(input integer n);
        repeat(n) @(negedge clk);
    endtask
    task automatic left_pulse;
        begin
            left_out=0;ticks(10);left_out=1;ticks(10);
        end
    endtask
    task automatic right_pulse;
        begin
            right_out=0;ticks(10);right_out=1;ticks(10);
        end
    endtask
    logic [7:0] observed;
    logic [7:0] first_status[0:46];
    localparam real BIT_NS=234.0*37.038; // Rounded divider 234 ticks at 27 MHz
    integer i,j,tx_count=0;
    integer hello_requests=0;
    logic [15:0] status_crc;
    always @(posedge clk) if(arst_n && dut.core.hello_request)
        hello_requests=hello_requests+1;
    function automatic logic [15:0] crc_step(input logic [15:0] c, input logic [7:0] b);
        logic [15:0] x; integer k;
        begin
            x=c^{b,8'b0};
            for(k=0;k<8;k=k+1) x=x[15] ? (x<<1)^16'h1021 : x<<1;
            crc_step=x;
        end
    endfunction
    task automatic host_byte(input logic [7:0] b);
        integer k;
        begin
            rx=0;#(BIT_NS);
            for(k=0;k<8;k=k+1) begin rx=b[k];#(BIT_NS); end
            rx=1;#(BIT_NS);
        end
    endtask
    task automatic host_hello(input logic [7:0] version);
        logic [7:0] bytes[0:12];
        logic [15:0] c; integer k;
        begin
            bytes[0]=8'ha5;bytes[1]=8'h5a;bytes[2]=version;
            bytes[3]=1;bytes[4]=0;
            bytes[5]=8'h78;bytes[6]=8'h56;bytes[7]=8'h34;bytes[8]=8'h12;
            bytes[9]=1;bytes[10]=0;
            c=16'hffff;
            for(k=2;k<11;k=k+1) c=crc_step(c,bytes[k]);
            bytes[11]=c[7:0];bytes[12]=c[15:8];
            for(k=0;k<13;k=k+1) host_byte(bytes[k]);
        end
    endtask
    initial forever begin
        @(negedge tx); #(BIT_NS * 1.5);
        for(i=0;i<8;i=i+1) begin observed[i]=tx; #(BIT_NS); end
        if(tx!==1) $fatal(1,"UART stop bit");
        case(tx_count)
            0: if(observed!==8'ha5) $fatal(1,"bad preamble0");
            1: if(observed!==8'h5a) $fatal(1,"bad preamble1");
            2: if(observed!==2) $fatal(1,"v2 version not sent");
            3: if(observed!==8'h80) $fatal(1,"not STATUS");
            4: if(observed!==34) $fatal(1,"v2 length not 34");
            default: begin end
        endcase
        if(tx_count<47) first_status[tx_count]=observed;
        tx_count=tx_count+1;
    end
    initial begin
        ticks(4);arst_n=1;ticks(15);
        if(dut.core.live_left!==0 || dut.core.live_right!==0)
            $fatal(1,"boot HIGH counted as pulse");
        left_pulse();left_pulse();right_pulse();
        if(dut.core.live_left!==2 || dut.core.live_right!==1)
            $fatal(1,"single-OUT top wiring/count");
        if(fpga_permit || pwm_left || pwm_right)
            $fatal(1,"default-off gate bypassed by encoder activity");
        // Real UART RX parser must reject v1 and recognize v2 wire frames.
        host_hello(1);ticks(12);
        if(hello_requests!==0) $fatal(1,"old protocol armed v2 parser");
        host_hello(2);ticks(12);
        if(hello_requests!==1) $fatal(1,"v2 HELLO not recognized over UART");
        if(fpga_permit || pwm_left || pwm_right)
            $fatal(1,"HELLO by itself enabled motors");
        ticks(120000);
        if(tx_count<47) $fatal(1,"v2 STATUS UART frame not transmitted");
        // Decode a complete UART-transmitted 47-byte STATUS, not just its header.
        // The first delivered STATUS may follow a reset/session flush; do not
        // assume the first snapshot (or its count) was transmitted.
        if({first_status[8],first_status[7],first_status[6],first_status[5]}!==32'd0 ||
           {first_status[10],first_status[9]}!==16'd1)
            $fatal(1,"v2 first STATUS header session/sequence mismatch");
        if({first_status[14],first_status[13],first_status[12],first_status[11]}>32'd2 ||
           {first_status[18],first_status[17],first_status[16],first_status[15]}>32'd1)
            $fatal(1,"v2 UART first STATUS count exceeds emitted pulses");
        if((first_status[28] & 8'h90)!==8'h10)
            $fatal(1,"v2 first STATUS mode/validity/unknown direction mismatch");
        if(first_status[28][0] &&
           {first_status[14],first_status[13],first_status[12],first_status[11]}<32'd2)
            $fatal(1,"v2 first STATUS left period valid without 2 rising edges");
        if(first_status[28][1] &&
           {first_status[18],first_status[17],first_status[16],first_status[15]}<32'd2)
            $fatal(1,"v2 first STATUS right period valid without 2 rising edges");
        status_crc=16'hffff;
        for(j=2;j<45;j=j+1) status_crc=crc_step(status_crc,first_status[j]);
        if(first_status[45]!==status_crc[7:0] || first_status[46]!==status_crc[15:8])
            $fatal(1,"v2 full STATUS UART CRC mismatch");
        $display("PASS tb_single_out_top: 2 encoder pins, v1 reject/v2 UART RX, full 47B STATUS TX/CRC, fail-closed gate");
        $finish;
    end
    initial begin #10000000; $fatal(1,"single-OUT top timeout"); end
endmodule
