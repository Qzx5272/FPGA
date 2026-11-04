`timescale 1ns/1ps
module tb_audio_pt8211_queue;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,valid=0;reg signed[15:0] l=0,r=0;
 wire ready,tick,bck,ws,din;wire[31:0]drops,under;wire[2:0]queued;
 audio_pt8211_queue #(.START_FRAMES(1)) dut(clk,rst,panic,valid,l,r,ready,tick,bck,ws,din,drops,under,queued);
 integer bits=0,seen=0,expected=1;reg[31:0] shift=0;reg[15:0] er,el;
 always @(posedge bck) if(!rst&&!panic)begin
  shift={shift[30:0],din};bits=bits+1;
  if(bits==16&&ws!==0)$fatal(1,"Right slot WS");
  if(bits==32)begin
   if(ws!==1)$fatal(1,"Left slot WS");
   bits=0;
   if(shift!=0)begin
    er=16'h2000+expected;el=16'h1000+expected;
    if(shift!=={er,el})$fatal(1,"FIFO order expected %h got %h",{er,el},shift);
    seen=seen+1;expected=expected+1;
   end
  end
 end
 task send(input integer n);begin
  @(negedge clk);while(!ready)@(negedge clk);
  l=16'h1000+n;r=16'h2000+n;valid=1;
  @(negedge clk);valid=0;
 end endtask
 integer n;
 initial begin
  repeat(5)@(negedge clk);rst=0;
  // Enqueue exactly when the serializer captures an empty head: frame must
  // remain queued for the next DAC frame, not be consumed unheard.
  while(!(dut.serializer.next_accum>=50000000&&dut.serializer.bck&&dut.serializer.bitpos==0))@(negedge clk);
  valid=1;l=16'h1001;r=16'h2001;
  @(negedge clk);valid=0;
  send(2);send(3);send(4);
  @(negedge clk);if(ready||queued!=4)$fatal(1,"Queue not full");
  valid=1;l=16'h7fff;r=16'h7fff;
  @(negedge clk);valid=0;
  if(drops!=1)$fatal(1,"Overflow counter");
  for(n=5;n<=10;n=n+1)send(n);
  wait(seen==10);repeat(2200)@(negedge clk);
  if(under==0||drops!=1||queued!=0)$fatal(1,"Drain counters");
  // Queue new PCM then panic before it reaches DAC. All state is flushed.
  send(11);@(negedge clk);panic=1;
  repeat(3)@(negedge clk);
  if(queued||drops||under||din)$fatal(1,"Panic failed");
  bits=0;shift=0;panic=0;
  repeat(2200)@(negedge clk);
  if(seen!=10||under!=0)$fatal(1,"Stale audio after panic");
  $display("PASS PT8211: 10 decoded stereo frames, latch-edge enqueue, overflow, drain, panic");$finish;
 end
 initial begin #1000000;$fatal(1,"Timeout");end
endmodule
