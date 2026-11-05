`timescale 1ns/1ps
`default_nettype none
// Same black-box test for RTL and the actual Gowin post-route netlist.
// No SDF: this is mapped functional verification; route timing is separate STA.
module tb_nano9k_mapped;
    logic clk = 0, arst_n = 1, rx = 1, left_out = 0, right_out = 0;
    logic motion_permit_async = 0, recovery_req_async = 0;
    logic safety_ok_async = 1, gate_fault_n_async = 1;
    wire tx, drv_left_in1, drv_left_in2, drv_right_in1, drv_right_in2;
    wire fpga_permit, recovery_ack, gate_clear;
    logic [7:0] bytes [0:46];
    integer frames = 0;
    always #18.5185 clk = ~clk;
    aw_car_nano9k dut (.*);

    function automatic logic [15:0] crc_byte(input logic [15:0] crc,
                                            input logic [7:0] data);
        logic [15:0] work;
        begin
            work = crc ^ {data, 8'b0};
            for (int bit_number = 0; bit_number < 8; bit_number++)
                work = work[15] ? (work << 1) ^ 16'h1021 : work << 1;
            return work;
        end
    endfunction
    task automatic read_byte(output logic [7:0] value);
        @(negedge tx);
        repeat (117) @(negedge clk);
        if (tx !== 0) $fatal(1, "invalid UART start");
        for (int bit_number = 0; bit_number < 8; bit_number++) begin
            repeat (234) @(negedge clk);
            value[bit_number] = tx;
        end
        repeat (234) @(negedge clk);
        if (tx !== 1) $fatal(1, "invalid UART stop");
    endtask
    task automatic check_frame;
        logic [15:0] crc;
        begin
            if ({bytes[0],bytes[1],bytes[2],bytes[3],bytes[4]} !== 40'ha55a028022)
                $fatal(1, "v2 STATUS header mismatch");
            crc = 16'hffff;
            for (int i = 2; i < 45; i++) crc = crc_byte(crc, bytes[i]);
            if ({bytes[46],bytes[45]} !== crc) $fatal(1, "STATUS CRC mismatch");
            if ({bytes[14],bytes[13],bytes[12],bytes[11]} !== 32'd3 ||
                {bytes[18],bytes[17],bytes[16],bytes[15]} !== 32'd5)
                $fatal(1, "encoder cones lost or wrong: left=%0d right=%0d", bytes[11],bytes[15]);
            if ((bytes[28] & 8'h9f) !== 8'h1f) $fatal(1, "encoder validity/mode mismatch");
            if ({bytes[32],bytes[31],bytes[30],bytes[29]} !== 32'd32 ||
                {bytes[36],bytes[35],bytes[34],bytes[33]} !== 32'd32)
                $fatal(1, "encoder period bytes lost");
            if ({bytes[40],bytes[39],bytes[38],bytes[37]} == 0 ||
                {bytes[44],bytes[43],bytes[42],bytes[41]} == 0)
                $fatal(1, "encoder age bytes lost");
            if (bytes[25] !== 0) $fatal(1, "power-up must remain DISARMED");
            frames++;
        end
    endtask
    initial begin
        // Begin with reset HIGH: exercise configuration FF INIT + physical POR.
        repeat (1100) @(negedge clk);
        for (int i = 0; i < 5; i++) begin
            if (i < 3) left_out = 1;
            right_out = 1;
            repeat (16) @(negedge clk);
            left_out = 0; right_out = 0;
            repeat (16) @(negedge clk);
        end
        wait (frames == 2);
        #3 arst_n = 0;
        #100;
        if ({fpga_permit,recovery_ack,gate_clear,drv_left_in1,drv_left_in2,
             drv_right_in1,drv_right_in2} !== 0) $fatal(1, "reset boundary not OFF");
        repeat (20) @(negedge clk);
        arst_n = 1;
        repeat (1100) @(negedge clk);
        if (tx !== 1) $fatal(1, "UART must return idle after reset/POR");
        $display("PASS tb_nano9k_mapped: configuration INIT/POR, 2 real v2 STATUS CRC, encoder count3/5 period32 age, reset/OFF");
        $finish;
    end
    initial forever begin
        for (int i = 0; i < 47; i++) read_byte(bytes[i]);
        check_frame();
    end
    always @(negedge clk) if ($time > 100 &&
        {fpga_permit,drv_left_in1,drv_left_in2,drv_right_in1,drv_right_in2} !== 0)
        $fatal(1, "uncommanded output while logical permit LOW");
    initial begin #40000000; $fatal(1, "mapped test timeout"); end
endmodule
`default_nettype wire
