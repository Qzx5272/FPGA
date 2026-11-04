`timescale 1ns/1ps
module tb_allocator;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,ev=0;wire ready;reg [1:0] kind=0;
 reg [7:0] src=1,contact=1;reg [3:0] part=0;reg [31:0] epoch=1,serial=1;
 reg [6:0] note=60,vel=100;reg retire=0;reg [1:0] retire_slot=0,q=0;reg [31:0] rg=0;
 wire active,gate,done,exhausted;wire [6:0] qn,qv;wire [3:0] qp;wire [31:0] gen,rejected,stale,dups;
 note_allocator #(.VOICES(4),.INDEX_BITS(2)) dut(clk,rst,panic,ev,ready,kind,src,contact,part,epoch,serial,note,vel,retire,retire_slot,rg,q,active,gate,qn,qv,qp,gen,done,rejected,stale,dups,exhausted);
 task send;input [1:0] k;input [7:0] s;input [31:0] seq;
 begin wait(ready);@(negedge clk);kind=k;src=s;serial=seq;ev=1;@(negedge clk);ev=0;wait(done);@(negedge clk);end endtask
 task check;input [1:0] slot;input a,g;
 begin q=slot;#1;if(active!==a||gate!==g)begin $display("FAIL slot %0d active/gate %b/%b expected %b/%b",slot,active,gate,a,g);$fatal;end end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  send(0,1,1);check(0,1,1);send(0,1,1);if(dups!=1)$fatal;
  send(0,2,1);check(1,1,1); // same pitch, independent source
  send(1,1,0);check(0,1,1);if(stale!=1)$fatal;
  send(1,1,1);check(0,1,0);check(1,1,1);
  send(0,1,2);check(2,1,1); // release tail still occupies slot 0
  send(1,1,1);check(2,1,1); // old release cannot kill retrigger
  @(negedge clk);retire=1;retire_slot=0;rg=999;@(negedge clk);retire=0;check(0,1,0);
  rg=gen;@(negedge clk);retire=1;@(negedge clk);retire=0;check(0,0,0);
  send(0,3,1);check(0,1,1);send(0,4,1);check(3,1,1);
  send(0,5,1);if(rejected!=1)$fatal;
  send(2,2,0);check(1,1,0);check(2,1,1);
  send(3,0,0);check(0,1,0);check(2,1,0);check(3,1,0);
  @(negedge clk);ev=1;@(negedge clk);panic=1;ev=0;@(negedge clk);panic=0;
  check(0,0,0);check(1,0,0);check(2,0,0);check(3,0,0);
  $display("PASS allocator: identities, duplicate, stale release, tail, generation, capacity, source, part, panic");$finish;
 end
 initial begin #100000;$fatal;end
endmodule
