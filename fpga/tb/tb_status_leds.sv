`timescale 1ns/1ps
module led_case #(parameter int HALF = 7)(output logic done = 0);
    logic clk = 0, running = 1;
    always #18.5185 if (running) clk = !clk;
    logic rst_n = 0;
    logic [7:0] safety_state = 0;
    logic [15:0] fault = 0;
    wire [5:0] leds_n;
    status_leds #(.BLINK_HALF_CYCLES(HALF)) dut(.*);
    task automatic tick;
        @(posedge clk); #1;
    endtask
    task automatic expect_led(input logic [5:0] expected);
        #1; if (leds_n !== expected) $fatal(1,"LED HALF=%0d state=%0d fault=%04x got=%06b expected=%06b",
            HALF,safety_state,fault,leds_n,expected);
    endtask
    initial begin
        #1; rst_n=1; #1; rst_n=0; expect_led(6'b111111);
        @(negedge clk); rst_n=1;
        expect_led(6'b111110);
        repeat (3) begin
            for (int i=1;i<=HALF;i++) begin
                tick(); expect_led(i==HALF ? 6'b111111 : 6'b111110);
            end
            for (int i=1;i<=HALF;i++) begin
                tick(); expect_led(i==HALF ? 6'b111110 : 6'b111111);
            end
        end
        // Exhaust every state encoding and individual fault bit. Warning bits
        // 8,9,10,12,13,14 do not override a healthy connected indication.
        for (int s=0;s<256;s++) begin
            safety_state=8'(s); fault=0; #1;
            if(s>=1 && s<=3) expect_led(6'b111110);
            else if(s>=4) expect_led(6'b000000);
            for (int b=0;b<16;b++) begin
                fault=16'(1<<b); #1;
                if(s>=4 || b<8 || b==11 || b==15) expect_led(6'b000000);
                else if(s>=1 && s<=3) expect_led(6'b111110);
            end
        end
        safety_state=3; fault=16'h77ff; expect_led(6'b000000);
        fault=0; expect_led(6'b111110); tick();
        safety_state=0; expect_led(6'b111110);
        // Reset remains effective without clock; LEDs cannot detect loss of
        // their own clock, so do not claim the stopped image is live health.
        @(negedge clk); running=0; rst_n=0; expect_led(6'b111111);
        #200; rst_n=1; expect_led(6'b111110);
        #200; expect_led(6'b111110);
        done=1;
    end
endmodule
module tb_status_leds;
    wire [2:0] done;
    led_case #(.HALF(1)) a(done[0]);
    led_case #(.HALF(7)) b(done[1]);
    led_case #(.HALF(16)) c(done[2]);
    initial begin
        wait(&done);
        $display("PASS tb_status_leds: active-low, exact blink1/7/16, 256 states x16 fault bits, priority, warning masks, reset/clock-stop");
        $finish;
    end
    initial begin #100000; $fatal(1,"LED unit timeout"); end
endmodule
