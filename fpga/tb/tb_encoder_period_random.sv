`timescale 1ns/1ps
module period_random_case #(parameter int T=4,C=4)(output logic done=0);
    logic clk=0;always #5 clk=~clk;
    logic rst_n=0,sample_valid=0,pulse=1,initialized,edge_seen,period_valid;
    logic [C-1:0] count;
    logic [T-1:0] period_ticks,age_ticks;
    pulse_counter #(.COUNT_WIDTH(C),.TIME_WIDTH(T)) dut(.*);
    integer tick=0,last_rise=-1,total=0,baseline=0,previous=0;
    integer n,expected_period=0,expected_valid=0,expected_seen=0,expected_age;
    logic [31:0] rng=32'hcf13579b;
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        for(n=0;n<12000;n=n+1) begin
            rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
            sample_valid=rng[0];pulse=rng[3];
            // Explicit long silence forces age saturation, then random recovery.
            if(n%1300<600) begin sample_valid=1;pulse=0;end
            tick=tick+1;
            if(last_rise>=0 && tick-last_rise >= (1<<T)-1) begin
                expected_seen=0;expected_valid=0;
            end
            if(sample_valid) begin
                if(baseline && !previous && pulse) begin
                    total=total+1;
                    if(last_rise>=0 && tick-last_rise <= (1<<T)-1) begin
                        expected_period=tick-last_rise;expected_valid=1;
                    end else begin expected_period=0;expected_valid=0;end
                    last_rise=tick;expected_seen=1;
                end
                baseline=1;previous=pulse;
            end
            expected_age=last_rise<0 ? (1<<T)-1 : tick-last_rise;
            if(expected_age>(1<<T)-1) expected_age=(1<<T)-1;
            @(posedge clk);#1;
            if(count!==C'(total) || initialized!==1'(baseline) ||
               age_ticks!==T'(expected_age) || period_ticks!==T'(expected_period) ||
               period_valid!==1'(expected_valid) || edge_seen!==1'(expected_seen))
                $fatal(1,"random period scoreboard T=%0d sample=%0d",T,n);
            @(negedge clk);
        end
        $display("COVER period_random.T%0d.samples 12000",T);done=1;
    end
endmodule
module tb_encoder_period_random;
    logic [1:0] done;
    period_random_case #(.T(4),.C(4)) tiny_case(done[0]);
    period_random_case #(.T(9),.C(16)) wide(done[1]);
    initial begin wait(&done);$display("PASS tb_encoder_period_random: independent timestamps, gaps, saturation and wrap");$finish;end
    initial begin #200000; $fatal(1,"period random timeout");end
endmodule
