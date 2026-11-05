`timescale 1ns/1ps
`default_nettype none
// TI DRV8833 Tables 1/2: drive/coast (fast decay), never request brake (11).
// direction must come from motor_pwm_pair's zero/setup sequence. This block
// has no clock/PWM generator; it does not replace the independent hardware gate.
module drv8833_adapter (
    input  wire logic rst_n,
    input  wire logic enable,
    input  wire logic pwm_left,
    input  wire logic pwm_right,
    input  wire logic [1:0] direction,
    output logic drv_left_in1,
    output logic drv_left_in2,
    output logic drv_right_in1,
    output logic drv_right_in2
);
    assign drv_left_in1  = rst_n && enable && pwm_left  && !direction[0];
    assign drv_left_in2  = rst_n && enable && pwm_left  &&  direction[0];
    assign drv_right_in1 = rst_n && enable && pwm_right && !direction[1];
    assign drv_right_in2 = rst_n && enable && pwm_right &&  direction[1];
endmodule
`default_nettype wire
