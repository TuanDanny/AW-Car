`timescale 1ns/1ps
module tb_single_out_v2_rx;
    logic clk=0; always #5 clk=~clk;
    logic rst_n=0, flush=0, byte_valid=0, byte_error=0;
    logic [7:0] byte_data=0;
    logic frame_valid, frame_error;
    logic [7:0] frame_type;
    logic [31:0] frame_session;
    logic [15:0] frame_sequence;
    logic [47:0] frame_payload;
    frame_rx #(.INTERBYTE_CYCLES(64), .FRAME_CYCLES(400),
               .PROTOCOL_VERSION(2)) dut (.*);
    function automatic logic [15:0] crc_step(input logic [15:0] prior, input logic [7:0] value);
        logic [15:0] t; integer k;
        begin
            t=prior^{value,8'b0};
            for(k=0;k<8;k=k+1) t=t[15] ? (t<<1)^16'h1021 : t<<1;
            crc_step=t;
        end
    endfunction
    task automatic put(input logic [7:0] value);
        begin
            @(negedge clk);byte_data=value;byte_valid=1;
            @(negedge clk);byte_valid=0;
        end
    endtask
    integer accepted=0,errors=0,i;
    logic [7:0] packet [0:18];
    logic [15:0] crc;
    always @(posedge clk) begin
        #1;
        if(frame_valid) begin
            accepted=accepted+1;
            if(frame_type!==3 || frame_session!==32'h12345678 ||
               frame_sequence!==16'h2345 ||
               frame_payload!==48'h054603010000)
                $fatal(1,"wrong v2 command parsed");
        end
        if(frame_error) errors=errors+1;
    end
    task automatic send(input logic [7:0] version);
        integer j;
        begin
            packet[0]=8'ha5;packet[1]=8'h5a;packet[2]=version;
            packet[3]=3;packet[4]=6;
            packet[5]=8'h78;packet[6]=8'h56;packet[7]=8'h34;packet[8]=8'h12;
            packet[9]=8'h45;packet[10]=8'h23;
            packet[11]=0;packet[12]=0;packet[13]=1;packet[14]=3;
            packet[15]=8'h46;packet[16]=8'h05;
            crc=16'hffff;
            for(j=2;j<17;j=j+1) crc=crc_step(crc,packet[j]);
            packet[17]=crc[7:0];packet[18]=crc[15:8];
            for(j=0;j<19;j=j+1) put(packet[j]);
            repeat(3) @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        send(1);
        if(accepted!=0 || errors==0) $fatal(1,"v1 frame accepted in v2-only mode");
        send(2);
        if(accepted!=1) $fatal(1,"v2 command not accepted");
        $display("PASS tb_single_out_v2_rx: v1 command rejected, v2 command/CRC/session/fields accepted");
        $finish;
    end
    initial begin #30000; $fatal(1,"v2 parser timeout"); end
endmodule
