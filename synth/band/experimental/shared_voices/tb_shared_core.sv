`timescale 1ns/1ps
module tb_shared_core;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,run_audio=0,mv=0,cv=0,xv=0,lost=0;
 reg [1:0] kind=0,command=0;reg [3:0] part=7;
 reg [31:0] ep=2,serial=0;reg [6:0] note=60;
 reg [13:0] value=0;reg [3:0] parameter_id=0;
 wire mr,cr,lr;wire [7:0] owner;wire [31:0] epoch;
 wire [15:0] voices,cycles;wire [31:0] rejected,deadline,clips,denied;
 wire valid;wire signed [15:0] left,right;
 reg [10:0] divider=0;wire tick=run_audio&&divider==1041;
 always @(posedge clk)if(rst||!run_audio)divider<=0;else divider<=tick?0:divider+1'b1;
 shared_band_core dut(.clk(clk),.rst(rst),.panic(panic),.sample_tick(tick),.play(1'b0),.stop(1'b0),
  .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(8'd2),.manual_contact(8'd0),.manual_part(part),
  .manual_epoch(ep),.manual_serial(serial),.manual_note(note),.manual_velocity(7'd10),
  .command_valid(cv),.command_ready(cr),.command(command),.command_part(part),.command_source(8'd2),
  .wet(7'd0),.master(7'd4),.tempo(8'd120),.transpose(8'd0),.status_part(part),.status_owner(owner),.status_epoch(epoch),
  .active_voices(voices),.render_cycles(cycles),.rejected(rejected),.deadline_miss(deadline),.clips(clips),.denied(denied),
  .audio_valid(valid),.left_out(left),.right_out(right),
  .source_lost(lost),.lost_ready(lr),.lost_source(8'd2),
  .upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
  .control_valid(xv),.control_part(part),.control_source(8'd2),.control_epoch(ep),.control_parameter(parameter_id),.control_value(value));
 wire [255:0] gates,allocated;wire [7:0] controls[0:7];
 genvar b;generate for(b=0;b<8;b=b+1)begin:observe
  assign gates[b*32+:32]=dut.banks[b].unit.allocator.gate;
  assign allocated[b*32+:32]=dut.banks[b].unit.allocator.active;
  assign controls[b]=dut.banks[b].unit.target_expression[7];
 end endgenerate
 integer frames=0,maxcycles=0,peak=0,i;
 always @(negedge clk)if(!rst&&valid)begin
  frames=frames+1;if(cycles>maxcycles)maxcycles=cycles;
  if(left>peak)peak=left;if(-$signed(left)>peak)peak=-$signed(left);
 end
 task send(input [1:0] k,input [31:0] ident);
 begin
  @(negedge clk);kind=k;serial=ident;note=48+ident%24;mv=1;
  while(!mr)@(negedge clk);@(negedge clk);mv=0;
 end endtask
 task drain;
 begin repeat(200)@(negedge clk);if(!dut.dispatch_ready||dut.dispatch_valid)$fatal(1,"event failed to drain");end
 endtask
 initial begin
  repeat(4)@(negedge clk);rst=0;repeat(8300)@(negedge clk);
  cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==2);ep=epoch;drain();
  for(i=0;i<256;i=i+1)send(0,i);drain();
  if(allocated!=={256{1'b1}}||gates!=={256{1'b1}}||rejected||denied)$fatal(1,"256 same-role allocation failed");
  if(dut.lead_present)$fatal(1,"choir falsely recognized as lead");
  // Update the owning role while its notes occupy every physical bank.
  value=90;xv=1;@(negedge clk);xv=0;repeat(8)@(negedge clk);
  for(i=0;i<8;i=i+1)if(controls[i]!=90)$fatal(1,"control not broadcast bank%0d",i);
  run_audio=1;wait(frames==64);@(negedge clk);run_audio=0;
  if(voices!=256||deadline||clips||peak==0||maxcycles>1041)$fatal(1,"audio load failed voices=%0d deadline=%0d clips=%0d peak=%0d cycles=%0d",voices,deadline,clips,peak,maxcycles);
  send(0,0);drain();if(dut.allocation_duplicates!=1||rejected)$fatal(1,"core duplicate handling");
  send(1,0);drain();if(gates[0]||allocated!=={256{1'b1}})$fatal(1,"tail lost");
  send(0,300);drain();if(rejected!=1)$fatal(1,"full tail capacity not reported");
  lost=1;while(!lr)@(negedge clk);@(negedge clk);lost=0;drain();
  if(gates!==0||owner!=2||!dut.ownership.returns[7])$fatal(1,"source loss failed immediate release/next-bar return intent");
  force dut.bar_tick=1;@(negedge clk);release dut.bar_tick;drain();
  if(owner!=0)$fatal(1,"lost owner not returned on bar");
  panic=1;@(negedge clk);panic=0;drain();
  if(allocated!==0||dut.dispatch_valid||!dut.dispatch_ready)$fatal(1,"panic failed");
  $display("PASS shared core256choir voices64frames,control broadcast,role identity,duplicate/tails/source loss/panic;maxcycles=%0d peak=%0d",maxcycles,peak);
  $finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
