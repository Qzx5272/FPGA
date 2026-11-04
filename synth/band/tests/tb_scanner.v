`timescale 1ns/1ps
module tb_scanner;
 reg clk=0;always #10 clk=~clk;
 reg rst=1;reg [9:0] dout=0;wire cs,sclk,din,valid;wire [2:0] channel;wire [119:0] samples;
 mcp3208_scanner dut(clk,rst,dout,cs,sclk,din,valid,channel,samples);
 integer edges=0,i,conversions=0;reg [31:0] command=0;integer expected;reg [2:0] selected;
 time high_start=0;
 always @(negedge cs)begin
  if($time-high_start<500)begin $display("FAIL CS high timing");$fatal;end
  edges=0;command=0;dout=0;
 end
 always @(posedge sclk)if(!cs)begin edges=edges+1;command={command[30:0],din};end
 always @(negedge sclk)if(!cs)begin
  if(edges==18)selected=command[2:0];
  for(i=0;i<10;i=i+1)begin
   expected=i*257+selected*37;
   dout[i]=(edges>=20&&edges<32)?((expected>>(31-edges))&1):0;
  end
 end
 always @(posedge cs)begin high_start=$time;end
 always @(posedge clk)if(valid)begin
  if(edges!=32||command[18:14]!={2'b11,channel})begin $display("FAIL ADC command %h channel %d",command,channel);$fatal;end
  for(i=0;i<10;i=i+1)if(samples[i*12+:12]!==i*257+channel*37)begin $display("FAIL ADC %d channel %d value %d",i,channel,samples[i*12+:12]);$fatal;end
  conversions=conversions+1;
  if(conversions==16)begin $display("PASS MCP3208: 10 independent DOUT, all channels twice, command and CS timing");$finish;end
 end
 initial begin repeat(3)@(negedge clk);rst=0;end
 initial begin #2000000;$fatal;end
endmodule
