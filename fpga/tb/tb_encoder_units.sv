`timescale 1ns/1ps
module tb_encoder_units;
    reg clk = 0;
    always #5 clk = !clk;
    reg arst_n = 0;
    wire rst_n;
    reset_sync reset_dut (.clk(clk), .arst_n(arst_n), .rst_n(rst_n));
    reg [1:0] raw = 2'b11;
    wire [1:0] filtered, unfiltered;
    wire valid, valid_one;
    input_sync_filter #(.FILTER_N(3)) filter_dut (
        .clk(clk), .rst_n(rst_n), .async_in(raw), .filtered(filtered), .valid(valid));
    input_sync_filter #(.FILTER_N(1)) filter_one (
        .clk(clk), .rst_n(rst_n), .async_in(raw), .filtered(unfiltered), .valid(valid_one));
    reg sample_valid = 0;
    reg [1:0] ab = 0;
    wire [3:0] count, inverted;
    wire bad, bad_inverted, initialized, initialized_inverted;
    quadrature_decoder #(.COUNT_WIDTH(4)) decoder (
        .clk(clk), .rst_n(rst_n), .sample_valid(sample_valid), .ab(ab),
        .count(count), .invalid_event(bad), .initialized(initialized));
    quadrature_decoder #(.COUNT_WIDTH(4), .INVERT(1)) reverse_decoder (
        .clk(clk), .rst_n(rst_n), .sample_valid(sample_valid), .ab(ab),
        .count(inverted), .invalid_event(bad_inverted), .initialized(initialized_inverted));
    task tick;
        begin @(posedge clk); #1; end
    endtask
    task reset_all;
        begin
            @(negedge clk); arst_n = 0; sample_valid = 0;
            #1; if (rst_n !== 0) $fatal(1, "reset did not assert asynchronously");
            repeat (2) tick();
            @(negedge clk); arst_n = 1;
            tick(); if (rst_n !== 0) $fatal(1, "reset released before two edges");
            tick(); if (rst_n !== 1) $fatal(1, "reset did not release");
        end
    endtask
    function integer phase_index(input integer phase);
        case (phase)
            0: phase_index = 0;
            1: phase_index = 1;
            3: phase_index = 2;
            2: phase_index = 3;
        endcase
    endfunction
    function [1:0] phase_value(input integer index);
        case (index % 4)
            0: phase_value = 0;
            1: phase_value = 1;
            2: phase_value = 3;
            3: phase_value = 2;
        endcase
    endfunction
    integer old_phase, new_phase, delta, expected, width, k;
    initial begin
        if ($test$plusargs("waves")) begin
            $dumpfile("tb_encoder_units.vcd"); $dumpvars(0, tb_encoder_units);
        end
        reset_all();
        repeat (8) tick();
        if (!valid || !valid_one || filtered !== 3 || unfiltered !== 3)
            $fatal(1, "filter startup failed at nonzero phase");
        // Pulses sampled for N-1, N, N+1 clocks after synchronization.
        for (width = 2; width <= 4; width = width + 1) begin
            @(negedge clk); raw = 0;
            repeat (width) @(negedge clk);
            raw = 3;
            repeat (3) tick();
            if (width == 2 && filtered !== 3) $fatal(1, "short glitch passed");
            if (width >= 3 && filtered !== 0) $fatal(1, "stable N-sample pulse lost");
            repeat (8) tick();
            if (filtered !== 3) $fatal(1, "filter failed recovery");
        end
        // Reference uses positions on the quadrature ring, not DUT case table.
        for (old_phase = 0; old_phase < 4; old_phase = old_phase + 1) begin
            for (new_phase = 0; new_phase < 4; new_phase = new_phase + 1) begin
                reset_all();
                @(negedge clk); sample_valid = 1; ab = old_phase;
                tick();
                if (count !== 0 || !initialized) $fatal(1, "initial phase counted");
                @(negedge clk); ab = new_phase;
                delta = (phase_index(new_phase) - phase_index(old_phase) + 4) % 4;
                expected = (delta == 1) ? 1 : (delta == 3) ? 15 : 0;
                tick();
                if (count !== expected[3:0] || inverted !== ((-expected) & 15))
                    $fatal(1, "transition %d -> %d count mismatch", old_phase, new_phase);
                if (bad !== (delta == 2) || bad_inverted !== (delta == 2))
                    $fatal(1, "invalid transition classification");
                tick(); if (bad) $fatal(1, "invalid event did not clear");
            end
        end
        reset_all();
        @(negedge clk); sample_valid = 1; ab = 0;
        tick();
        for (k = 1; k <= 40; k = k + 1) begin
            @(negedge clk); ab = phase_value(k); tick();
            if (count !== (k & 15) || inverted !== ((-k) & 15))
                $fatal(1, "counter modulo/inversion failed");
        end
        @(negedge clk); sample_valid = 0; ab = 3;
        repeat (3) tick();
        if (count !== 8) $fatal(1, "invalid sample changed count");
        // Assert between clock edges, including reset of filter readiness.
        #2; arst_n = 0; #1;
        if (rst_n !== 0 || count !== 0 || valid !== 0) $fatal(1, "async reset outputs");
        $display("PASS tb_encoder_units: reset, filter boundaries, 16 transitions, wrap");
        $finish;
    end
    initial begin #100000; $fatal(1, "timeout tb_encoder_units"); end
endmodule
