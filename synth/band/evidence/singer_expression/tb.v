`timescale 1ns/1ps
module tb_singer_expression;
 reg xv=0;reg[3:0]xp=15;reg[7:0]xs=2;reg[31:0]xe=2;reg[13:0]value=0;
 integer bank_updates=0;
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
 .command_valid(cv),.command_ready(cr),.command(cmd),.command_part(4'd15),.command_source(8'd2),
 .wet(7'd0),.master(7'd32),.tempo(8'd120),.transpose(8'd0),.status_part(4'd15),.status_owner(owner),.status_epoch(epoch),.active_voices(voices),.left_out(left_out),.right_out(right_out),.audio_valid(audio_valid),.deadline_miss(deadline_miss),.singer_dropped(singer_dropped),
 .source_lost(1'b0),.lost_source(8'd0),.upload_valid(1'b0),.upload_command(3'd0),.upload_index(32'd0),.upload_value(32'd0),.upload_aux(32'd0),
 .control_valid(xv),.control_part(xp),.control_source(xs),.control_epoch(xe),.control_parameter(4'd0),.control_value(value));

 always @(posedge clk)if(dut.bank_control_valid)bank_updates=bank_updates+1;
 task control(input[7:0]source,input[31:0]epoch,input[3:0]part,input[13:0]v);begin
  @(negedge clk);xs=source;xe=epoch;xp=part;value=v;xv=1;
  @(negedge clk);xv=0;repeat(12)@(negedge clk);
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;repeat(20)@(negedge clk);
  cv=1;while(!cr)@(negedge clk);@(negedge clk);cv=0;
  wait(owner==2);repeat(100)@(negedge clk);
  if(epoch!=2||dut.singer_expression!=127||dut.singer_scaled_mix!=100)$fatal(1,"Default/owner");
  control(2,2,15,64);if(dut.singer_expression!=64||dut.singer_scaled_mix!=50)$fatal(1,"Owner expression");
  control(3,2,15,0);if(dut.singer_expression!=64)$fatal(1,"Unauthorized control");
  control(2,1,15,0);if(dut.singer_expression!=64)$fatal(1,"Stale epoch control");
  control(1,0,15,0);if(dut.singer_scaled_mix!=0)$fatal(1,"Conductor silence");
  control(1,0,15,16383);if(dut.singer_scaled_mix!=100||dut.singer_expression!=127)$fatal(1,"Clamp");
  if(bank_updates!=0)$fatal(1,"Singer control leaked into choir bank");
  control(1,0,7,32);if(bank_updates!=1||dut.singer_expression!=127)$fatal(1,"Choir control isolation");
  $display("PASS singer expression:owner/epoch authorization,conductor,zero/max/clamp,choir isolation");$finish;
 end
 initial begin #1000000;$fatal(1,"Timeout");end
endmodule
