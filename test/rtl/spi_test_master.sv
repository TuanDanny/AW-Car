`timescale 1ns/1ps
`default_nettype none
module spi_test_master (
    input wire logic miso,
    output logic cs_n = 1'b1, sclk = 1'b0, mosi = 1'b0
);
    logic [7:0] tx [0:31];
    logic [7:0] rx [0:31];
    function automatic logic [15:0] byte_crc(input logic [15:0] old_crc, input logic [7:0] value);
        logic [15:0] c;
        c = old_crc ^ {value, 8'b0};
        for (int b = 0; b < 8; b = b+1) c = c[15] ? (c << 1) ^ 16'h1021 : c << 1;
        byte_crc = c;
    endfunction
    task automatic fix_crc;
        logic [15:0] c;
        c = 16'hffff;
        for (int i=0; i<30; i=i+1) c = byte_crc(c, tx[i]);
        tx[30] = c[7:0]; tx[31] = c[15:8];
    endtask
    task automatic make_command(input int seq, input int left, input int right);
        for (int i=0; i<32; i=i+1) tx[i] = 0;
        tx[0]=8'h53; tx[1]=8'h31; tx[2]=1;
        tx[4]=seq[7:0]; tx[5]=seq[15:8];
        tx[6]=left[7:0]; tx[7]=left[15:8];
        tx[8]=right[7:0]; tx[9]=right[15:8];
        fix_crc();
    endtask
    task automatic begin_frame(input int skew_ns);
        #(skew_ns);
        for (int i=0; i<32; i=i+1) rx[i]=0;
        sclk=0; mosi=tx[0][7]; cs_n=0;
        #2000;
    endtask
    task automatic shift_bits(input int nbits, input int high_ns, input int low_ns);
        for (int b=0; b<nbits; b=b+1) begin
            mosi = b<256 ? tx[b/8][7-b%8] : 1'b0;
            #(low_ns); sclk=1;
            #1;
            if (b<256) rx[b/8][7-b%8]=miso;
            #(high_ns-1); sclk=0;
        end
    endtask
    task automatic end_frame;
        #2000; cs_n=1; mosi=0; #2000;
    endtask
    task automatic exchange(input int nbits, input int skew_ns, input int high_ns, input int low_ns);
        begin_frame(skew_ns); shift_bits(nbits, high_ns, low_ns); end_frame();
    endtask
    function automatic logic [15:0] get16(input int offset);
        get16 = {rx[offset+1],rx[offset]};
    endfunction
    function automatic logic [31:0] get32(input int offset);
        get32 = {rx[offset+3],rx[offset+2],rx[offset+1],rx[offset]};
    endfunction
    task automatic check_rx(input int expected_seq);
        logic [15:0] c;
        if (rx[0]!==8'h53 || rx[1]!==8'h52 || rx[2]!==1 || (rx[3]&8'hf8)!==0)
            $fatal(1,"RX header/version/flags: %h %h %h %h",rx[0],rx[1],rx[2],rx[3]);
        c=16'hffff;
        for (int i=0; i<30; i=i+1) c=byte_crc(c,rx[i]);
        if (get16(30)!==c) $fatal(1,"RX CRC expected %h got %h",c,get16(30));
        if (get16(4)!==expected_seq[15:0]) $fatal(1,"prior applied_seq expected %h got %h",expected_seq[15:0],get16(4));
    endtask
endmodule
