// PT8211 integration; core-clock audio queue, no external DAC clock.
module band_workstation_pt8211_top #(parameter TWIDDLE_FILE="fft_twiddle_2048.mem",parameter WINDOW_FILE="hann_2048.mem",parameter AUDIO_CLOCK_TIMEOUT=50000,parameter PEDAL_STABLE_CYCLES=250000,parameter COEFF_FILE="coeffs.mem",parameter MIC_TIMEOUT=5000000)(
 input wire clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 output wire[31:0]dac_dropped,dac_underruns,
 input wire [9:0] adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire play_button,stop_button,panic_button,input wire [3:0] root,input wire minor_mode,
 input wire [3:0] pedal_raw,output wire [3:0] pedal_down,seat_led,output wire [15:0] deferred_returns,
 output wire microphone_stale,
 output wire [31:0] mic_received,mic_repeated,mic_skipped,mic_timeouts,
 input wire analysis_clk,pixel_clk,video_link_ready,
 output wire[23:0]video_rgb,output wire video_hsync_n,video_vsync_n,video_active,video_valid,
 output wire[31:0]video_frame_count,
 output wire display_available,spectrum_valid,output wire signed[15:0]spectrum_real,spectrum_imag,
 output wire[31:0]spectrum_frame,spectrum_last_sample,visualization_skipped,fft_clips,rejected_bins,
 output wire[16:0]spectrum_peak_left,spectrum_peak_right
);
 wire display_clk=pixel_clk;wire display_read,display_release;wire[10:0]display_address;
 wire [63:0] held;assign seat_led={|held[63:48],|held[47:32],|held[31:16],|held[15:0]};
 wire signed[15:0]pcm_left,pcm_right;wire pcm_valid,audio_stop;
 wire rst,panic,tick;wire [4:0] selected_scale;
 stable_selector selector(clk,rst,{minor_mode,root},selected_scale);wire signed[23:0]microphone;
 microphone_capture #(.TIMEOUT_CYCLES(MIC_TIMEOUT)) input_audio(
  .core_clk(clk),.rst(rst),.panic(panic),.bck(mic_bck),.ws(mic_ws),.sd(mic_sd),.sample_tick(tick),
  .microphone_sample(microphone),.input_stale(microphone_stale),.received_frames(mic_received),
  .repeated_frames(mic_repeated),.skipped_frames(mic_skipped),.timeouts(mic_timeouts),
  .framing_errors_bck(),.overruns_bck());
 // Loss mutes the singer through its existing bounded gain slew; band tracks
 // continue. The vocoder filter history is not claimed to be reset by this.
 band_stage_pt8211_engine #(.EXTERNAL_AUDIO(0),.LOCAL_INPUTS(1),.COEFF_FILE(COEFF_FILE),.PEDAL_STABLE_CYCLES(PEDAL_STABLE_CYCLES)) engine(
  .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
  .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
  .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
  .local_play(play_button),.local_stop(stop_button),.local_panic(panic_button),.local_root(selected_scale[3:0]),.local_minor(selected_scale[4]),.local_held(held),
  .external_sample_tick(1'b0),.pcm_left(pcm_left),.pcm_right(pcm_right),.pcm_valid(pcm_valid),.reset_out(rst),.panic_out(panic),
  .microphone_sample(microphone),.singer_mix(microphone_stale?7'd0:7'd127),
  .dac_dropped(dac_dropped),.dac_underruns(dac_underruns),.singer_gate(),.singer_note(),.transport_sample_tick(tick),.audio_stop(audio_stop),.pedal_raw(pedal_raw),.pedal_down(pedal_down),.deferred_returns(deferred_returns));
 pcm_spectrum_buffered #(.TWIDDLE_FILE(TWIDDLE_FILE),.WINDOW_FILE(WINDOW_FILE)) analyzer(
 .audio_clk(clk),.analysis_clk(analysis_clk),.display_clk(display_clk),.rst(rst||panic||audio_stop||!video_link_ready),
 .pcm_valid(pcm_valid),.pcm_left(pcm_left),.pcm_right(pcm_right),
 .read_enable(display_read),.read_address(display_address),.release_frame(display_release),
 .frame_available(display_available),.read_valid(spectrum_valid),.read_real(spectrum_real),.read_imag(spectrum_imag),
 .frame_number(spectrum_frame),.last_sample(spectrum_last_sample),.rejected_bins(rejected_bins),
 .peak_left(spectrum_peak_left),.peak_right(spectrum_peak_right),
 .visualization_skipped(visualization_skipped),.fft_clips(fft_clips));
 // Asynchronous assertion, two-pixel-clock release including stopped clocks.
 wire video_async_reset=rst||panic||audio_stop||!video_link_ready;
 (* ASYNC_REG="TRUE" *)reg[1:0]video_reset_hold=2'b11;
 always @(posedge pixel_clk or posedge video_async_reset)
  if(video_async_reset)video_reset_hold<=2'b11;
  else video_reset_hold<={video_reset_hold[0],1'b0};
 wire video_reset=video_reset_hold[1];
 wire[9:0]video_x,video_y;wire video_boundary;wire[23:0]bar_rgb;
 video_timing_640x480 raster(pixel_clk,video_reset,video_x,video_y,
  video_active,video_hsync_n,video_vsync_n,video_boundary);
 spectrum_bars bars(.clk(pixel_clk),.rst(video_reset),.frame_start(video_boundary),
  .pixel_x(video_x),.pixel_y(video_y),.frame_available(display_available),
  .read_valid(spectrum_valid),.read_real(spectrum_real),.read_imag(spectrum_imag),
  .read_enable(display_read),.read_address(display_address),.release_frame(display_release),
  .rgb(bar_rgb),.display_valid(video_valid),.displayed_frames(video_frame_count));
 assign video_rgb=video_active?bar_rgb:24'd0;
endmodule
