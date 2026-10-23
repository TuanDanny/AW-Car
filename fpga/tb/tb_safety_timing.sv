`timescale 1ns/1ps
module tb_safety_timing;
    logic clk=0;
    always #18.519 clk=!clk;
    logic rst_n=0, recovery_req=0, hello_request=0, arm_zero_request=0;
    logic command_valid=0;
    logic [7:0] safety_state;
    logic [15:0] fault;
    logic motor_enable, command_enable;
    // Real default watchdog at 27 MHz; keep ARM_PENDING at zero throughout.
    safety_fsm dut (.clk(clk), .rst_n(rst_n), .inputs_valid(1'b1),
        .motion_permit(1'b0), .recovery_req(recovery_req), .safety_ok(1'b1), .gate_ok(1'b1),
        .hello_request(hello_request), .arm_zero_request(arm_zero_request), .disable_request(1'b0),
        .clear_fault_request(1'b0), .command_valid(command_valid), .pwm_rejected(1'b0),
        .event_session(32'd123), .event_sequence(16'd1), .status_sent(1'b0),
        .status_session(32'd0), .status_state(8'd0), .safety_state(safety_state), .fault(fault),
        .motor_enable(motor_enable), .command_enable(command_enable), .context_load(),
        .session_active(), .active_session(), .sequence_base(), .motor_command(), .recovery_ack(), .gate_clear());
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        repeat(3) @(negedge clk); recovery_req=1;
        @(negedge clk); recovery_req=0;
        repeat(2) @(negedge clk); hello_request=1;
        @(negedge clk); hello_request=0;
        repeat(2) @(negedge clk); arm_zero_request=1;
        @(negedge clk); arm_zero_request=0;
        repeat(1323000) @(negedge clk); //49 ms
        if (safety_state!=2 || motor_enable) $fatal(1, "49 ms ARM zero/lease");
        repeat(26999) @(negedge clk);
        if (safety_state!=2) $fatal(1, "watchdog one cycle early");
        command_valid=1; @(negedge clk); command_valid=0;
        if (safety_state!=4 || fault!=1 || motor_enable) $fatal(1, "50 ms exact timeout");
        repeat(27000) @(negedge clk);
        if (safety_state!=4 || motor_enable) $fatal(1, "51 ms auto restart");
        $display("PASS tb_safety_timing: default 27MHz, 49/50/51 ms, exact 1350000 ticks"); $finish;
    end
    initial begin #60000000; $fatal(1, "timing timeout"); end
endmodule
