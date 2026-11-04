// Accepted event telemetry; capture cannot stall the musical engine.
// Timestamp is a free-running48kHz sample counter, independent of score transport.
module event_capture_fifo(
 input wire clk,rst,clear,sample_tick,input wire capture,input wire[223:0]event_data,
 output wire valid,input wire ready,output wire[223:0]data,output reg[31:0]overflows,input wire[1:0]collision);
 reg[223:0]memory[0:63];reg[5:0]rd,wr;reg[6:0]count;reg[63:0]ticks;
 wire pop=valid&&ready;wire push=capture&&(count<64||pop);
 wire[7:0]kind=event_data[15:8];
 assign valid=count!=0;assign data=memory[rd];
 always @(posedge clk)begin
  if(rst)begin rd<=0;wr<=0;count<=0;ticks<=0;overflows<=0;end
  else begin
   if(sample_tick)ticks<=ticks+1'b1;
   if(clear)begin rd<=0;wr<=0;count<=0;end
   else begin
    if((capture&&!push)||collision!=0)overflows<=overflows+{31'd0,(capture&&!push)}+collision;
    if(push)begin
     memory[wr]<={event_data[223:192],ticks,event_data[127:16],(kind==127?8'he0:(8'hc0|kind)),8'd4};wr<=wr+1'b1;
    end
    if(pop)rd<=rd+1'b1;
    case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   end
  end
 end
endmodule
