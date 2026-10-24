`timescale 1ns/1ps
module safety_matrix_case #(parameter int W=8,H=16,C=8,M=3)(output logic finished=0);
    logic clk=0;
    always #5 clk=!clk;
    logic rst_n=0, inputs_valid=0, motion_permit=0, recovery_req=0, safety_ok=1, gate_ok=1;
    logic hello_request=0, arm_zero_request=0, disable_request=0, clear_fault_request=0;
    logic command_valid=0, pwm_rejected=0, status_sent=0;
    logic [31:0] event_session=32'h12345678, status_session=0;
    logic [15:0] event_sequence=16'hfffe;
    logic [7:0] status_state=0;
    logic context_load, session_active, command_enable, motor_enable, motor_command, recovery_ack, gate_clear;
    logic [31:0] active_session;
    logic [15:0] sequence_base, fault;
    logic [7:0] safety_state;
    safety_fsm #(.WATCHDOG_CYCLES(W),.HANDSHAKE_CYCLES(H),.CLEAR_CYCLES(C),.CLEAR_HOLD_CYCLES(M)) dut(.*);
    logic [5:0] states_seen=0;
    logic [7:0] faults_seen=0;
    always @(posedge clk) begin
        #1;
        if(rst_n) begin
            if(safety_state<6) states_seen[safety_state]=1;
            faults_seen=faults_seen|fault[7:0];
            if((^{motor_enable,command_enable,motor_command,recovery_ack,gate_clear,safety_state,fault})===1'bx)
                $fatal(1,"unknown safety outputs W/H/C/M=%0d/%0d/%0d/%0d",W,H,C,M);
            if(motor_enable && (safety_state!=3 || !session_active || !motion_permit || !safety_ok || !gate_ok))
                $fatal(1,"unsafe authority in matrix");
            if(gate_clear && (motor_enable || motion_permit || recovery_req || !safety_ok || safety_state!=5))
                $fatal(1,"invalid clear authority in matrix");
        end
    end
    task automatic tick(input integer n);
        repeat(n) @(negedge clk);
    endtask
    task automatic boot;
        begin
            rst_n=0; inputs_valid=0; motion_permit=0; recovery_req=0; safety_ok=1; gate_ok=1;
            hello_request=0; arm_zero_request=0; disable_request=0; clear_fault_request=0;
            command_valid=0; pwm_rejected=0; status_sent=0;
            tick(2); rst_n=1; tick(2); inputs_valid=1; tick(2);
        end
    endtask
    task automatic recover;
        begin
            motion_permit=0; recovery_req=0; tick(2);
            recovery_req=1; tick(1);
            if(!recovery_ack || session_active) $fatal(1,"matrix recovery ack");
            recovery_req=0; tick(1); hello_request=1; tick(1); hello_request=0; tick(1);
            if(!session_active || active_session!==event_session || sequence_base!==event_sequence)
                $fatal(1,"matrix recovery session");
        end
    endtask
    task automatic arm;
        begin
            recover; arm_zero_request=1; tick(1); arm_zero_request=0;
            if(safety_state!=2 || motor_enable) $fatal(1,"matrix ARM_PENDING");
            status_sent=1; status_session=event_session; status_state=2; tick(1); status_sent=0;
            if(!recovery_ack || motor_enable) $fatal(1,"matrix STATUS confirmation");
            motion_permit=1; tick(1);
            if(!motor_enable || safety_state!=3) $fatal(1,"matrix ARMED");
            command_valid=1; tick(1); command_valid=0;
        end
    endtask
    task automatic expect_fault(input logic [15:0] cause);
        begin
            if(safety_state!=4 || fault!==cause || session_active || motor_enable || motor_command)
                $fatal(1,"matrix fault expected=%h got=%h state=%0d W/H/C/M=%0d/%0d/%0d/%0d",
                       cause,fault,safety_state,W,H,C,M);
        end
    endtask
    integer event_no, k;
    logic [15:0] expected;
    initial begin
        // Competing events on the same edge, including invalidating a valid CMD.
        for(event_no=0;event_no<6;event_no=event_no+1) begin
            boot; arm; command_valid=1;
            case(event_no)
                0: begin disable_request=1; expected=0; end
                1: begin safety_ok=0; gate_ok=0; disable_request=1; expected=2; end
                2: begin pwm_rejected=1; expected=16; end
                3: begin motion_permit=0; expected=4; end
                4: begin recovery_req=1; expected=8; end
                5: begin pwm_rejected=1; motion_permit=0; recovery_req=1; expected=16; end
            endcase
            #1;
            if(motor_enable || motor_command) $fatal(1,"matrix event didn't mask permission");
            tick(1); command_valid=0;
            if(event_no==0) begin
                if(safety_state!=0 || fault || session_active) $fatal(1,"DISABLE priority");
            end else expect_fault(expected);
        end
        // Exact deadline, then the priority of DISABLE at that same deadline.
        boot; arm;
        tick(W-1);
        if(!motor_enable || command_enable) $fatal(1,"matrix watchdog early/missing command mask");
        command_valid=1; tick(1); command_valid=0; expect_fault(1);
        boot; arm; tick(W-1); command_valid=1; disable_request=1; tick(1);
        if(safety_state!=0 || fault || session_active) $fatal(1,"DISABLE must precede watchdog");
        // Fault causes accumulate and DISABLE never erases an existing fault.
        boot; arm; pwm_rejected=1; tick(1); pwm_rejected=0; expect_fault(16);
        safety_ok=0; disable_request=1; tick(1); expect_fault(18);
        safety_ok=1; tick(1); disable_request=0; expect_fault(18);
        // Status and permit on the same edge cannot combine into an ARM bypass.
        boot; recover; arm_zero_request=1; tick(1); arm_zero_request=0;
        status_sent=1; status_session=event_session; status_state=2; motion_permit=1; tick(1);
        expect_fault(8);
        // HELLO at the GPIO transaction deadline loses to timeout.
        boot; recovery_req=1; tick(1); recovery_req=0; tick(H-1);
        hello_request=1; tick(1); hello_request=0; expect_fault(64);
        // Holding recovery HIGH also has a deadline.
        boot; recovery_req=1; tick(1); tick(H); expect_fault(64);
        // Clear is accepted only after a fresh GPIO/session transaction.
        boot; arm; safety_ok=0; tick(1); safety_ok=1; motion_permit=0; recover;
        clear_fault_request=1; tick(1); clear_fault_request=0;
        if(safety_state!=5 || !gate_clear) $fatal(1,"matrix clear entry");
        for(k=1;k<=C;k=k+1) begin
            tick(1);
            if(M<C && k>=M) begin
                if(safety_state!=0 || fault || session_active || gate_clear)
                    $fatal(1,"clear did not finish at hold=%0d tick=%0d",M,k);
            end else if(k<C) begin
                if(safety_state!=5 || !gate_clear) $fatal(1,"clear completed early");
            end else expect_fault(34);
        end
        // A gate held low forces timeout even when the hold duration is valid.
        boot; arm; gate_ok=0; tick(1); motion_permit=0; recover;
        clear_fault_request=1; tick(1); clear_fault_request=0; tick(C); expect_fault(34);
        // A newly asserted physical fault aborts CLEAR on the next edge.
        boot; arm; safety_ok=0; tick(1); safety_ok=1; motion_permit=0; recover;
        clear_fault_request=1; tick(1); clear_fault_request=0; safety_ok=0; tick(1); expect_fault(2);
        // Explicit illegal-state injection exercises the fail-safe default.
        boot; $deposit(dut.state,3'b111); tick(1); expect_fault(128);
        #2;
        if(states_seen!==6'h3f || faults_seen!==8'hff)
            $fatal(1,"missing safety state/fault coverage %h/%h",states_seen,faults_seen);
        $display("COVER safety.W%0d.H%0d.C%0d.M%0d.states 6",W,H,C,M);
        $display("COVER safety.W%0d.H%0d.C%0d.M%0d.fault_bits 8",W,H,C,M);
        $display("COVER safety.W%0d.H%0d.C%0d.M%0d.collisions 9",W,H,C,M);
        finished=1;
    end
endmodule

module safety_minimum_case #(parameter bit SHORT_HANDSHAKE=0)(output logic finished=0);
    logic clk=0, rst_n=0, recovery_req=0, hello_request=0, arm_zero_request=0;
    always #5 clk=!clk;
    logic [7:0] state;
    logic [15:0] fault;
    logic permit;
    safety_fsm #(.WATCHDOG_CYCLES(1),.HANDSHAKE_CYCLES(SHORT_HANDSHAKE?1:8),
                 .CLEAR_CYCLES(1),.CLEAR_HOLD_CYCLES(1)) dut(
        .clk(clk),.rst_n(rst_n),.inputs_valid(1'b1),.motion_permit(1'b0),.recovery_req(recovery_req),
        .safety_ok(1'b1),.gate_ok(1'b1),.hello_request(hello_request),.arm_zero_request(arm_zero_request),
        .disable_request(1'b0),.clear_fault_request(1'b0),.command_valid(1'b1),.pwm_rejected(1'b0),
        .event_session(32'd1),.event_sequence(16'd1),.status_sent(1'b1),.status_session(32'd1),.status_state(8'd2),
        .safety_state(state),.fault(fault),.motor_enable(permit),.context_load(),.session_active(),
        .active_session(),.sequence_base(),.command_enable(),.motor_command(),.recovery_ack(),.gate_clear());
    initial begin
        repeat(2) @(negedge clk); rst_n=1;
        @(negedge clk); recovery_req=1;
        @(negedge clk); recovery_req=0;
        @(negedge clk); hello_request=1;
        @(negedge clk); hello_request=0;
        if(SHORT_HANDSHAKE) begin
            if(state!=4 || fault!=64 || permit) $fatal(1,"one-cycle handshake accepted late HELLO");
        end else begin
            @(negedge clk); arm_zero_request=1;
            @(negedge clk); arm_zero_request=0;
            if(state!=2 || permit) $fatal(1,"one-cycle watchdog ARM entry");
            @(negedge clk);
            if(state!=4 || fault!=1 || permit) $fatal(1,"one-cycle watchdog not expired");
        end
        $display("COVER safety.minimum.handshake%0d 1",SHORT_HANDSHAKE);
        finished=1;
    end
endmodule

module tb_safety_matrix;
    logic [6:0] finished;
    safety_matrix_case #(.W(8),.H(16),.C(8),.M(1)) c0(finished[0]);
    safety_matrix_case #(.W(32),.H(16),.C(8),.M(3)) c1(finished[1]);
    safety_matrix_case #(.W(8),.H(16),.C(32),.M(4)) c2(finished[2]);
    safety_matrix_case #(.W(8),.H(16),.C(5),.M(5)) c3(finished[3]);
    safety_matrix_case #(.W(8),.H(16),.C(5),.M(6)) c4(finished[4]);
    safety_minimum_case c5(finished[5]);
    safety_minimum_case #(.SHORT_HANDSHAKE(1)) c6(finished[6]);
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_safety_matrix.vcd"); $dumpvars(0,tb_safety_matrix); end
        wait(&finished);
        $display("PASS tb_safety_matrix: 7 timer configurations, 6 states/8 fault bits, collisions, exact clear/lease deadlines");
        $finish;
    end
    initial begin #1000000; $fatal(1,"safety matrix timeout"); end
endmodule
