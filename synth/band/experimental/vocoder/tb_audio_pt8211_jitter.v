`timescale 1ns/1ps
module tb_audio_pt8211_jitter;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,valid=0;reg[15:0]l=0,r=0;
 wire ready,tick,bck,ws,din;wire[31:0]drops,under;wire[2:0]queued;
 audio_pt8211_queue dut(clk,rst,1'b0,valid,l,r,ready,tick,bck,ws,din,drops,under,queued);
 integer cycle=0,n=0,bits=0,seen=0;reg[31:0]shift=0;reg[15:0]el,er;
 always @(negedge clk)if(!rst)begin
  valid=0;
  // Alternate light/full render completion, including a >1 sample gap.
  if(n<12&&cycle==n*1042+(n%2?1090:200))begin
   if(!ready)$fatal(1,"No queue space");valid=1;l=16'h1001+n;r=16'h2001+n;n=n+1;
  end
  cycle=cycle+1;
 end
 always @(posedge bck)if(!rst)begin
  shift={shift[30:0],din};bits=bits+1;
  if(bits==32)begin
   bits=0;
   if(shift!=0)begin
    el=16'h1001+seen;er=16'h2001+seen;
    if(shift!=={er,el})$fatal(1,"Jitter reordered PCM");seen=seen+1;
   end else if(seen>0&&seen<12)$fatal(1,"Jitter inserted silence");
   if(seen==12)begin
    if(drops||under)$fatal(1,"Jitter counters nonzero");
    $display("PASS PT8211 prefill:12 decoded frames alternating200/1090cycle completion,no silence/drop/underrun");$finish;
   end
  end
 end
 initial begin repeat(5)@(posedge clk);#1;rst=0;end
 initial begin #500000;$fatal(1,"Timeout");end
endmodule
