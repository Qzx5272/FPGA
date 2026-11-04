// Physical constraints and external timing must be supplied before building.
module band_stage_physical_top(input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 input [9:0] adc_dout,output adc_cs_n,adc_sclk,adc_din,
 input play_button,stop_button,panic_button,input [3:0] root,input minor_mode,
 input [3:0] pedal_raw,output [3:0] seat_led);
 band_stage_top band(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
 .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(play_button),.stop_button(stop_button),.panic_button(panic_button),.root(root),.minor_mode(minor_mode),
 .pedal_raw(pedal_raw),.seat_led(seat_led),.pedal_down(),.deferred_returns(),
 .microphone_stale(),.mic_received(),.mic_repeated(),.mic_skipped(),.mic_timeouts());
endmodule
