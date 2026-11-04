`timescale 1ns/1ps
module tb_biquad;
 reg clk_in=0;always #10 clk_in=~clk_in;
 reg rst_in=1,valid_in=0;
 reg signed [31:0] b0_0,b1_0,b2_0,a1_0,a2_0,b0_1,b1_1,b2_1,a1_1,a2_1,x_n,x_n1,x_n2,i_n1,i_n2,y_n1,y_n2;
 wire signed [31:0] i_n,y_n;wire valid_out;
 double_biquad dut(.*);
 reg [31:0] vectors[0:4863];integer k,cycles,maximum=0;
 initial begin
  $readmemh("vectors.hex",vectors);
  repeat(4)@(negedge clk_in);rst_in=0;
  for(k=0;k<256;k=k+1)begin
   b0_0=vectors[k*19+0];
   b1_0=vectors[k*19+1];
   b2_0=vectors[k*19+2];
   a1_0=vectors[k*19+3];
   a2_0=vectors[k*19+4];
   b0_1=vectors[k*19+5];
   b1_1=vectors[k*19+6];
   b2_1=vectors[k*19+7];
   a1_1=vectors[k*19+8];
   a2_1=vectors[k*19+9];
   x_n=vectors[k*19+10];
   x_n1=vectors[k*19+11];
   x_n2=vectors[k*19+12];
   i_n1=vectors[k*19+13];
   i_n2=vectors[k*19+14];
   y_n1=vectors[k*19+15];
   y_n2=vectors[k*19+16];

   valid_in=1;@(negedge clk_in);valid_in=0;cycles=0;
   while(!valid_out)begin @(negedge clk_in);cycles=cycles+1;if(cycles>100)$fatal(1,"deadline");end
   if(i_n!==vectors[k*19+17]||y_n!==vectors[k*19+18])$fatal(1,"fixed-point vector %0d got %h/%h expected %h/%h",k,i_n,y_n,vectors[k*19+17],vectors[k*19+18]);
   if(cycles>maximum)maximum=cycles;
   @(negedge clk_in);
  end
  // Reset must initialize both result registers even if no new input arrives.
  rst_in=1;@(negedge clk_in);
  if(i_n!==0||y_n!==0||valid_out!==0)$fatal(1,"reset output");
  $display("PASS256 independent signed fixed-point vectors, maxcycles=%0d, reset outputs",maximum);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
