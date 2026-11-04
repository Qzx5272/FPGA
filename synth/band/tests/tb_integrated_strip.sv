`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,valid=0;
 reg signed [15:0] left=0,right=0;
 wire data;
 always #10 clk=~clk;
 rhythm_strip #(.LED_COUNT(3)) dut(clk,rst,valid,left,right,data);
 task decode(output reg[23:0] word);
 integer i,high_cycles;reg[23:0] current_word;time started;
 begin
  for(i=0;i<72;i=i+1)begin
   @(posedge data);
   if(i!=0&&$time-started!=1260)$fatal(1,"bit period");
   started=$time;@(negedge data);high_cycles=($time-started)/20;
   if(high_cycles!=16&&high_cycles!=33)$fatal(1,"pulse width");
   current_word={current_word[22:0],high_cycles==33};
   if(i==23)word=current_word;
   if(i%24==23&&current_word!==word)$fatal(1,"torn frame");
  end
 end endtask
 reg[23:0]w;time ended;
 initial begin
  repeat(4)@(negedge clk);rst=0;decode(w);if(w!==0)$fatal(1,"startup");
  valid=1;right=-32768;ended=$time;@(posedge data);
  if($time-ended<280000)$fatal(1,"latch gap");
  wait(!dut.sending);decode(w);if(w!==24'h402000)$fatal(1,"right channel, first attack %h",w);
  @(negedge clk);right=0;repeat(25000)@(negedge clk);wait(!dut.sending);decode(w);if(w!==0)$fatal(1,"silence");
  @(negedge clk);left=2048;wait(dut.sending);wait(!dut.sending);decode(w);
  if(w==0||w[23:16]==0||w[15:8]!=0||w[7:0]==0)$fatal(1,"left channel, second hue %h",w);
  $display("PASS GRB data, bit widths, latch, whole frame, stereo attacks, hue change and silence");$finish;
 end
 initial #20000000 $fatal(1,"timeout");
endmodule
