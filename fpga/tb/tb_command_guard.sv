`timescale 1ns/1ps
module tb_command_guard;
    logic clk = 0;
    always #5 clk = !clk;
    logic rst_n = 0, context_load = 0, session_active = 0, command_enable = 0, frame_valid = 0;
    logic [31:0] active_session = 32'h12345678, frame_session = 32'h12345678;
    logic [15:0] sequence_base = 16'hfffe, frame_sequence = 0;
    logic [7:0] frame_type = 0;
    logic [47:0] frame_payload = {16'd1350, 16'd675, 16'd0};
    logic hello_request, arm_zero_request, disable_request, clear_fault_request, command_valid, rejected;
    logic [31:0] event_session;
    logic [15:0] event_sequence, command_left, command_right;
    logic [1:0] command_direction;
    command_guard dut (.*);
    logic reverse_valid, reverse_rejected;
    logic [1:0] reverse_direction;
    command_guard #(.ALLOW_REVERSE(1)) reverse_dut (
        .clk(clk), .rst_n(rst_n), .context_load(context_load), .session_active(session_active),
        .active_session(active_session), .sequence_base(sequence_base), .command_enable(command_enable),
        .frame_valid(frame_valid), .frame_type(frame_type), .frame_session(frame_session),
        .frame_sequence(frame_sequence), .frame_payload(frame_payload),
        .hello_request(), .arm_zero_request(), .disable_request(), .clear_fault_request(),
        .command_valid(reverse_valid), .rejected(reverse_rejected), .event_session(), .event_sequence(),
        .command_left(), .command_right(), .command_direction(reverse_direction));
    task automatic offer(input logic [7:0] kind, input logic [15:0] seq,
                         input logic [5:0] expected);
        begin
            @(negedge clk); frame_type = kind; frame_sequence = seq; frame_valid = 1;
            @(posedge clk); #1;
            if ({rejected, command_valid, clear_fault_request, disable_request,
                 arm_zero_request, hello_request} !== expected)
                $fatal(1, "guard event kind=%h seq=%h", kind, seq);
            if (event_session !== frame_session || event_sequence !== seq) $fatal(1, "event fields not atomic");
            if (command_valid && {command_right, command_left, 6'b0, command_direction, 8'b0} !== frame_payload)
                $fatal(1, "command pair not atomic");
            @(negedge clk); frame_valid = 0;
            @(posedge clk); #1;
            if ({rejected, command_valid, clear_fault_request, disable_request,
                 arm_zero_request, hello_request} !== 0) $fatal(1, "event is not pulse");
        end
    endtask
    integer i;
    initial begin
        if ($test$plusargs("waves")) begin $dumpfile("tb_command_guard.vcd"); $dumpvars(0, tb_command_guard); end
        repeat (3) @(negedge clk); rst_n = 1;
        offer(3, 1, 6'b100000); // No session, no authority.
        offer(1, 0, 6'b000001);
        offer(2, 1, 6'b100000); // HELLO did not install a session.
        @(negedge clk); session_active = 1; context_load = 1;
        @(negedge clk); context_load = 0;
        offer(2, 16'hffff, 6'b000010);
        command_enable = 1;
        offer(3, 0, 6'b010000); // Wrap ffff -> 0000.
        offer(3, 0, 6'b100000);
        offer(3, 16'hffff, 6'b100000);
        offer(3, 16'h8000, 6'b100000);
        offer(3, 7, 6'b010000); // Lost frames allowed.
        frame_session = 99; offer(3, 8, 6'b100000);
        offer(4, 8, 6'b000100); // Global safe reduction only.
        frame_session = active_session;
        for (i = 0; i < 8; i = i + 1) begin
            frame_payload = {16'd1350, 16'd675, 16'd0};
            case (i)
                0: frame_payload[0] = 1;
                1: frame_payload[7] = 1;
                2: frame_payload[10] = 1;
                3: frame_payload[15] = 1;
                4: frame_payload[8] = 1;
                5: frame_payload[9] = 1;
                6: frame_payload[31:16] = 1351;
                7: frame_payload[47:32] = 65535;
            endcase
            offer(3, 8, 6'b100000);
        end
        frame_payload = 0; command_enable = 0;
        offer(3, 8, 6'b100000);
        command_enable = 1; offer(3, 8, 6'b010000); // Rejected frames did not consume sequence.
        offer(5, 9, 6'b001000);
        offer(5, 9, 6'b100000);
        session_active = 0; offer(3, 10, 6'b100000);
        active_session = 32'h55aa55aa; frame_session = active_session;
        sequence_base = 100; session_active = 1;
        @(negedge clk); context_load = 1; frame_valid = 1; frame_type = 3; frame_sequence = 101;
        @(posedge clk); #1;
        if (command_valid || command_left || command_right) $fatal(1, "context load lost priority");
        @(negedge clk); context_load = 0; frame_valid = 0;
        offer(3, 100, 6'b100000); offer(3, 101, 6'b010000);
        offer(3, 16'h8064, 6'b010000); // Largest fresh delta: 32767.
        offer(3, 16'h0064, 6'b100000); // Ambiguous delta: 32768.
        @(negedge clk); context_load = 1;
        @(negedge clk); context_load = 0;
        frame_payload = {16'd1350, 16'd1, 8'd3, 8'd0};
        @(negedge clk); frame_valid = 1; frame_type = 3; frame_sequence = 102;
        @(posedge clk); #1;
        if (!rejected || command_valid || !reverse_valid || reverse_rejected || reverse_direction !== 3)
            $fatal(1, "ALLOW_REVERSE policy parameter");
        @(negedge clk); frame_valid = 0;
        rst_n = 0; session_active = 0; command_enable = 0;
        @(negedge clk); rst_n = 1; offer(3, 102, 6'b100000);
        $display("PASS tb_command_guard: authority, atomic events, wrap/gap/old/duplicate/session, reserved/duty/reverse, reset");
        $finish;
    end
    initial begin #100000; $fatal(1, "guard timeout"); end
endmodule
