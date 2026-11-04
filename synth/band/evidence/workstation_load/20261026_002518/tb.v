`timescale 1ns/1ps
module tb;
 reg clk=0,audio_clk=0;always #10 clk=~clk;always #20.345052 audio_clk=~audio_clk;
 offline_workstation_top dut(.clk(clk),.audio_clk(audio_clk),.uart_rx_pin(1'b1),
 .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),.adc_dout(10'd0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),
 .display_clk(clk),.display_read(1'b0),.display_release(1'b0),.display_address(11'd0));
 integer checked=0,peak=0,maxcycles=0;reg started=0;
 always @(negedge clk)begin
  if(dut.band.engine.playing)started=1;
  if(started)begin
   if(dut.band.i2s_dropped||dut.band.i2s_underruns||dut.band.engine.deadline_miss||dut.band.engine.clips||dut.band.engine.rejected||dut.band.fft_clips||dut.band.rejected_bins)$fatal(1,"load error counters");
   if(dut.band.pcm_valid)begin
    if($signed(dut.band.pcm_left)>peak)peak=$signed(dut.band.pcm_left);
    if(dut.band.engine.render_cycles>maxcycles)maxcycles=dut.band.engine.render_cycles;
    if(dut.band.engine.song_position>=500&&dut.band.engine.song_position<5000)begin
     if(dut.band.engine.active_voices!=256)$fatal(1,"load lost position=%0d voices=%0d",dut.band.engine.song_position,dut.band.engine.active_voices);
     checked=checked+1;
    end
   end
  end
 end
 initial begin
  wait(dut.band.engine.playing);wait(!dut.band.engine.playing);repeat(10000)@(negedge clk);
  if(dut.band.engine.song_position!=6000||dut.band.engine.active_voices!=0||checked<4490||peak==0||!dut.display_available)$fatal(1,"completion/count/FFT");
  $display("PASS256 slots held:checked_frames=%0d peak=%0d maxcycles=%0d naturalend6000 released0 display_stalled zeroerrors",checked,peak,maxcycles);$finish;
 end
 initial begin #150000000;$fatal(1,"timeout");end
endmodule
