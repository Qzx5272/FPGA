`timescale 1ns/1ps
module tb_ownership;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,bar=0,valid=0,rr=0;reg [1:0] cmd=0;reg [3:0] part=3,q=3;reg [7:0] src=1;
 wire ready,rv,mute,pending,exhausted;wire [3:0] rp;wire [7:0] owner;wire [31:0] epoch,conflicts;
 track_ownership dut(clk,rst,panic,bar,valid,ready,cmd,part,src,rv,rr,rp,q,owner,epoch,mute,pending,conflicts,exhausted,q,,,1'b0,8'd0);
 task send;input [1:0] c;input [7:0] s;
 begin wait(ready);@(negedge clk);cmd=c;src=s;valid=1;@(negedge clk);valid=0;end endtask
 task ack;
 begin wait(rv);repeat(4)@(negedge clk);if(ready)$fatal;rr=1;@(negedge clk);rr=0;end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  send(0,1);ack();if(owner!=1||epoch!=2)$fatal;
  send(0,2);if(conflicts!=1||owner!=1)$fatal;
  send(1,1);if(!pending||owner!=1)$fatal;
  repeat(10)@(negedge clk);if(owner!=1)$fatal;
  bar=1;@(negedge clk);bar=0;ack();wait(ready);#1;
  if(owner!=0||epoch!=3||pending)$fatal;
  send(2,1);ack();if(!mute)$fatal;send(3,1);if(mute)$fatal;
  send(0,2);ack();send(1,2);panic=1;@(negedge clk);panic=0;#1;
  if(owner!=2||pending||epoch!=4)$fatal;
  $display("PASS ownership: exclusive seats, epoch, backpressure, bar-quantized return, mute, panic");$finish;
 end
 initial begin #100000;$fatal;end
endmodule
