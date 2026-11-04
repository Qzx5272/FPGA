`timescale 1ns/1ps
module tb_partial;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,start=0,cv=0;reg [2:0] addr=0;reg [31:0] ph=0,inc=0;
 reg [15:0] env=0,target=0,slew=1;
 wire ready,initialized,done;wire signed [31:0] sum;wire [15:0] count;wire [31:0] misses;
 partial_lane #(.ADDRESS_BITS(3)) dut(clk,rst,start,cv,addr,ph,inc,env,target,slew,ready,initialized,done,sum,count,misses);
 integer i,n;integer before_sum;integer elapsed;
 task configure;input [2:0] a;input [31:0] p,f;input [15:0] e,t,s;
 begin wait(ready);@(negedge clk);addr=a;ph=p;inc=f;env=e;target=t;slew=s;cv=1;@(negedge clk);cv=0;end endtask
 task render;
 begin @(negedge clk);start=1;@(negedge clk);start=0;elapsed=0;
  while(!done)begin @(negedge clk);elapsed=elapsed+1;end
  if(elapsed>20||misses!=0)$fatal;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;wait(initialized);
  render();if(sum!=0||count!=0)$fatal;
  // Distinct amplitudes and phases expose a one-cycle gain tag misalignment.
  configure(0,32'h40000000,32'd1,16'd65535,16'd65535,1);
  configure(1,32'hc0000000,32'd2,16'd32768,16'd32768,1);
  configure(7,32'h40000000,32'd3,16'd16384,16'd16384,1);
  render();if(sum<98290||sum>98310||count!=3)begin $display("FAIL gain alignment sum=%0d count=%0d",sum,count);$fatal;end
  configure(0,32'h40000000,32'd1,16'd100,16'd0,16'd30);
  for(n=0;n<4;n=n+1)render();
  if(dut.env_ram.memory[0]!=0||count!=2)$fatal;
  if({dut.phase_hi.memory[1],dut.phase_lo.memory[1]}=={dut.phase_hi.memory[7],dut.phase_lo.memory[7]})$fatal;
  $display("PASS partial lane: independent phases, frequencies, gain alignment, envelopes, zero state, deadlines");$finish;
 end
 initial begin #100000;$fatal;end
endmodule
