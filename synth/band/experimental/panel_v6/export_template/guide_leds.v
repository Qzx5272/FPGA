// LED pitch-class guide from actual accepted score events. No predicted audio.
module guide_leds #(parameter HOLD_SAMPLES=4800)(
 input wire clk,rst,panic,sample_tick,playing,
 input wire note_on,input wire[6:0] note,
 output reg[11:0] pitch_leds,output reg beat_led,
 input wire beat_tick
);
 reg[31:0] remaining;
 always @(posedge clk)begin
  if(rst||panic||!playing)begin pitch_leds<=0;beat_led<=0;remaining<=0;end
  else begin
   if(sample_tick&&remaining!=0)begin remaining<=remaining-1'b1;if(remaining==1)begin pitch_leds<=0;beat_led<=0;end end
   if(beat_tick)begin beat_led<=1;remaining<=HOLD_SAMPLES;end
   if(note_on)begin pitch_leds[note%12]<=1;remaining<=HOLD_SAMPLES;end
  end
 end
endmodule
