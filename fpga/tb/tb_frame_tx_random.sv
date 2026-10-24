`timescale 1ns/1ps
module tb_frame_tx_random;
    logic clk=0;
    always #5 clk=!clk;
    logic rst_n=0, flush=0, snapshot_valid=0, byte_ready=0;
    logic snapshot_ready, snapshot_dropped, byte_valid, byte_last;
    logic [7:0] byte_data;
    logic [31:0] session=0, snapshot_left=0, snapshot_right=0, snapshot_time=0, frame_session;
    logic [15:0] snapshot_seq=0, fault=0;
    logic [3:0] snapshot_status=0;
    logic [7:0] safety_state=0, frame_state;
    frame_tx dut(.*);
    logic [7:0] expected [0:30];
    logic [31:0] expected_session;
    logic [7:0] expected_state;
    logic checking=0;
    integer position=0, drops=0, completed=0;
    logic [15:0] crc;
    logic [23:0] polynomial;
    integer i, bit_no, seed, frame_no, cycles;
    logic [31:0] rng;
    task automatic randomize_fields;
        begin
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5); session=rng;
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5); snapshot_left=rng;
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5); snapshot_right=rng;
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5); snapshot_time=rng;
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
            snapshot_seq=rng[15:0]; snapshot_status=rng[19:16]; fault=rng[31:16]; safety_state=8'(frame_no);
        end
    endtask
    task automatic reference_frame;
        begin
            expected[0]=8'ha5; expected[1]=8'h5a; expected[2]=1; expected[3]=8'h80; expected[4]=18;
            expected_session=session; expected_state=safety_state;
            for(i=0;i<4;i=i+1) begin
                expected[5+i]=8'(session>>(8*i)); expected[11+i]=8'(snapshot_left>>(8*i));
                expected[15+i]=8'(snapshot_right>>(8*i)); expected[19+i]=8'(snapshot_time>>(8*i));
            end
            expected[9]=snapshot_seq[7:0]; expected[10]=snapshot_seq[15:8];
            expected[23]=snapshot_seq[7:0]; expected[24]=snapshot_seq[15:8];
            expected[25]=safety_state; expected[26]=fault[7:0]; expected[27]=fault[15:8];
            expected[28]={4'b0,snapshot_status};
            crc=16'hffff;
            for(i=2;i<29;i=i+1) begin
                polynomial={crc,8'b0}^{expected[i],16'b0};
                for(bit_no=23;bit_no>=16;bit_no=bit_no-1)
                    if(polynomial[bit_no]) polynomial=polynomial^(24'h011021<<(bit_no-16));
                crc=polynomial[15:0];
            end
            expected[29]=crc[7:0]; expected[30]=crc[15:8];
        end
    endtask
    always @(posedge clk) begin
        if(rst_n && checking && byte_valid) begin
            if(position>30 || byte_data!==expected[position] || byte_last!==(position==30) ||
               frame_session!==expected_session || frame_state!==expected_state)
                $fatal(1,"random STATUS mismatch seed=%0d frame=%0d position=%0d",seed,frame_no,position);
            if(byte_ready) position=position+1;
        end
        #1; if(snapshot_dropped) drops=drops+1;
    end
    initial begin
        if($test$plusargs("waves")) begin $dumpfile("tb_frame_tx_random.vcd"); $dumpvars(0,tb_frame_tx_random); end
        repeat(3) @(negedge clk); rst_n=1;
        for(seed=1;seed<=10;seed=seed+1) begin
            rng=32'(seed);
            for(frame_no=0;frame_no<256;frame_no=frame_no+1) begin
                @(negedge clk); randomize_fields; reference_frame;
                position=0; checking=1; snapshot_valid=1; byte_ready=0;
                @(negedge clk); snapshot_valid=0;
                if(snapshot_ready) $fatal(1,"snapshot was not accepted");
                cycles=0;
                while(!snapshot_ready && cycles<1000) begin
                    randomize_fields;
                    // Extra snapshots while busy must be dropped, with no queue.
                    snapshot_valid=(cycles==0 || cycles==3);
                    byte_ready=(rng[0] || cycles%16==15);
                    @(negedge clk); cycles=cycles+1;
                end
                snapshot_valid=0; byte_ready=0; checking=0;
                if(!snapshot_ready || position!=31) $fatal(1,"random STATUS not complete");
                repeat(3) @(negedge clk);
                if(byte_valid) $fatal(1,"busy snapshot was queued");
                completed=completed+1;
            end
        end
        if(completed!=2560 || drops!=5120) $fatal(1,"STATUS coverage counts %0d/%0d",completed,drops);
        $display("COVER frame_tx.random_frames 2560");
        $display("COVER frame_tx.busy_drops 5120");
        $display("COVER frame_tx.state_byte_values 256");
        $display("PASS tb_frame_tx_random: arbitrary fields, independent CRC/packing, stalls, frozen metadata and drops");
        $finish;
    end
    initial begin #30000000; $fatal(1,"random STATUS timeout"); end
endmodule
