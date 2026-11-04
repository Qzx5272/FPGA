`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,valid=0;reg signed[15:0]l=0,r=0;always #10 clk=~clk;
 wire[127:0]bands;wire[383:0]trace_l,trace_r;wire[5:0]peak_l,peak_r;
 score_analysis dut(clk,rst,valid,l,r,bands,trace_l,trace_r,peak_l,peak_r);
 task sample(input integer n,input integer bin,input integer amp);
 begin repeat(20)@(negedge clk);l=$rtoi(amp*$sin(6.283185307*n*bin/2048.0));r=l>>>1;valid=1;@(negedge clk);valid=0;end
 endtask
 task check_band(input integer bin,expected);
 integer peak,which,level;
 begin
  for(integer i=0;i<24576;i=i+1)sample(i,bin,6000);
  peak=0;which=0;
  for(integer b=0;b<32;b=b+1)begin level=bands[b*4+:4];if(level>peak)begin peak=level;which=b;end end
  if(which!=expected||peak<8||peak_l<40||peak_r>=peak_l||trace_l==trace_r)$fatal(1,"FFT/PCM feedback %d %d %d",bin,which,peak);
 end endtask
 initial begin repeat(6)@(negedge clk);rst=0;check_band(11,8);check_band(42,15);
  for(integer i=0;i<24576;i++)sample(i,0,0);
  if(bands!==0||peak_l!=0||peak_r!=0)$fatal(1,"silence");
  $display("PASS real stereo PCM, two FFT frequency bands and silence");$finish;
 end
endmodule

