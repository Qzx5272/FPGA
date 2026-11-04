`timescale 1ns/1ps
module tb_dispatch;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,mv=0,cv=0;wire mr,cr;
 reg [1:0] kind=0,cmd=0;reg [7:0] src=1,key=1;
 reg [3:0] part=6;reg [31:0] ep=2,seq=1;reg [6:0] note=60;
 wire [7:0] owner;wire [31:0] epoch;wire [15:0] voices;
 band_core dut(.clk(clk),.rst(rst),.panic(panic),.sample_tick(1'b0),.play(1'b0),.stop(1'b0),
 .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(src),.manual_contact(key),.manual_part(part),
 .manual_epoch(ep),.manual_serial(seq),.manual_note(note),.manual_velocity(7'd100),
 .command_valid(cv),.command_ready(cr),.command(cmd),.command_part(4'd6),.command_source(8'd1),
 .wet(7'd0),.master(7'd32),.tempo(8'd120),.transpose(8'd0),.status_part(4'd6),.status_owner(owner),.status_epoch(epoch),.active_voices(voices),
 .source_lost(1'b0),.lost_source(8'd0),.upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
 .control_valid(1'b0),.control_part(4'd0),.control_source(8'd1),.control_epoch(32'd0),.control_parameter(4'd0),.control_value(14'd0));
 task send;input [1:0] k;input [31:0] serial;input [6:0] pitch;begin
  @(negedge clk);kind=k;seq=serial;note=pitch;src=1;part=6;mv=1;
  while(!mr)@(negedge clk);
  @(negedge clk);mv=0;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;repeat(8300)@(negedge clk);
  cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==1);repeat(80)@(negedge clk);ep=epoch;
  send(0,1,60);send(0,2,64);
  // The second note was accepted while the allocator was scanning the first.
  // A producer may change its bus after acknowledgment; that must not alter it.
  src=2;part=5;seq=999;note=99;key=200;
  repeat(150)@(negedge clk);
  if(dut.banks[6].unit.allocator.active!=32'd3||dut.banks[5].unit.allocator.active!=0)$fatal(1,"buffered route changed");
  if(dut.banks[6].unit.allocator.note[0]!=60||dut.banks[6].unit.allocator.note[1]!=64)$fatal(1,"buffered pitch changed");
  if(dut.banks[6].unit.allocator.serial[1]!=2||dut.banks[6].unit.allocator.source[1]!=1)$fatal(1,"buffered identity changed");
  key=1;send(1,1,60);repeat(100)@(negedge clk);
  if(dut.banks[6].unit.allocator.gate[0]||!dut.banks[6].unit.allocator.gate[1])$fatal(1,"release affected wrong note");
  send(0,3,67);panic=1;@(negedge clk);panic=0;repeat(100)@(negedge clk);
  if(dut.banks[6].unit.allocator.active!=0||dut.dispatch_valid)$fatal(1,"panic left queued note");
  $display("PASS dispatch: queued identity survives producer bus changes under allocator backpressure; exact release and panic flush");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
