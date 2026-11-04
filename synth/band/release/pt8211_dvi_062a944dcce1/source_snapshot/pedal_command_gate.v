// Local-seat ownership hold, not audio sustain. Active-high dry contacts need
// board-specific voltage/pull-up wiring. No pin assignments are implied here.
module pedal_command_gate #(parameter STABLE_CYCLES=250000)(
 input wire clk,rst,panic,input wire [3:0] pedal_raw,
 input wire in_valid,output wire in_ready,input wire [1:0] in_command,
 input wire [3:0] in_part,input wire [7:0] in_source,
 output reg out_valid,input wire out_ready,output reg [1:0] out_command,
 output reg [3:0] out_part,output reg [7:0] out_source,
 output reg [3:0] pedal_down,output reg [15:0] deferred
);
 reg [3:0] sync1,sync2;reg [31:0] count[0:3];
 reg [7:0] saved_source[0:15];integer i;
 reg found;reg [3:0] selected;
 wire local_source=in_source>=17&&in_source<=20;
 assign in_ready=!out_valid&&!rst&&!panic;
 always @*begin
  found=0;selected=0;
  for(integer p=0;p<16;p=p+1)
   if(!found&&deferred[p]&&!pedal_down[saved_source[p]-17])begin found=1;selected=p;end
 end
 always @(posedge clk)begin
  if(rst||panic)begin
   sync1<=0;sync2<=0;pedal_down<=0;deferred<=0;out_valid<=0;
   out_command<=0;out_part<=0;out_source<=0;
   for(i=0;i<4;i=i+1)count[i]<=0;
   for(i=0;i<16;i=i+1)saved_source[i]<=17;
  end else begin
   sync1<=pedal_raw;sync2<=sync1;
   for(i=0;i<4;i=i+1)
    if(sync2[i]==pedal_down[i])count[i]<=0;
    else if(count[i]==STABLE_CYCLES-1)begin pedal_down[i]<=sync2[i];count[i]<=0;end
    else count[i]<=count[i]+1'b1;
   if(out_valid&&out_ready)out_valid<=0;
   if(in_valid&&in_ready)begin
    if(in_command==0)deferred[in_part]<=0;
    if(in_command==1&&local_source&&pedal_down[in_source-17])begin
     deferred[in_part]<=1;saved_source[in_part]<=in_source;
    end else begin
     out_valid<=1;out_command<=in_command;out_part<=in_part;out_source<=in_source;
    end
   end else if(!out_valid&&found)begin
    deferred[selected]<=0;out_valid<=1;out_command<=1;out_part<=selected;out_source<=saved_source[selected];
   end
  end
 end
endmodule
