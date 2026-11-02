`timescale 1ns/1ps
module tb_single_out_protocol;
    logic clk=0;
    always #5 clk=~clk;
    logic rst_n=0, flush=0, snapshot_valid=0;
    logic snapshot_ready, snapshot_dropped, byte_valid, byte_ready=0, byte_last;
    logic [7:0] byte_data;
    logic [31:0] session=32'h12345678, snapshot_left=32'h11223344;
    logic [31:0] snapshot_right=32'h55667788, snapshot_time=32'h99aabbcc;
    logic [15:0] snapshot_seq=16'h4321, fault=16'h0123;
    logic [3:0] snapshot_status=0;
    logic [7:0] snapshot_status_ext=8'h3f, safety_state=8'h02;
    logic [31:0] snapshot_left_period=32'h10203040;
    logic [31:0] snapshot_right_period=32'h50607080;
    logic [31:0] snapshot_left_age=32'h90a0b0c0;
    logic [31:0] snapshot_right_age=32'hd0e0f000;
    logic [31:0] frame_session;
    logic [7:0] frame_state;
    frame_tx #(.PROTOCOL_VERSION(2)) dut (.*);
    logic [7:0] expected [0:46];
    logic [511:0] vectors [0:6];
    logic [15:0] crc;
    integer i,j;

    function automatic logic [15:0] crc_step(input logic [15:0] prior, input logic [7:0] value);
        logic [15:0] t;
        integer k;
        begin
            t=prior^{value,8'b0};
            for(k=0;k<8;k=k+1) t=t[15] ? (t<<1)^16'h1021 : t<<1;
            crc_step=t;
        end
    endfunction
    task automatic word4(input integer offset, input logic [31:0] value);
        integer k;
        for(k=0;k<4;k=k+1) expected[offset+k]=value[k*8+:8];
    endtask
    initial begin
        $readmemh("../../firmware/shared/fpga-vectors-v2.hex", vectors);
        if (vectors[6][511:504]!==47) $fatal(1,"v2 golden length");
        expected[0]=8'ha5;expected[1]=8'h5a;expected[2]=2;
        expected[3]=8'h80;expected[4]=34;
        word4(5,session);
        expected[9]=snapshot_seq[7:0];expected[10]=snapshot_seq[15:8];
        word4(11,snapshot_left);word4(15,snapshot_right);word4(19,snapshot_time);
        expected[23]=snapshot_seq[7:0];expected[24]=snapshot_seq[15:8];
        expected[25]=safety_state;expected[26]=fault[7:0];
        expected[27]=fault[15:8];expected[28]=snapshot_status_ext;
        word4(29,snapshot_left_period);word4(33,snapshot_right_period);
        word4(37,snapshot_left_age);word4(41,snapshot_right_age);
        crc=16'hffff;
        for(i=2;i<45;i=i+1) crc=crc_step(crc,expected[i]);
        expected[45]=crc[7:0];expected[46]=crc[15:8];
        for(i=0;i<47;i=i+1)
            if(expected[i]!==vectors[6][i*8+:8])
                $fatal(1,"v2 layout/CRC differs from independent Python golden byte %0d",i);
        repeat(3) @(negedge clk);rst_n=1;
        @(negedge clk);snapshot_valid=1;
        @(negedge clk);snapshot_valid=0;
        // Change all source fields while busy to prove atomic freeze.
        snapshot_left=0;snapshot_right=0;snapshot_time=0;
        snapshot_seq=0;snapshot_status_ext=0;fault=0;safety_state=0;
        snapshot_left_period=0;snapshot_right_period=0;
        snapshot_left_age=0;snapshot_right_age=0;session=0;
        for(j=0;j<47;j=j+1) begin
            if(!byte_valid || byte_data!==expected[j] ||
               byte_last!==(j==46) || frame_session!==32'h12345678 ||
               frame_state!==2)
                $fatal(1,"v2 frame byte/metadata mismatch at %d",j);
            // Random-looking backpressure must freeze current byte.
            if(j%3==0) begin
                repeat(3) @(negedge clk);
                if(byte_data!==expected[j]) $fatal(1,"v2 stall corrupted byte");
            end
            byte_ready=1;@(negedge clk);byte_ready=0;
        end
        if(!snapshot_ready || snapshot_dropped) $fatal(1,"v2 TX not released");
        $display("PASS tb_single_out_protocol: v2 47-byte STATUS, CRC, 4 extra fields, frozen snapshot and stalls");
        $finish;
    end
    initial begin #100000; $fatal(1,"v2 serializer timeout"); end
endmodule
