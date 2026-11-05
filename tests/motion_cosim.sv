`timescale 1ns/1ps
// Interactive wire-level fixture. Production RTL is supplied via --fpga-root.
module tb_motion_cosim;
    logic clk = 0, arst_n = 0;
    integer flags = 4;
    wire logical_permit = flags[0];
    wire req = flags[1];
    wire safety = flags[2];
    wire driver_permit = flags[3];
    wire freeze_clock = flags[4];
    logic gate_ok = 1;
    wire tx, ack, fpga_permit, gate_clear;
    wire host_tx, host_ready;
    wire l1, l2, r1, r2;
    wire gate_enable = driver_permit && fpga_permit && gate_ok && safety;
    always #18.5185 begin
        if (!freeze_clock) clk = ~clk;
        else clk = 0;
    end
    always @(negedge safety or posedge gate_clear) begin
        if (!safety) gate_ok = 0;
        else if (!logical_permit && !fpga_permit) gate_ok = 1;
    end
    aw_car_top dut(
        .clk(clk), .arst_n(arst_n), .rx(host_tx), .tx(tx),
        .left_out(flags[5]), .right_out(flags[6]),
        .motion_permit_async(logical_permit), .recovery_req_async(req),
        .safety_ok_async(safety), .gate_fault_n_async(gate_ok),
        .drv_left_in1(l1), .drv_left_in2(l2), .drv_right_in1(r1), .drv_right_in2(r2),
        .fpga_permit(fpga_permit), .recovery_ack(ack), .gate_clear(gate_clear)
    );
    logic [7:0] outgoing[0:63];
    integer tx_count = 0, tx_index = 0;
    wire send_byte = tx_index < tx_count;
    wire [7:0] host_data = send_byte ? outgoing[tx_index] : 8'h00;
    uart_tx host_uart(.clk(clk), .rst_n(arst_n), .data(host_data),
                      .valid(send_byte), .ready(host_ready), .tx(host_tx), .done());
    always @(posedge clk) if (arst_n && send_byte && host_ready) tx_index <= tx_index + 1;
    wire [7:0] received;
    wire byte_valid;
    uart_rx receive_uart(.clk(clk), .rst_n(arst_n), .rx(tx), .data(received),
                         .valid(byte_valid), .framing_error(), .break_error());
    logic [7:0] incoming[0:63];
    integer rx_count = 0, left_ticks = 0, right_ticks = 0;
    always @(posedge clk) begin
        if (byte_valid) begin
            if (rx_count >= 64) $fatal(1, "cosim RX overflow");
            incoming[rx_count] = received; rx_count = rx_count + 1;
        end
        if (gate_enable && (l1 || l2)) left_ticks = left_ticks + 1;
        if (gate_enable && (r1 || r2)) right_ticks = right_ticks + 1;
        if (gate_enable && !logical_permit) $fatal(1, "gate without logical permit");
    end
    integer count, result, i;
    reg [511:0] data;
    initial begin
        #200 arst_n = 1;
        forever begin
            result = $fscanf(32'h80000000, "%d %d %h", flags, count, data);
            if (result != 3) $finish;
            if (count < 0 || count > 64) $fatal(1, "invalid input length");
            if (count != 0) begin
                if (tx_index < tx_count || !host_ready) $fatal(1, "host overwrote UART in flight");
                for (i = 0; i < count; i = i + 1) outgoing[i] = data[i * 8 +: 8];
                tx_index = 0; tx_count = count;
            end
            #1000000;
            $write("@IO %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d ",
                   $time / 1000, ack, fpga_permit, gate_ok,
                   dut.core.safety_state, dut.core.fault,
                   (tx_index >= tx_count && host_ready),
                   left_ticks, right_ticks, gate_enable, rx_count);
            for (i = 0; i < rx_count; i = i + 1) $write("%02x", incoming[i]);
            $write("\n"); $fflush();
            rx_count = 0; left_ticks = 0; right_ticks = 0;
        end
    end
endmodule
