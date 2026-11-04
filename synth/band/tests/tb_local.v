`timescale 1ns/1ps
module tb_local;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,pv=0,off=0,sv=1,cr=1,mr=0;reg [6:0] contact=0,pressure=90;reg [31:0] serial=1;
 reg [3:0] root=0;wire ready,busy,cv,mv;wire [1:0] command,kind;wire [3:0] sp,cp,mp;wire [7:0] cs,ms,mc;wire [31:0] ep,seq,denied;wire [6:0] note,velocity;wire [63:0] held;
 reg [7:0] owners[0:15];reg [31:0] epochs[0:15];integer i;
 local_performer dut(clk,rst,panic,pv,ready,off,contact,pressure,serial,root,1'b0,busy,sp,sv,owners[sp],epochs[sp],cv,cr,command,cp,cs,mv,mr,kind,ms,mc,mp,ep,seq,note,velocity,denied,held);
 integer returns=0;reg grant=1;
 always @(posedge clk)if(cv&&cr)begin
  if(command==0&&owners[cp]!=cs&&grant)begin owners[cp]<=cs;epochs[cp]<=epochs[cp]+1;end
  if(command==1)returns=returns+1;
 end
 task pad;input o;input [6:0] c;input [31:0] s;
 begin wait(ready);@(negedge clk);off=o;contact=c;serial=s;pv=1;@(negedge clk);pv=0;end endtask
 task accept;input [1:0] k;input [3:0] p;input [6:0] n;input [31:0] e;
 begin wait(mv);#1;if(kind!=k||mp!=p||note!=n||ep!=e)$fatal(1,"local identity");@(negedge clk);mr=1;@(negedge clk);mr=0;end endtask
 initial begin
  for(i=0;i<16;i=i+1)begin owners[i]=0;epochs[i]=1;end
  repeat(3)@(negedge clk);rst=0;
  pad(0,0,1);accept(0,6,60,2);if(ms!=17)$fatal;
  root=9;pad(1,0,1);accept(1,6,60,2); // release must keep the old pitch and epoch
  pad(0,17,1);accept(0,1,38,2);if(ms!=18)$fatal;
  owners[4]=2;pad(0,32,1);repeat(20)@(negedge clk);if(denied!=1||mv||returns!=1)$fatal;
  pad(1,32,1);repeat(20)@(negedge clk);if(mv)$fatal;
  pad(0,0,2);accept(0,6,69,2);pad(0,1,2);accept(0,6,71,2);
  pad(1,0,2);accept(1,6,69,2);repeat(10)@(negedge clk);if(returns!=1)$fatal(1,"returned before last contact");
  pad(1,1,2);accept(1,6,71,2);repeat(10)@(negedge clk);if(returns!=2)$fatal(1,"last contact did not return");
  grant=0;pad(0,48,3);repeat(1100)@(negedge clk);if(!ready||denied!=2)$fatal(1,"failed takeover wedged local seat");
  panic=1;@(negedge clk);panic=0;if(held!=0)$fatal;
  $display("PASS local seats: distinct sources, automatic takeover, old-pitch release, drum roles, ownership conflict, panic");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
