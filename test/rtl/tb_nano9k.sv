`timescale 1ns/1ps
`default_nettype none
// The SAME black-box tests run against RTL and the actual post-PnR netlist.
module tb_nano9k;
    logic clk=0,arst_n=1,enc_left=0,enc_right=1;
    always #18.5185185 clk=~clk;
    wire logic mosi,sclk,cs_n,miso,l1,l2,r1,r2;
    wire logic [5:0] leds;
    spi_test_master master(.miso(miso),.cs_n(cs_n),.sclk(sclk),.mosi(mosi));
    simplev1_nano9k dut(.clk(clk),.arst_n(arst_n),.spi_mosi(mosi),.spi_sclk(sclk),.spi_cs_n(cs_n),.spi_miso(miso),
        .enc_left(enc_left),.enc_right(enc_right),.drv_left_in1(l1),.drv_left_in2(l2),
        .drv_right_in1(r1),.drv_right_in2(r2),.leds_n(leds));
    always @(negedge clk) if($time>200) begin
        if(l1&&l2 || r1&&r2) $fatal(1,"board boundary overlap");
        if ((^{l1,l2,r1,r2})===1'bx) $fatal(1,"board boundary unknown after configuration");
    end
    initial begin
        // No button reset: prove configuration INIT/POR by observation.
        repeat(1600) @(negedge clk);
        if({l1,l2,r1,r2}!==0) $fatal(1,"POR not neutral");
        master.make_command(16'h1234,1350,-1350);master.exchange(256,7,500,500);master.check_rx(0);
        if(master.rx[3]!==1 || master.get32(6)!==0 || master.get32(10)!==0 || master.get32(26)!==0)
            $fatal(1,"boot status/initial-high encoder");
        repeat(1400) @(negedge clk);
        repeat(1350) begin
            @(negedge clk);
            if({l1,l2,r1,r2}!==4'b1001) $fatal(1,"board full duty / direction");
        end
        // Production 256-clock filter. Short noise must not count.
        enc_left=1;repeat(100) @(negedge clk);enc_left=0;repeat(400) @(negedge clk);
        enc_right=0;repeat(400) @(negedge clk);
        enc_right=1;repeat(500) @(negedge clk);
        enc_right=0;repeat(500) @(negedge clk);
        enc_right=1;repeat(400) @(negedge clk);
        master.make_command(16'hbeef,-1350,1350);master.exchange(256,29,490,510);master.check_rx(16'h1234);
        if(master.rx[3]!==4 || master.get32(6)!==0 || master.get32(10)!==2 || master.get32(18)!==1000 || master.get32(26)==0)
            $fatal(1,"mapped encoder count/period/age flags: flags=%h lc=%0d rc=%0d rp=%0d age=%0d",master.rx[3],master.get32(6),master.get32(10),master.get32(18),master.get32(26));
        repeat(2800) @(negedge clk);
        repeat(1350) begin
            @(negedge clk);
            if({l1,l2,r1,r2}!==4'b0110) $fatal(1,"board opposite polarity");
        end
        master.make_command(55,0,0);master.tx[3]=1;master.fix_crc();master.exchange(256,13,510,490);master.check_rx(16'hbeef);
        master.make_command(56,0,0);master.exchange(255,8,500,500);
        master.make_command(57,0,0);master.tx[30]=master.tx[30]^1;master.exchange(256,21,500,500);master.check_rx(16'hbeef);
        master.make_command(58,0,0);master.begin_frame(11);master.shift_bits(130,500,500);
        #7;arst_n=0;#2;
        if({l1,l2,r1,r2}!==0) $fatal(1,"board asynchronous S2 shutdown");
        master.end_frame();arst_n=1;repeat(1600) @(negedge clk);
        master.make_command(59,0,0);master.exchange(256,36,500,500);master.check_rx(0);
        if({l1,l2,r1,r2}!==0 || master.rx[3]!==1) $fatal(1,"board reset/parser recovery");
        $display("PASS tb_nano9k: no-button POR, actual target pins/ports, production filter, encoder snapshot CRC/period/age, prior seq, full signed PWM, malformed frames, asynchronous S2");
        $finish;
    end
    initial begin #10000000;$fatal(1,"tb_nano9k timeout");end
endmodule
