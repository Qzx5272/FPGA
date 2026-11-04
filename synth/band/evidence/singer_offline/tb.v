`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 wire tx,bck,ws,din,pa;
 offline_singer_top dut(.clk(clk),.uart_rx_pin(1'b1),.mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),
 .uart_tx_pin(tx),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa));
 initial begin
  wait(!dut.band.engine.rst);wait(dut.band.engine.playing);
  wait(dut.band.engine.song_position>=24);repeat(200)@(negedge clk);
  if(!dut.band.engine.singer_gate||dut.band.engine.singer_note!=63)$fatal(1,"Boot score/pitch");
  if(dut.band.engine.core.singer_expression!=64||dut.band.engine.master!=20||dut.band.engine.wet!=12||dut.band.engine.core.collaboration_enabled)$fatal(1,"Boot presets");
  if(!dut.band.microphone_stale||dut.band.engine.singer_mix!=0)$fatal(1,"Missing mic must mute voice");
  wait(!dut.band.engine.playing);repeat(200)@(negedge clk);
  if(dut.band.engine.song_position!=192||dut.band.engine.singer_gate||dut.band.engine.deadline_miss||dut.band.engine.dac_dropped)$fatal(1,"Boot completion");
  $display("PASS exported singer top: no UART commands,autoplay,transposed note63,expression64/master20/wet12/collaboration0,no-mic mute,naturalend192,zero deadlines/drops");$finish;
 end
 initial begin #10000000;$fatal(1,"Timeout");end
endmodule
