`timescale 1ns/1ps
module tb_cdc;
 reg wc=0,rc=0;always #10 wc=~wc;always #20.345052 rc=~rc;
 reg rst=1,panic=0,sv=0;reg signed [23:0] l=0,r=0;
 wire tick,bck,ws,sd;wire [31:0] drops,underruns;
 audio_i2s_bridge dut(wc,rc,rst,panic,sv,l,r,tick,bck,ws,sd,drops,underruns);
 integer delay=0,generated=0,received=0,frames=0,slot=-1,checked=0;
 reg [47:0] expected=0;reg [23:0] channel=0;reg started=0;
 always @(negedge wc)begin
  sv=0;
  if(!rst&&!panic)begin
   if(tick)delay=23;
   if(delay>0)begin delay=delay-1;if(delay==0)begin generated=generated+1;l=generated*12345;r=-generated*2345;sv=1;end end
  end
 end
 always @(negedge rc)if(!rst&&!panic&&dut.serializer.div==7&&dut.serializer.slot==0)begin
  expected=dut.valid?dut.frame:0;slot=-1;started=1;frames=frames+1;
  if(dut.valid)begin received=received+1;if(dut.frame!={24'(received*12345),24'(-received*2345)})$fatal(1,"FIFO order/payload");end
 end
 always @(posedge bck)if(started&&!rst&&!panic)begin
  slot=slot+1;if(ws!==(slot>=32))$fatal(1,"WS");
  if(slot%32>=1&&slot%32<=24)channel={channel[22:0],sd};else if(sd!==0)$fatal(1,"padding");
  if(slot==24||slot==56)begin if(channel!==(slot==24?expected[47:24]:expected[23:0]))$fatal(1,"I2S payload");checked=checked+1;end
  if(frames==1000&&slot==63)begin
   if(drops!=0||underruns!=1||received!=999||checked!=2000)$fatal(1,"counters");
   $display("PASS asynchronous audio bridge: 999 ordered stereo frames, exact I2S24 words, one startup silence, zero drops");$finish;
  end
 end
 initial begin repeat(10)@(negedge wc);rst=0;end
 initial begin #22000000;$fatal(1,"timeout");end
endmodule
