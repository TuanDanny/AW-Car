`timescale 1ns/1ps
`default_nettype none
module command_guard #(
    parameter int PERIOD_CYCLES = 1350,
    parameter bit ALLOW_REVERSE = 0
) (
    input  logic clk,
    input  logic rst_n,
    input  logic context_load,
    input  logic session_active,
    input  logic [31:0] active_session,
    input  logic [15:0] sequence_base,
    input  logic command_enable,
    input  logic frame_valid,
    input  logic [7:0] frame_type,
    input  logic [31:0] frame_session,
    input  logic [15:0] frame_sequence,
    input  logic [47:0] frame_payload,
    output logic hello_request,
    output logic arm_zero_request,
    output logic disable_request,
    output logic clear_fault_request,
    output logic command_valid,
    output logic rejected,
    output logic [31:0] event_session,
    output logic [15:0] event_sequence,
    output logic [15:0] command_left,
    output logic [15:0] command_right,
    output logic [1:0] command_direction
);
    logic [15:0] last_sequence, delta;
    logic correct_session, fresh, payload_ok;
    assign delta = frame_sequence - last_sequence;
    assign correct_session = session_active && active_session != 0 && frame_session == active_session;
    assign fresh = delta != 0 && !delta[15];
    assign payload_ok = frame_payload[7:0] == 0 && frame_payload[15:10] == 0 &&
        (ALLOW_REVERSE || frame_payload[9:8] == 0) &&
        frame_payload[31:16] <= PERIOD_CYCLES && frame_payload[47:32] <= PERIOD_CYCLES;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            last_sequence <= 0; hello_request <= 0; arm_zero_request <= 0;
            disable_request <= 0; clear_fault_request <= 0; command_valid <= 0;
            rejected <= 0; event_session <= 0; event_sequence <= 0;
            command_left <= 0; command_right <= 0; command_direction <= 0;
        end else begin
            hello_request <= 0; arm_zero_request <= 0; disable_request <= 0;
            clear_fault_request <= 0; command_valid <= 0; rejected <= 0;
            if (context_load) begin
                last_sequence <= sequence_base;
                command_left <= 0; command_right <= 0; command_direction <= 0;
            end else if (frame_valid) begin
                event_session <= frame_session; event_sequence <= frame_sequence;
                if (frame_type == 4) disable_request <= 1;
                else if (frame_type == 1 && frame_session != 0) hello_request <= 1;
                else if (correct_session && fresh &&
                         (frame_type == 2 || frame_type == 5 ||
                          (frame_type == 3 && command_enable && payload_ok))) begin
                    last_sequence <= frame_sequence;
                    case (frame_type)
                        2: arm_zero_request <= 1;
                        5: clear_fault_request <= 1;
                        3: begin
                            command_valid <= 1;
                            command_left <= frame_payload[31:16];
                            command_right <= frame_payload[47:32];
                            command_direction <= frame_payload[9:8];
                        end
                        default: begin end
                    endcase
                end else rejected <= 1;
            end
        end
    end
endmodule
`default_nettype wire
