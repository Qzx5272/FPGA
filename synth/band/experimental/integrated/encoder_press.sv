module encoder_press #(parameter HOLD=40000000)(
 input clk,rst,pressed,output reg tap,long_hit
);
 reg [$clog2(HOLD+1)-1:0] elapsed;
 reg consumed;
 always @(posedge clk) begin
  tap<=0;long_hit<=0;
  if(rst)begin elapsed<=0;consumed<=0;end
  else if(!pressed)begin
   tap<=elapsed!=0&&!consumed;elapsed<=0;consumed<=0;
  end else if(!consumed)begin
   if(elapsed==HOLD-1)begin long_hit<=1;consumed<=1;end
   else elapsed<=elapsed+1'b1;
  end
 end
endmodule
