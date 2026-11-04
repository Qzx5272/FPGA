`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,tick=0,ev=0;
 reg [1:0] kind=0;reg [7:0] source=2,contact=0;reg [3:0] part=0;
 reg [31:0] epoch=1,serial=0;reg [6:0] note=60,velocity=100;
 reg cv=0;reg [3:0] cp=0,parameter_id=0;reg [13:0] value=0;
 wire ready,refready,valid,refvalid,done,matched,capacity,lead;
 wire signed [15:0] left,right,mono;
 wire [15:0] voices,cycles,refvoices,refcycles;
 wire [31:0] rejected,deadline,clips,rr,rd,rc;
 shared_voice_bank dut(clk,rst,panic,tick,ev,ready,kind,source,contact,part,epoch,serial,note,velocity,
  valid,left,voices,cycles,rejected,deadline,clips,1'b0,done,matched,capacity,lead,right,
  cv,cp,parameter_id,value);
 voice_bank #(.BANK_BITS(0),.BANK_ID(0)) reference_bank(clk,rst,panic,tick,ev,refready,
  kind,source,contact,part,epoch,serial,note,velocity,
  refvalid,mono,refvoices,refcycles,rr,rd,rc,cv,cp,parameter_id,value);
 integer role,frame,t,peak,maxcycles=0,seen;reg compare_single=1;
 reg signed [31:0] expected_left,expected_right,wide;
 always @(negedge clk)if(!rst)begin
  if(valid!==refvalid)$fatal(1,"renderer schedule changed");
  if(valid)begin
   seen=seen+1;if(cycles>maxcycles)maxcycles=cycles;
   if(compare_single)begin
    wide=$signed(mono);
    expected_left=part==2?(wide>>>1):part==5?(wide>>>1)+(wide>>>3):wide;
    expected_right=part==4?(wide>>>1)+(wide>>>3):part==1?(wide>>>1)+(wide>>>2):wide;
    if($signed(left)!==expected_left||$signed(right)!==expected_right)
     $fatal(1,"pan/PCM differs role%0d got%0d/%0d expected%0d/%0d",part,left,right,expected_left,expected_right);
   end else if(left!==mono||right!==mono)$fatal(1,"choir PCM mismatch");
   if(left>peak)peak=left;if(-$signed(left)>peak)peak=-$signed(left);
  end
 end
 task send(input integer ident);
 begin
  @(negedge clk);while(!ready||!refready)@(negedge clk);
  serial=ident;ev=1;@(negedge clk);ev=0;
  while(!ready||!refready)@(negedge clk);
 end endtask
 task render;
 begin
  @(negedge clk);tick=1;@(negedge clk);tick=0;
  repeat(1040)@(negedge clk);
 end endtask
 initial begin
  seen=0;peak=0;
  for(role=0;role<8;role=role+1)begin
   rst=1;repeat(4)@(negedge clk);rst=0;part=role;peak=0;seen=0;
   send(1);
   if(lead!==(role==6))$fatal(1,"role-aware lead identity");
   // Change a different role; active role's expression must remain independent.
   cp=(role+1)%8;parameter_id=0;value=0;cv=1;@(negedge clk);cv=0;
   for(frame=0;frame<64;frame=frame+1)render();
   if(voices!=1||seen!=64||peak==0||deadline||rd)$fatal(1,"role output/deadline failure role%0d",role);
  end
  rst=1;repeat(4)@(negedge clk);rst=0;part=7;compare_single=0;seen=0;
  for(t=0;t<32;t=t+1)send(t);
  for(frame=0;frame<64;frame=frame+1)render();
  if(voices!=32||seen!=64||deadline||rd)$fatal(1,"full choir deadline voices=%0d frames=%0d missed=%0d cycles=%0d",voices,seen,deadline,cycles);
  $display("PASS universal bank all8roles PCM/pan,isolated controls,lead identity,32choir;maxcycles=%0d",maxcycles);
  $finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
