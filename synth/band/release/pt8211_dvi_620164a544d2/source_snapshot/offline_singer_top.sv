// Microphone pins must be supplied from the actual board/ADC wiring.
module offline_singer_top(input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN);
 band_microphone_top band(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
 .microphone_stale(),.mic_received(),.mic_repeated(),.mic_skipped(),.mic_timeouts());
endmodule
