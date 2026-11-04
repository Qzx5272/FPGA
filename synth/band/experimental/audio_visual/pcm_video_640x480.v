// Complete logical parallel RGB video source. HDMI serialization/pins are external.
module pcm_video_640x480 #(
 parameter TWIDDLE_FILE="fft_twiddle_2048.mem",parameter WINDOW_FILE="hann_2048.mem"
)(
 input audio_clk,analysis_clk,pixel_clk,rst,pcm_valid,
 input signed[15:0]pcm_left,pcm_right,
 output[23:0]rgb,output hsync_n,vsync_n,active_video,display_valid,
 output[31:0]displayed_frames,visualization_skipped,fft_clips,rejected_bins
);
 wire[9:0]x,y;wire frame_boundary;wire[23:0]active_rgb;
 video_timing_640x480 timing(pixel_clk,rst,x,y,active_video,hsync_n,vsync_n,frame_boundary);
 pcm_spectrum_display #(.TWIDDLE_FILE(TWIDDLE_FILE),.WINDOW_FILE(WINDOW_FILE)) display(
  .audio_clk(audio_clk),.analysis_clk(analysis_clk),.display_clk(pixel_clk),.rst(rst),
  .pcm_valid(pcm_valid),.pcm_left(pcm_left),.pcm_right(pcm_right),
  .frame_start(frame_boundary),.pixel_x(x),.pixel_y(y),.rgb(active_rgb),
  .display_valid(display_valid),.displayed_frames(displayed_frames),
  .visualization_skipped(visualization_skipped),.fft_clips(fft_clips),.rejected_bins(rejected_bins));
 assign rgb=active_video?active_rgb:24'd0;
endmodule
