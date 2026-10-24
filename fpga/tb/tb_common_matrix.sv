`timescale 1ns/1ps
module filter_matrix_case #(parameter int N = 1, W = 1)(output logic done = 0);
    logic clk = 0, running = 1, rst_n = 0;
    always #5 if (running) clk = !clk;
    logic [W-1:0] raw = '1, filtered;
    logic valid;
    input_sync_filter #(.WIDTH(W), .FILTER_N(N)) dut (
        .clk(clk), .rst_n(rst_n), .async_in(raw), .filtered(filtered), .valid(valid));
    // Reference keeps a history of sampled vectors. A change is allowed only
    // after N identical samples at the output of a two-edge sampling pipeline.
    logic [W-1:0] history [0:N+1];
    logic [W-1:0] expected = 0;
    logic expected_valid = 0, identical;
    integer samples = 0, checks = 0, i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            samples = 0; expected = 0; expected_valid = 0;
            for (i = 0; i < N+2; i = i+1) history[i] = 0;
        end else begin
            for (i = N+1; i > 0; i = i-1) history[i] = history[i-1];
            history[0] = raw; samples = samples + 1;
            identical = 1;
            for (i = 3; i < N+2; i = i+1)
                if (history[i] != history[2]) identical = 0;
            if (samples >= N+2 && identical) begin
                expected = history[2]; expected_valid = 1;
            end
        end
        #1;
        if ({valid, filtered} !== {expected_valid, expected})
            $fatal(1, "filter N=%0d W=%0d sample=%0d got=%b/%h expected=%b/%h",
                   N,W,samples,valid,filtered,expected_valid,expected);
        checks = checks + 1;
    end
    task automatic settle(input logic [W-1:0] value, input integer cycles);
        begin @(negedge clk); #2; raw = value; repeat(cycles) @(negedge clk); end
    endtask
    integer width, k;
    logic [31:0] rng = 32'h1259abcd;
    initial begin
        repeat(2) @(negedge clk); #2; rst_n = 1;
        settle('1,N+5);
        for (width=1; width<=N+1; width=width+1) begin
            settle(0,width); settle('1,N+5);
        end
        for (k=0;k<2000;k=k+1) begin
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
            settle(W'(rng),1+(rng%(N+3)));
        end
        // Reset with a partial candidate, while no clock can clear state.
        settle(0,1); running=0; #2; rst_n=0; #2;
        if (valid !== 0 || filtered !== 0) $fatal(1,"filter async reset N=%0d",N);
        #20; running=1; repeat(2) @(negedge clk); rst_n=1;
        settle('1,N+6);
        if(checks<2000) $fatal(1,"filter coverage missing");
        $display("COVER filter.N%0d.W%0d.samples %0d",N,W,checks);
        done=1;
    end
endmodule

module tb_common_matrix;
    logic [5:0] finished;
    filter_matrix_case #(.N(1),.W(1)) c0(finished[0]);
    filter_matrix_case #(.N(2),.W(2)) c1(finished[1]);
    filter_matrix_case #(.N(3),.W(4)) c2(finished[2]);
    filter_matrix_case #(.N(4),.W(2)) c3(finished[3]);
    filter_matrix_case #(.N(5),.W(3)) c4(finished[4]);
    filter_matrix_case #(.N(8),.W(4)) c5(finished[5]);
    logic clk=0, running=1, arst_n=0, rst_n;
    always #5 if(running) clk=!clk;
    reset_sync dut(.*);
    integer phase;
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_common_matrix.vcd"); $dumpvars(0,tb_common_matrix); end
        for(phase=1;phase<=9;phase=phase+1) begin
            @(negedge clk); arst_n=0; #1;
            if(rst_n!==0) $fatal(1,"reset assert phase %0d",phase);
            @(negedge clk); #(phase+0.25); arst_n=1;
            @(posedge clk); #0.001;
            if(rst_n!==0) $fatal(1,"reset early release phase %0d",phase);
            @(posedge clk); #0.001;
            if(rst_n!==1) $fatal(1,"reset late release phase %0d",phase);
        end
        @(negedge clk); running=0; #2; arst_n=0; #1;
        if(rst_n!==0) $fatal(1,"reset requires stopped clock");
        arst_n=1; #30;
        if(rst_n!==0) $fatal(1,"reset release without clock");
        running=1; @(posedge clk); #1;
        if(rst_n!==0) $fatal(1,"reset first resumed edge");
        @(posedge clk); #1;
        if(rst_n!==1) $fatal(1,"reset second resumed edge");
        wait(&finished);
        $display("COVER reset.release_phases 9");
        $display("COVER reset.stopped_clock 1");
        $display("PASS tb_common_matrix: history scoreboard, 6 filter configurations, reset phases/stopped clock");
        $finish;
    end
    initial begin #2000000; $fatal(1,"common matrix timeout"); end
endmodule
