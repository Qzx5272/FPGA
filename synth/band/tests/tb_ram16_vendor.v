`timescale 1ns/1ps
module tb_ram16_vendor;
 reg clk=0;always #10 clk=~clk;
 GSR GSR(.GSRI(1'b1));
 reg we=0,re=0;reg [8:0] wa=0,ra=0;reg [15:0] data=0;
 wire [15:0] q;reg [15:0] expected[0:511];integer i;
 partial_ram16 dut(clk,we,re,wa,ra,data,q);
 initial begin
  repeat(4)@(negedge clk);
  for(i=0;i<512;i=i+1)begin wa=i;data=(i*3181)^16'h8c37;expected[i]=data;we=1;@(negedge clk);end
  we=0;re=1;
  for(i=0;i<512;i=i+1)begin ra=i;@(negedge clk);if(q!==expected[i])$fatal(1,"vendor RAM mismatch addr=%0d got=%h expected=%h pcea=%b pceb=%b memory=%h",i,q,expected[i],dut.ram.pcea,dut.ram.pceb,dut.ram.ram_MEM[15:0]);end
  re=0;ra=0;repeat(4)@(negedge clk);if(q!==expected[511])$fatal(1,"read enable ignored");
  $display("PASS vendor SDPB16: all 512 addresses, 16-bit words and held read output");$finish;
 end
endmodule
