`timescale 1ns/1ps
module tb_voice;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,tick=0,panic=0,enable=1;
 reg [7:0] keys=1;
 reg [2:0] unit=0;
 wire signed [15:0] sample;wire active;
 voice_engine dut(clk,rst,tick,panic,enable,keys,3'd4,unit,7'd80,7'd100,16'd150,16'd150,sample,active);
 integer f,i,j;integer peak=0;
 task frame;
 begin
   @(negedge clk);tick=1;@(negedge clk);tick=0;
   repeat(1039)@(negedge clk);
   if(^sample===1'bx)begin $display("FAIL unknown output");$finish;end
   if(sample>peak)peak=sample;
   $fwrite(f,"%0d\n",sample);
 end
 endtask
 initial begin
   f=$fopen("synth/test-output/voice_samples.txt","w");
   repeat(4)@(negedge clk);rst=0;
   for(j=0;j<8;j=j+1)begin
     unit=j;
     for(i=0;i<7200;i=i+1)frame;
   end
   keys=0;for(i=0;i<1000;i=i+1)frame;
   if(sample!=0||active)begin $display("FAIL release");$finish;end
   keys=1;for(i=0;i<1000;i=i+1)frame;
   panic=1;repeat(4)@(negedge clk);
   if(sample!=0||active)begin $display("FAIL panic");$finish;end
   if(peak<100)begin $display("FAIL silent output");$finish;end
   $fclose(f);$display("PASS voice synthesis, release, panic; peak=%0d",peak);$finish;
 end
endmodule
