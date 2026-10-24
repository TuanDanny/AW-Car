`timescale 1ns/1ps
`default_nettype none
module safety_fsm #(
    parameter int WATCHDOG_CYCLES = 1350000,
    parameter int HANDSHAKE_CYCLES = 6750000,
    parameter int CLEAR_CYCLES = 135000,
    parameter int CLEAR_HOLD_CYCLES = 2700
) (
    input logic clk, rst_n,
    input logic inputs_valid, motion_permit, recovery_req, safety_ok, gate_ok,
    input logic hello_request, arm_zero_request, disable_request, clear_fault_request,
    input logic command_valid, pwm_rejected,
    input logic [31:0] event_session,
    input logic [15:0] event_sequence,
    input logic status_sent,
    input logic [31:0] status_session,
    input logic [7:0] status_state,
    output logic context_load, session_active,
    output logic [31:0] active_session,
    output logic [15:0] sequence_base,
    output logic command_enable, motor_enable, motor_command,
    output logic recovery_ack, gate_clear,
    output logic [7:0] safety_state,
    output logic [15:0] fault
);
    localparam int WW = WATCHDOG_CYCLES > 1 ? $clog2(WATCHDOG_CYCLES) : 1;
    localparam int HW = HANDSHAKE_CYCLES > 1 ? $clog2(HANDSHAKE_CYCLES) : 1;
    localparam int CW = CLEAR_CYCLES > 1 ? $clog2(CLEAR_CYCLES) : 1;
    localparam int MW = CLEAR_HOLD_CYCLES > 1 ? $clog2(CLEAR_HOLD_CYCLES) : 1;
    typedef enum logic [2:0] {DISARMED, HANDSHAKE, ARM_PENDING, ARMED, FAULT, CLEAR_WAIT} state_t;
    typedef enum logic [2:0] {WAIT_LOW, WAIT_HIGH, WAIT_RELEASE, READY, USED} recovery_t;
    state_t state;
    recovery_t recovery;
    logic [WW-1:0] watchdog_count;
    logic [HW-1:0] handshake_count;
    logic [CW-1:0] clear_count;
    logic [MW-1:0] hold_count;
    logic arm_confirmed, prev_safety, prev_gate;
    logic watchdog_due, handshake_due, recovery_start, external_fault;
    assign safety_state = {5'd0, state};
    assign watchdog_due = (state == ARM_PENDING || state == ARMED) && watchdog_count == 0;
    assign handshake_due = (state == HANDSHAKE || recovery == WAIT_RELEASE || recovery == READY)
                           && handshake_count == 0;
    assign recovery_start = recovery == WAIT_HIGH && recovery_req && !motion_permit;
    assign external_fault = (!safety_ok && (state != FAULT || prev_safety)) ||
        (!gate_ok && ((state != FAULT && state != CLEAR_WAIT) || prev_gate));
    assign motor_enable = inputs_valid && state == ARMED && motion_permit && safety_ok && gate_ok
                          && !recovery_req && !disable_request && !context_load && !pwm_rejected;
    // Count zero means expiration at the NEXT edge; don't mask motor_enable
    // a clock early, but prevent any command at that expiration edge.
    assign command_enable = motor_enable && !watchdog_due;
    assign motor_command = command_valid && command_enable;
    assign recovery_ack = inputs_valid && ((recovery == WAIT_RELEASE) ||
                          (arm_confirmed && (state == ARM_PENDING || state == ARMED)));
    assign gate_clear = inputs_valid && state == CLEAR_WAIT && safety_ok &&
                        !motion_permit && !recovery_req;
    task automatic invalidate;
        begin
            session_active <= 0; active_session <= 0; sequence_base <= 0;
            context_load <= 1; arm_confirmed <= 0;
        end
    endtask
    task automatic trip(input logic [15:0] cause);
        begin
            state <= FAULT; fault <= fault | cause;
            recovery <= WAIT_LOW; invalidate;
        end
    endtask
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= DISARMED; recovery <= WAIT_LOW; fault <= 0;
            context_load <= 0; session_active <= 0; active_session <= 0; sequence_base <= 0;
            watchdog_count <= 0; handshake_count <= 0; clear_count <= 0; hold_count <= 0;
            arm_confirmed <= 0; prev_safety <= 0; prev_gate <= 0;
        end else begin
            context_load <= 0;
            if (inputs_valid) begin
                prev_safety <= safety_ok; prev_gate <= gate_ok;
                if (state == ARM_PENDING || state == ARMED)
                    if (!watchdog_due) watchdog_count <= watchdog_count - 1'b1;
                if (state == HANDSHAKE || recovery == WAIT_RELEASE || recovery == READY)
                    if (!handshake_due) handshake_count <= handshake_count - 1'b1;
                if (recovery == WAIT_LOW && !motion_permit && !recovery_req) recovery <= WAIT_HIGH;
                if (recovery == WAIT_RELEASE && !recovery_req && !motion_permit) recovery <= READY;

                // Reductions of authority always precede recovery or commands.
                if (external_fault) trip(16'h0002);
                else if (disable_request) begin
                    invalidate; recovery <= WAIT_LOW;
                    if (fault != 0) state <= FAULT;
                    else state <= DISARMED;
                end else if (watchdog_due) trip(16'h0001);
                else if (pwm_rejected) trip(16'h0010);
                else if (state == ARMED && !motion_permit) trip(16'h0004);
                else if ((state == ARMED || state == ARM_PENDING) && recovery_req) trip(16'h0008);
                else if (handshake_due) trip(16'h0040);
                else if (recovery_start) begin
                    invalidate; recovery <= WAIT_RELEASE;
                    handshake_count <= HANDSHAKE_CYCLES - 1;
                    if (fault != 0) state <= FAULT;
                    else state <= DISARMED;
                end else if (recovery == WAIT_RELEASE && motion_permit) trip(16'h0008);
                else if (hello_request && recovery == READY && !motion_permit && !recovery_req
                         && event_session != 0 && safety_ok) begin
                    active_session <= event_session; session_active <= 1;
                    sequence_base <= event_sequence; context_load <= 1;
                    recovery <= USED; arm_confirmed <= 0;
                    handshake_count <= HANDSHAKE_CYCLES - 1;
                    if (fault != 0) state <= FAULT;
                    else state <= HANDSHAKE;
                end else begin
                    case (state)
                        DISARMED: ;
                        HANDSHAKE: begin
                            if (motion_permit || recovery_req) trip(16'h0008);
                            else if (arm_zero_request && session_active && !context_load) begin
                                state <= ARM_PENDING; arm_confirmed <= 0;
                                watchdog_count <= WATCHDOG_CYCLES - 1;
                            end
                        end
                        ARM_PENDING: begin
                            if (motion_permit) begin
                                if (arm_confirmed) state <= ARMED;
                                else trip(16'h0008);
                            end else if (status_sent && status_session == active_session &&
                                         status_state == 2 && session_active) arm_confirmed <= 1;
                        end
                        ARMED: if (motor_command) watchdog_count <= WATCHDOG_CYCLES - 1;
                        FAULT: if (clear_fault_request && session_active && !context_load &&
                                   safety_ok && !motion_permit && !recovery_req) begin
                            state <= CLEAR_WAIT; clear_count <= CLEAR_CYCLES - 1;
                            hold_count <= CLEAR_HOLD_CYCLES - 1;
                        end
                        CLEAR_WAIT: begin
                            if (motion_permit || recovery_req) trip(16'h0008);
                            else if (clear_count == 0) trip(16'h0020);
                            else begin
                                clear_count <= clear_count - 1'b1;
                                if (hold_count != 0) hold_count <= hold_count - 1'b1;
                                else if (gate_ok) begin
                                    fault <= 0; state <= DISARMED; recovery <= WAIT_LOW; invalidate;
                                end
                            end
                        end
                        default: trip(16'h0080);
                    endcase
                end
            end
        end
    end
endmodule
`default_nettype wire
