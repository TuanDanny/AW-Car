`timescale 1ns/1ps
module tb_crc16_matrix;
    logic [15:0] crc=0, next_crc;
    logic [7:0] data=0;
    crc16_byte dut(.*);
    // Independent polynomial long division over {crc XOR data, zero byte};
    // deliberately differs from the DUT's eight conditional shift steps.
    function automatic [15:0] reference(input logic [15:0] seed, input logic [7:0] value);
        logic [23:0] polynomial;
        integer bit_no;
        begin
            polynomial={seed,8'b0}^{value,16'b0};
            for(bit_no=23;bit_no>=16;bit_no=bit_no-1)
                if(polynomial[bit_no]) polynomial=polynomial^(24'h011021<<(bit_no-16));
            reference=polynomial[15:0];
        end
    endfunction
    integer seed, byte_no, checks=0;
    task automatic check(input logic [15:0] previous_crc, input logic [7:0] value);
        begin
            crc=previous_crc; data=value; #1;
            if(next_crc!==reference(previous_crc,value))
                $fatal(1,"CRC seed=%h byte=%h got=%h expected=%h",crc,data,next_crc,reference(crc,data));
            checks=checks+1;
        end
    endtask
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_crc16_matrix.vcd"); $dumpvars(0,tb_crc16_matrix); end
        // Every previous CRC, with four byte patterns; every byte for additional
        // independent seeds. This is broad input coverage, not all 2^24 pairs.
        for(seed=0;seed<65536;seed=seed+1) begin
            check(seed[15:0],0); check(seed[15:0],255);
            check(seed[15:0],8'h55); check(seed[15:0],8'haa);
        end
        for(seed=0;seed<256;seed=seed+1)
            for(byte_no=0;byte_no<256;byte_no=byte_no+1)
                check({seed[7:0],~seed[7:0]},byte_no[7:0]);
        if(checks!=327680) $fatal(1,"CRC case count");
        $display("COVER crc.previous_values 65536");
        $display("COVER crc.byte_values 256");
        $display("COVER crc.comparisons %0d",checks);
        $display("PASS tb_crc16_matrix: %0d polynomial-division comparisons",checks); $finish;
    end
    initial begin #500000; $fatal(1,"CRC matrix timeout"); end
endmodule
