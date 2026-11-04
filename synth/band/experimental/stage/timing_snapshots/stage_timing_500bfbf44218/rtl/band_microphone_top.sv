// Experimental complete transport integration. Microphone pins/clock source
// are unspecified: this is NOT a board-programmable top or an ASRC.
module band_microphone_top #(parameter COEFF_FILE="coeffs.mem",parameter MIC_TIMEOUT=5000000)(
 input wire clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 output wire microphone_stale,
 output wire [31:0] mic_received,mic_repeated,mic_skipped,mic_timeouts
);
 wire rst,panic,tick;wire signed[23:0]microphone;
 microphone_capture #(.TIMEOUT_CYCLES(MIC_TIMEOUT)) input_audio(
  .core_clk(clk),.rst(rst),.panic(panic),.bck(mic_bck),.ws(mic_ws),.sd(mic_sd),.sample_tick(tick),
  .microphone_sample(microphone),.input_stale(microphone_stale),.received_frames(mic_received),
  .repeated_frames(mic_repeated),.skipped_frames(mic_skipped),.timeouts(mic_timeouts),
  .framing_errors_bck(),.overruns_bck());
 // Loss mutes the singer through its existing bounded gain slew; band tracks
 // continue. The vocoder filter history is not claimed to be reset by this.
 band_singer_board_engine #(.COEFF_FILE(COEFF_FILE)) engine(
  .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
  .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
  .adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
  .local_play(1'b0),.local_stop(1'b0),.local_panic(1'b0),.local_root(4'd0),.local_minor(1'b0),.local_held(),
  .external_sample_tick(1'b0),.pcm_left(),.pcm_right(),.pcm_valid(),.reset_out(rst),.panic_out(panic),
  .microphone_sample(microphone),.singer_mix(microphone_stale?7'd0:7'd127),
  .dac_dropped(),.dac_underruns(),.singer_gate(),.singer_note(),.transport_sample_tick(tick));
endmodule
