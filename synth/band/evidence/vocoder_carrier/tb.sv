`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,frame_valid=0,gate=0;reg[6:0]note=0,velocity=0;
wire ready,valid_out;wire signed[23:0]sample_out;wire[31:0]dropped_frames;
vocoder_carrier dut(.*);
reg[31:0]v[0:20479];integer n,t,error,peak_error=0,maxcycles=0,pcm;reg signed[31:0]expectation;
initial begin
 pcm=$fopen("carrier.hex","w");
 $readmemh("vectors.hex",v);repeat(4)@(negedge clk);rst=0;@(negedge clk);
 for(n=0;n<4096;n=n+1)begin
  if(!ready)$fatal(1,"not ready");
  gate=v[n*5];note=v[n*5+1];velocity=v[n*5+2];frame_valid=1;
  @(negedge clk);frame_valid=0;gate=0;note=127;velocity=0;t=0;
  while(!valid_out)begin @(negedge clk);t=t+1;if(t>100)$fatal(1,"deadline");end
  $fdisplay(pcm,"%h",sample_out);
  expectation=v[n*5+3];error=$signed(sample_out)-expectation;if(error<0)error=-error;
  if(error>256)$fatal(1,"Fourier mismatch sample%0d got%0d expected%0d error%0d",n,sample_out,expectation,error);
  if(v[n*5+4]&&sample_out!==0)$fatal(1,"release not exact silence");
  if(error>peak_error)peak_error=error;if(t>maxcycles)maxcycles=t;
  @(negedge clk);
 end
 $fclose(pcm);
 gate=1;velocity=127;note=69;frame_valid=1;@(negedge clk);frame_valid=0;
 repeat(7)@(negedge clk);panic=1;@(negedge clk);
 if(sample_out!==0||valid_out!==0)$fatal(1,"panic");panic=0;
 repeat(100)begin @(negedge clk);if(valid_out)$fatal(1,"stale result after panic");end
 $display("PASS4096 Fourier samples,64harmonic/Nyquist mask,legato,release,panic;maxcycles=%0d maxerror24bitLSB=%0d",maxcycles,peak_error);$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
