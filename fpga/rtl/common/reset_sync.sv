`timescale 1ns/1ps
`default_nettype none
module reset_sync (
    input  logic clk,
    input  logic arst_n,
    output logic rst_n
);
    (* ASYNC_REG = "TRUE" *) logic [1:0] release_ff;
    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n)
            release_ff <= 2'b00;
        else
            release_ff <= {release_ff[0], 1'b1};
    end
    assign rst_n = release_ff[1];
endmodule
`default_nettype wire
