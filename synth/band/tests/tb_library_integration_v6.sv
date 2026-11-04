`timescale 1ns/1ps
module tb_library_integration_v6;
 reg clk=0;always #10 clk=~clk;
 reg audio=0;always #20.345052 audio=~audio;
 reg song_next=0;wire fault;wire[31:0]drops,under;
 workstation_expansion_top dut(.clk(clk),.audio_clk(audio),.pc_rx(1'b1),.ble_rx(1'b1),.usb_rx(1'b1),
 .pc_tx(),.ble_tx(),.usb_tx(),.enc_a(8'd0),.enc_b(8'd0),.pedal_raw(4'd0),
 .adc_dout(10'd0),.adc_cs_n(),.adc_sclk(),.adc_din(),.mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.song_next(song_next),
 .i2s_bck(),.i2s_ws(),.i2s_sd(),.guide_pitch(),.guide_bar(),.panel_part(),.panel_values(),
 .clock_fault(fault),.microphone_stale(),.drops(drops),.underruns(under));
 defparam dut.engine.song_selector.STABLE_CYCLES=3;
 initial begin
  wait(!dut.rst);wait(!fault);repeat(100)@(negedge clk);
  song_next=1;repeat(8)@(negedge clk);song_next=0;
  wait(dut.engine.library_busy);wait(!dut.engine.library_busy);
  repeat(100)@(negedge clk);
  if(dut.engine.library_failed||dut.engine.upload_errors||!dut.engine.playing||dut.engine.library_current!=1)
   $fatal(1,"library commit/start failed errors=%0d failed=%b playing=%b song=%0d",dut.engine.upload_errors,dut.engine.library_failed,dut.engine.playing,dut.engine.library_current);
  if(dut.engine.stored_events!=64||dut.engine.stored_duration!=792000)
   $fatal(1,"wrong library bank events=%0d duration=%0d",dut.engine.stored_events,dut.engine.stored_duration);
  repeat(5000)@(negedge clk);
  if(drops||under||dut.engine.deadline_miss)$fatal(1,"audio deadline during ROM upload");
  $display("PASS integrated ROM library: nonzero ROM base,CRC/atomic score commit,local next song,automatic start,zero audio fault");$finish;
 end
 initial begin #10000000;$fatal(1,"timeout state=%0d errors=%0d pending=%b",dut.engine.library_loader.state,dut.engine.upload_errors,dut.engine.upload_pending);end
endmodule
