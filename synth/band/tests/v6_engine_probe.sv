module v6_engine_probe(input clk,output valid,output signed[15:0]left,right,
 output[31:0]deadline,clips,drops,underruns,output[15:0]voices,cycles,output playing);
 band_stage_pt8211_engine dut(.clk(clk),.uart_rx_pin(1'b1),.uart_tx_pin(),
 .HP_BCK(),.HP_WS(),.HP_DIN(),.PA_EN(),.adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),
 .local_play(1'b0),.local_stop(1'b0),.local_panic(1'b0),.local_root(4'd0),.local_minor(1'b0),
 .local_held(),.external_sample_tick(1'b0),.pcm_left(left),.pcm_right(right),.pcm_valid(valid),
 .reset_out(),.panic_out(),.microphone_sample(24'sd0),.singer_mix(7'd80),.dac_dropped(drops),.dac_underruns(underruns),
 .singer_gate(),.singer_note(),.transport_sample_tick(),.audio_stop(),.pedal_raw(4'd0),.pedal_down(),.deferred_returns());
 assign deadline=dut.deadline_miss;assign clips=dut.clips;assign voices=dut.active_voices;
 assign cycles=dut.render_cycles;assign playing=dut.playing;
endmodule
