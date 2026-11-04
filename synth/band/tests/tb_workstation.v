`timescale 1ns/1ps
module tb_workstation;
 reg clk=0,audio_clk=0;always #10 clk=~clk;always #20.345052 audio_clk=~audio_clk;
 reg [9:0] dout=0;wire cs,sclk,din,tx,bclk,lr,data;wire [3:0] leds;
 reg play=0,stop=0,panic=0;reg [3:0] root=0;reg [11:0] lead_pressure=0,drum_pressure=0,expression=0,bend=0;
 workstation_top dut(clk,audio_clk,1'b1,tx,dout,cs,sclk,din,play,stop,panic,root,1'b0,bclk,lr,data,leds);
 integer edges=0,i,raw;reg [31:0] command=0;reg [2:0] selected=0;reg [31:0] misses;
 always @(negedge cs)begin edges=0;command=0;dout=0;end
 always @(posedge sclk)if(!cs)begin edges=edges+1;command={command[30:0],din};end
 always @(negedge sclk)if(!cs)begin
  if(edges==18)selected=command[2:0];
  for(i=0;i<10;i=i+1)begin
   raw=selected==0?(i==0?lead_pressure:i==2?drum_pressure:i==8?expression:i==9?bend:0):0;
   dout[i]=(edges>=20&&edges<32)?((raw>>(31-edges))&1):0;
  end
 end
 initial begin
  wait(!dut.rst);repeat(30000)@(negedge clk); // establish released baselines and initialize effects
  lead_pressure=2500;drum_pressure=3500;
  wait(leds[1:0]==3);wait(dut.left!=0);
  if(dut.engine.core.ownership.owners[6]!=17||dut.engine.core.ownership.owners[0]!=18)$fatal(1,"local ownership");
  misses=dut.underruns;repeat(20000)@(negedge clk);
  if(dut.dropped!=0||dut.underruns!=misses||dut.engine.deadline_miss!=0)$fatal(1,"steady audio service");
  expression=1024;bend=3072;
  wait(dut.engine.core.banks[6].unit.target_expression[0]==32);
  wait(dut.engine.core.banks[6].unit.target_bend[0]==192);
  root=9;lead_pressure=0;wait(!leds[0]);repeat(100)@(negedge clk);
  if(dut.engine.core.banks[6].unit.allocator.gate!=0)$fatal(1,"old note release after key change");
  panic=1;repeat(10)@(negedge clk);if(dut.left!=0||leds!=0)$fatal(1,"physical panic");
  panic=0;repeat(40000)@(negedge clk);if(leds!=0)$fatal(1,"held pad retriggered after panic");
  $display("PASS soldered-peripheral integration RTL: two ADC seats, independent expression/pitch -> ownership -> band voices -> asynchronous I2S; key change release, physical panic and held-pad inhibition");$finish;
 end
 initial begin #12000000;$fatal(1,"timeout");end
endmodule
