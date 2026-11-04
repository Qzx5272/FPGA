`timescale 1ns/1ps
module tb_central_parameters_slew;
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
 wire ref_mr,ref_cr,ref_lr,ref_valid;wire [7:0] ref_owner;wire [31:0] ref_epoch;
 wire [15:0] ref_voices,ref_cycles;wire [31:0] ref_rejected,ref_deadline,ref_clips,ref_denied;
 wire signed [15:0] ref_left,ref_right;integer compared=0;
 always @(negedge clk)if(!rst)begin
  if({mr,cr,lr,owner,epoch,voices,cycles,rejected,deadline,clips,denied,valid}!==
     {ref_mr,ref_cr,ref_lr,ref_owner,ref_epoch,ref_voices,ref_cycles,ref_rejected,ref_deadline,ref_clips,ref_denied,ref_valid})$fatal(1,"control/telemetry mismatch mr=%b/%b cr=%b/%b lr=%b/%b owner=%d/%d epoch=%d/%d voices=%d/%d cycles=%d/%d rejected=%d/%d deadline=%d/%d clips=%d/%d denied=%d/%d valid=%b/%b",mr,ref_mr,cr,ref_cr,lr,ref_lr,owner,ref_owner,epoch,ref_epoch,voices,ref_voices,cycles,ref_cycles,rejected,ref_rejected,deadline,ref_deadline,clips,ref_clips,denied,ref_denied,valid,ref_valid);
  if(valid)begin
   if(left!==ref_left||right!==ref_right)$fatal(1,"PCM mismatch");
   compared=compared+1;
  end
 end
 central_band_singer_core dut(.clk(clk),.rst(rst),.panic(panic),.sample_tick(tick),.play(1'b0),.stop(1'b0),
  .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(8'd2),.manual_contact(8'd0),.manual_part(part),
  .manual_epoch(ep),.manual_serial(serial),.manual_note(note),.manual_velocity(7'd10),
  .command_valid(cv),.command_ready(cr),.command(command),.command_part(part),.command_source(8'd2),
  .microphone_sample(24'sd0),.singer_mix(7'd127),.wet(7'd0),.master(7'd16),.tempo(8'd120),.transpose(8'd0),.status_part(part),.status_owner(owner),.status_epoch(epoch),
  .active_voices(voices),.render_cycles(cycles),.rejected(rejected),.deadline_miss(deadline),.clips(clips),.denied(denied),
  .audio_valid(valid),.left_out(left),.right_out(right),
  .source_lost(lost),.lost_ready(lr),.lost_source(8'd2),
  .upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
  .control_valid(xv),.control_part(part),.control_source(8'd2),.control_epoch(ep),.control_parameter(parameter_id),.control_value(value));
 shared_band_singer_core reference_core(.clk(clk),.rst(rst),.panic(panic),.sample_tick(tick),.play(1'b0),.stop(1'b0),
  .manual_valid(mv),.manual_ready(ref_mr),.manual_kind(kind),.manual_source(8'd2),.manual_contact(8'd0),.manual_part(part),
  .manual_epoch(ep),.manual_serial(serial),.manual_note(note),.manual_velocity(7'd10),
  .command_valid(cv),.command_ready(ref_cr),.command(command),.command_part(part),.command_source(8'd2),
  .microphone_sample(24'sd0),.singer_mix(7'd127),.wet(7'd0),.master(7'd16),.tempo(8'd120),.transpose(8'd0),.status_part(part),.status_owner(ref_owner),.status_epoch(ref_epoch),
  .active_voices(ref_voices),.render_cycles(ref_cycles),.rejected(ref_rejected),.deadline_miss(ref_deadline),.clips(ref_clips),.denied(ref_denied),
  .audio_valid(ref_valid),.left_out(ref_left),.right_out(ref_right),
  .source_lost(lost),.lost_ready(ref_lr),.lost_source(8'd2),
  .upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
  .control_valid(xv),.control_part(part),.control_source(8'd2),.control_epoch(ep),.control_parameter(parameter_id),.control_value(value));
 wire [255:0] gates,allocated;wire [7:0] controls[0:7];
 genvar b;generate for(b=0;b<8;b=b+1)begin:observe
  assign gates[b*32+:32]=dut.banks[b].unit.allocator.gate;
  assign allocated[b*32+:32]=dut.banks[b].unit.allocator.active;
  assign controls[b]=dut.role_controls.target_expression[7];
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
  // Dedicated electronic singer(part15) must remain independently dispatchable
  // while all256 instrument slots are occupied. It is not another pool slot.
  part=15;cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==2);ep=epoch;drain();send(0,5000);drain();
  if(!dut.singer_gate||dut.singer_rejected)$fatal(1,"dedicated singer blocked by full shared pool");
  part=7;ep=2;
  run_audio=1;
  fork
   begin
    wait(frames==8);@(negedge clk);parameter_id=1;value=14000;xv=1;@(negedge clk);xv=0;
    wait(frames==16);@(negedge clk);parameter_id=0;value=50;xv=1;@(negedge clk);xv=0;
    wait(frames==24);@(negedge clk);parameter_id=2;value=4;xv=1;@(negedge clk);xv=0;
    wait(frames==32);@(negedge clk);parameter_id=7;value=1;xv=1;@(negedge clk);xv=0;
    wait(frames==40);@(negedge clk);parameter_id=6;value=16000;xv=1;@(negedge clk);xv=0;
    wait(frames==48);@(negedge clk);parameter_id=4;value=4096;xv=1;@(negedge clk);xv=0;
    wait(frames==56);@(negedge clk);parameter_id=5;value=7;xv=1;@(negedge clk);xv=0;
   end
   begin wait(frames==256);@(negedge clk);run_audio=0;end
  join
  if(voices!=256||deadline||clips||peak==0||maxcycles>1041)$fatal(1,"audio load failed voices=%0d deadline=%0d clips=%0d peak=%0d cycles=%0d",voices,deadline,clips,peak,maxcycles);
  if(dut.role_controls.expression[7]!=50||dut.role_controls.bend[7]!=218)$fatal(1,"slew did not reach expression50/bend218");
  send(0,0);drain();if(dut.allocation_duplicates!=1||rejected)$fatal(1,"core duplicate handling");
  send(1,0);drain();if(gates[0]||allocated!=={256{1'b1}})$fatal(1,"tail lost");
  send(0,300);drain();if(rejected!=1)$fatal(1,"full tail capacity not reported");
  lost=1;while(!lr)@(negedge clk);@(negedge clk);lost=0;drain();
  if(dut.singer_gate||dut.singer_dropped)$fatal(1,"broadcast source loss missed singer or dropped audio");
  if(gates!==0||owner!=2||!dut.ownership.returns[7])$fatal(1,"source loss failed immediate release/next-bar return intent");
  force dut.bar_tick=1;force reference_core.bar_tick=1;@(negedge clk);release dut.bar_tick;release reference_core.bar_tick;drain();
  if(owner!=0)$fatal(1,"lost owner not returned on bar");
  if(dut.ownership.owners[15]!=0)$fatal(1,"singer owner not returned on bar");
  panic=1;@(negedge clk);panic=0;drain();
  if(allocated!==0||dut.dispatch_valid||!dut.dispatch_ready)$fatal(1,"panic failed");
  if(compared!=256)$fatal(1,"missing exact PCM comparison");
  $display("PASS central parameter exact stereo/control comparison256frames; shared singer core256choir voices256frames,control broadcast,role identity,duplicate/tails/source loss/panic;maxcycles=%0d peak=%0d",maxcycles,peak);
  $finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
