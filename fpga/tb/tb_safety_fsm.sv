`timescale 1ns/1ps
module tb_safety_fsm;
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0, inputs_valid = 0, motion_permit = 0, recovery_req = 0;
    logic safety_ok = 1, gate_ok = 1;
    logic hello_request = 0, arm_zero_request = 0, disable_request = 0, clear_fault_request = 0;
    logic command_valid = 0, pwm_rejected = 0, status_sent = 0;
    logic [31:0] event_session = 32'h12345678, status_session = 0;
    logic [15:0] event_sequence = 20;
    logic [7:0] status_state = 0;
    logic context_load, session_active, command_enable, motor_enable, motor_command;
    logic recovery_ack, gate_clear;
    logic [31:0] active_session;
    logic [15:0] sequence_base, fault;
    logic [7:0] safety_state;
    safety_fsm #(.WATCHDOG_CYCLES(12), .HANDSHAKE_CYCLES(80),
                 .CLEAR_CYCLES(8), .CLEAR_HOLD_CYCLES(3)) dut (.*);
    task automatic tick(input integer n);
        repeat(n) @(negedge clk);
    endtask
    task automatic boot;
        begin
            rst_n = 0; inputs_valid = 0; motion_permit = 0; recovery_req = 0;
            hello_request = 0; arm_zero_request = 0; clear_fault_request = 0;
            disable_request = 0; command_valid = 0; pwm_rejected = 0;
            status_sent = 0; safety_ok = 1; gate_ok = 1;
            tick(2); rst_n = 1; tick(2); inputs_valid = 1; tick(2);
        end
    endtask
    task automatic recover;
        begin
            motion_permit = 0; recovery_req = 0; tick(3);
            recovery_req = 1; tick(1);
            if (!recovery_ack || session_active) $fatal(1, "recovery acknowledge/flush");
            recovery_req = 0; tick(2);
            if (recovery_ack) $fatal(1, "recovery acknowledge stuck");
            hello_request = 1; tick(1); hello_request = 0; tick(2);
            if (!session_active || active_session != event_session || sequence_base != event_sequence)
                $fatal(1, "session installation");
        end
    endtask
    task automatic arm;
        begin
            arm_zero_request = 1; tick(1); arm_zero_request = 0;
            if (safety_state != 2 || motor_enable || recovery_ack) $fatal(1, "ARM must wait at zero");
        end
    endtask
    task automatic confirm;
        begin
            status_session = event_session; status_state = 2; status_sent = 1;
            tick(1); status_sent = 0;
            if (!recovery_ack || motor_enable) $fatal(1, "STATUS acknowledgment");
            motion_permit = 1; tick(1);
            if (safety_state != 3 || !motor_enable) $fatal(1, "Motion confirmation");
        end
    endtask
    task automatic clear;
        begin
            recover; clear_fault_request = 1; tick(1); clear_fault_request = 0;
            if (!gate_clear || motor_enable) $fatal(1, "clear must hold both permits low");
            gate_ok = 1; tick(3);
            if (safety_state != 0 || fault != 0 || session_active || gate_clear)
                $fatal(1, "clear must return disarmed without session");
        end
    endtask
    integer i;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_safety_fsm.vcd"); $dumpvars(0, tb_safety_fsm); end
        boot;
        hello_request = 1; arm_zero_request = 1; command_valid = 1; tick(3);
        if (session_active || motor_enable) $fatal(1, "UART alone armed");
        hello_request = 0; arm_zero_request = 0; command_valid = 0;
        // Startup HIGH must not be interpreted as a new recovery transaction.
        rst_n = 0; inputs_valid = 0; recovery_req = 1; motion_permit = 1; tick(2);
        rst_n = 1; tick(2); inputs_valid = 1; tick(4);
        if (recovery_ack || session_active || motor_enable) $fatal(1, "stale boot GPIO");
        recover; arm;
        status_sent = 1; status_session = event_session + 1; status_state = 2; tick(1);
        status_session = event_session; status_state = 3; tick(1); status_sent = 0;
        if (recovery_ack) $fatal(1, "wrong status confirmed ARM");
        motion_permit = 1; tick(1);
        if (safety_state != 4 || !(fault & 8)) $fatal(1, "early permit must fault");
        clear; recover; arm; confirm;
        command_valid = 1; tick(1); command_valid = 0;
        tick(11);
        if (!motor_enable || command_enable) $fatal(1, "watchdog expired early or deadline command enabled");
        command_valid = 1; tick(1); command_valid = 0;
        if (safety_state != 4 || motor_enable || session_active || !(fault & 1))
            $fatal(1, "timeout must beat same-edge CMD");
        clear; recover; arm;
        // No CMD after ARM: even HELLO/STATUS cannot refresh the initial lease.
        hello_request = 1; status_sent = 1; status_session = event_session; status_state = 2;
        tick(11);
        if (safety_state != 2) $fatal(1, "initial watchdog early");
        tick(1); hello_request = 0; status_sent = 0;
        if (safety_state != 4 || !(fault & 1)) $fatal(1, "initial watchdog not enforced");
        clear; recover; arm; confirm;
        for (i=0; i<20; i=i+1) begin
            tick(7); command_valid = 1; tick(1); command_valid = 0;
            if (!motor_enable) $fatal(1, "valid CMD didn't refresh");
        end
        tick(10); command_valid = 1; tick(1); command_valid = 0;
        tick(2);
        if (!motor_enable) $fatal(1, "CMD one tick before timeout must refresh");
        disable_request = 1; #1;
        if (motor_enable || motor_command) $fatal(1, "disable didn't mask immediately");
        tick(1); disable_request = 0; tick(1);
        if (safety_state != 0 || session_active) $fatal(1, "disable didn't invalidate");
        recover; arm; confirm; motion_permit = 0; tick(1);
        if (safety_state != 4 || !(fault & 4)) $fatal(1, "lost permit");
        clear; recover; arm; confirm; recovery_req = 1; tick(1);
        if (safety_state != 4 || !(fault & 8)) $fatal(1, "reconnect while armed");
        clear; recover; arm; confirm; safety_ok = 0; gate_ok = 0; tick(1);
        if (safety_state != 4 || !(fault & 2)) $fatal(1, "external fault");
        clear_fault_request = 1; tick(2); clear_fault_request = 0;
        if (gate_clear || motor_enable) $fatal(1, "CLEAR while physical fault active");
        motion_permit = 0; safety_ok = 1; clear; // latched gate can be cleared only now
        recover; arm; confirm; pwm_rejected = 1; tick(1); pwm_rejected = 0;
        if (safety_state != 4 || !(fault & 16)) $fatal(1, "internal PWM fault");
        motion_permit = 0; gate_ok = 0; tick(2); recover;
        clear_fault_request = 1; tick(1); clear_fault_request = 0; tick(8);
        if (safety_state != 4 || !(fault & 32) || gate_clear) $fatal(1, "gate clear timeout");
        boot; recover; tick(80);
        if (safety_state != 4 || !(fault & 64)) $fatal(1, "handshake timeout");
        // Reset at each protocol stage always erases authority.
        for (i=0; i<6; i=i+1) begin
            boot;
            if (i>0) recover;
            if (i>1) arm;
            if (i>2) confirm;
            if (i>3) begin safety_ok=0; tick(1); motion_permit=0; safety_ok=1; end
            if (i>4) begin recover; clear_fault_request=1; tick(1); clear_fault_request=0; end
            rst_n=0; #1;
            if (motor_enable || recovery_ack || gate_clear || session_active) $fatal(1, "reset authority");
        end
        boot; recovery_req=1; tick(1); rst_n=0; #1;
        if(recovery_ack || session_active) $fatal(1,"reset during GPIO acknowledge");
        boot; recovery_req=1; tick(1); recovery_req=0; tick(2); rst_n=0; #1;
        if(recovery_ack || session_active) $fatal(1,"reset during HELLO window");
        $display("PASS tb_safety_fsm: recovery, ARM, deadline priority, clear/fault/reset"); $finish;
    end
    initial begin #1000000; $fatal(1, "test timeout"); end
endmodule
