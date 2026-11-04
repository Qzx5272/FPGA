`timescale 1ns/1ps
module tb;
reg clk_in=0;always #10 clk_in=~clk_in;
reg rst_in=1,valid_in=0;
reg signed [31:0] carrier_in[15:0],envelope_in[15:0];
wire ready_out,valid_out;wire signed [23:0] sample_out;wire [31:0]clip_count;
vocoder_mixer dut(.*);
reg [31:0] v[0:8703];integer n,j,t;
initial begin
 $readmemh("vectors.hex",v);
 repeat(3)@(negedge clk_in);rst_in=0;@(negedge clk_in);
 for(n=0;n<256;n=n+1)begin
  for(j=0;j<16;j=j+1)begin carrier_in[j]=v[n*34+j];envelope_in[j]=v[n*34+16+j];end
  valid_in=1;@(negedge clk_in);valid_in=0;t=0;
  for(j=0;j<16;j=j+1)begin carrier_in[j]=0;envelope_in[j]=0;end
  while(!valid_out)begin @(negedge clk_in);t=t+1;if(t>20)$fatal(1,"timeout");end
  if(t!=16||sample_out!==v[n*34+32][23:0]||clip_count!==v[n*34+33])$fatal(1,"vector %0d",n);
  @(negedge clk_in);
 end
 rst_in=1;@(negedge clk_in);
 if(clip_count!==0||valid_out!==0||sample_out!==0)$fatal(1,"reset");
 $display("PASS256 mixer boundary vectors: positive/negative saturation, negative envelope clamp, input latching, counter/reset,16cycles");$finish;
end
endmodule
