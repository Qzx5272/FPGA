`timescale 1ns/1ps
module tb_rom_song_loader_v6;
 reg clk=0,rst=1,request=0,ready=0,upload_pending=0,uploading=0;
 reg[7:0]selection=0;reg[31:0]upload_errors=0;
 wire valid,busy,failed;wire[223:0]payload;wire[7:0]current_song;
 integer commands=0,words_seen=0,recovery=0;
 always #5 clk=~clk;
 rom_song_loader #(.TIMEOUT_CYCLES(100000)) dut(clk,rst,request,selection,
  upload_pending,uploading,upload_errors,valid,ready,payload,busy,failed,current_song);
 always @(posedge clk)if(valid&&ready)begin
  commands=commands+1;
  if(payload[15:8]==13&&payload[63:56]<3)words_seen=words_seen+1;
  if(payload[15:8]==5&&(dut.state==10||dut.state==11))recovery=recovery+1;
 end
 task pulse_request;begin @(negedge clk);request=1;@(negedge clk);request=0;end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;ready=1;
  pulse_request();
  wait(dut.state==7);@(negedge clk);upload_pending=1;@(negedge clk);upload_pending=0;
  wait(!busy);if(failed||words_seen==0||current_song!=0)$fatal(1,"successful load failed");
  selection=8'hff;pulse_request();@(posedge clk);
  if(!failed||busy)$fatal(1,"bad selection not rejected");
  selection=1;ready=0;pulse_request();
  wait(dut.state==9);ready=1;wait(!busy);
  if(!failed||recovery!=2)$fatal(1,"timeout recovery sequence failed recovery=%0d",recovery);
  $display("PASS commands=%0d words=%0d recovery=%0d",commands,words_seen,recovery);$finish;
 end
 initial begin #2000000;$fatal(1,"test timeout state=%0d",dut.state);end
endmodule
