`timescale 1ns/1ps
// Band PCM insert with explicit one-extra-audio-frame latency budget.
// Start at band PCM completion, finish before the NEXT band PCM completion.
// The DAC must consume this delayed stream, never mix it with undelayed PCM.
// carrier_in belongs to the same musical frame as band_left/right.
// mic_in is a core-clock sample supplied by the input CDC / rate policy.
module band_vocoder_insert #(parameter COEFF_FILE="coeffs.mem") (
 input wire clk,rst,panic,frame_valid,
 output wire frame_ready,
 input wire signed [15:0] band_left,band_right,
 input wire signed [23:0] carrier_in,mic_in,
 input wire [6:0] voice_gain,
 output reg signed [23:0] left_out,right_out,
 output reg audio_valid,
 output reg [31:0] dropped_frames,mix_clips,
 output wire [31:0] vocoder_clips
);
 wire core_ready,core_valid;wire signed [23:0] voice;
 wire [31:0] rejected_unused;
 reg active;
 reg signed [23:0] held_left,held_right;
 reg [6:0] held_gain,smooth_gain;
 wire [6:0] next_gain=smooth_gain<voice_gain ? smooth_gain+1'b1 : smooth_gain>voice_gain ? smooth_gain-1'b1 : smooth_gain;
 reg signed [31:0] scaled_voice;
 reg mix_pending;
 wire signed [31:0] voice_product=voice*$signed({1'b0,held_gain});
 wire signed [32:0] mix_left=$signed(held_left)+(scaled_voice>>>7);
 wire signed [32:0] mix_right=$signed(held_right)+(scaled_voice>>>7);
 wire clipped=(mix_left>8388607)||(mix_left < -8388608)||(mix_right>8388607)||(mix_right < -8388608);
 assign frame_ready=!rst&&!panic&&!active&&core_ready;
 vocoder_core #(.COEFF_FILE(COEFF_FILE)) voice_core(
  .clk_in(clk),.rst_in(rst||panic),.valid_in(frame_valid&&frame_ready),
  .carrier_sample_in(carrier_in),.modulator_sample_in(mic_in),
  .ready_out(core_ready),.valid_out(core_valid),.sample_out(voice),
  .clip_count(vocoder_clips),.rejected_count(rejected_unused));
 function signed [23:0] saturate(input signed [32:0] x);
  begin saturate=x>8388607 ? 24'sh7fffff : x < -8388608 ? 24'sh800000 : x[23:0];end
 endfunction
 always @(posedge clk)begin
  if(rst||panic)begin
   active<=0;held_left<=0;held_right<=0;held_gain<=0;smooth_gain<=0;scaled_voice<=0;
   mix_pending<=0;audio_valid<=0;left_out<=0;right_out<=0;dropped_frames<=0;mix_clips<=0;
  end else begin
   audio_valid<=0;mix_pending<=0;
   if(frame_valid&&frame_ready)begin
    held_left<={band_left,8'd0};held_right<={band_right,8'd0};
    // At48kHz a complete0..127 fade takes2.65ms. Panic remains immediate.
    held_gain<=next_gain;smooth_gain<=next_gain;active<=1;
   end
   if(frame_valid&&!frame_ready&&dropped_frames!=32'hffffffff)dropped_frames<=dropped_frames+1'b1;
   if(core_valid)begin scaled_voice<=voice_product;mix_pending<=1;end
   if(mix_pending)begin
    left_out<=saturate(mix_left);right_out<=saturate(mix_right);audio_valid<=1;active<=0;
    if(clipped&&mix_clips!=32'hffffffff)mix_clips<=mix_clips+1'b1;
   end
  end
 end
endmodule
