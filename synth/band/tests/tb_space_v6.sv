`timescale 1ns/1ps
module tb_space_v6;
 reg clk=0;always #5 clk=~clk;reg rst=1,clear=0,valid=0;reg signed[15:0]l=0,r=0;reg[6:0]wet=0;reg[1:0]mode=0;
 wire ready,vo;wire signed[15:0]lo,ro;wire[31:0]clips,overruns;
 stereo_space effect(clk,rst,clear,valid,l,r,wet,mode,ready,vo,lo,ro,clips,overruns);
 integer i,m,echoes;reg signed[15:0]last;
 task frame(input signed[15:0]a,b);begin
 @(negedge clk);valid=1;l=a;r=b;@(negedge clk);valid=0;
 wait(vo);@(negedge clk);last=lo;
 end endtask
 task reset;begin clear=1;@(negedge clk);clear=0;wait(ready);@(negedge clk);end endtask
 initial begin
 repeat(3)@(negedge clk);rst=0;wait(ready);@(negedge clk);
 frame(1234,-4567);if(lo!=1234||ro!=-4567)$fatal(1,"bypass exactness");
 for(m=0;m<3;m=m+1)begin
  reset();mode=m;wet=127;echoes=0;
  for(i=0;i<12500;i=i+1)begin
   frame(i==0?16'sd12000:16'sd0,i==0?-16'sd8000:16'sd0);
   if(i>100&&last!=0)echoes=echoes+1;
  end
  if(echoes==0||clips||overruns)$fatal(1,"effect response mode=%0d echoes=%0d clips=%0d overrun=%0d",m,echoes,clips,overruns);
 end
 reset();frame(0,0);if(lo||ro)$fatal(1,"clear retained tail");
 $display("PASS effects: exact bypass,delay/reverb/chorus impulse responses,zero clip/overrun,tail clear");$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
