module input_filter #(parameter N=1,STABLE=250000,parameter [N-1:0] RESET=0)(
 input clk,rst,input[N-1:0]raw,output reg[N-1:0]level,rise,fall);
 (* ASYNC_REG="TRUE" *)reg[N-1:0]meta,sync;
 reg[$clog2(STABLE+1)-1:0]count[0:N-1];integer i;
 always @(posedge clk)begin
  if(rst)begin meta<=RESET;sync<=RESET;level<=RESET;rise<=0;fall<=0;for(i=0;i<N;i=i+1)count[i]<=0;end
  else begin meta<=raw;sync<=meta;rise<=0;fall<=0;
   for(i=0;i<N;i=i+1)begin
    if(sync[i]==level[i])count[i]<=0;
    else if(count[i]==STABLE-1)begin level[i]<=sync[i];rise[i]<=sync[i];fall[i]<=!sync[i];count[i]<=0;end
    else count[i]<=count[i]+1'b1;
   end
  end
 end
endmodule
