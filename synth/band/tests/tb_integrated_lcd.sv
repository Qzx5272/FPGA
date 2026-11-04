`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,de=0;reg[17:0]rgb=0;wire od;wire[17:0]oc;
 always #20 clk=~clk;
 lcd_output_stage dut(clk,rst,de,rgb,od,oc);
 integer i,count=0;reg expected_de;reg[17:0]expected_rgb;
 initial begin
  for(i=0;i<10000;i=i+1)begin
   @(negedge clk);
   rst=i<3||i==5000;
   de=(i%1192)>=182&&(i%1192)<982;
   rgb=$random;
   expected_de=!rst&&de;expected_rgb=expected_de?rgb:0;
   @(posedge clk);#1;
   if(od!==expected_de||oc!==expected_rgb)$fatal(1,"RGB/DE output pipeline mismatch");
   if(od)count=count+1;
  end
  if(count<6000)$fatal(1,"missing active pixels");
  $display("PASS LCD registered RGB/DE alignment, blanking, reset, 10000 pixels");$finish;
 end
endmodule
