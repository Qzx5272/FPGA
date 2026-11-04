// Board-only shell for the currently connected hardware.
// Expansion modules remain in the full workstation export. Rebuild a separately
// constrained shell to enable real microphone/ADC/pedal connections.
module board_pt8211_dvi_top(
 input wire clk,uart_rx_pin,
 output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 output wire tmds_clk_p,tmds_clk_n,
 output wire[2:0]tmds_d_p,tmds_d_n
);
 offline_workstation_top workstation(
  .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
  .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
  .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),
  .adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
  .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),
  .root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),.seat_led(),
  .tmds_clk_p(tmds_clk_p),.tmds_clk_n(tmds_clk_n),
  .tmds_d_p(tmds_d_p),.tmds_d_n(tmds_d_n),.video_valid()
 );
endmodule
