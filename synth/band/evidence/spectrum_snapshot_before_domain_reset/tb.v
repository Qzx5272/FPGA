`timescale 1ns/1ps
module tb;
reg ac=0,dc=0,run=1;always #5 ac=~ac;always #13 if(run)dc=~dc;
reg rst=1,bv=0,ren=0,rel=0;wire br,available,rv;
reg[10:0]bi=0,addr=0;reg signed[15:0]xr=0,xi=0;wire signed[15:0]yr,yi;
reg[31:0]fid=7,last=9999;wire[31:0]ofid,olast,rejects;wire[16:0]pl,pr;
integer i;
spectrum_snapshot dut(ac,dc,rst,bv,br,bi,xr,xi,fid,last,17'd32768,17'd1234,ren,addr,rel,available,rv,yr,yi,ofid,olast,pl,pr,rejects);
task put(input integer k);begin
 @(negedge ac);while(!br)@(negedge ac);bi=k;xr=k-1024;xi=1024-k;bv=1;
 @(negedge ac);bv=0;
end endtask
initial begin
 repeat(4)@(negedge dc);rst=0;
 put(1);if(rejects!=1)$fatal(1,"out of order not rejected");
 put(0);fid=8;put(1);if(rejects!=2)$fatal(1,"mixed frame not rejected");fid=7;
 @(negedge dc);run=0;
 for(i=0;i<2048;i=i+1)put(i);
 if(br)$fatal(1,"full frame not frozen");
 // Producer may hold next valid while display is absent; RAM stays frozen.
 bv=1;bi=0;xr=123;xi=456;fid=9;repeat(200)@(negedge ac);
 if(br||rejects!=2)$fatal(1,"reader backpressure");run=1;
 wait(available);@(negedge dc);
 if(ofid!=7||olast!=9999||pl!=32768||pr!=1234)$fatal(1,"metadata");
 for(i=0;i<2048;i=i+1)begin
  ren=1;addr=i;@(negedge dc);
  if(!rv||yr!=i-1024||yi!=1024-i)$fatal(1,"frozen bin mismatch %d",i);
 end
 // Release wins over a simultaneous read and retracts valid.
 rel=1;@(negedge dc);rel=0;ren=0;
 if(available||rv)$fatal(1,"release/read collision");
 wait(br);@(posedge ac);#1;@(negedge ac);bv=0; // first bin accepted on ready/valid edge
 if(dut.expected!=1)$fatal(1,"held producer did not resume exactly once");
 for(i=1;i<2048;i=i+1)put(i);
 wait(available);@(negedge dc);if(ofid!=9)$fatal(1,"next frame identity");
 ren=1;addr=0;@(negedge dc);if(yr!=123||yi!=456)$fatal(1,"next frame data");
 run=0;rst=1;repeat(3)@(negedge ac);rst=0;
 if(available||rv||rejects)$fatal(1,"stopped display reset");run=1;
 repeat(5)@(negedge dc);if(available||rv)$fatal(1,"stale publication after reset");
 $display("PASS spectrum snapshot2048:two complete frames,all bins,metadata,stopped reader,backpressure,ordering,release collision,reset");$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
