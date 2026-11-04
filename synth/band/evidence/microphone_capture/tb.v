`timescale 1ns/1ps
module tb;
 reg core_clk=0,bck=0,run_bck=1;always #10 core_clk=~core_clk;always #160 if(run_bck)bck=~bck;
 reg rst=1,panic=0,ws=0,sd=0,sample_tick=0;
 wire signed[23:0]microphone_sample;wire input_stale;
 wire[31:0]received_frames,repeated_frames,skipped_frames,timeouts,framing_errors_bck,overruns_bck;
 microphone_capture #(.TIMEOUT_CYCLES(4000)) dut(.*);
 task bit_tick(input ch,data);begin @(negedge bck);ws=ch;sd=data;@(posedge bck);#2;end endtask
 task word(input ch,input[23:0]data);integer j;begin
  bit_tick(ch,0);for(j=1;j<32;j=j+1)bit_tick(ch,j<=24?data[24-j]:1'b0);
 end endtask
 task snapshot;begin @(negedge core_clk);sample_tick=1;@(negedge core_clk);sample_tick=0;end endtask
 initial begin
  repeat(5)@(negedge bck);rst=0;repeat(5)@(negedge bck);
  if(!input_stale||microphone_sample!==0)$fatal(1,"Startup");
  word(1,0);word(0,24'h123456);word(1,24'h777777);word(0,24'hfffb2e);word(1,0);bit_tick(0,0);
  repeat(3)bit_tick(0,0);@(negedge bck);run_bck=0;repeat(100)@(negedge core_clk);snapshot();
  if(microphone_sample!==24'hfffb2e||received_frames!=2||skipped_frames!=1||input_stale||framing_errors_bck||overruns_bck)$fatal(1,"Frame capture received=%0d skipped=%0d errors=%0d sample=%h",received_frames,skipped_frames,framing_errors_bck,microphone_sample);
  snapshot();if(repeated_frames!=1)$fatal(1,"Rate mismatch not counted");
  // Force timeout and snapshot on the same clock edge: clearing must win.
  while(dut.idle_cycles<3999)@(negedge core_clk);
  sample_tick=1;@(negedge core_clk);sample_tick=0;
  if(dut.held!==0)$fatal(1,"Timeout snapshot retained old PCM");
  repeat(100)@(negedge core_clk);
  if(!input_stale||microphone_sample!==0||timeouts!=1)$fatal(1,"Clock loss");
  run_bck=1;repeat(5)@(negedge bck);word(1,0);word(0,24'h654321);word(1,0);bit_tick(0,0);
  repeat(3)bit_tick(0,0);@(negedge bck);run_bck=0;repeat(100)@(negedge core_clk);
  if(microphone_sample!==0)$fatal(1,"Old PCM reappeared before fresh snapshot");snapshot();
  if(input_stale||microphone_sample!==24'h654321||received_frames!=3)$fatal(1,"Fresh recovery");
  panic=1;#1;if(microphone_sample!==0)$fatal(1,"Immediate panic");
  repeat(4)@(negedge core_clk);panic=0;repeat(30)@(negedge core_clk);
  if(!input_stale||microphone_sample!==0||received_frames!=0)$fatal(1,"Stale post-panic");
  $display("PASS microphone I2S/CDC: signed left PCM,snapshot,skip/repeat counters,stopped BCK timeout,flushed recovery,panic");$finish;
 end
 initial begin #1000000;$fatal(1,"Timeout");end
endmodule
