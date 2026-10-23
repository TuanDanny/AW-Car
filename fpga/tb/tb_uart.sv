`timescale 1ns/1ps
module tb_uart;
    // RX stimulus and TX observer use independent elapsed-time UART models.
    localparam real BIT_NS = 200.0;
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0, rx = 1;
    logic [7:0] rx_data, tx_data = 0;
    logic rx_valid, framing_error, break_error, tx_valid = 0, tx_ready, tx_line, tx_done;
    uart_rx #(.CLK_HZ(100000000), .BAUD(5000000)) receiver (
        .clk(clk), .rst_n(rst_n), .rx(rx), .data(rx_data), .valid(rx_valid),
        .framing_error(framing_error), .break_error(break_error));
    uart_tx #(.CLK_HZ(100000000), .BAUD(5000000)) transmitter (
        .clk(clk), .rst_n(rst_n), .data(tx_data), .valid(tx_valid),
        .ready(tx_ready), .tx(tx_line), .done(tx_done));
    integer received = 0, framing = 0, breaks = 0, transmitted = 0, done_count = 0;
    logic expect_rx = 0, check_tx = 1;
    logic [7:0] expected_rx;
    always @(posedge clk) begin
        #1;
        if (rx_valid) begin
            if (!expect_rx || rx_data !== expected_rx) $fatal(1, "RX mismatch %h/%h", rx_data, expected_rx);
            received = received + 1;
        end
        if (framing_error) framing = framing + 1;
        if (break_error) breaks = breaks + 1;
        if (tx_done) done_count = done_count + 1;
        if (rst_n && (^{rx_valid, framing_error, break_error, tx_ready, tx_line}) === 1'bx)
            $fatal(1, "unknown UART output");
    end
    logic [7:0] observed_tx;
    integer bit_no;
    initial forever begin
        @(negedge tx_line);
        #(BIT_NS / 2);
        if (tx_line !== 0 && check_tx) $fatal(1, "TX start bit");
        for (bit_no = 0; bit_no < 8; bit_no = bit_no + 1) begin
            #(BIT_NS); observed_tx[bit_no] = tx_line;
        end
        #(BIT_NS);
        if (check_tx) begin
            if (tx_line !== 1 || observed_tx !== transmitted[7:0])
                $fatal(1, "TX byte/stop %h expected %h", observed_tx, transmitted[7:0]);
            transmitted = transmitted + 1;
        end
    end
    task automatic send_rx(input logic [7:0] value, input real bit_ns, input logic good_stop);
        integer i, before_count;
        begin
            expected_rx = value; expect_rx = good_stop; before_count = received;
            rx = 0; #(bit_ns);
            for (i = 0; i < 8; i = i + 1) begin rx = value[i]; #(bit_ns); end
            rx = good_stop; #(bit_ns);
            if (good_stop && received != before_count + 1) $fatal(1, "RX missing byte");
            expect_rx = 0;
        end
    endtask
    integer i, rate, saved;
    real bit_ns;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_uart.vcd"); $dumpvars(0, tb_uart); end
        repeat (4) @(negedge clk); rst_n = 1;
        #73;
        // Sub-half-bit glitch must not be treated as a byte.
        rx = 0; #30; rx = 1; #(BIT_NS * 11);
        if (received != 0) $fatal(1, "false start emitted byte");
        for (rate = 0; rate < 3; rate = rate + 1) begin
            case (rate)
                0: bit_ns = BIT_NS;
                1: bit_ns = BIT_NS / 1.02;
                2: bit_ns = BIT_NS / 0.98;
            endcase
            #37;
            for (i = 0; i < 256; i = i + 1) send_rx(i[7:0], bit_ns, 1);
        end
        saved = received;
        send_rx(8'hff, BIT_NS, 0); rx = 1; #(BIT_NS * 2);
        if (framing != 1 || received != saved) $fatal(1, "bad stop not rejected");
        rx = 0; #(BIT_NS * 30); rx = 1; #(BIT_NS * 2);
        if (breaks != 1 || framing != 2 || received != saved) $fatal(1, "break event/recovery");
        send_rx(8'h5a, BIT_NS, 1); rx = 1;
        // Reset between start and stop discards an incomplete byte.
        rx = 0; #(BIT_NS * 3); rst_n = 0; rx = 1;
        #50; rst_n = 1; #(BIT_NS * 12);
        if (received != saved + 1) $fatal(1, "reset leaked partial RX");
        send_rx(8'ha5, BIT_NS, 1); rx = 1;
        for (i = 0; i < 256; i = i + 1) begin
            while (!tx_ready) @(negedge clk);
            tx_data = i[7:0]; tx_valid = 1;
            @(negedge clk); tx_valid = 0;
            repeat (4) @(negedge clk);
            // A pulse while busy must not queue a second byte.
            tx_data = ~i[7:0]; tx_valid = 1;
            @(negedge clk); tx_valid = 0;
        end
        while (!tx_ready) @(negedge clk);
        #(BIT_NS * 2);
        if (transmitted != 256 || done_count != 256) $fatal(1, "TX handshake/count");
        check_tx = 0;
        tx_data = 0; tx_valid = 1; @(negedge clk); tx_valid = 0;
        #(BIT_NS * 3); rst_n = 0; #1;
        if (tx_line !== 1 || tx_ready !== 1) $fatal(1, "reset TX idle");
        #49; rst_n = 1; #(BIT_NS * 12);
        $display("PASS tb_uart: all 256 bytes at nominal/+2%%/-2%%, phase, false start, stop, break, reset, TX busy");
        $finish;
    end
    initial begin #5000000; $fatal(1, "UART timeout"); end
endmodule
