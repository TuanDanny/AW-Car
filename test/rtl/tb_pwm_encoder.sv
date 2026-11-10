`timescale 1ns/1ps
`default_nettype none
module tb_pwm_encoder;
    logic clk=0,rst_n=0,enable=0,pin_in=1;
    logic signed [15:0] target_left=0,target_right=0;
    wire logic l1,l2,r1,r2,seen;
    wire logic [31:0] count,period_ticks,age_ticks;
    always #18.5185185 clk=~clk;
    pwm_pair pwm(.clk(clk),.rst_n(rst_n),.enable(enable),.target_left(target_left),.target_right(target_right),
        .left_in1(l1),.left_in2(l2),.right_in1(r1),.right_in2(r2));
    encoder #(.FILTER_CYCLES(8)) enc(.clk(clk),.rst_n(rst_n),.pin_in(pin_in),
        .count(count),.period_ticks(period_ticks),.age_ticks(age_ticks),.seen(seen));
    always @(negedge clk) if (rst_n) begin
        if(l1&&l2 || r1&&r2) $fatal(1,"PWM overlap");
    end
    task automatic duty_test(input int duty);
        int a,b,c,d,mag;
        @(negedge clk); target_left=duty; target_right=-duty;
        repeat(2701) @(negedge clk);
        while(pwm.phase!=0) @(negedge clk);
        a=0;b=0;c=0;d=0;mag=duty<0 ? -duty:duty;
        for(int i=0;i<1350;i=i+1) begin
            a=a+int'(l1); b=b+int'(l2); c=c+int'(r1); d=d+int'(r2);
            @(negedge clk);
        end
        if(a!=(duty>0?mag:0) || b!=(duty<0?mag:0) || c!=(duty<0?mag:0) || d!=(duty>0?mag:0))
            $fatal(1,"PWM duty %0d counts %0d %0d %0d %0d",duty,a,b,c,d);
    endtask
    initial begin
        #100;rst_n=1;enable=1;
        repeat(30) @(negedge clk);
        if(count!==0 || seen!==0 || age_ticks!==0 || period_ticks!==0) $fatal(1,"initial high fabricated an edge");
        // Sub-filter glitches in either direction must be rejected.
        pin_in=0;repeat(3) @(negedge clk);pin_in=1;repeat(20) @(negedge clk);
        if(count!==0) $fatal(1,"short low noise fabricated edge");
        pin_in=0;repeat(20) @(negedge clk);
        pin_in=1;repeat(3) @(negedge clk);pin_in=0;repeat(20) @(negedge clk);
        if(count!==0) $fatal(1,"short high noise counted");
        pin_in=1;repeat(20) @(negedge clk);
        if(count!==1 || !seen || period_ticks!==0) $fatal(1,"first filtered edge");
        pin_in=0;repeat(80) @(negedge clk);
        pin_in=1;repeat(20) @(negedge clk);
        if(count!==2 || period_ticks!==100 || age_ticks!==9) $fatal(1,"period/age ticks count=%0d period=%0d age=%0d",count,period_ticks,age_ticks);
        repeat(20) @(negedge clk);
        if(age_ticks!==29) $fatal(1,"age does not advance each 27MHz tick");
        // Accelerate only unreachable-in-a-short-run overflow states, not normal timing.
        force enc.age_ticks=32'hfffffffe;
        @(negedge clk); release enc.age_ticks; repeat(4) @(negedge clk);
        if(age_ticks!==32'hffffffff) $fatal(1,"age must saturate");
        pin_in=0;repeat(20) @(negedge clk);
        force enc.count=32'hffffffff;
        @(negedge clk); release enc.count;
        pin_in=1;repeat(20) @(negedge clk);
        if(count!==0 || period_ticks!==32'hffffffff) $fatal(1,"unsigned wrap/saturated period");
        duty_test(0);duty_test(1);duty_test(10);duty_test(675);duty_test(1349);duty_test(1350);
        duty_test(-1350);duty_test(-1349);duty_test(-675);duty_test(-10);duty_test(-1);duty_test(0);
        // Sign changes force a complete neutral PWM period, then the new sign.
        duty_test(1350);
        while(pwm.phase!=100) @(negedge clk);
        target_left=-1350;target_right=1350;
        while(pwm.phase!=0) begin
            if({l1,l2,r1,r2}!==4'b1001) $fatal(1,"target update affected a partial PWM period");
            @(negedge clk);
        end
        repeat(1350) begin
            if({l1,l2,r1,r2}!==0) $fatal(1,"missing neutral reversal period");
            @(negedge clk);
        end
        if({l1,l2,r1,r2}!==4'b0110) $fatal(1,"unnecessary extra reversal delay");
        enable=0;@(negedge clk);
        if({l1,l2,r1,r2}!==0) $fatal(1,"watchdog enable did not kill within one clk");
        rst_n=0;#1;
        if({l1,l2,r1,r2}!==0 || count!==0 || seen!==0) $fatal(1,"reset");
        $display("PASS tb_pwm_encoder: 12 signed duties, 1350-tick periods, no overlap, boundary-only update, filter/baseline/count/period/age/saturation/wrap");
        $finish;
    end
    initial begin #10000000; $fatal(1,"tb_pwm_encoder timeout"); end
endmodule
