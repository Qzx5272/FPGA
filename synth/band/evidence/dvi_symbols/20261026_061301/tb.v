`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg[27:0]s;reg[27:0]stimulus[0:19999];reg[29:0]expected[0:19999];
wire[9:0]blue,green,red;integer i;
dvi_symbols dut(clk,s[27],s[26],s[25],s[24],s[23:0],blue,green,red);
initial begin
$readmemh("stimulus.hex",stimulus);$readmemh("expected.hex",expected);s=0;
for(i=0;i<20000;i=i+1)begin
 @(negedge clk);s=stimulus[i];@(posedge clk);#1;
 if(i>=2&&{red,green,blue}!==expected[i])$fatal(1,"TMDS RGB/sync mismatch index%0d got%h expected%h",i,{red,green,blue},expected[i]);
end
$display("PASS 20000 cycles:3 RGB lanes,sync controls,reset flush,disparity coding");$finish;
end
endmodule
