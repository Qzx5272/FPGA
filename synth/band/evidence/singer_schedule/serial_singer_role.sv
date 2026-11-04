`timescale 1ns/1ps
// Integratable singer role: authorized event identities -> note priority ->
// band-limited carrier -> microphone vocoder -> delayed stereo band mix.
// Raw input authorization and asynchronous microphone transport remain upstream.
module singer_role #(parameter COEFF_FILE="coeffs.mem")(
 input wire clk,rst,panic,event_valid,output wire event_ready,
 input wire [1:0] event_kind,input wire [7:0] event_source,event_contact,
 input wire [3:0] event_part,input wire [31:0] event_epoch,event_serial,
 input wire [6:0] event_note,event_velocity,
 input wire frame_valid,output wire frame_ready,
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
 vocoder_band_lane #(.COEFF_FILE(COEFF_FILE)) audio(
  .clk(clk),.rst(rst),.panic(panic),.frame_valid(frame_valid),.frame_ready(frame_ready),
  .band_left(band_left),.band_right(band_right),.mic_in(mic_in),
  .gate(singer_gate),.note(singer_note),.velocity(singer_velocity),.voice_gain(voice_gain),
  .left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),
  .dropped_frames(dropped_frames),.mix_clips(mix_clips),.vocoder_clips(vocoder_clips));
endmodule
