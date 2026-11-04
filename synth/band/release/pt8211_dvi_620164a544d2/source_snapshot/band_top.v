// Verified seven-pin board interface. Optional soldered peripherals remain isolated.
module band_top(input clk,input uart_rx_pin,output uart_tx_pin,
 output HP_BCK,HP_WS,HP_DIN,output PA_EN);
 band_board_engine engine(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
  .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
  .adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
  .local_play(1'b0),.local_stop(1'b0),.local_panic(1'b0),.local_root(4'd0),.local_minor(1'b0),.local_held(),
  .external_sample_tick(1'b0),.pcm_left(),.pcm_right(),.pcm_valid(),.reset_out(),.panic_out());
endmodule
