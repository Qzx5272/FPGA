`timescale 1ns/1ps
module tb;
reg clk=0,rstn=0;always #10 clk=~clk;
wire serial,pixel,locked,ready;integer edges=0,start_edges,i,passno;realtime start_time,period;
GSR GSR(.GSRI(1'b1));gowin_video_clock dut(clk,rstn,serial,pixel,locked,ready);
always @(posedge serial)edges=edges+1;
initial begin #1000000;$fatal(1,"PLL lock or measurement timeout");end
initial begin
 #100;rstn=1;
 for(passno=0;passno<2;passno=passno+1)begin
  wait(ready);@(negedge pixel);start_time=$realtime;start_edges=edges;
  for(i=0;i<1000;i=i+1)begin @(negedge pixel);if(!locked||!ready)$fatal(1,"unexpected unlock");end
  period=($realtime-start_time)/1000.0;
  if(period<39.654421488||period>39.684421488||edges-start_edges!=5000)$fatal(1,"PLL frequency/ratio period%f edges%0d",period,edges-start_edges);
  $display("PASS segment%0d pixel_period_ns=%f serial_edges=%0d",passno,period,edges-start_edges);
  @(negedge clk);rstn=0;#1;if(ready)$fatal(1,"ready did not clear asynchronously");
  #200;if(ready)$fatal(1,"ready during reset");rstn=1;
 end
 $finish;
end
endmodule
