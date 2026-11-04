`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg audio_clk=0,audio_run=0;always #20.345052 if(audio_run)audio_clk=~audio_clk;
 initial begin
  wait(!dut.band.engine.rst);repeat(12000)@(negedge clk);
  if(dut.band.engine.playing||dut.band.engine.offline_started||!dut.band.audio_clock_fault)$fatal(1,"autoplay escaped absent audio clock");
  audio_run=1;
 end
 wire tx,bck,ws,din,pa;
 offline_workstation_top dut(.adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),.play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),.seat_led(),.clk(clk),.uart_rx_pin(1'b1),.mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),
 .uart_tx_pin(tx),.audio_clk(audio_clk),.i2s_bck(bck),.i2s_ws(ws),.i2s_sd(din),.display_clk(clk),.display_read(1'b0),.display_release(1'b0),.display_address(11'd0),.PA_EN(pa));
 initial begin
  wait(!dut.band.engine.rst);wait(dut.band.engine.playing);
  wait(dut.band.engine.song_position>=24);repeat(200)@(negedge clk);
  if(!dut.band.engine.singer_gate||dut.band.engine.singer_note!=63)$fatal(1,"Boot score/pitch");
  if(dut.band.engine.core.singer_expression!=64||dut.band.engine.master!=20||dut.band.engine.wet!=12||dut.band.engine.core.collaboration_enabled)$fatal(1,"Boot presets");
  if(!dut.band.microphone_stale||dut.band.engine.singer_mix!=0)$fatal(1,"Missing mic must mute voice");
  wait(!dut.band.engine.playing);repeat(200)@(negedge clk);
  if(dut.band.engine.song_position!=192||dut.band.engine.singer_gate||dut.band.engine.deadline_miss||dut.band.engine.dac_dropped)$fatal(1,"Boot completion");
  @(negedge audio_clk);audio_run=0;repeat(51000)@(negedge clk);
  if(!dut.band.audio_clock_fault)$fatal(1,"missing clock not detected");
  audio_run=1;wait(!dut.band.audio_clock_fault);repeat(20000)@(negedge clk);
  if(dut.band.engine.playing||!dut.band.engine.offline_started)$fatal(1,"autoplay repeated after clock recovery");
  $display("PASS exported workstation:waited for clock,one-shot autoplay,no automatic replay after outage; no UART commands,autoplay,transposed note63,expression64/master20/wet12/collaboration0,no-mic mute,naturalend192,zero deadlines/drops");$finish;
 end
 initial begin #10000000;$fatal(1,"Timeout");end
endmodule
