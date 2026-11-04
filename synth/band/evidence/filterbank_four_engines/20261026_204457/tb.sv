`timescale 1ns/1ps
module tb;
reg clk_in=0;always #10 clk_in=~clk_in;
reg rst_in=1,valid_in=0;
reg signed [31:0] carrier_sample_in=0,modulator_sample_in=0;
wire signed [31:0] carrier_out[15:0],envelope_out[15:0];
wire valid_out,ready_out;
filterbank #(.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/four_engines/b9f528faecf1/coeffs.mem")) dut(.*);
reg [31:0] vectors[0:139263];
integer n,j,cycles,maximum=0;
initial begin
 $readmemh("vectors.hex",vectors);
 repeat(4)@(negedge clk_in);
 if(valid_out!==0||ready_out!==0)$fatal(1,"reset control");
 rst_in=0;@(negedge clk_in);
 for(n=0;n<4096;n=n+1)begin
  if(n==2048)begin
   // Reset while a poisoned transaction is actually in progress.
   valid_in=1;modulator_sample_in=1234567;carrier_sample_in=-1234567;
   repeat(7)@(negedge clk_in);rst_in=1;valid_in=0;
   repeat(2)@(negedge clk_in);
   if(valid_out!==0)$fatal(1,"reset valid");
   for(j=0;j<16;j=j+1)if(carrier_out[j]!==0||envelope_out[j]!==0)$fatal(1,"reset data");
   rst_in=0;@(negedge clk_in);
  end
  if(!ready_out)$fatal(1,"not ready before sample");
  modulator_sample_in=vectors[n*34];carrier_sample_in=vectors[n*34+1];valid_in=1;
  @(negedge clk_in);valid_in=0;cycles=0;
  while(!valid_out)begin
   // Inputs can change while busy; a spurious valid must not corrupt state.
   if(cycles==5)begin valid_in=1;modulator_sample_in=32'h7fffffff;carrier_sample_in=32'h80000000;end
   if(cycles==6)valid_in=0;
   @(negedge clk_in);cycles=cycles+1;
   if(cycles>1000)$fatal(1,"deadline");
  end
  for(j=0;j<16;j=j+1)begin
   if(carrier_out[j]!==vectors[n*34+2+j*2]||envelope_out[j]!==vectors[n*34+3+j*2])
    $fatal(1,"sample %0d band %0d got %h/%h expected %h/%h",n,j,carrier_out[j],envelope_out[j],vectors[n*34+2+j*2],vectors[n*34+3+j*2]);
  end
  if(cycles>maximum)maximum=cycles;
  @(negedge clk_in);
  if(valid_out!==0)$fatal(1,"valid not pulse");
 end
 $display("PASS4096 samples x16 bands; busy input rejection, mid-transaction reset; maxcycles=%0d",maximum);$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
