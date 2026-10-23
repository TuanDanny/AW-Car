`timescale 1ns/1ps
`default_nettype none
module motor_pwm_pair #(
    parameter integer PERIOD_CYCLES = 1350,
    parameter integer DUTY_WIDTH = 16,
    parameter integer ZERO_CYCLES = 27000,
    parameter integer SETUP_CYCLES = 27
) (
    input  wire clk,
    input  wire rst_n,
    input  wire enable,
    input  wire command_valid,
    input  wire [DUTY_WIDTH-1:0] command_left,
    input  wire [DUTY_WIDTH-1:0] command_right,
    input  wire [1:0] command_direction,
    output wire pwm_left,
    output wire pwm_right,
    output reg [1:0] direction,
    output wire interlock_active,
    output reg command_rejected
);
    function integer bits_for;
        input integer value;
        integer v;
        begin
            v = value - 1; bits_for = 0;
            while (v > 0) begin bits_for = bits_for + 1; v = v >> 1; end
            if (bits_for == 0) bits_for = 1;
        end
    endfunction
    localparam integer WAIT_MAX = ZERO_CYCLES > SETUP_CYCLES ? ZERO_CYCLES : SETUP_CYCLES;
    localparam integer WAIT_WIDTH = bits_for(WAIT_MAX);
    localparam [1:0] RUN = 0, WAIT_ZERO = 1, WAIT_SETUP = 2, LOAD = 3;
    reg [1:0] state;
    reg [WAIT_WIDTH-1:0] wait_count;
    reg [DUTY_WIDTH-1:0] pending_left, pending_right;
    reg [1:0] pending_direction;
    wire valid = command_valid && command_left <= PERIOD_CYCLES && command_right <= PERIOD_CYCLES;
    wire same_direction = command_direction == direction;
    wire pwm_enable = enable && (state == RUN || state == LOAD);
    wire pwm_command = enable && ((state == RUN && valid && same_direction) ||
                                 (state == LOAD && (!valid || same_direction)));
    wire [DUTY_WIDTH-1:0] pwm_left_command = valid ? command_left : pending_left;
    wire [DUTY_WIDTH-1:0] pwm_right_command = valid ? command_right : pending_right;
    wire unused_period, unused_rejected, unused_applied;
    wire [DUTY_WIDTH-1:0] unused_left, unused_right;
    assign interlock_active = state == WAIT_ZERO || state == WAIT_SETUP;
    pwm_pair #(.PERIOD_CYCLES(PERIOD_CYCLES), .DUTY_WIDTH(DUTY_WIDTH)) pwm (
        .clk(clk), .rst_n(rst_n), .enable(pwm_enable), .command_valid(pwm_command),
        .command_left(pwm_left_command), .command_right(pwm_right_command),
        .pwm_left(pwm_left), .pwm_right(pwm_right), .period_start(unused_period),
        .command_rejected(unused_rejected), .command_applied(unused_applied),
        .active_left(unused_left), .active_right(unused_right));
    always @(posedge clk or negedge rst_n) begin
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
                pending_left <= command_left; pending_right <= command_right;
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
