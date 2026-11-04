// Three-clock PCM analysis/display boundary. Reader owns one complete spectrum
// until release_frame. A slow reader stalls analysis but cannot stall audio.
module pcm_spectrum_buffered #(
 parameter LOG_N=11,parameter TWIDDLE_FILE="fft_twiddle_2048.mem",parameter WINDOW_FILE="hann_2048.mem"
)(
 input audio_clk,analysis_clk,display_clk,rst,pcm_valid,
 input signed[15:0]pcm_left,pcm_right,
 input read_enable,input[LOG_N-1:0]read_address,input release_frame,
 output frame_available,read_valid,output signed[15:0]read_real,read_imag,
 output[31:0]frame_number,last_sample,output[16:0]peak_left,peak_right,
 output[31:0]visualization_skipped,fft_clips,rejected_bins
);
 wire valid,ready;wire[LOG_N-1:0]bin;wire signed[15:0]re,im;
 wire[31:0]frame,last;wire[16:0]pl,pr;
 pcm_spectrum #(.LOG_N(LOG_N),.TWIDDLE_FILE(TWIDDLE_FILE),.WINDOW_FILE(WINDOW_FILE)) analysis(
 audio_clk,analysis_clk,rst,pcm_valid,pcm_left,pcm_right,
 valid,ready,bin,re,im,frame,last,pl,pr,visualization_skipped,fft_clips);
 spectrum_snapshot #(.LOG_N(LOG_N)) display_frame(
 analysis_clk,display_clk,rst,valid,ready,bin,re,im,frame,last,pl,pr,
 read_enable,read_address,release_frame,frame_available,read_valid,read_real,read_imag,
 frame_number,last_sample,peak_left,peak_right,rejected_bins);
endmodule
