`timescale 1ns/1ps
module tb_pool;
 parameter LB=3;
 localparam N=1<<(LB+9);
 reg clk=0;always #10 clk=~clk;
 reg rst=1,start=0,cv=0;reg [LB+8:0] address=0;reg [31:0] phase=0,inc=0;
 wire ready,initialized,valid;wire signed [23:0] sample;
 wire [15:0] count,cycles;wire [31:0] misses;
 partial_pool #(.LANE_BITS(LB)) dut(clk,rst,start,cv,address,phase,inc,16'd50000,16'd60000,16'd17,ready,initialized,valid,sample,count,cycles,misses);
 integer i,n,f;integer frames=32;
 initial begin
  if($value$plusargs("frames=%d",frames))begin end
  f=$fopen("synth/band/evidence/pool_samples.txt","w");
  repeat(3)@(negedge clk);rst=0;wait(initialized);
  for(i=0;i<N;i=i+1)begin
   @(negedge clk);cv=1;address=i;phase=i*32'h9e3779b9;
   // Coherent bins 50+5*i in a 131072-sample record, below Nyquist for 8192.
   inc=(50+5*i)*32768;
  end
  @(negedge clk);cv=0;
  for(n=0;n<frames;n=n+1)begin
   @(negedge clk);start=1;@(negedge clk);start=0;wait(valid);#1;
   if(count!=N||cycles>=1041||misses!=0||sample===24'bx)begin $display("FAIL pool %0d count=%0d cycles=%0d",N,count,cycles);$fatal;end
   $fwrite(f,"%0d\n",sample);
   @(negedge clk);
  end
  $fclose(f);$display("PASS pool capacity=%0d active=%0d cycles=%0d frames=%0d",N,count,cycles,frames);$finish;
 end
 initial begin #100000000000;$fatal;end
endmodule
