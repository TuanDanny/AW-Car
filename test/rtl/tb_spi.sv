`timescale 1ns/1ps
`default_nettype none
module tb_spi;
    logic clk=0, arst_n=0, enc_left=0, enc_right=0;
    always #18.5185185 clk=~clk;
    wire logic mosi, sclk, cs_n, miso, twin_miso;
    wire logic l1,l2,r1,r2,tl1,tl2,tr1,tr2;
    wire logic [5:0] leds, twin_leds;
    logic observer_difference=0;
    logic [7:0] golden [0:127];
    logic [31:0] expected_lc,expected_rc,expected_lp,expected_rp,expected_la,expected_ra;
    int accepted_seq=0, checked_frames=0;
    spi_test_master master(.miso(miso),.cs_n(cs_n),.sclk(sclk),.mosi(mosi));
    simplev1_core #(.WATCHDOG_CYCLES(2000000),.ENCODER_FILTER_CYCLES(8),.LED_HALF_CYCLES(17)) dut(
        .clk(clk),.arst_n(arst_n),.spi_mosi(mosi),.spi_sclk(sclk),.spi_cs_n(cs_n),.spi_miso(miso),
        .enc_left(enc_left),.enc_right(enc_right),.drv_left_in1(l1),.drv_left_in2(l2),
        .drv_right_in1(r1),.drv_right_in2(r2),.leds_n(leds));
    simplev1_core #(.WATCHDOG_CYCLES(2000000),.ENCODER_FILTER_CYCLES(8),.LED_HALF_CYCLES(31)) twin(
        .clk(clk),.arst_n(arst_n),.spi_mosi(mosi),.spi_sclk(sclk),.spi_cs_n(cs_n),.spi_miso(twin_miso),
        .enc_left(enc_left),.enc_right(enc_right),.drv_left_in1(tl1),.drv_left_in2(tl2),
        .drv_right_in1(tr1),.drv_right_in2(tr2),.leds_n(twin_leds));
    always @(posedge clk) begin
        if (dut.link.cs_fall) begin
            expected_lc=dut.left_count; expected_rc=dut.right_count;
            expected_lp=dut.left_period; expected_rp=dut.right_period;
            expected_la=dut.left_age; expected_ra=dut.right_age;
        end
        #1;
        if (arst_n && dut.rst_n) begin
            if ({l1,l2,r1,r2,miso} !== {tl1,tl2,tr1,tr2,twin_miso}) $fatal(1,"observer changed drive or SPI");
            if (l1 && l2 || r1 && r2) $fatal(1,"H-bridge overlap");
            if ((^{l1,l2,r1,r2,miso})===1'bx) $fatal(1,"unknown physical output");
            if (leds!=twin_leds) observer_difference=1;
            if (leds[5:1]!==5'b11111) $fatal(1,"unused LEDs");
        end
    end
    task automatic check_snapshot;
        if (master.get32(6)!==expected_lc || master.get32(10)!==expected_rc ||
            master.get32(14)!==expected_lp || master.get32(18)!==expected_rp ||
            master.get32(22)!==expected_la || master.get32(26)!==expected_ra)
            $fatal(1,"RX fields did not come from the same CS snapshot");
    endtask
    task automatic rejected(input int bits_to_send);
        master.exchange(bits_to_send,7,491,509);
        if (bits_to_send>=256) begin master.check_rx(accepted_seq); check_snapshot(); end
        if (dut.applied_seq!==accepted_seq[15:0] || dut.target_left!==16'sd1350 || dut.target_right!==-16'sd1350)
            $fatal(1,"malformed frame changed atomic command (%0d bits)",bits_to_send);
        checked_frames=checked_frames+1;
    endtask
    initial begin
        logic [15:0] check_crc;
        check_crc=16'hffff;
        for (int i=1;i<=9;i=i+1) check_crc=master.byte_crc(check_crc,8'h30+i);
        if (check_crc!==16'h29b1) $fatal(1,"CCITT-FALSE reference check");
        $readmemh("data/fpga_spi_vectors.hex",golden);
        master.make_command(0,0,0);
        for(int i=0;i<32;i=i+1) if(master.tx[i]!==golden[i]) $fatal(1,"golden TX neutral byte %0d",i);
        master.make_command(16'h1234,1350,-1350);
        for(int i=0;i<32;i=i+1) if(master.tx[i]!==golden[32+i]) $fatal(1,"golden TX signed byte %0d",i);
        #100; arst_n=1;
        repeat(100) @(negedge clk);
        if ({l1,l2,r1,r2}!==0 || !dut.timed_out) $fatal(1,"boot not neutral");
        if (!observer_difference) $fatal(1,"observer independence stimulus ineffective");
        master.make_command(1,1350,-1350);
        master.begin_frame(19); master.shift_bits(256,500,500);
        repeat(12) @(negedge clk);
        if (dut.applied_seq!==0 || {l1,l2,r1,r2}!==0) $fatal(1,"commit happened before CS rise");
        master.end_frame(); master.check_rx(0); check_snapshot();
        for(int i=0;i<32;i=i+1) if(master.rx[i]!==golden[64+i]) $fatal(1,"golden boot RX byte %0d",i);
        accepted_seq=1;
        repeat(1400) @(negedge clk);
        repeat(1350) begin
            @(negedge clk);
            if ({l1,l2,r1,r2}!==4'b1001) $fatal(1,"full duty not constant HIGH on selected polarity");
        end
        // Every reserved byte, independently with a correct CRC.
        for(int i=3;i<30;i=i+1) if(i==3 || i>=10) begin
            master.make_command(2,0,0); master.tx[i]=1; master.fix_crc(); rejected(256);
        end
        for(int i=0;i<3;i=i+1) begin
            master.make_command(2,0,0); master.tx[i]=master.tx[i]^8'h01; master.fix_crc(); rejected(256);
        end
        for(int i=0;i<3;i=i+1) begin
            master.make_command(2,0,0);
            if(i<2) master.tx[30+i]=master.tx[30+i]^8'h80;
            else master.tx[6]=master.tx[6]^8'h01;
            rejected(256);
        end
        for(int side=0;side<2;side=side+1) for(int k=0;k<4;k=k+1) begin
            case(k)
                0: master.make_command(2,side ? 0:1351,side ? 1351:0);
                1: master.make_command(2,side ? 0:-1351,side ? -1351:0);
                2: master.make_command(2,side ? 0:32767,side ? 32767:0);
                3: master.make_command(2,side ? 0:-32768,side ? -32768:0);
            endcase
            rejected(256);
        end
        master.make_command(2,0,0);
        rejected(0); rejected(1); rejected(7); rejected(8); rejected(239); rejected(240);
        rejected(248); rejected(255); rejected(257); rejected(264); rejected(512);
        // Non-byte CS abort must not contaminate the following frame. Sweep 27MHz phase.
        for(int i=0;i<37;i=i+1) begin
            master.make_command(10+i,1350,-1350);
            master.exchange(256,i,480+(i%5)*10,520-(i%5)*10);
            master.check_rx(accepted_seq); check_snapshot(); accepted_seq=10+i;
            if (dut.applied_seq!==accepted_seq[15:0]) $fatal(1,"phase-swept command not applied");
            checked_frames=checked_frames+1;
        end
        // A reset master may reuse a seq and wrap/restart without any ARM/session.
        master.make_command(65535,1350,-1350); master.exchange(256,3,500,500); master.check_rx(accepted_seq); accepted_seq=65535;
        master.make_command(0,1350,-1350); master.exchange(256,4,500,500); master.check_rx(accepted_seq); accepted_seq=0;
        master.make_command(0,1350,-1350); master.exchange(256,5,500,500); master.check_rx(0);
        enc_left=1; repeat(20) @(negedge clk); enc_left=0; repeat(20) @(negedge clk);
        if (dut.left_count!==1 || dut.left_period!==0) $fatal(1,"first encoder edge/period");
        master.make_command(77,-1350,1350);
        fork
            begin
                master.exchange(256,11,500,500);
            end
            begin
                #20000; enc_left=1; enc_right=1;
                #20000; enc_left=0; enc_right=0;
                #20000; enc_left=1; enc_right=1;
            end
        join
        master.check_rx(0); check_snapshot();
        if(master.get32(6)!==1 || master.get32(10)!==0 || dut.left_count!==3 || dut.right_count!==2)
            $fatal(1,"encoder changes during transfer did not exercise snapshot freeze");
        repeat(2800) @(negedge clk);
        repeat(1350) begin
            @(negedge clk);
            if ({l1,l2,r1,r2}!==4'b0110) $fatal(1,"negative full duty");
        end
        if (leds[0]!==0) $fatal(1,"connected observer");
        // Reset in a partially received frame; raw reset must clear drive immediately.
        master.make_command(88,500,500); master.begin_frame(13); master.shift_bits(100,500,500);
        #7; arst_n=0; #1;
        if ({l1,l2,r1,r2}!==0) $fatal(1,"asynchronous reset drive");
        master.end_frame(); arst_n=1; repeat(50) @(negedge clk);
        master.make_command(99,0,0); master.exchange(256,1,500,500); master.check_rx(0);
        if(dut.applied_seq!==99 || {l1,l2,r1,r2}!==0) $fatal(1,"reset/parser recovery");
        $display("PASS tb_spi: %0d rejected/phase frames, atomic CS commit, golden CRC, prior-seq, frozen snapshot, observer independence",checked_frames);
        $finish;
    end
    initial begin #100000000; $fatal(1,"tb_spi timeout"); end
endmodule
