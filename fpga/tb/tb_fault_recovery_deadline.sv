`timescale 1ns/1ps
module fault_recovery_deadline_case #(
    parameter int H=80, W=20, C=8, M=3
) (output logic finished=0);
    logic clk=0;
    always #18.519 clk=!clk;
    logic rst_n=0, inputs_valid=0, motion_permit=0, recovery_req=0, safety_ok=1, gate_ok=0;
    logic hello_request=0, arm_zero_request=0, disable_request=0, clear_fault_request=0;
    logic command_valid=0, pwm_rejected=0, status_sent=0;
    logic [31:0] event_session=32'hca110000, status_session=0;
    logic [15:0] event_sequence=1;
    logic [7:0] status_state=0, safety_state;
    logic context_load, session_active, command_enable, motor_enable, motor_command, recovery_ack, gate_clear;
    logic [31:0] active_session;
    logic [15:0] sequence_base, fault;
    safety_fsm #(.WATCHDOG_CYCLES(W), .HANDSHAKE_CYCLES(H),
        .CLEAR_CYCLES(C), .CLEAR_HOLD_CYCLES(M)) dut (.*);
    task automatic tick(input integer n);
        repeat(n) @(negedge clk);
    endtask
    task automatic boot_fault;
        begin
            rst_n=0; inputs_valid=0; motion_permit=0; recovery_req=0;
            safety_ok=1; gate_ok=0; hello_request=0; clear_fault_request=0;
            arm_zero_request=0; disable_request=0;
            tick(2); rst_n=1; inputs_valid=1; tick(3);
            if (safety_state!=4 || fault!=2 || session_active)
                $fatal(1,"failed to enter latched physical gate FAULT");
        end
    endtask
    task automatic recover_hello;
        begin
            recovery_req=0; tick(2);
            recovery_req=1; tick(1);
            if (!recovery_ack || session_active) $fatal(1,"fault recovery GPIO acknowledge");
            recovery_req=0; tick(1);
            event_session=event_session+1; hello_request=1; tick(1); hello_request=0;
            if (safety_state!=4 || !session_active || active_session!==event_session)
                $fatal(1,"HELLO did not open recovery session while retaining FAULT");
            // This edge is t0: the new HELLO has just installed its lease.
        end
    endtask
    task automatic finish_clear;
        begin
            gate_ok=1; tick(M+2);
            if (safety_state!=0 || fault!=0 || session_active || gate_clear || motor_enable)
                $fatal(1,"valid clear did not return DISARMED with session invalidated");
        end
    endtask
    always @(posedge clk) begin
        #1;
        if (rst_n && (motor_enable || command_enable || motor_command))
            $fatal(1,"recovery/clear granted motor authority without ARM");
        if (gate_clear && (safety_state!=5 || motion_permit || recovery_req || !safety_ok))
            $fatal(1,"invalid recovery gate-clear permission");
    end
    integer which, age, phase_before;
    initial begin
        // FAULT alone is not an open recovery session and must not accumulate
        // a handshake timeout while waiting indefinitely for the operator.
        if (H<1000) begin
            boot_fault; tick(2*H);
            if (fault!=2 || session_active) $fatal(1,"idle FAULT incorrectly timed out");
        end
        for (which=0;which<3;which=which+1) begin
            boot_fault; recover_hello;
            case(which)
                0: age=H-1;
                1: age=H;
                default: age=H+5;
            endcase
            tick(age-1);
            phase_before=dut.phase_count; // Diagnostic only; assertions use public outputs.
            clear_fault_request=1; tick(1); clear_fault_request=0;
            $display("RECOVERY H=%0d clear_age=%0d phase_before=%0d state=%0d session=%0b fault=%h gate_clear=%0b",
                     H,age,phase_before,safety_state,session_active,fault,gate_clear);
            if (which==0) begin
                if (safety_state!=5 || !gate_clear || !session_active || fault!=2)
                    $fatal(1,"CLEAR_FAULT rejected one tick before recovery deadline");
                finish_clear;
            end else begin
                if (safety_state!=4 || session_active || active_session!=0 ||
                    sequence_base!=0 || fault!=16'h0042 || gate_clear)
                    $fatal(1,"expired recovery accepted CLEAR_FAULT at/after deadline H=%0d age=%0d",H,age);
                // UART-only retry cannot revive the expired recovery context.
                hello_request=1; clear_fault_request=1; arm_zero_request=1; tick(2);
                hello_request=0; clear_fault_request=0; arm_zero_request=0;
                if (session_active || gate_clear || safety_state!=4)
                    $fatal(1,"expired session reopened without a new GPIO recovery");
            end
        end
        // Expiry is recoverable, but requires another complete GPIO+HELLO exchange.
        recover_hello; tick(1); clear_fault_request=1; tick(1); clear_fault_request=0;
        if (!gate_clear || safety_state!=5) $fatal(1,"new recovery after timeout failed");
        finish_clear;
        $display("COVER safety.fault_recovery.H%0d.deadline_positions 3",H);
        $display("COVER safety.fault_recovery.H%0d.new_gpio_after_expiry 1",H);
        finished=1;
    end
endmodule

module tb_fault_recovery_deadline;
    logic [2:0] finished;
    fault_recovery_deadline_case #(.H(32)) short_window (.finished(finished[0]));
    fault_recovery_deadline_case small_window (.finished(finished[1]));
    fault_recovery_deadline_case #(.H(6750000), .W(1350000), .C(135000), .M(2700))
        nominal_250ms (.finished(finished[2]));
    initial begin
        wait (&finished);
        $display("PASS tb_fault_recovery_deadline: FAULT HELLO lease before/at/after expiry, idle fault and new recovery");
        $finish;
    end
    initial begin #1000000000; $fatal(1,"timeout tb_fault_recovery_deadline"); end
endmodule
