`timescale 1ns/1ps
// Integratable singer role: authorized event identities -> note priority ->
// band-limited carrier -> microphone vocoder -> delayed stereo band mix.
// Raw input authorization and asynchronous microphone transport remain upstream.
module singer_role #(parameter COEFF_FILE="coeffs.mem")(
 input wire clk,rst,panic,event_valid,output wire event_ready,
 input wire [1:0] event_kind,input wire [7:0] event_source,event_contact,
 input wire [3:0] event_part,input wire [31:0] event_epoch,event_serial,
 input wire [6:0] event_note,event_velocity,
 input wire sample_tick,frame_valid,output wire frame_ready,
 input wire signed [15:0] band_left,band_right,
 input wire signed [23:0] mic_in,input wire [6:0] voice_gain,
 output wire signed [23:0] left_out,right_out,output wire audio_valid,
 output wire singer_gate,output wire [6:0] singer_note,
 output wire [31:0] rejected,stale_off,duplicates,dropped_frames,mix_clips,vocoder_clips
);
 wire [6:0] singer_velocity;
 singer_note_control notes(clk,rst,panic,event_valid,event_ready,event_kind,event_source,event_contact,
  event_part,event_epoch,event_serial,event_note,event_velocity,singer_gate,singer_note,singer_velocity,
  rejected,stale_off,duplicates);
 // Precompute carrier alongside band rendering, not after band PCM arrives.
 // The independent completions are joined once; rapid full-to-idle transitions
 // then require only the125cycle vocoder/mix service, not199cycles.
 wire carrier_ready,carrier_valid,insert_ready;
 wire signed [23:0] carrier_sample;
 wire [31:0] carrier_drops,insert_drops;
 reg band_pending,carrier_pending;
 reg signed [15:0] held_left,held_right;
 reg signed [23:0] held_mic,held_carrier;
 reg [6:0] held_gain;
 reg [31:0] join_drops;
 wire join_valid=band_pending&&carrier_pending&&insert_ready;
 assign frame_ready=!rst&&!panic&&!band_pending;
 assign dropped_frames=join_drops+carrier_drops+insert_drops;
 vocoder_carrier source(clk,rst,panic,sample_tick,singer_gate,singer_note,singer_velocity,
  carrier_ready,carrier_valid,carrier_sample,carrier_drops);
 always @(posedge clk)begin
  if(rst||panic)begin
   band_pending<=0;carrier_pending<=0;held_left<=0;held_right<=0;held_mic<=0;held_carrier<=0;held_gain<=0;join_drops<=0;
  end else begin
   if(join_valid)begin band_pending<=0;carrier_pending<=0;end
   if(frame_valid&&frame_ready)begin
    band_pending<=1;held_left<=band_left;held_right<=band_right;held_mic<=mic_in;held_gain<=voice_gain;
   end
   if(carrier_valid)begin carrier_pending<=1;held_carrier<=carrier_sample;end
   if((frame_valid&&!frame_ready)||(carrier_valid&&carrier_pending&&!join_valid))
    if(join_drops!=32'hffffffff)join_drops<=join_drops+1'b1;
  end
 end
 band_vocoder_insert #(.COEFF_FILE(COEFF_FILE)) audio(
  .clk(clk),.rst(rst),.panic(panic),.frame_valid(join_valid),.frame_ready(insert_ready),
  .band_left(held_left),.band_right(held_right),.mic_in(held_mic),
  .carrier_in(held_carrier),.voice_gain(held_gain),
  .left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),
  .dropped_frames(insert_drops),.mix_clips(mix_clips),.vocoder_clips(vocoder_clips));
endmodule
