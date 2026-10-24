`timescale 1ns/1ps
module uart_matrix_case #(parameter int HZ=800000, BAUD=100000)(output logic finished=0);
    localparam int B=(HZ+BAUD/2)/BAUD;
    logic clk=0, rst_n=0, rx=1;
    always #5 clk=!clk;
    logic [7:0] tx_data=0, rx_data;
    logic tx_valid=0, tx_ready, tx, tx_done, rx_valid, framing_error, break_error;
    uart_tx #(.CLK_HZ(HZ),.BAUD(BAUD)) transmitter(
        .clk(clk),.rst_n(rst_n),.data(tx_data),.valid(tx_valid),.ready(tx_ready),.tx(tx),.done(tx_done));
    uart_rx #(.CLK_HZ(HZ),.BAUD(BAUD)) receiver(
        .clk(clk),.rst_n(rst_n),.rx(rx),.data(rx_data),.valid(rx_valid),.framing_error(framing_error),.break_error(break_error));
    integer received=0;
    logic allow_rx=0;
    logic [7:0] expected_rx;
    always @(posedge clk) begin
        #1;
        if(rst_n && rx_valid) begin
            if(!allow_rx || rx_data!==expected_rx)
                $fatal(1,"UART matrix RX HZ=%0d got=%h expected=%h",HZ,rx_data,expected_rx);
            received=received+1; allow_rx=0;
        end
        if(rst_n && (framing_error || break_error)) $fatal(1,"unexpected UART matrix line error HZ=%0d",HZ);
    end
    task automatic boot;
        begin
            @(negedge clk); rst_n=0; tx_valid=0; rx=1; allow_rx=0;
            repeat(3) @(negedge clk); rst_n=1;
            repeat(3) @(negedge clk);
        end
    endtask
    task automatic start_tx(input logic [7:0] value);
        begin
            @(negedge clk); tx_data=value; tx_valid=1;
            @(posedge clk); #2;
            if(tx!==0 || tx_ready!==0 || tx_done!==0) $fatal(1,"TX accept HZ=%0d",HZ);
            @(negedge clk); tx_valid=0;
        end
    endtask
    task automatic send_rx(input logic [7:0] value);
        integer bit_no, before_count;
        logic [9:0] packet;
        begin
            packet={1'b1,value,1'b0}; before_count=received;
            @(negedge clk); #2; expected_rx=value; allow_rx=1;
            for(bit_no=0;bit_no<10;bit_no=bit_no+1) begin rx=packet[bit_no]; #(10*B); end
            rx=1; repeat(4) @(negedge clk);
            if(received!=before_count+1 || allow_rx) $fatal(1,"RX missing HZ=%0d",HZ);
        end
    endtask
    integer value, tick, slot, bit_no, before_count;
    logic [9:0] packet;
    initial begin
        boot;
        for(value=0;value<256;value=value+1) begin
            packet={1'b1,value[7:0],1'b0}; start_tx(value[7:0]);
            // Check every output tick against the wire format, including the
            // full stop bit and ignored requests while busy.
            for(tick=1;tick<=10*B;tick=tick+1) begin
                tx_valid=(tick<10*B); tx_data=~value[7:0];
                @(posedge clk); #2;
                if(tick<10*B) begin
                    if(tx!==packet[tick/B] || tx_ready!==0 || tx_done!==0)
                        $fatal(1,"TX duration/busy HZ=%0d value=%h tick=%0d",HZ,value,tick);
                end else if(tx!==1 || tx_ready!==1 || tx_done!==1)
                    $fatal(1,"TX stop/done length HZ=%0d",HZ);
                @(negedge clk);
            end
            tx_valid=0;
        end
        for(value=0;value<256;value=value+1) send_rx(value[7:0]);
        for(slot=0;slot<10;slot=slot+1) begin
            start_tx(8'h55); repeat(slot*B+B/2) @(negedge clk);
            #2; rst_n=0; #1;
            if(tx!==1 || tx_ready!==1 || tx_done!==0) $fatal(1,"TX reset slot=%0d HZ=%0d",slot,HZ);
            boot;
            packet=10'b1101010100; before_count=received;
            @(negedge clk); #2;
            for(bit_no=0;bit_no<=slot;bit_no=bit_no+1) begin
                rx=packet[bit_no];
                if(bit_no<slot) #(10*B); else #(5*B);
            end
            rst_n=0; rx=1; #1;
            if(rx_valid!==0) $fatal(1,"RX reset output HZ=%0d",HZ);
            boot; repeat(11*B) @(negedge clk);
            if(received!=before_count) $fatal(1,"aborted RX leaked slot=%0d HZ=%0d",slot,HZ);
            send_rx(8'ha5);
        end
        if(received!=266) $fatal(1,"RX coverage count HZ=%0d",HZ);
        $display("COVER uart.HZ%0d.bytes 256",HZ);
        $display("COVER uart.HZ%0d.tx_reset_slots 10",HZ);
        $display("COVER uart.HZ%0d.rx_reset_slots 10",HZ);
        finished=1;
    end
endmodule

module tb_uart_matrix;
    logic [3:0] finished;
    uart_matrix_case #(.HZ(800000)) c0(finished[0]);
    uart_matrix_case #(.HZ(900000)) c1(finished[1]);
    uart_matrix_case #(.HZ(1649999)) c2(finished[2]);
    uart_matrix_case #(.HZ(1650000)) c3(finished[3]);
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_uart_matrix.vcd"); $dumpvars(0,tb_uart_matrix); end
        wait(&finished);
        $display("PASS tb_uart_matrix: minimum/odd/rounded divider, all bytes, exact TX ticks, RX/TX reset at 10 symbols");
        $finish;
    end
    initial begin #20000000; $fatal(1,"UART matrix timeout"); end
endmodule
