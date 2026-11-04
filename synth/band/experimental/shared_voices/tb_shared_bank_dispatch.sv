`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,panic=0,ev=0;
 reg [1:0] ek=0;reg [7:0] es=2,ec=0;reg [3:0] ep=6;
 reg [31:0] ee=1,ei=0;reg [6:0] en=60,el=100;
 wire ready,done,probe;wire [7:0] br,bd,bm,bc,bv;
 wire [7:0] ready_raw,done_raw;reg [7:0] allow_ready=255;
 reg [2:0] slow_done=0;
 assign br=ready_raw&allow_ready;
 assign bd={slow_done[2],done_raw[6:0]};
 always @(posedge clk)if(rst||panic)slow_done<=0;else slow_done<={slow_done[1:0],done_raw[7]};
 wire [1:0] k;wire [7:0] s,c;wire [3:0] p;wire [31:0] e,id;
 wire [6:0] n,v;wire [31:0] rejected,duplicates;
 shared_bank_dispatch router(clk,rst,panic,ev,ready,ek,es,ec,ep,ee,ei,en,el,
  br,bd,bm,bc,bv,probe,k,s,c,p,e,id,n,v,done,rejected,duplicates);
 reg [4:0] query=0,rs=0;reg [7:0] retire=0;reg [31:0] rg=0;
 wire [7:0] active,gate;wire [31:0] generation[0:7];
 wire [31:0] local_rejected[0:7];
 genvar b;
 generate for(b=0;b<8;b=b+1)begin:banks
  wire [6:0] note,vel;wire [3:0] part;wire [31:0] stale,dup;wire exhausted;
  shared_note_allocator a(clk,rst,panic,bv[b],ready_raw[b],k,s,c,p,e,id,n,v,
   retire[b],rs,rg,query,active[b],gate[b],note,vel,part,generation[b],
   done_raw[b],local_rejected[b],stale,dup,exhausted,probe,bm[b],bc[b],);
 end endgenerate
 integer i,j,ac,gc;reg [31:0] oldgen,newgen;
 task send(input [1:0] kind,input [31:0] serial);
 begin
  @(negedge clk);while(!ready)@(negedge clk);
  ek=kind;ei=serial;ev=1;
  @(negedge clk);ev=0;
  while(!done)@(negedge clk);
 end endtask
 task count(input integer expected_active,input integer expected_gates);
 begin
  ac=0;gc=0;
  for(i=0;i<32;i=i+1)begin
   @(negedge clk);query=i;#1;
   for(j=0;j<8;j=j+1)begin ac=ac+active[j];gc=gc+gate[j];end
  end
  if(ac!==expected_active||gc!==expected_gates)
   $fatal(1,"count active=%0d gate=%0d expected=%0d/%0d",ac,gc,expected_active,expected_gates);
 end endtask
 task retire0(input [31:0] gen);
 begin @(negedge clk);rs=0;rg=gen;retire=1;@(negedge clk);retire=0;end
 endtask
 initial begin
  repeat(4)@(negedge clk);rst=0;
  // All256 identities belong to the SAME musical role and contact.
  for(integer t=0;t<256;t=t+1)send(0,t);
  count(256,256);
  if(rejected||duplicates)$fatal(1,"premature reject");
  for(j=0;j<8;j=j+1)if(local_rejected[j])$fatal(1,"bank reject");
  send(0,0);count(256,256);
  if(duplicates!=1)$fatal(1,"duplicate allocated to another bank");
  send(0,256);if(rejected!=1)$fatal(1,"full not rejected");
  send(1,0);count(256,255);
  send(0,999);if(rejected!=2)$fatal(1,"tail slot stolen");
  @(negedge clk);query=0;#1;oldgen=generation[0];
  retire0(oldgen);count(255,255);
  send(0,999);count(256,256);
  send(1,0);count(256,256); // Old serial cannot release replacement.
  @(negedge clk);query=0;#1;newgen=generation[0];
  if(newgen==oldgen)$fatal(1,"generation reused");
  send(1,999);retire0(oldgen);count(256,255);
  retire0(newgen);count(255,255);
  send(3,0);count(255,0); // Part release spans all banks, tails retained.
  @(negedge clk);panic=1;@(negedge clk);panic=0;count(0,0);
  send(0,1000);es=3;send(0,1001);es=2;send(2,0);count(2,1);
  // Panic during a probe cancels the transaction and clears all banks.
  @(negedge clk);while(!ready)@(negedge clk);ek=0;ei=1002;ev=1;
  @(negedge clk);ev=0;
  wait(probe);@(negedge clk);panic=1;@(negedge clk);panic=0;
  repeat(80)@(negedge clk);count(0,0);
  if(!ready)$fatal(1,"panic left router busy");
  // One unavailable bank must block the atomic probe without partial accepts.
  @(negedge clk);allow_ready=127;ek=0;ei=2000;ev=1;
  @(negedge clk);ev=0;ei=3000; // Producer changes payload after acceptance.
  repeat(20)begin @(negedge clk);if(bv||ready||done)$fatal(1,"backpressure bypass");end
  if(id!=2000)$fatal(1,"captured identity changed");
  allow_ready=255;while(!done)@(negedge clk);count(1,1);
  send(1,2000);count(1,0);
  $display("PASS shared256 same-role identities, duplicates, full rejection, tails, stale releases/retirement, source/part release, probe panic");
  $finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
