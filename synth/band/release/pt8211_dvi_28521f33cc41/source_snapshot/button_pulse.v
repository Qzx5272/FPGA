// Debounced active-high button, one pulse per press. Default 5 ms at 50 MHz.
module button_pulse #(parameter STABLE_CYCLES=250000)(input wire clk,rst,raw,output reg pulse);
 reg [1:0] synchronized;reg stable;reg [31:0] count;
 always @(posedge clk)begin
  synchronized<={synchronized[0],raw};pulse<=0;
  if(rst)begin synchronized<=0;stable<=0;count<=0;end
  else if(synchronized[1]==stable)count<=0;
  else if(count==STABLE_CYCLES-1)begin stable<=synchronized[1];pulse<=synchronized[1];count<=0;end
  else count<=count+1'b1;
 end
endmodule
