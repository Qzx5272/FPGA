`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,event_valid=0,frame_valid=0,sample_tick=0;
wire event_ready,frame_ready,audio_valid,singer_gate;wire[6:0]singer_note;
reg[1:0]event_kind=0;reg[7:0]event_source=1,event_contact=0;
reg[3:0]event_part=15;reg[31:0]event_epoch=1,event_serial=1;
reg[6:0]event_note=60,event_velocity=100,voice_gain=0;
reg signed[15:0]band_left=0,band_right=0;reg signed[23:0]mic_in=0;
wire signed[23:0]left_out,right_out;
wire[31:0]rejected,stale_off,duplicates,dropped_frames,mix_clips,vocoder_clips;
singer_role #(.COEFF_FILE("COEFF_PATH"))dut(.*);
integer frames=0,t;
always @(negedge clk)if(audio_valid)begin
 frames=frames+1;
 if(left_out!==frames*25600||right_out!==-frames*25600)$fatal(1,"ordered dry frame %0d",frames);
end
initial begin
 repeat(4)@(negedge clk);rst=0;@(negedge clk);event_valid=1;@(negedge clk);event_valid=0;
 repeat(70)@(negedge clk);
 // A full band frame completes966 cycles after tick0; next light frame72
 // cycles after tick1041. Their PCM arrivals are only147 cycles apart.
 for(t=0;t<2500;t=t+1)begin
  sample_tick=t==0||t==1041;
  frame_valid=t==966||t==1113;
  if(t==966)begin band_left=100;band_right=-100;end
  if(t==1113)begin band_left=200;band_right=-200;end
  @(negedge clk);
 end
 if(frames!=2||dropped_frames)$fatal(1,"load-transition drop frames=%0d dropped=%0d",frames,dropped_frames);
 panic=1;@(negedge clk);
 if(left_out!==0||right_out!==0||audio_valid!==0)$fatal(1,"panic");
 $display("PASS full-to-light render schedule:147cycle PCM gap,2 ordered frames,no drops,panic");$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
