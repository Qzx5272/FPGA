`timescale 1ns/1ps
module tb_singer_stress;
 reg clk=0;always #10 clk=~clk;
 reg sample_tick=0,run_audio=0;reg[10:0] sample_divider=0;
 reg signed[23:0] microphone=0;reg[31:0] noise=32'h12345678;
 integer frames=0,peak=0,magnitude,p,i,maxcycles=0;
 reg[3:0]command_part=15;reg lose=0,xv=0;wire lost_ready;wire[15:0]render_cycles;
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
  if(magnitude>peak)peak=magnitude;if(render_cycles>maxcycles)maxcycles=render_cycles;
 end
 reg rst=1,panic=0,mv=0,cv=0;wire mr,cr;
 reg [1:0] kind=0,cmd=0;reg [7:0] src=1,key=1;
 reg [3:0] part=15;reg [31:0] ep=2,seq=1;reg [6:0] note=60;
 wire [7:0] owner;wire [31:0] epoch;wire [15:0] voices;
 band_singer_core #(.COEFF_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/vocoder/ported/coeffs.mem")) dut(.microphone_sample(microphone),.singer_mix(7'd100),.clk(clk),.rst(rst),.panic(panic),.sample_tick(sample_tick),.play(1'b0),.stop(1'b0),
 .manual_valid(mv),.manual_ready(mr),.manual_kind(kind),.manual_source(src),.manual_contact(key),.manual_part(part),
 .manual_epoch(ep),.manual_serial(seq),.manual_note(note),.manual_velocity(7'd100),
 .command_valid(cv),.command_ready(cr),.command(cmd),.command_part(command_part),.command_source(8'd1),
 .wet(7'd0),.master(7'd4),.tempo(8'd120),.transpose(8'd0),.status_part(command_part),.status_owner(owner),.status_epoch(epoch),.active_voices(voices),.render_cycles(render_cycles),.left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),.deadline_miss(deadline_miss),.singer_dropped(singer_dropped),
 .source_lost(lose),.lost_ready(lost_ready),.lost_source(8'd1),.upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
 .control_valid(xv),.control_part(command_part),.control_source(8'd1),.control_epoch(32'd0),.control_parameter(4'd7),.control_value(14'd0));
 task send;input [1:0] k;input [31:0] serial;input [6:0] pitch;begin
  @(negedge clk);kind=k;seq=serial;note=pitch;src=1;mv=1;
  while(!mr)@(negedge clk);
  @(negedge clk);mv=0;
 end endtask
 task take;input[3:0]track;begin
  @(negedge clk);command_part=track;part=track;cv=1;
  while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==1);repeat(80)@(negedge clk);ep=epoch;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;repeat(8300)@(negedge clk);
  take(15);key=0;send(0,1,60);repeat(100)@(negedge clk);
  for(p=0;p<8;p=p+1)begin
   take(p==7?7:p+8);
   xv=1;@(negedge clk);xv=0;repeat(8)@(negedge clk);
   for(i=0;i<32;i=i+1)begin key=i;send(0,1000+p*32+i,40+i);end
   repeat(100)@(negedge clk);
  end
  #1;run_audio=1;repeat(1024*1041)@(negedge clk);#1;run_audio=0;repeat(400)@(negedge clk);
  if(frames!=1024||voices!=256||!dut.singer_gate||deadline_miss||singer_dropped||peak==0)
   $fatal(1,"full load frames=%0d voices=%0d miss=%0d drop=%0d peak=%0d",frames,voices,deadline_miss,singer_dropped,peak);
  // Release every source1 note using the actual broadcast transaction.
  lose=1;while(!lost_ready)@(negedge clk);@(negedge clk);lose=0;repeat(300)@(negedge clk);
  #1;run_audio=1;repeat(16*1041)@(negedge clk);#1;run_audio=0;repeat(400)@(negedge clk);
  if(frames!=1040||voices||dut.singer_gate||deadline_miss||singer_dropped)
   $fatal(1,"release transition frames=%0d voices=%0d miss=%0d drop=%0d",frames,voices,deadline_miss,singer_dropped);
  panic=1;@(negedge clk);if(left_out!==0||right_out!==0)$fatal(1,"panic");
  $display("PASS256 band voices plus singer:1024loaded+16release frames,atomic source release,zero drops/deadlines,panic; max_band_cycles=%0d peak_pcm16=%0d",maxcycles,peak);$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
