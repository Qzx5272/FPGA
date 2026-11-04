`timescale 1ns/1ps
module tb_hello;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,tick=0,panic=0,enable=1,gate=0,slow=0;
 wire signed [15:0] sample;wire active;
 hello_engine dut(clk,rst,tick,panic,enable,gate,slow,7'd127,7'd100,sample,active);
 integer f,i,peak=0;
 task frame;
 begin
   @(negedge clk);tick=1;@(negedge clk);tick=0;
   repeat(1039)@(negedge clk);
   if(^sample===1'bx)begin $display("FAIL unknown hello");$finish;end
   if(sample>peak)peak=sample;
   if(sample==32767||sample==-32768)begin $display("FAIL clipped hello");$finish;end
   $fwrite(f,"%0d\n",sample);
 end
 endtask
 initial begin
   f=$fopen("synth/test-output/hello_samples.txt","w");
   repeat(4)@(negedge clk);rst=0;gate=1;
   for(i=0;i<64000;i=i+1)frame;
   if(sample!=0||active)begin $display("FAIL hello completion");$finish;end
   // Holding the trigger must not automatically loop.
   for(i=0;i<500;i=i+1)frame;
   if(active)begin $display("FAIL hello loop");$finish;end
   gate=0;frame;slow=1;gate=1;
   for(i=0;i<721;i=i+1)frame;
   if(!active||dut.frame!=1)begin $display("FAIL slow timing");$finish;end
   panic=1;repeat(4)@(negedge clk);
   if(sample!=0||active)begin $display("FAIL hello panic");$finish;end
   if(peak<100)begin $display("FAIL silent hello");$finish;end
   $fclose(f);$display("PASS dynamic hello: completion, no loop, slow timing, panic, no clipping; peak=%0d",peak);$finish;
 end
endmodule
