`timescale 1ns/1ps
`default_nettype none
module crc16_byte (
    input  logic [15:0] crc,
    input  logic [7:0] data,
    output logic [15:0] next_crc
);
    function automatic logic [15:0] update_crc(input logic [15:0] previous_crc,
                                               input logic [7:0] value);
        logic [15:0] work;
        integer i;
        begin
            work = previous_crc ^ {value, 8'h00};
            for (i = 0; i < 8; i = i + 1)
                if (work[15]) work = (work << 1) ^ 16'h1021;
                else work = work << 1;
            update_crc = work;
        end
    endfunction
    assign next_crc = update_crc(crc, data);
endmodule
`default_nettype wire
