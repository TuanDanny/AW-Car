`timescale 1ns/1ps
`default_nettype none
module uart_rx #(
    parameter int CLK_HZ = 27000000,
    parameter int BAUD = 115200
) (
    input  logic clk,
    input  logic rst_n,
    input  logic rx,
    output logic [7:0] data,
    output logic valid,
    output logic framing_error,
    output logic break_error
);
    // Supported configuration: BIT_CYCLES >= 8. No generated fabric clock.
    localparam int BIT_CYCLES = (CLK_HZ + BAUD / 2) / BAUD;
    localparam int HALF_CYCLES = BIT_CYCLES / 2;
    localparam int CW = (BIT_CYCLES > 1) ? $clog2(BIT_CYCLES) : 1;
    localparam int BREAK_CYCLES = 11 * BIT_CYCLES;
    localparam int BW = $clog2(BREAK_CYCLES + 1);
    typedef enum logic [2:0] {IDLE, START, DATA, STOP, WAIT_HIGH} state_t;
    state_t state;
    (* ASYNC_REG = "TRUE" *) logic meta_ff, sync_ff;
    logic [CW-1:0] timer;
    logic [BW-1:0] low_count;
    logic [2:0] bit_index;
    logic [7:0] shift;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            meta_ff <= 1; sync_ff <= 1;
        end else begin
            meta_ff <= rx; sync_ff <= meta_ff;
        end
    end
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; timer <= 0; low_count <= 0; bit_index <= 0;
            shift <= 0; data <= 0; valid <= 0; framing_error <= 0; break_error <= 0;
        end else begin
            valid <= 0; framing_error <= 0; break_error <= 0;
            if (sync_ff) low_count <= 0;
            else if (low_count < BREAK_CYCLES) low_count <= low_count + 1'b1;
            if (!sync_ff && low_count == BREAK_CYCLES - 1) begin
                break_error <= 1;
                state <= WAIT_HIGH;
            end else begin
                case (state)
                    IDLE: if (!sync_ff) begin
                        state <= START; timer <= HALF_CYCLES - 1;
                    end
                    START: if (timer != 0) timer <= timer - 1'b1;
                        else if (sync_ff) state <= IDLE;
                        else begin
                            state <= DATA; timer <= BIT_CYCLES - 1; bit_index <= 0;
                        end
                    DATA: if (timer != 0) timer <= timer - 1'b1;
                        else begin
                            shift[bit_index] <= sync_ff;
                            timer <= BIT_CYCLES - 1;
                            if (bit_index == 7) state <= STOP;
                            else bit_index <= bit_index + 1'b1;
                        end
                    STOP: if (timer != 0) timer <= timer - 1'b1;
                        else if (sync_ff) begin
                            data <= shift; valid <= 1; state <= IDLE;
                        end else begin
                            framing_error <= 1; state <= WAIT_HIGH;
                        end
                    WAIT_HIGH: if (sync_ff) state <= IDLE;
                    default: state <= IDLE;
                endcase
            end
        end
    end
endmodule
`default_nettype wire
