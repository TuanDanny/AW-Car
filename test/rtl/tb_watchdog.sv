`timescale 1ns/1ps
`default_nettype none
module tb_watchdog;
    localparam int DEADLINE=13500000;
    logic clk=0,arst_n=0;
    always #18.5185185 clk=~clk;
    wire logic mosi,sclk,cs_n,miso,l1,l2,r1,r2;
    wire logic [5:0] leds;
    spi_test_master master(.miso(miso),.cs_n(cs_n),.sclk(sclk),.mosi(mosi));
    simplev1_core dut(.clk(clk),.arst_n(arst_n),.spi_mosi(mosi),.spi_sclk(sclk),.spi_cs_n(cs_n),.spi_miso(miso),
        .enc_left(1'b0),.enc_right(1'b0),.drv_left_in1(l1),.drv_left_in2(l2),.drv_right_in1(r1),.drv_right_in2(r2),.leds_n(leds));
    initial begin
        #100;arst_n=1;repeat(50) @(negedge clk);
        master.make_command(100,1350,1350);master.exchange(256,17,500,500);master.check_rx(0);
        while(dut.watchdog_ticks<DEADLINE-15000) @(negedge clk);
        if(dut.timed_out || {l1,l2,r1,r2}!==4'b1010) $fatal(1,"watchdog fired early");
        // A valid-looking but bad-CRC frame just before the deadline must not refresh it.
        master.make_command(101,1350,1350);master.tx[31]=master.tx[31]^1;
        master.exchange(256,2,500,500);master.check_rx(100);
        if(dut.applied_seq!==100 || dut.watchdog_ticks<DEADLINE-15000) $fatal(1,"invalid frame refreshed deadline");
        while(dut.watchdog_ticks<DEADLINE-1) @(negedge clk);
        if(dut.timed_out || {l1,l2,r1,r2}!==4'b1010) $fatal(1,"500ms deadline early");
        @(negedge clk);
        if(!dut.timed_out || dut.target_left!==0 || dut.target_right!==0) $fatal(1,"500ms deadline late");
        @(negedge clk);
        if({l1,l2,r1,r2}!==0) $fatal(1,"watchdog did not override PWM mid-period");
        master.make_command(0,-1350,-1350);master.exchange(256,9,500,500);master.check_rx(100);
        if(!master.rx[3][0] || dut.timed_out || dut.applied_seq!==0) $fatal(1,"timeout status/recovery latched a fault");
        repeat(1400) @(negedge clk);
        if({l1,l2,r1,r2}!==4'b0101 || leds[0]!==0) $fatal(1,"timeout recovery did not resume");
        master.make_command(1,0,0);master.exchange(256,20,500,500);master.check_rx(0);
        repeat(1400) @(negedge clk);
        if({l1,l2,r1,r2}!==0) $fatal(1,"neutral did not stop");
        $display("PASS tb_watchdog: actual default 13500000 clocks (500ms), invalid CRC cannot refresh, output kill <=1 clk, fresh valid command recovers");
        $finish;
    end
    initial begin #510000000; $fatal(1,"tb_watchdog timeout"); end
endmodule
