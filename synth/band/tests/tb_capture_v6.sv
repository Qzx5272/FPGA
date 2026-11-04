`timescale 1ns/1ps
module tb_capture_v6;
 reg clk=0;always #5 clk=~clk;reg rst=1,clear=0,tick=0,capture=0,ready=0;
 reg[223:0]event_data=224'd4;reg[1:0]collision=0;wire valid;wire[223:0]data;wire[31:0]overflows;
 event_capture_fifo fifo(clk,rst,clear,tick,capture,event_data,valid,ready,data,overflows,collision);
 integer i;reg[223:0]held;
 initial begin
 repeat(3)@(negedge clk);rst=0;tick=1;repeat(10)@(negedge clk);tick=0;
 event_data[15:8]=11;event_data[23:16]=3;event_data[223:192]=127;capture=1;
 @(negedge clk);capture=0;held=data;
 if(!valid||data[15:8]!=8'hcb||data[191:128]!=10||data[223:192]!=127)$fatal(1,"capture encoding");
 repeat(4)@(negedge clk);if(data!==held)$fatal(1,"stalled capture changed");
 capture=1;for(i=0;i<64;i=i+1)@(negedge clk);capture=0;
 if(overflows!=1||fifo.count!=64)$fatal(1,"bounded overflow");
 capture=1;ready=1;@(negedge clk);capture=0;ready=0;
 if(overflows!=1||fifo.count!=64)$fatal(1,"full pop+push");
 collision=2;@(negedge clk);collision=0;if(overflows!=3)$fatal(1,"collision accounting");
 clear=1;@(negedge clk);clear=0;if(valid)$fatal(1,"panic clear");
 event_data[15:8]=127;capture=1;@(negedge clk);capture=0;
 if(!valid||data[15:8]!=8'he0)$fatal(1,"panic event encoding");
 $display("PASS capture: sample timestamps,event encoding,stable backpressure,bounded overflow,simultaneous push/pop,collision count,panic flush");$finish;
 end
endmodule
