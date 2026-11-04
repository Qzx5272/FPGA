`timescale 1ns/1ps
module tb_delay;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,clear=0,valid=0;reg signed [15:0] l=0,r=0;reg [6:0] wet=64;
 wire ready,done;wire signed [15:0] ol,orr;wire [31:0] clips,overruns;
 stereo_delay #(.ADDRESS_BITS(3)) dut(clk,rst,clear,valid,l,r,wet,ready,done,ol,orr,clips,overruns);
 integer n;integer expected_l,expected_r;
 task sample;
 input integer il,ir,el,er;
 begin
  @(negedge clk);l=il;r=ir;valid=1;
  @(negedge clk);valid=0;
  wait(done);#1;
  if(ol!==el||orr!==er)begin $display("FAIL delay sample %0d: %0d,%0d expected %0d,%0d",n,ol,orr,el,er);$fatal;end
  @(negedge clk);
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;wait(ready);
  for(n=0;n<64;n=n+1)begin
   expected_l=0;expected_r=0;
   if(n==0||n==8)expected_l=8192;
   if(n==16)expected_r=4096;
   if(n==24)expected_l=2048;
   if(n==32)expected_r=1024;
   if(n==40)expected_l=512;
   if(n==48)expected_r=256;
   if(n==56)expected_l=128;
   sample(n==0?16384:0,0,expected_l,expected_r);
  end
  @(negedge clk);clear=1;@(negedge clk);clear=0;wait(ready);
  for(n=0;n<20;n=n+1)sample(0,0,0,0);
  sample(-2,0,-1,0);
  for(n=1;n<40;n=n+1)begin
   sample(0,0,n==8?-1:0,n==16?-1:0);
  end
  // An arithmetic-shift feedback bug would leave a perpetual negative one here.
  for(n=0;n<8;n=n+1)if(dut.mem_l[n]!=0||dut.mem_r[n]!=0)begin $display("FAIL non-decaying tail");$fatal;end
  wet=0;sample(-32768,32767,-32768,32767);
  for(n=0;n<24;n=n+1)sample(32767,32767,32767,32767);
  if(clips==0||overruns!=0)begin $display("FAIL counters");$fatal;end
  @(negedge clk);valid=1;repeat(5)@(negedge clk);valid=0;
  if(overruns==0)begin $display("FAIL deadline counter");$fatal;end
  $display("PASS stereo delay: impulse, stereo feedback, clear, bypass, saturation, deadline");$finish;
 end
 initial begin #100000;$display("FAIL timeout");$fatal;end
endmodule
