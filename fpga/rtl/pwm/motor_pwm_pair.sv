`timescale 1ns/1ps
`default_nettype none
module motor_pwm_pair #(
    parameter int PERIOD_CYCLES = 1350,
    parameter int DUTY_WIDTH = 16,
    parameter int ZERO_CYCLES = 27000,
    parameter int SETUP_CYCLES = 27
) (
    input  logic clk,
    input  logic rst_n,
    input  logic enable,
    input  logic command_valid,
    input  logic [DUTY_WIDTH-1:0] command_left,
    input  logic [DUTY_WIDTH-1:0] command_right,
    input  logic [1:0] command_direction,
    output logic pwm_left,
    output logic pwm_right,
    output logic [1:0] direction,
    output logic interlock_active,
    output logic command_rejected
);
    localparam int WAIT_MAX = ZERO_CYCLES > SETUP_CYCLES ? ZERO_CYCLES : SETUP_CYCLES;
    localparam int WAIT_WIDTH = (WAIT_MAX > 1) ? $clog2(WAIT_MAX) : 1;
    localparam int VALUE_WIDTH = (PERIOD_CYCLES > 1) ? $clog2(PERIOD_CYCLES + 1) : 1;
    typedef enum logic [1:0] {
        RUN = 2'd0, WAIT_ZERO = 2'd1, WAIT_SETUP = 2'd2, LOAD = 2'd3
    } state_t;
    state_t state;
    logic [WAIT_WIDTH-1:0] wait_count;
    logic [VALUE_WIDTH-1:0] pending_left, pending_right;
    logic [1:0] pending_direction;
    logic valid, same_direction, pwm_enable, pwm_command;
    logic [DUTY_WIDTH-1:0] pwm_left_command, pwm_right_command;
    logic unused_period, unused_rejected, unused_applied;
    logic [DUTY_WIDTH-1:0] unused_left, unused_right;
    assign valid = command_valid && command_left <= PERIOD_CYCLES && command_right <= PERIOD_CYCLES;
    assign same_direction = command_direction == direction;
    assign pwm_enable = enable && (state == RUN || state == LOAD);
    assign pwm_command = enable && ((state == RUN && valid && same_direction) ||
                                   (state == LOAD && (!valid || same_direction)));
    assign pwm_left_command = valid ? command_left : pending_left;
    assign pwm_right_command = valid ? command_right : pending_right;
    assign interlock_active = state == WAIT_ZERO || state == WAIT_SETUP;
    pwm_pair #(.PERIOD_CYCLES(PERIOD_CYCLES), .DUTY_WIDTH(DUTY_WIDTH)) pwm (
        .clk(clk), .rst_n(rst_n), .enable(pwm_enable), .command_valid(pwm_command),
        .command_left(pwm_left_command), .command_right(pwm_right_command),
        .pwm_left(pwm_left), .pwm_right(pwm_right), .period_start(unused_period),
        .command_rejected(unused_rejected), .command_applied(unused_applied),
        .active_left(unused_left), .active_right(unused_right));
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= RUN; wait_count <= 0; direction <= 0;
            pending_left <= 0; pending_right <= 0; pending_direction <= 0;
            command_rejected <= 0;
        end else begin
            command_rejected <= command_valid && (!enable || !valid);
            if (!enable) begin
                state <= RUN; wait_count <= 0; direction <= 0;
                pending_left <= 0; pending_right <= 0; pending_direction <= 0;
            end else if (valid && (state == WAIT_ZERO || state == WAIT_SETUP || !same_direction)) begin
                // A newer command replaces the whole pending pair and restarts the zero interval.
                pending_left <= VALUE_WIDTH'(command_left); pending_right <= VALUE_WIDTH'(command_right);
                pending_direction <= command_direction;
                state <= WAIT_ZERO; wait_count <= ZERO_CYCLES - 1;
            end else begin
                case (state)
                    WAIT_ZERO: if (wait_count == 0) begin
                        direction <= pending_direction;
                        state <= WAIT_SETUP; wait_count <= SETUP_CYCLES - 1;
                    end else wait_count <= wait_count - 1'b1;
                    WAIT_SETUP: if (wait_count == 0) state <= LOAD;
                        else wait_count <= wait_count - 1'b1;
                    LOAD: state <= RUN;
                    default: state <= RUN;
                endcase
            end
        end
    end
endmodule
`default_nettype wire
