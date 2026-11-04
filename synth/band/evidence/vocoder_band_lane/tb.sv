`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,frame_valid=0;
reg signed[15:0]band_left=0,band_right=0;
reg signed[23:0]mic_in=0;reg gate=1;reg[6:0]note=60,velocity=100;reg[6:0]voice_gain=0;
wire frame_ready,audio_valid;wire signed[23:0]left_out,right_out;
wire[31:0]dropped_frames,mix_clips,vocoder_clips;
vocoder_band_lane #(.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem"))dut(.*);
reg[31:0]v[0:4095];integer n,t,maximum=0;
initial begin
 $readmemh("vectors.hex",v);repeat(4)@(negedge clk);rst=0;@(negedge clk);
 for(n=0;n<512;n=n+1)begin
  if(!frame_ready)$fatal(1,"frame service deadline");
  mic_in=v[n*8];gate=1;note=60;velocity=100;band_left=v[n*8+2];band_right=v[n*8+3];voice_gain=v[n*8+4];frame_valid=1;
  @(negedge clk);frame_valid=0;t=0;
  // Change every external payload; accepted frame must remain coherent.
  mic_in=0;gate=0;note=127;velocity=0;band_left=0;band_right=0;voice_gain=0;
  while(!audio_valid)begin
   if(t==4)frame_valid=1;if(t==5)frame_valid=0;
   @(negedge clk);t=t+1;if(t>=1040)$fatal(1,"48k throughput exceeded");
  end
  if(left_out!==v[n*8+5][23:0]||right_out!==v[n*8+6][23:0]||mix_clips!==v[n*8+7]||dropped_frames!==n+1)
   $fatal(1,"aligned frame %0d L=%h R=%h expected=%h/%h clip=%0d",n,left_out,right_out,v[n*8+5],v[n*8+6],mix_clips);
  if(t>maximum)maximum=t;
  repeat(1040-t)@(negedge clk);
 end
 frame_valid=1;@(negedge clk);frame_valid=0;repeat(20)@(negedge clk);panic=1;@(negedge clk);
 if(left_out!==0||right_out!==0||audio_valid!==0)$fatal(1,"panic");
 panic=0;repeat(200)begin @(negedge clk);if(audio_valid)$fatal(1,"old frame escaped panic");end
 $display("PASS512 complete carrier/vocoder/band frames at1041clocks/frame; mute gain, saturation, busy rejection, panic; maxcycles=%0d",maximum);$finish;
end
initial begin #20000000;$fatal(1,"timeout");end
endmodule
