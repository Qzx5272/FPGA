`timescale 1ns/1ps
module tb_rom_equivalence;
 GSR GSR(.GSRI(1'b1));
 reg clk=0;always #10 clk=~clk;
 reg rst=1,valid=0;reg [31:0] phase=0,lfsr=32'h19483725;
 wire av,bv;wire signed [17:0] a,b;integer i,checked=0;
 hq_sine_quarter trial(clk,rst,valid,phase,av,a);
 hq_sine_reference reference(clk,rst,valid,phase,bv,b);
 always @(negedge clk)begin
  if(av!==bv)$fatal(1,"latency mismatch");
  if(av)begin if(a!==b)$fatal(1,"sample mismatch %d %d",a,b);checked=checked+1;end
 end
 initial begin
  repeat(8)@(posedge clk);#1;rst=0;
  for(i=0;i<1048576;i=i+1)begin
   @(posedge clk);#1;lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
   valid=(i%17)!=0;rst=(i%65536)==32768;
   if(i<16384)case(i%4)
    0:phase=(i/4)<<20;
    1:phase=((i/4)<<20)+32'h000fffff;
    2:phase=((i/4)<<20)+1;
    3:phase=((i/4)<<20)+32'h00080000;
   endcase
   else phase=lfsr;
  end
  @(posedge clk);#1;rst=0;valid=0;repeat(8)@(posedge clk);
  if(checked<900000)$fatal(1,"insufficient samples");
  $display("PASS exact ROM equivalence: checked=%0d, all segment boundaries/quadrants, random fractions, valid bubbles and reset",checked);$finish;
 end
endmodule
