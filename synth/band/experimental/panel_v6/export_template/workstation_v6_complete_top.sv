// Complete source-only integration: I2S instrument + physical panel + DVI/FFT.
// No CST exists for expansion pins. Do not program until pins/timing are reviewed.
module workstation_v6_complete_top(
 input wire clk,audio_clk,pc_rx,ble_rx,usb_rx,output wire pc_tx,ble_tx,usb_tx,
 input wire[7:0]enc_a,enc_b,input wire[3:0]pedal_raw,input wire[9:0]adc_dout,
 output wire adc_cs_n,adc_sclk,adc_din,
 input wire mic_bck,mic_ws,mic_sd,play_button,stop_button,panic_button,song_next,
 output wire i2s_bck,i2s_ws,i2s_sd,output wire[11:0]guide_pitch,output wire guide_bar,
 output wire[3:0]panel_part,output wire[111:0]panel_values,
 output wire clock_fault,microphone_stale,output wire[31:0]drops,underruns,
 output wire tmds_clk_p,tmds_clk_n,output wire[2:0]tmds_d_p,tmds_d_n,output wire video_valid);
 wire signed[15:0]left,right;wire pcm_valid,reset_audio,stop_audio;
 workstation_expansion_top audio(
 .clk(clk),.audio_clk(audio_clk),.pc_rx(pc_rx),.ble_rx(ble_rx),.usb_rx(usb_rx),.pc_tx(pc_tx),.ble_tx(ble_tx),.usb_tx(usb_tx),
 .enc_a(enc_a),.enc_b(enc_b),.pedal_raw(pedal_raw),.adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),.play_button(play_button),.stop_button(stop_button),.panic_button(panic_button),.song_next(song_next),
 .i2s_bck(i2s_bck),.i2s_ws(i2s_ws),.i2s_sd(i2s_sd),.guide_pitch(guide_pitch),.guide_bar(guide_bar),.panel_part(panel_part),.panel_values(panel_values),
 .clock_fault(clock_fault),.microphone_stale(microphone_stale),.drops(drops),.underruns(underruns),
 .monitor_left(left),.monitor_right(right),.monitor_valid(pcm_valid),.monitor_reset(reset_audio),.monitor_stop(stop_audio));
 wire pixel_clk,video_ready,video_active,hsync_n,vsync_n;wire[23:0]rgb;
 reg[3:0]por=4'hf;always @(posedge clk)por<={por[2:0],1'b0};
 gowin_dvi_output video_output(.clk50(clk),.resetn(!por[3]),.active_video(video_active),.hsync_n(hsync_n),.vsync_n(vsync_n),.rgb(rgb),
 .pixel_clk(pixel_clk),.video_ready(video_ready),.tmds_clk_p(tmds_clk_p),.tmds_clk_n(tmds_clk_n),.tmds_d_p(tmds_d_p),.tmds_d_n(tmds_d_n));
 workstation_v6_video_feedback feedback(clk,pixel_clk,reset_audio||stop_audio||!video_ready,pcm_valid,left,right,
 rgb,hsync_n,vsync_n,video_active,video_valid);
endmodule

module workstation_v6_video_feedback(
 input wire clk,pixel_clk,rst,pcm_valid,input wire signed[15:0]left,right,
 output wire[23:0]rgb,output wire hsync_n,vsync_n,active,display_valid);
 wire display_read,display_release,available,read_valid;wire[10:0]address;
 wire signed[15:0]real_bin,imag_bin;
 pcm_spectrum_buffered analyzer(.audio_clk(clk),.analysis_clk(clk),.display_clk(pixel_clk),.rst(rst),
 .pcm_valid(pcm_valid),.pcm_left(left),.pcm_right(right),.read_enable(display_read),.read_address(address),.release_frame(display_release),
 .frame_available(available),.read_valid(read_valid),.read_real(real_bin),.read_imag(imag_bin),
 .frame_number(),.last_sample(),.rejected_bins(),.peak_left(),.peak_right(),.visualization_skipped(),.fft_clips());
 (* ASYNC_REG="TRUE" *)reg[1:0]release_reset=2'b11;
 always @(posedge pixel_clk or posedge rst)if(rst)release_reset<=2'b11;else release_reset<={release_reset[0],1'b0};
 wire[9:0]x,y;wire boundary;wire[23:0]bar_rgb;
 video_timing_640x480 raster(pixel_clk,release_reset[1],x,y,active,hsync_n,vsync_n,boundary);
 spectrum_bars bars(.clk(pixel_clk),.rst(release_reset[1]),.frame_start(boundary),.pixel_x(x),.pixel_y(y),
 .frame_available(available),.read_valid(read_valid),.read_real(real_bin),.read_imag(imag_bin),
 .read_enable(display_read),.read_address(address),.release_frame(display_release),.rgb(bar_rgb),.display_valid(display_valid),.displayed_frames());
 assign rgb=active?bar_rgb:24'd0;
endmodule
