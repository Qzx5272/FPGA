`timescale 1ns/1ps
module tb_local_pedal;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,pv=0,off=0,bar=0;reg [3:0] pedals=0;
 reg [6:0] contact=0;reg [31:0] serial=1;
 wire ready,busy,cv,cr,mv,rv,muted,pending,exhausted;wire [1:0] command,kind;
 wire [3:0] sp,cp,mp,rp,down;wire [7:0] cs,ms,mc,owner,so;
 wire [31:0] ep,seq,denied,epoch,se,conflicts;wire [6:0] note,velocity;
 wire [63:0] held;wire [15:0] deferred;
 local_pedal_performer #(.STABLE_CYCLES(3)) dut(clk,rst,panic,pv,ready,off,contact,7'd90,serial,4'd0,1'b0,
  busy,sp,1'b1,so,se,cv,cr,command,cp,cs,mv,1'b1,kind,ms,mc,mp,ep,seq,note,velocity,denied,held,pedals,down,deferred);
 track_ownership own(clk,rst,panic,bar,cv,cr,command,cp,cs,rv,1'b1,rp,4'd6,owner,epoch,muted,pending,conflicts,exhausted,sp,so,se,1'b0,8'd0);
 integer ons=0,offs=0;
 always @(posedge clk)if(mv)begin
  if(kind==0)ons=ons+1;else offs=offs+1;
  if(ms!=17||mp!=6||note!=60||ep!=epoch)$fatal(1,"note identity");
 end
 task pad;input o;input [31:0] s;
 begin wait(ready);@(negedge clk);off=o;serial=s;pv=1;@(negedge clk);pv=0;repeat(30)@(negedge clk);end endtask
 task barline;begin @(negedge clk);bar=1;@(negedge clk);bar=0;repeat(45)@(negedge clk);end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  pedals=1;@(negedge clk);pedals=0;repeat(8)@(negedge clk);
  if(down)$fatal(1,"bounce accepted");
  pedals=1;repeat(8)@(negedge clk);pad(0,1);pad(1,1);
  if(held||owner!=17||!deferred[6]||pending||ons!=1||offs!=1)$fatal(1,"hold ownership without sustaining audio");
  barline();if(owner!=17)$fatal(1,"returned while pedal held");
  pedals=0;repeat(12)@(negedge clk);
  if(!pending||owner!=17)$fatal(1,"must request return, not immediate handover");
  barline();if(owner!=0)$fatal(1,"bar return");
  pedals=1;repeat(8)@(negedge clk);pad(0,2);pad(1,2);
  pad(0,3);if(deferred[6])$fatal(1,"new take did not cancel deferred return");
  pedals=0;repeat(12)@(negedge clk);barline();if(owner!=17||!held[0])$fatal(1,"old pedal return killed new note");
  pad(1,3);barline();if(owner!=0)$fatal(1,"normal final release");
  pedals=1;repeat(8)@(negedge clk);pad(0,4);pad(1,4);
  panic=1;@(negedge clk);panic=0;
  if(deferred||held||cv)$fatal(1,"panic stale event");
  barline();if(owner!=0)$fatal(1,"panic ownership return");
  $display("PASS local pedal + actual ownership: debounce, note release independent of ownership hold, next-bar return, retrigger cancellation, panic");$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
