`timescale 1ns/1ps
module tb_frame_rx;
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0, flush = 0, byte_valid = 0, byte_error = 0;
    logic [7:0] byte_data = 0;
    logic frame_valid, frame_error;
    logic [7:0] kind;
    logic [31:0] session;
    logic [15:0] seq;
    logic [47:0] payload;
    frame_rx #(.INTERBYTE_CYCLES(32), .FRAME_CYCLES(128)) dut (
        .clk(clk), .rst_n(rst_n), .flush(flush), .byte_data(byte_data),
        .byte_valid(byte_valid), .byte_error(byte_error), .frame_valid(frame_valid),
        .frame_error(frame_error), .frame_type(kind), .frame_session(session),
        .frame_sequence(seq), .frame_payload(payload));
    logic [255:0] vectors [0:6];
    logic [255:0] expected;
    logic allow_frame = 0;
    integer frames = 0, errors = 0;
    integer i, j, seed, mode, saved;
    always @(posedge clk) begin
        #1;
        if (frame_valid) begin
            if (!allow_frame || kind !== expected[3*8 +: 8] || session !== expected[5*8 +: 32] ||
                seq !== expected[9*8 +: 16] ||
                (kind == 3 && payload !== expected[11*8 +: 48]) || (kind != 3 && payload !== 0))
                $fatal(1, "frame committed early/corrupt");
            frames = frames + 1;
        end
        if (frame_error) errors = errors + 1;
    end
    task automatic put(input logic [7:0] value, input integer gap);
        begin
            @(negedge clk); byte_data = value; byte_valid = 1;
            @(negedge clk); byte_valid = 0;
            repeat (gap) @(negedge clk);
        end
    endtask
    task automatic send(input logic [255:0] frame, input logic good);
        integer i, before_count, length;
        begin
            expected = frame; allow_frame = good; before_count = frames;
            length = frame[255:248];
            for (i = 0; i < length; i = i + 1) put(frame[i*8 +: 8], 0);
            repeat (2) @(negedge clk);
            if (frames != before_count + good)
                $fatal(1, "frame count mismatch seed=%0d case=%0d", seed, j);
            allow_frame = 0;
        end
    endtask
    logic [15:0] crc = 16'hffff, next_crc;
    logic [7:0] crc_data;
    crc16_byte crc_dut (.crc(crc), .data(crc_data), .next_crc(next_crc));
    logic [71:0] check_string = 72'h313233343536373839;
    logic [255:0] corrupt;
    logic [31:0] rng;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_frame_rx.vcd"); $dumpvars(0, tb_frame_rx); end
        $readmemh("../../firmware/shared/fpga-vectors.hex", vectors);
        for (i = 8; i >= 0; i = i - 1) begin crc_data = check_string[i*8 +: 8]; #1; crc = next_crc; #1; end
        if (crc !== 16'h29b1) $fatal(1, "CRC-16 check value");
        repeat (3) @(negedge clk); rst_n = 1;
        for (i = 0; i < 6; i = i + 1) send(vectors[i], 1);
        send(vectors[6], 0); // STATUS is not an inbound command type.
        // Every byte protected by the CRC, plus each CRC byte, gets corrupted.
        for (i = 2; i < 19; i = i + 1) begin
            corrupt = vectors[2]; corrupt[i*8 +: 8] = corrupt[i*8 +: 8] ^ 8'h01;
            send(corrupt, 0);
            repeat (34) @(negedge clk);
            send(vectors[2], 1);
        end
        // Overlapping preamble and immediate resync after a bad version A5.
        put(8'ha5, 0); send(vectors[2], 1);
        put(8'ha5, 0); put(8'h5a, 0); put(8'ha5, 0);
        expected = vectors[2]; allow_frame = 1; saved = frames;
        for (i = 1; i < 19; i = i + 1) put(vectors[2][i*8 +: 8], 0);
        repeat (2) @(negedge clk); allow_frame = 0;
        if (frames != saved + 1) $fatal(1, "overlap resync");
        // Interbyte and whole-frame limits, and a byte exactly at deadline.
        put(8'ha5, 0); repeat (32) @(negedge clk); send(vectors[2], 1);
        // A 31-clock byte interval is accepted; exactly 32 clocks expires.
        expected = vectors[2]; allow_frame = 1; saved = frames;
        put(8'ha5, 0); repeat (30) @(negedge clk);
        byte_data = 8'h5a; byte_valid = 1;
        @(negedge clk); byte_valid = 0;
        for (i = 2; i < 19; i = i + 1) put(vectors[2][i*8 +: 8], 0);
        repeat (2) @(negedge clk); allow_frame = 0;
        if (frames != saved + 1) $fatal(1, "byte before deadline lost");
        saved = errors;
        put(8'ha5, 0); repeat (31) @(negedge clk);
        byte_data = 8'h5a; byte_valid = 1;
        @(negedge clk); byte_valid = 0;
        if (errors != saved + 1) $fatal(1, "byte at deadline won over timeout");
        send(vectors[2], 1);
        // Keep every gap below 32; place final CRC at frame age127/128.
        expected = vectors[2]; allow_frame = 1; saved = frames;
        for (i = 0; i < 19; i = i + 1)
            put(vectors[2][i*8 +: 8], (i < 3) ? 23 : (i == 3) ? 22 : 0);
        repeat (2) @(negedge clk); allow_frame = 0;
        if (frames != saved + 1) $fatal(1, "frame before deadline lost");
        saved = errors;
        for (i = 0; i < 19; i = i + 1) put(vectors[2][i*8 +: 8], (i < 4) ? 23 : 0);
        repeat (2) @(negedge clk);
        if (errors != saved + 1) $fatal(1, "CRC at whole-frame deadline won over timeout");
        send(vectors[2], 1);
        saved = errors;
        for (i = 0; i < 10; i = i + 1) put(vectors[2][i*8 +: 8], 15);
        repeat (34) @(negedge clk);
        if (errors <= saved) $fatal(1, "whole-frame timeout missing");
        send(vectors[2], 1);
        put(8'ha5, 0); put(8'h5a, 0); put(1, 0);
        byte_error = 1; @(negedge clk); byte_error = 0;
        send(vectors[2], 1);
        put(8'ha5, 0); put(8'h5a, 0);
        flush = 1; @(negedge clk); flush = 0; send(vectors[2], 1);
        put(8'ha5, 0); put(8'h5a, 0); rst_n = 0;
        @(negedge clk); rst_n = 1; send(vectors[2], 1);
        // Reset/flush before each remaining byte discards partial commands.
        for (j = 1; j < 19; j = j + 1) begin
            for (i = 0; i < j; i = i + 1) put(vectors[2][i*8 +: 8], 0);
            rst_n = 0; @(negedge clk); rst_n = 1;
            for (i = j; i < 19; i = i + 1) put(vectors[2][i*8 +: 8], 0);
            repeat (34) @(negedge clk); send(vectors[2], 1);
            for (i = 0; i < j; i = i + 1) put(vectors[2][i*8 +: 8], 0);
            flush = 1; @(negedge clk); flush = 0;
            for (i = j; i < 19; i = i + 1) put(vectors[2][i*8 +: 8], 0);
            repeat (34) @(negedge clk); send(vectors[2], 1);
        end
        // Fixed seeds: mixed CRC/length/type/version faults, truncation, noise.
        for (seed = 1; seed <= 10; seed = seed + 1) begin
            rng = seed;
            for (j = 0; j < 1000; j = j + 1) begin
                rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
                mode = rng % 8; corrupt = vectors[2];
                case (mode)
                    0, 1: send(corrupt, 1);
                    2: begin corrupt[18*8 +: 8] = corrupt[18*8 +: 8] ^ 8'h80; send(corrupt, 0); end
                    3: begin corrupt[4*8 +: 8] = 255; send(corrupt, 0); end
                    4: begin corrupt[3*8 +: 8] = 0; send(corrupt, 0); end
                    5: begin corrupt[2*8 +: 8] = 2; send(corrupt, 0); end
                    6: begin
                        for (i = 0; i < 7; i = i + 1) put(corrupt[i*8 +: 8], 0);
                        repeat (34) @(negedge clk);
                    end
                    7: begin
                        for (i = 0; i < 8; i = i + 1) put(rng[(i%4)*8 +: 8], 0);
                        repeat (130) @(negedge clk);
                    end
                endcase
            end
            repeat (130) @(negedge clk); send(vectors[2], 1);
        end
        if (errors == 0) $fatal(1, "no malformed frame exercised");
        $display("PASS tb_frame_rx: golden CRC/frames, protected byte mutations, timeout/flush/reset/resync, 10 x 1000 mixed cases");
        $finish;
    end
    initial begin #30000000; $fatal(1, "frame RX timeout"); end
endmodule
