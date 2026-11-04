`timescale 1ns/1ps
module tb_input_bridge;
 reg bck=0,core_clk=0;always #5 bck=~bck;always #13 core_clk=~core_clk;
 reg rst=1,ws=0,sd=0,frame_pop=1;
 wire frame_valid;wire [47:0] frame_data;wire [31:0] framing_errors_bck,overruns_bck;
 i2s_input_bridge dut(.*);
 integer received=0,i;reg check_order=1;
 reg [47:0] expected;
 always @(posedge core_clk)if(!rst&&frame_pop&&frame_valid&&check_order)begin
  received=received+1;expected={24'(received*12345),24'(-received*789)};
  if(frame_data!==expected)$fatal(1,"input CDC ordering %d got %h expected %h",received,frame_data,expected);
 end
 task bit_tick;input channel,data;
 begin @(negedge bck);ws=channel;sd=data;@(posedge bck);#2;end endtask
 task word;input channel;input [23:0] data;integer j;
 begin bit_tick(channel,0);for(j=1;j<32;j=j+1)bit_tick(channel,j<=24?data[24-j]:1'b1);end endtask
 initial begin
  repeat(4)@(negedge bck);rst=0;repeat(6)@(negedge bck);
  word(1,0);
  for(i=1;i<=100;i=i+1)begin word(0,i*12345);word(1,-i*789);end
  bit_tick(0,0);repeat(5)@(negedge core_clk);
  if(received!=100||framing_errors_bck||overruns_bck)$fatal(1,"normal input CDC counters");
  frame_pop=0;check_order=0;
  repeat(31)bit_tick(0,0);word(1,0);
  for(i=0;i<12;i=i+1)begin word(0,24'habcdef);word(1,24'h123456);end
  bit_tick(0,0);
  if(overruns_bck==0)$fatal(1,"congestion not detected");
  // Flush unread FIFO and held receiver word; no stale sample may cross reset.
  @(negedge bck);rst=1;repeat(4)@(negedge core_clk);
  if(frame_valid||overruns_bck||framing_errors_bck)$fatal(1,"reset flush");
  rst=0;received=0;check_order=1;frame_pop=1;repeat(6)@(negedge bck);
  word(1,0);word(0,12345);word(1,-789);bit_tick(0,0);repeat(5)@(negedge core_clk);
  if(received!=1||overruns_bck||framing_errors_bck)$fatal(1,"post-reset frame");
  $display("PASS input CDC:100 exact ordered stereo frames across unrelated clocks, congestion detected, FIFO and receiver reset flushed, fresh frame after reset");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
