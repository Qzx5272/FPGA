`timescale 1ns/1ps
module tb_singer_score;
 reg play=0,uv=0;reg[2:0]uc=0;reg[31:0]ui=0,uw=0,ua=0;
 wire ur,pending,playing;wire[31:0]upload_errors,position;

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
 band_singer_core #(.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem")) dut(.microphone_sample(microphone),.singer_mix(7'd100),.clk(clk),.rst(rst),.panic(panic),.sample_tick(sample_tick),.play(play),.playing(playing),.song_position(position),.stop(1'b0),
 .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(src),.manual_contact(key),.manual_part(part),
 .manual_epoch(ep),.manual_serial(seq),.manual_note(note),.manual_velocity(7'd100),
 .command_valid(cv),.command_ready(cr),.command(cmd),.command_part(4'd15),.command_source(8'd1),
 .wet(7'd0),.master(7'd32),.tempo(8'd120),.transpose(8'd0),.status_part(4'd15),.status_owner(owner),.status_epoch(epoch),.active_voices(voices),.left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),.deadline_miss(deadline_miss),.singer_dropped(singer_dropped),
 .source_lost(1'b0),.lost_source(8'd0),.upload_valid(uv),.upload_ready(ur),.upload_command(uc),.upload_index(ui),.upload_value(uw),.upload_aux(ua),.upload_pending(pending),.upload_errors(upload_errors),
 .control_valid(1'b0),.control_part(4'd0),.control_source(8'd1),.control_epoch(32'd0),.control_parameter(4'd0),.control_value(14'd0));
 task send;input [1:0] k;input [31:0] serial;input [6:0] pitch;begin
  @(negedge clk);kind=k;seq=serial;note=pitch;src=1;part=15;mv=1;
  while(!mr)@(negedge clk);
  @(negedge clk);mv=0;
 end endtask

 task upload(input[2:0]c,input[31:0]i,v,a);begin
  @(negedge clk);while(!ur)@(negedge clk);uc=c;ui=i;uw=v;ua=a;uv=1;
  @(negedge clk);uv=0;while(!ur)@(negedge clk);
 end endtask
 task launch;begin
  @(negedge clk);play=1;@(negedge clk);play=0;run_audio=1;
 end endtask
 task at_sample(input integer n);begin wait(position>=n);repeat(200)@(negedge clk);end endtask
 task drain;begin run_audio=0;repeat(400)@(negedge clk);end endtask
 integer base_frames;
 initial begin
  repeat(3)@(negedge clk);rst=0;repeat(9000)@(negedge clk);
  upload(3'd3,32'd4,32'd320,32'd3781544712);
  upload(3'd0,32'd0,32'd823100,32'd0);
  upload(3'd1,32'd0,32'd1,32'd0);
  upload(3'd2,32'd0,32'd0,32'd0);
  upload(3'd0,32'd1,32'd3901,32'd0);
  upload(3'd1,32'd1,32'd1,32'd0);
  upload(3'd2,32'd1,32'd96,32'd0);
  upload(3'd0,32'd2,32'd823548,32'd0);
  upload(3'd1,32'd2,32'd2,32'd0);
  upload(3'd2,32'd2,32'd160,32'd0);
  upload(3'd0,32'd3,32'd4349,32'd0);
  upload(3'd1,32'd3,32'd2,32'd0);
  upload(3'd2,32'd3,32'd240,32'd0);
  upload(3'd4,32'd1,32'd0,32'd0);

  if(!pending||upload_errors)$fatal(1,"Atomic score commit");
  launch();at_sample(20);if(!dut.singer_gate||dut.singer_note!=60||owner!=0)$fatal(1,"Auto note1");
  at_sample(120);if(dut.singer_gate)$fatal(1,"Auto off1");
  at_sample(180);if(!dut.singer_gate||dut.singer_note!=67)$fatal(1,"Auto note2");
  at_sample(280);if(dut.singer_gate)$fatal(1,"Auto off2");
  wait(!playing);repeat(64*1041)@(negedge clk);drain();
  if(position!=320||peak==0||dut.singer_gate||deadline_miss||singer_dropped)$fatal(1,"Auto completion");
  // Take the running machine's track. Old machine off and natural end must
  // not terminate the human note on the same track.
  launch();at_sample(32);@(negedge clk);cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==1);repeat(100)@(negedge clk);ep=epoch;send(0,500,72);
  at_sample(128);if(!dut.singer_gate||dut.singer_note!=72)$fatal(1,"Old auto release killed human");
  at_sample(200);if(dut.singer_note!=72)$fatal(1,"Machine stole human track");
  wait(!playing);repeat(2000)@(negedge clk);
  if(!dut.singer_gate||dut.singer_note!=72)$fatal(1,"Natural end killed human");
  // Request next-bar return; the next performance start emits the real bar
  // boundary, allowing machine notes again without a forced internal signal.
  @(negedge clk);cmd=1;cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  repeat(100)@(negedge clk);drain();launch();at_sample(24);
  if(owner!=0||epoch!=3||!dut.singer_gate||dut.singer_note!=60)$fatal(1,"Machine return at new bar");
  if(dut.banks[7].unit.allocator.active||deadline_miss||singer_dropped||upload_errors)$fatal(1,"Singer isolated accounting");
  panic=1;@(negedge clk);panic=0;repeat(100)@(negedge clk);
  if(dut.singer_gate||playing)$fatal(1,"Panic");
  $display("PASS encoded singer score:atomic upload,2auto notes/off,natural end,human takeover survives old release/end,new-bar return,panic;peak=%0d",peak);$finish;
 end
 initial begin #30000000;$fatal(1,"Timeout");end
endmodule
