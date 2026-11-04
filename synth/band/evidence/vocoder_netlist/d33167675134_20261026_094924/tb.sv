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
 for(n=0;n<320;n=n+1)begin
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
   if(cycles>200)$fatal(1,"deadline");
  end
  if(sample_out!==vectors[(n<256?n:2048+n-256)*4+2][23:0]||clip_count!==vectors[(n<256?n:2048+n-256)*4+3]||rejected_count!==rejected)
   $fatal(1,"sample %0d got %h expected %h clips %0d reject %0d",n,sample_out,vectors[(n<256?n:2048+n-256)*4+2],clip_count,rejected_count);
  if(cycles>maximum)maximum=cycles;
  repeat(2)@(negedge clk_in);
 end
 $display("PASS vendor-netlist320 samples (256 voiced/noise +64 reset/rail/decay), reset, backpressure, clip/reject counters; maxcycles=%0d",maximum);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
