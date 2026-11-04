`timescale 1ns/1ps
module tb;
GSR GSR(.GSRI(1'b1));
reg clk_in=0;always #10 clk_in=~clk_in;
reg rst_in=1,valid_in=0;
reg signed [23:0] carrier_sample_in=0,modulator_sample_in=0;
wire signed [23:0] sample_out;
wire valid_out,ready_out;wire [31:0] clip_count,rejected_count;
vocoder_core dut(.*);
reg [31:0] vectors[0:16383];integer n,cycles,maximum=0,rejected=0;
initial begin
 $display("BEGIN vendor netlist");
 $readmemh("vectors.hex",vectors);
 repeat(4)@(negedge clk_in);rst_in=0;@(negedge clk_in);
 for(n=0;n<8;n=n+1)begin
  if(n==256)begin
   valid_in=1;repeat(7)@(negedge clk_in);rst_in=1;valid_in=0;
   repeat(2)@(negedge clk_in);
   if(valid_out!==0||sample_out!==0||clip_count!==0||rejected_count!==0)$fatal(1,"reset");
   rst_in=0;rejected=0;@(negedge clk_in);
  end
  if(n%16==0)$display("PROGRESS n=%0d time=%0t",n,$time);
  if(!ready_out)$fatal(1,"not ready");
  modulator_sample_in=vectors[(n<256?n:2048+n-256)*4];carrier_sample_in=vectors[(n<256?n:2048+n-256)*4+1];valid_in=1;
  @(negedge clk_in);valid_in=0;cycles=0;
  while(!valid_out)begin
   if(cycles==5)begin valid_in=1;rejected=rejected+1;end
   if(cycles==6)valid_in=0;
   @(negedge clk_in);cycles=cycles+1;
   if(cycles>1000)$fatal(1,"deadline");
  end

  $display("BAND %0d 0 %0d %0d",n,$signed(dut.\carrier[0] ),$signed(dut.\envelope[0] ));
  $display("BAND %0d 1 %0d %0d",n,$signed(dut.\carrier[1] ),$signed(dut.\envelope[1] ));
  $display("BAND %0d 2 %0d %0d",n,$signed(dut.\carrier[2] ),$signed(dut.\envelope[2] ));
  $display("BAND %0d 3 %0d %0d",n,$signed(dut.\carrier[3] ),$signed(dut.\envelope[3] ));
  $display("BAND %0d 4 %0d %0d",n,$signed(dut.\carrier[4] ),$signed(dut.\envelope[4] ));
  $display("BAND %0d 5 %0d %0d",n,$signed(dut.\carrier[5] ),$signed(dut.\envelope[5] ));
  $display("BAND %0d 6 %0d %0d",n,$signed(dut.\carrier[6] ),$signed(dut.\envelope[6] ));
  $display("BAND %0d 7 %0d %0d",n,$signed(dut.\carrier[7] ),$signed(dut.\envelope[7] ));
  $display("BAND %0d 8 %0d %0d",n,$signed(dut.\carrier[8] ),$signed(dut.\envelope[8] ));
  $display("BAND %0d 9 %0d %0d",n,$signed(dut.\carrier[9] ),$signed(dut.\envelope[9] ));
  $display("BAND %0d 10 %0d %0d",n,$signed(dut.\carrier[10] ),$signed(dut.\envelope[10] ));
  $display("BAND %0d 11 %0d %0d",n,$signed(dut.\carrier[11] ),$signed(dut.\envelope[11] ));
  $display("BAND %0d 12 %0d %0d",n,$signed(dut.\carrier[12] ),$signed(dut.\envelope[12] ));
  $display("BAND %0d 13 %0d %0d",n,$signed(dut.\carrier[13] ),$signed(dut.\envelope[13] ));
  $display("BAND %0d 14 %0d %0d",n,$signed(dut.\carrier[14] ),$signed(dut.\envelope[14] ));
  $display("BAND %0d 15 %0d %0d",n,$signed(dut.\carrier[15] ),$signed(dut.\envelope[15] ));
  if(cycles>maximum)maximum=cycles;
  repeat(2)@(negedge clk_in);
 end
 $display("DIAGNOSTIC ONLY eight samples; acceptance checks removed, reset, backpressure, clip/reject counters; maxcycles=%0d",maximum);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
