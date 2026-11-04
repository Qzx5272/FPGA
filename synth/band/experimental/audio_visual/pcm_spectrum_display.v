// PCM -> Hann/2048 FFT -> frozen spectrum -> frame-swapped pixel bars.
// Video timing/encoding is supplied by the caller; audio has no ready input.
module pcm_spectrum_display #(
 parameter TWIDDLE_FILE="fft_twiddle_2048.mem",parameter WINDOW_FILE="hann_2048.mem"
)(
 input audio_clk,analysis_clk,display_clk,rst,pcm_valid,
 input signed[15:0]pcm_left,pcm_right,
 input frame_start,input[9:0]pixel_x,pixel_y,
 output[23:0]rgb,output display_valid,output[31:0]displayed_frames,
 output[31:0]visualization_skipped,fft_clips,rejected_bins
);
 wire read_enable,release_frame,frame_available,read_valid;
 wire[10:0]read_address;wire signed[15:0]read_real,read_imag;
 pcm_spectrum_buffered #(.TWIDDLE_FILE(TWIDDLE_FILE),.WINDOW_FILE(WINDOW_FILE)) analyzer(
  .audio_clk(audio_clk),.analysis_clk(analysis_clk),.display_clk(display_clk),.rst(rst),
  .pcm_valid(pcm_valid),.pcm_left(pcm_left),.pcm_right(pcm_right),
  .read_enable(read_enable),.read_address(read_address),.release_frame(release_frame),
  .frame_available(frame_available),.read_valid(read_valid),.read_real(read_real),.read_imag(read_imag),
  .visualization_skipped(visualization_skipped),.fft_clips(fft_clips),.rejected_bins(rejected_bins));
 spectrum_bars view(.clk(display_clk),.rst(rst),.frame_start(frame_start),.pixel_x(pixel_x),.pixel_y(pixel_y),
  .frame_available(frame_available),.read_valid(read_valid),.read_real(read_real),.read_imag(read_imag),
  .read_enable(read_enable),.read_address(read_address),.release_frame(release_frame),
  .rgb(rgb),.display_valid(display_valid),.displayed_frames(displayed_frames));
endmodule
