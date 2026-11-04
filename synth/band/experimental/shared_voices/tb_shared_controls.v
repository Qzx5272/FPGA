`timescale 1ns/1ps
module tb_controls;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,cv=0,xv=0;reg [1:0] command=0;reg [7:0] source=2,xsource=2;reg [31:0] xepoch=2;
 reg [3:0] xp=6,param=0;reg [13:0] value=0;wire ready;wire [7:0] owner;wire [31:0] epoch;
 shared_band_core dut(.clk(clk),.rst(rst),.panic(1'b0),.sample_tick(1'b0),.play(1'b0),.stop(1'b0),
  .manual_valid(1'b0),.manual_kind(2'd0),.manual_source(8'd1),.manual_contact(8'd0),.manual_part(4'd0),.manual_epoch(32'd0),.manual_serial(32'd0),.manual_note(7'd60),.manual_velocity(7'd100),
  .command_valid(cv),.command_ready(ready),.command(command),.command_part(4'd6),.command_source(source),
  .wet(7'd0),.master(7'd32),.tempo(8'd120),.transpose(8'd0),.status_part(4'd6),.status_owner(owner),.status_epoch(epoch),
  .source_lost(1'b0),.lost_source(8'd0),.upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
  .control_valid(xv),.control_part(xp),.control_source(xsource),.control_epoch(xepoch),.control_parameter(param),.control_value(value));
 task control;input [7:0] s;input [31:0] e;input [13:0] v;
 begin @(negedge clk);xsource=s;xepoch=e;value=v;xv=1;@(negedge clk);xv=0;repeat(5)@(negedge clk);end endtask
 initial begin
  repeat(4)@(negedge clk);rst=0;repeat(8300)@(negedge clk);
  wait(ready);cv=1;@(negedge clk);cv=0;wait(ready);#1;
  if(owner!=2||epoch!=2)$fatal(1,"takeover failed");
  control(3,2,19);if(dut.banks[6].unit.target_expression[6]!=128)$fatal(1,"other source changed patch");
  control(2,1,20);if(dut.banks[6].unit.target_expression[6]!=128)$fatal(1,"stale epoch changed patch");
  control(2,2,21);if(dut.banks[6].unit.target_expression[6]!=21)$fatal(1,"valid owner control lost");
  control(1,0,22);if(dut.banks[6].unit.target_expression[6]!=22)$fatal(1,"conductor control lost");
  // A score vowel and conductor expression reach authorization together. The
  // score must wait for the shared parameter port, not disappear as consumed.
  @(negedge clk);xv=1;xsource=1;value=23;
  force dut.auto_valid=1;force dut.auto_kind=2;force dut.auto_part=7;force dut.auto_note=4;force dut.auto_serial=32'd99;
  @(negedge clk);xv=0;
  wait(dut.accepted_control);#1;if(dut.auto_ready)$fatal(1,"score consumed during parameter collision");
  wait(dut.auto_ready);@(posedge clk);@(negedge clk);
  release dut.auto_valid;release dut.auto_kind;release dut.auto_part;release dut.auto_note;release dut.auto_serial;
  repeat(5)@(negedge clk);
  if(dut.banks[7].unit.vowel[7]!=4||dut.banks[6].unit.target_expression[6]!=23)$fatal(1,"parameter arbitration lost update");
  $display("PASS controls: owner and epoch checks, conductor override, score/host parameter collision without lost vowel");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
