// Soldered-peripheral integration target. No pin assignment or board certification yet.
// Requires a real 24.576 MHz audio clock and a compatible external I2S DAC.
// Transport is 24 bits; the current band/effect mix remains 16 significant bits.
module workstation_top(
 input wire clk,audio_clk,uart_rx_pin,output wire uart_tx_pin,
 input wire [9:0] adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire play_button,stop_button,panic_button,input wire [3:0] root,input wire minor_mode,
 output wire dac_bclk,dac_lrclk,dac_data,output wire [3:0] seat_led
);
 wire [63:0] held;wire sample_tick,valid,rst,panic;wire signed [15:0] left,right;
 wire [31:0] dropped,underruns;
 band_board_engine #(.LOCAL_INPUTS(1),.EXTERNAL_AUDIO(1)) engine(
  .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),.HP_BCK(),.HP_WS(),.HP_DIN(),.PA_EN(),
  .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
  .local_play(play_button),.local_stop(stop_button),.local_panic(panic_button),.local_root(root),.local_minor(minor_mode),.local_held(held),
  .external_sample_tick(sample_tick),.pcm_left(left),.pcm_right(right),.pcm_valid(valid),.reset_out(rst),.panic_out(panic));
 audio_i2s_bridge audio(clk,audio_clk,rst,panic,valid,{left,8'd0},{right,8'd0},sample_tick,dac_bclk,dac_lrclk,dac_data,dropped,underruns);
 assign seat_led={|held[63:48],|held[47:32],|held[31:16],|held[15:0]};
endmodule
