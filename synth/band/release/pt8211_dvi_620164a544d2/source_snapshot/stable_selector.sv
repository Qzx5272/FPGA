// Human-operated selector: synchronize, then accept a whole stable word.
// This is not a general coherent CDC bus protocol. A settled physical selector
// must remain unchanged for STABLE_CYCLES before it affects new note onsets.
module stable_selector #(parameter WIDTH=5,parameter STABLE_CYCLES=250000)(
 input wire clk,rst,input wire [WIDTH-1:0] raw,output reg [WIDTH-1:0] value
);
 (* async_reg="true" *) reg [WIDTH-1:0] sync1,sync2;
 reg [WIDTH-1:0] candidate;reg [31:0] count;
 always @(posedge clk)begin
  if(rst)begin sync1<=0;sync2<=0;candidate<=0;value<=0;count<=0;end
  else begin
   sync1<=raw;sync2<=sync1;
   if(sync2!=candidate)begin
    candidate<=sync2;count<=1;
    if(STABLE_CYCLES==1)value<=sync2;
   end else if(count<STABLE_CYCLES)begin
    count<=count+1'b1;
    if(count==STABLE_CYCLES-1)value<=candidate;
   end
  end
 end
endmodule
