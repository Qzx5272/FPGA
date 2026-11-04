// Experimental complete transport integration. Microphone pins/clock source
// are unspecified: this is NOT a board-programmable top or an ASRC.
module band_stage_top #(parameter PEDAL_STABLE_CYCLES=250000,parameter COEFF_FILE="coeffs.mem",parameter MIC_TIMEOUT=5000000)(
 input wire clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 input wire [9:0] adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire play_button,stop_button,panic_button,input wire [3:0] root,input wire minor_mode,
 input wire [3:0] pedal_raw,output wire [3:0] pedal_down,seat_led,output wire [15:0] deferred_returns,
 output wire microphone_stale,
 output wire [31:0] mic_received,mic_repeated,mic_skipped,mic_timeouts
);
 wire [63:0] held;assign seat_led={|held[63:48],|held[47:32],|held[31:16],|held[15:0]};
 wire rst,panic,tick;wire [4:0] selected_scale;
 stable_selector selector(clk,rst,{minor_mode,root},selected_scale);wire signed[23:0]microphone;
 microphone_capture #(.TIMEOUT_CYCLES(MIC_TIMEOUT)) input_audio(
  .core_clk(clk),.rst(rst),.panic(panic),.bck(mic_bck),.ws(mic_ws),.sd(mic_sd),.sample_tick(tick),
  .microphone_sample(microphone),.input_stale(microphone_stale),.received_frames(mic_received),
  .repeated_frames(mic_repeated),.skipped_frames(mic_skipped),.timeouts(mic_timeouts),
  .framing_errors_bck(),.overruns_bck());
 // Loss mutes the singer through its existing bounded gain slew; band tracks
 // continue. The vocoder filter history is not claimed to be reset by this.
 band_stage_engine #(.LOCAL_INPUTS(1),.COEFF_FILE(COEFF_FILE),.PEDAL_STABLE_CYCLES(PEDAL_STABLE_CYCLES)) engine(
  .clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
  .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
  .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
  .local_play(play_button),.local_stop(stop_button),.local_panic(panic_button),.local_root(selected_scale[3:0]),.local_minor(selected_scale[4]),.local_held(held),
  .external_sample_tick(1'b0),.pcm_left(),.pcm_right(),.pcm_valid(),.reset_out(rst),.panic_out(panic),
  .microphone_sample(microphone),.singer_mix(microphone_stale?7'd0:7'd127),
  .dac_dropped(),.dac_underruns(),.singer_gate(),.singer_note(),.transport_sample_tick(tick),.pedal_raw(pedal_raw),.pedal_down(pedal_down),.deferred_returns(deferred_returns));
endmodule
