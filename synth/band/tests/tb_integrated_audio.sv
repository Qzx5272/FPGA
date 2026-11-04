`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,halt=0,valid=0;always #10 clk=~clk;
 reg[15:0]left=16'h8123,right=16'h7654;
 wire bck,ws,sd,tick,mv,ready;wire signed[23:0]mic;wire[31:0]drop,under;
 tri micwire;reg drive=0,enable=0;assign micwire=enable?drive:1'bz;pullup(micwire);
 audio48_duplex #(.WARMUP(4)) dut(clk,rst,halt,valid,left,right,micwire,bck,ws,sd,tick,mic,mv,drop,under,ready);
 reg prevws=1;integer slot=0,rx=0,tx=0;reg[23:0]expected=24'h812345;
 always @(negedge bck)if(!rst)begin
  #1;if(ws!=prevws)begin slot=0;prevws=ws;end else slot=slot+1;
  if(!ws&&slot>=1&&slot<=24)begin enable<=#69 1;drive<=#69 expected[24-slot];end else enable<=#69 0;
 end
 always @(negedge clk)begin
  valid=0;if(!rst&&tick&&!halt)valid=1;
  if(mv)begin if(mic!==expected)$fatal(1,"mic %h != %h",mic,expected);rx=rx+1;expected=~expected;end
 end
 reg tws=0;integer tslot=0;reg[15:0]word=0,lword=0;
 always @(posedge bck)if(!rst)begin
  if(ws!=tws)begin tws=ws;tslot=0;end else tslot=tslot+1;
  if(tslot>=1&&tslot<=16)word={word[14:0],sd};
  if(tslot==16)begin
   if(!ws)lword=word;
   else if(!halt&&(lword!=0||word!=0))begin
    if(lword!==left||word!==right)$fatal(1,"DAC %h %h",lword,word);tx=tx+1;
   end
  end
  if(tslot>=17&&tslot<=31&&sd!==0)$fatal(1,"padding");
 end
 initial begin
  repeat(8)@(negedge clk);rst=0;
  wait(rx>=64&&tx>=64);@(negedge clk);
  if(drop||under)$fatal(1,"queue loss %d %d",drop,under);
  halt=1;repeat(3000)@(negedge clk);if(sd!==0||!ready)$fatal(1,"halt");
  halt=0;wait(tx>=68);if(drop||under)$fatal(1,"restart queue");
  $display("PASS 64-slot I2S, signed stereo, 70ns tri-state mic, queue, halt/restart");$finish;
 end
 initial begin #4000000;$fatal(1,"timeout");end
endmodule
