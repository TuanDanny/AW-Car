`timescale 1ns/1ps
`default_nettype none
// Oversampled mode-0 slave. Every register uses clk; SCLK is data, never a clock.
module spi32 (
    input wire logic clk, rst_n,
    input wire logic cs_n, sclk, mosi,
    input wire logic [7:0] status_flags,
    input wire logic [15:0] applied_seq,
    input wire logic [31:0] left_count, right_count,
    input wire logic [31:0] left_period, right_period, left_age, right_age,
    output logic miso,
    output logic command_valid,
    output logic [15:0] command_seq,
    output logic signed [15:0] command_left, command_right
);
    (* syn_keep = 1 *) logic cs_meta, cs_sync;
    (* syn_keep = 1 *) logic sclk_meta, sclk_sync;
    (* syn_keep = 1 *) logic mosi_meta, mosi_sync;
    logic cs_previous, sclk_previous, active;
    logic [8:0] bit_count;
    logic overflow, bad_frame;
    logic [7:0] rx_shift;
    logic [15:0] rx_crc, received_crc, rx_seq;
    logic signed [15:0] rx_left, rx_right;
    // Byte 0 occupies [239:232]. The frozen record shifts only on SCLK falls.
    logic [239:0] sr32;
    logic [15:0] tx_crc;
    wire logic cs_fall = cs_previous && !cs_sync;
    wire logic cs_rise = !cs_previous && cs_sync;
    wire logic sclk_rise = !sclk_previous && sclk_sync;
    wire logic sclk_fall = sclk_previous && !sclk_sync;
    wire logic [7:0] rx_byte = {rx_shift[6:0], mosi_sync};

    function automatic logic [15:0] crc_bit(input logic [15:0] crc, input logic bit_in);
        crc_bit = {crc[14:0], 1'b0} ^ ((crc[15] ^ bit_in) ? 16'h1021 : 16'h0000);
    endfunction

    function automatic logic [239:0] snapshot(
        input logic [7:0] flags,
        input logic [15:0] seq,
        input logic [31:0] lc, rc, lp, rp, la, ra
    );
        logic [239:0] value;
        value = '0;
        value[239 - 0*8 -: 8] = 8'h53;
        value[239 - 1*8 -: 8] = 8'h52;
        value[239 - 2*8 -: 8] = 8'h01;
        value[239 - 3*8 -: 8] = flags;
        value[239 - 4*8 -: 8] = seq[7:0];
        value[239 - 5*8 -: 8] = seq[15:8];
        for (int i = 0; i < 4; i = i + 1) begin
            value[239 - (6+i)*8 -: 8] = lc[i*8 +: 8];
            value[239 - (10+i)*8 -: 8] = rc[i*8 +: 8];
            value[239 - (14+i)*8 -: 8] = lp[i*8 +: 8];
            value[239 - (18+i)*8 -: 8] = rp[i*8 +: 8];
            value[239 - (22+i)*8 -: 8] = la[i*8 +: 8];
            value[239 - (26+i)*8 -: 8] = ra[i*8 +: 8];
        end
        snapshot = value;
    endfunction

    // CS setup/hold and intertransaction gap are >=2us (54 clk ticks).
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cs_meta <= 1'b1; cs_sync <= 1'b1; cs_previous <= 1'b1;
            sclk_meta <= 1'b0; sclk_sync <= 1'b0; sclk_previous <= 1'b0;
            mosi_meta <= 1'b0; mosi_sync <= 1'b0;
        end else begin
            cs_meta <= cs_n; cs_sync <= cs_meta; cs_previous <= cs_sync;
            sclk_meta <= sclk; sclk_sync <= sclk_meta; sclk_previous <= sclk_sync;
            mosi_meta <= mosi; mosi_sync <= mosi_meta;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; bit_count <= '0; overflow <= 1'b0; bad_frame <= 1'b0;
            rx_shift <= '0; rx_crc <= 16'hffff; received_crc <= '0;
            rx_seq <= '0; rx_left <= '0; rx_right <= '0;
            sr32 <= '0; tx_crc <= 16'hffff;
            command_valid <= 1'b0; command_seq <= '0;
            command_left <= '0; command_right <= '0;
        end else begin
            command_valid <= 1'b0;
            if (cs_fall) begin
                active <= 1'b1; bit_count <= '0; overflow <= 1'b0;
                bad_frame <= sclk_sync; // mode 0 must enter CS with SCLK low
                rx_shift <= '0; rx_crc <= 16'hffff; received_crc <= '0;
                rx_seq <= '0; rx_left <= '0; rx_right <= '0;
                sr32 <= snapshot(status_flags, applied_seq, left_count, right_count,
                                  left_period, right_period, left_age, right_age);
                tx_crc <= 16'hffff;
            end else if (cs_rise) begin
                active <= 1'b0;
                if (active && bit_count == 9'd256 && !overflow && !bad_frame &&
                    rx_crc == received_crc &&
                    rx_left >= -16'sd1350 && rx_left <= 16'sd1350 &&
                    rx_right >= -16'sd1350 && rx_right <= 16'sd1350) begin
                    command_seq <= rx_seq;
                    command_left <= rx_left;
                    command_right <= rx_right;
                    command_valid <= 1'b1;
                end
            end else if (active && !cs_sync) begin
                if (sclk_rise) begin
                    if (bit_count == 9'd256) overflow <= 1'b1;
                    else begin
                        bit_count <= bit_count + 1'b1;
                        rx_shift <= rx_byte;
                        if (bit_count < 9'd240) begin
                            rx_crc <= crc_bit(rx_crc, mosi_sync);
                            tx_crc <= crc_bit(tx_crc, sr32[239]);
                        end
                        if (bit_count[2:0] == 3'd7) begin
                            case (bit_count[7:3])
                                5'd0: if (rx_byte != 8'h53) bad_frame <= 1'b1;
                                5'd1: if (rx_byte != 8'h31) bad_frame <= 1'b1;
                                5'd2: if (rx_byte != 8'h01) bad_frame <= 1'b1;
                                5'd4: rx_seq[7:0] <= rx_byte;
                                5'd5: rx_seq[15:8] <= rx_byte;
                                5'd6: rx_left[7:0] <= rx_byte;
                                5'd7: rx_left[15:8] <= rx_byte;
                                5'd8: rx_right[7:0] <= rx_byte;
                                5'd9: rx_right[15:8] <= rx_byte;
                                5'd30: received_crc[7:0] <= rx_byte;
                                5'd31: received_crc[15:8] <= rx_byte;
                                default: if (rx_byte != 8'h00) bad_frame <= 1'b1;
                            endcase
                        end
                    end
                end
                if (sclk_fall) begin
                    if (bit_count == 9'd240)
                        sr32 <= {tx_crc[7:0], tx_crc[15:8], 224'b0};
                    else sr32 <= {sr32[238:0], 1'b0};
                end
            end
        end
    end
    assign miso = rst_n && !cs_n && active ? sr32[239] : 1'b0;
endmodule
