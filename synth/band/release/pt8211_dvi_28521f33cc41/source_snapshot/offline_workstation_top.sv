// Source-only integration boundary; all new physical pins/timing required.
module offline_workstation_top(input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 input[9:0]adc_dout,output adc_cs_n,adc_sclk,adc_din,
 input play_button,stop_button,panic_button,input[3:0]root,input minor_mode,
 input[3:0]pedal_raw,output[3:0]seat_led,
 output tmds_clk_p,tmds_clk_n,output[2:0]tmds_d_p,tmds_d_n,output video_valid);
 wire pixel_clk,video_ready,video_active,video_hsync_n,video_vsync_n;
 wire[23:0]video_rgb;
 reg[3:0]video_por=4'hf;
 always @(posedge clk)video_por<={video_por[2:0],1'b0};
 gowin_dvi_output video_output(.clk50(clk),.resetn(!video_por[3]),
  .active_video(video_active),.hsync_n(video_hsync_n),.vsync_n(video_vsync_n),.rgb(video_rgb),
  .pixel_clk(pixel_clk),.video_ready(video_ready),.tmds_clk_p(tmds_clk_p),.tmds_clk_n(tmds_clk_n),
  .tmds_d_p(tmds_d_p),.tmds_d_n(tmds_d_n));
 
 band_workstation_pt8211_top band(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),
 .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(play_button),.stop_button(stop_button),.panic_button(panic_button),.root(root),.minor_mode(minor_mode),
 .pedal_raw(pedal_raw),.seat_led(seat_led),
 .analysis_clk(clk),.pixel_clk(pixel_clk),.video_link_ready(video_ready),.video_rgb(video_rgb),.video_hsync_n(video_hsync_n),
 .video_vsync_n(video_vsync_n),.video_active(video_active),.video_valid(video_valid),.video_frame_count());
endmodule
