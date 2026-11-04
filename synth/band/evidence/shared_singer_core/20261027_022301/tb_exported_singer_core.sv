`timescale 1ns/1ps
module tb_shared_singer_core;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,run_audio=0,mv=0,cv=0,xv=0,lost=0;
 reg [1:0] kind=0,command=0;reg [3:0] part=7;
 reg [31:0] ep=2,serial=0;reg [6:0] note=60;
 reg [13:0] value=0;reg [3:0] parameter_id=0;
 wire mr,cr,lr;wire [7:0] owner;wire [31:0] epoch;
 wire [15:0] voices,cycles;wire [31:0] rejected,deadline,clips,denied;
 wire valid;wire signed [15:0] left,right;
 reg [25:0] divider=0;wire tick=run_audio&&divider>=49952000;
 always @(posedge clk)if(rst||!run_audio)divider<=0;else divider<=tick?divider+48000-50000000:divider+48000;
 band_singer_core dut(.clk(clk),.rst(rst),.panic(panic),.sample_tick(tick),.play(1'b0),.stop(1'b0),
  .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(8'd2),.manual_contact(8'd0),.manual_part(part),
  .manual_epoch(ep),.manual_serial(serial),.manual_note(note),.manual_velocity(7'd10),
  .command_valid(cv),.command_ready(cr),.command(command),.command_part(part),.command_source(8'd2),
  .microphone_sample(24'sd1000000),.singer_mix(7'd127),.wet(7'd32),.master(7'd16),.tempo(8'd120),.transpose(8'd0),.status_part(part),.status_owner(owner),.status_epoch(epoch),
  .active_voices(voices),.render_cycles(cycles),.rejected(rejected),.deadline_miss(deadline),.clips(clips),.denied(denied),
  .audio_valid(valid),.left_out(left),.right_out(right),
  .source_lost(lost),.lost_ready(lr),.lost_source(8'd2),
  .upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
  .control_valid(xv),.control_part(part),.control_source(8'd2),.control_epoch(ep),.control_parameter(parameter_id),.control_value(value));
 wire [255:0] gates,allocated;wire [7:0] controls[0:7];
 genvar b;generate for(b=0;b<8;b=b+1)begin:observe
  assign gates[b*32+:32]=dut.banks[b].unit.allocator.gate;
  assign allocated[b*32+:32]=dut.banks[b].unit.allocator.active;
  assign controls[b]=dut.role_controls.target_expression[7];
 end endgenerate
 integer frames=0,maxcycles=0,peak=0,i,j,minvoices=256;
 reg [31:0] epochs[0:15];
 always @(negedge clk)if(!rst&&valid)begin
  frames=frames+1;if(voices<minvoices)minvoices=voices;if(cycles>maxcycles)maxcycles=cycles;
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
  for(j=0;j<8;j=j+1)begin
   part=j;cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
   wait(owner==2);ep=epoch;epochs[j]=ep;drain();
   for(i=0;i<32;i=i+1)send(0,j*32+i);drain();
  end
  if(allocated!=={256{1'b1}}||gates!=={256{1'b1}}||rejected||denied)$fatal(1,"mixed256 allocation failed");
  if(!dut.lead_present)$fatal(1,"mixed lead not recognized");
  part=15;cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==2);ep=epoch;drain();send(0,5000);drain();
  if(!dut.singer_gate||dut.singer_rejected)$fatal(1,"dedicated singer blocked");
  run_audio=1;wait(frames==512);@(negedge clk);run_audio=0;
  if(deadline||clips||peak==0||maxcycles>1041||dut.singer_dropped)
   $fatal(1,"mixed deadline/clips/audio failure voices=%0d minvoices=%0d deadline=%0d clips=%0d peak=%0d cycles=%0d",voices,minvoices,deadline,clips,peak,maxcycles);
  lost=1;while(!lr)@(negedge clk);@(negedge clk);lost=0;drain();
  if(gates!==0||dut.singer_gate)$fatal(1,"mixed source loss missed gates");
  panic=1;@(negedge clk);panic=0;drain();
  if(allocated!==0||dut.dispatch_valid||!dut.dispatch_ready)$fatal(1,"mixed panic failed");
  $display("PASS mixed256 initial slots roles0..7+singer+wet32 512frames exact50MHz/48kHz; minvoices=%0d maxcycles=%0d peak=%0d",minvoices,maxcycles,peak);
  $finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
