`timescale 1ns/1ps
// Complete monophonic electronic-singer audio lane, before board/ownership wiring.
// Musical controls come from the owning human or machine singer role.
// Band PCM, microphone and control snapshot are captured as one frame.
module vocoder_band_lane #(parameter COEFF_FILE="coeffs.mem") (
 input wire clk,rst,panic,frame_valid,
 output wire frame_ready,
 input wire signed [15:0] band_left,band_right,
 input wire signed [23:0] mic_in,
 input wire gate,input wire [6:0] note,velocity,voice_gain,
 output wire signed [23:0] left_out,right_out,
 output wire audio_valid,
 output reg [31:0] dropped_frames,
 output wire [31:0] mix_clips,vocoder_clips
);
 reg active;
 reg signed [15:0] held_left,held_right;
 reg signed [23:0] held_mic;
 reg [6:0] held_gain;
 wire carrier_ready,carrier_valid,insert_ready;
 wire signed [23:0] carrier;
 wire [31:0] carrier_drops,insert_drops;
 assign frame_ready=!rst&&!panic&&!active&&carrier_ready&&insert_ready;
 vocoder_carrier source(clk,rst,panic,frame_valid&&frame_ready,gate,note,velocity,
  carrier_ready,carrier_valid,carrier,carrier_drops);
 band_vocoder_insert #(.COEFF_FILE(COEFF_FILE)) insert(
  .clk(clk),.rst(rst),.panic(panic),.frame_valid(carrier_valid),.frame_ready(insert_ready),
  .band_left(held_left),.band_right(held_right),.carrier_in(carrier),.mic_in(held_mic),.voice_gain(held_gain),
  .left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),
  .dropped_frames(insert_drops),.mix_clips(mix_clips),.vocoder_clips(vocoder_clips));
 always @(posedge clk)begin
  if(rst||panic)begin active<=0;held_left<=0;held_right<=0;held_mic<=0;held_gain<=0;dropped_frames<=0;end
  else begin
   if(frame_valid&&frame_ready)begin
    active<=1;held_left<=band_left;held_right<=band_right;held_mic<=mic_in;held_gain<=voice_gain;
   end
   if(audio_valid)active<=0;
   if(frame_valid&&!frame_ready&&dropped_frames!=32'hffffffff)dropped_frames<=dropped_frames+1'b1;
  end
 end
endmodule
