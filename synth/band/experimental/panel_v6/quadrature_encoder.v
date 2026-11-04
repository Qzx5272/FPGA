// Synchronized, debounced Gray decoder. One detent = four legal transitions.
module quadrature_encoder #(parameter STABLE_CYCLES=25000)(
 input wire clk,rst,a,b,
 output reg increment,decrement,output reg[31:0] invalid_transitions
);
 (* ASYNC_REG="TRUE" *) reg[1:0] a_sync,b_sync;
 reg[1:0] candidate,stable;
 reg[31:0] count;
 reg signed[3:0] quarters;
 reg signed[2:0] direction;
 always @* begin
  case({stable,candidate})
   4'b0001,4'b0111,4'b1110,4'b1000:direction=1;
   4'b0010,4'b1011,4'b1101,4'b0100:direction=-1;
   default:direction=0;
  endcase
 end
 always @(posedge clk)begin
  if(rst)begin a_sync<=0;b_sync<=0;candidate<=0;stable<=0;count<=0;quarters<=0;increment<=0;decrement<=0;invalid_transitions<=0;end
  else begin
   a_sync<={a_sync[0],a};b_sync<={b_sync[0],b};increment<=0;decrement<=0;
   if({a_sync[1],b_sync[1]}!=candidate)begin candidate<={a_sync[1],b_sync[1]};count<=0;end
   else if(count<STABLE_CYCLES)count<=count+1'b1;
   else if(candidate!=stable)begin
    stable<=candidate;
    if(direction==0)begin quarters<=0;invalid_transitions<=invalid_transitions+1'b1;end
    else if(direction==1&&quarters==3)begin increment<=1;quarters<=0;end
    else if(direction==-1&&quarters==-3)begin decrement<=1;quarters<=0;end
    else quarters<=quarters+direction;
   end
  end
 end
endmodule
