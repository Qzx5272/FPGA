// No physical pins assigned. Needs a verified24.576MHz audio clock.
module workstation_expansion_top #(parameter SHARED_MIC_CLOCK=1)(
 input wire clk,audio_clk,pc_rx,ble_rx,usb_rx,output wire pc_tx,ble_tx,usb_tx,
 input wire[7:0]enc_a,enc_b,input wire[3:0]pedal_raw,input wire[9:0]adc_dout,output wire adc_cs_n,adc_sclk,adc_din,
 input wire mic_bck,mic_ws,mic_sd,input wire play_button,stop_button,panic_button,song_next,
 output wire i2s_bck,i2s_ws,i2s_sd,output wire[11:0]guide_pitch,output wire guide_bar,
 output wire[3:0]panel_part,output wire[111:0]panel_values,
 output wire clock_fault,microphone_stale,output wire[31:0]drops,underruns,
 output wire signed[15:0]monitor_left,monitor_right,output wire monitor_valid,monitor_reset,monitor_stop);
 wire rst,panic,tick,pcm_valid,stop_audio;wire signed[15:0]left,right;wire signed[23:0]mic;
 assign monitor_left=left;assign monitor_right=right;assign monitor_valid=pcm_valid;
 assign monitor_reset=rst||panic;assign monitor_stop=stop_audio;
 wire[31:0]clock_losses;
 audio_clock_watchdog watch_clock(clk,audio_clk,rst,clock_fault,clock_losses);
 microphone_capture capture(.core_clk(clk),.rst(rst),.panic(panic),.bck(SHARED_MIC_CLOCK?i2s_bck:mic_bck),.ws(SHARED_MIC_CLOCK?i2s_ws:mic_ws),.sd(mic_sd),
 .sample_tick(tick),.microphone_sample(mic),.input_stale(microphone_stale),.received_frames(),
 .repeated_frames(),.skipped_frames(),.timeouts(),.framing_errors_bck(),.overruns_bck());
 workstation_expansion_engine #(.EXTERNAL_AUDIO(1),.LOCAL_INPUTS(1)) engine(
 .clk(clk),.uart_rx_pin(pc_rx),.uart_tx_pin(pc_tx),.ble_rx(ble_rx),.ble_tx(ble_tx),.usb_rx(usb_rx),.usb_tx(usb_tx),
 .enc_a(enc_a),.enc_b(enc_b),.transport_fault(clock_fault),.external_drops(drops),.external_underruns(underruns),
 .song_next(song_next),
 .guide_pitch(guide_pitch),.guide_bar(guide_bar),.panel_part(panel_part),.panel_values(panel_values),
 .HP_BCK(),.HP_WS(),.HP_DIN(),.PA_EN(),.adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .local_play(play_button),.local_stop(stop_button),.local_panic(panic_button),.local_root(4'd0),.local_minor(1'b0),
 .local_held(),.external_sample_tick(tick),.pcm_left(left),.pcm_right(right),.pcm_valid(pcm_valid),
 .reset_out(rst),.panic_out(panic),.microphone_sample(mic),.singer_mix(7'd80),.dac_dropped(),.dac_underruns(),
 .singer_gate(),.singer_note(),.transport_sample_tick(),.audio_stop(stop_audio),
 .pedal_raw(pedal_raw),.pedal_down(),.deferred_returns());
 i2s24_queue_bridge dac(.core_clk(clk),.audio_clk(audio_clk),.rst(rst),.panic(panic||stop_audio),
 .frame_valid(pcm_valid),.left_in({left,8'd0}),.right_in({right,8'd0}),.frame_ready(),.sample_tick(tick),
 .bck(i2s_bck),.ws(i2s_ws),.sd(i2s_sd),.dropped_frames(drops),
 .underruns_audio_domain(),.underruns_core_domain(underruns));
endmodule
