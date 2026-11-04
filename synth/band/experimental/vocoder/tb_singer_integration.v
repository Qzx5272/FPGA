`timescale 1ns/1ps
module tb_singer_integration;
 reg clk=0;always #10 clk=~clk;
 reg sample_tick=0,run_audio=0;reg[10:0] sample_divider=0;
 reg signed[23:0] microphone=0;reg[31:0] noise=32'h12345678;
 integer frames=0,peak=0,magnitude;
 wire signed[15:0] left_out,right_out;wire audio_valid;wire[31:0] deadline_miss,singer_dropped;
 always @(negedge clk)begin
  sample_tick=0;
  if(run_audio)begin
   if(sample_divider==0)begin sample_tick=1;noise={noise[30:0],noise[31]^noise[21]^noise[1]^noise[0]};microphone=noise[23:0];end
   sample_divider=sample_divider==1040?0:sample_divider+1'b1;
  end else sample_divider=0;
 end
 always @(posedge clk)if(audio_valid)begin
  frames=frames+1;magnitude=$signed(left_out);if(magnitude<0)magnitude=-magnitude;
  if(magnitude>peak)peak=magnitude;
 end
 reg rst=1,panic=0,mv=0,cv=0;wire mr,cr;
 reg [1:0] kind=0,cmd=0;reg [7:0] src=1,key=1;
 reg [3:0] part=15;reg [31:0] ep=2,seq=1;reg [6:0] note=60;
 wire [7:0] owner;wire [31:0] epoch;wire [15:0] voices;
 band_singer_core #(.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem")) dut(.microphone_sample(microphone),.singer_mix(7'd100),.clk(clk),.rst(rst),.panic(panic),.sample_tick(sample_tick),.play(1'b0),.stop(1'b0),
 .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(src),.manual_contact(key),.manual_part(part),
 .manual_epoch(ep),.manual_serial(seq),.manual_note(note),.manual_velocity(7'd100),
 .command_valid(cv),.command_ready(cr),.command(cmd),.command_part(4'd15),.command_source(8'd1),
 .wet(7'd0),.master(7'd32),.tempo(8'd120),.transpose(8'd0),.status_part(4'd15),.status_owner(owner),.status_epoch(epoch),.active_voices(voices),.left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),.deadline_miss(deadline_miss),.singer_dropped(singer_dropped),
 .source_lost(1'b0),.lost_source(8'd0),.upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
 .control_valid(1'b0),.control_part(4'd0),.control_source(8'd1),.control_epoch(32'd0),.control_parameter(4'd0),.control_value(14'd0));
 task send;input [1:0] k;input [31:0] serial;input [6:0] pitch;begin
  @(negedge clk);kind=k;seq=serial;note=pitch;src=1;part=15;mv=1;
  while(!mr)@(negedge clk);
  @(negedge clk);mv=0;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;#1;run_audio=1;
  repeat(16*1041)@(negedge clk);#1;run_audio=0;repeat(400)@(negedge clk);
  if(deadline_miss||singer_dropped)$fatal(1,"startup effect clear produced unmatched frames");
  frames=0;peak=0;
  cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==1);repeat(80)@(negedge clk);ep=epoch;
  send(0,1,60);send(0,2,64);
  // The second note was accepted while the allocator was scanning the first.
  // A producer may change its bus after acknowledgment; that must not alter it.
  src=2;part=5;seq=999;note=99;key=200;
  repeat(150)@(negedge clk);
  if(dut.electronic_singer.notes.allocator.active!=32'd3||dut.banks[5].unit.allocator.active!=0)$fatal(1,"buffered route changed");
  if(dut.electronic_singer.notes.allocator.note[0]!=60||dut.electronic_singer.notes.allocator.note[1]!=64)$fatal(1,"buffered pitch changed");
  if(dut.electronic_singer.notes.allocator.serial[1]!=2||dut.electronic_singer.notes.allocator.source[1]!=1)$fatal(1,"buffered identity changed");
  if(dut.banks[7].unit.allocator.active!=0)$fatal(1,"singer duplicated into choir bank");
  // Wrong owner is rejected by the actual band authorization, before singer.
  @(negedge clk);src=2;part=15;kind=1;seq=2;key=1;note=64;mv=1;
  while(!mr)@(negedge clk);@(negedge clk);mv=0;repeat(100)@(negedge clk);
  if(!dut.singer_gate||dut.singer_note!=64)$fatal(1,"wrong owner killed singer");
  key=1;send(1,1,60);repeat(100)@(negedge clk);
  if(dut.electronic_singer.notes.allocator.gate[0]||!dut.electronic_singer.notes.allocator.gate[1])$fatal(1,"release affected wrong note");
  run_audio=1;repeat(256*1041)@(negedge clk);#1;run_audio=0;repeat(400)@(negedge clk);
  if(frames!=256||peak==0||deadline_miss||singer_dropped)$fatal(1,"integrated audio frames=%0d peak=%0d deadline=%0d drop=%0d",frames,peak,deadline_miss,singer_dropped);
  send(0,3,67);panic=1;@(negedge clk);panic=0;repeat(100)@(negedge clk);
  if(dut.electronic_singer.notes.allocator.active!=0||dut.dispatch_valid)$fatal(1,"panic left queued note");
  $display("PASS real band ownership to singer: queued identity, wrong-owner rejection, no choir duplication, exact release,256 real-core audio frames with synthetic microphone and panic");$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
