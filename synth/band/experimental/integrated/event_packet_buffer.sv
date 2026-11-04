// Elastic register boundary: separate ingress arbitration from authorization.
module event_packet_buffer(input clk,rst,input in_valid,output in_ready,input[223:0]in_payload,
 output reg valid,input ready,output reg[223:0]payload);
 assign in_ready=!valid||ready;
 always @(posedge clk)begin
  if(rst)begin valid<=0;payload<=0;end
  else if(in_ready)begin valid<=in_valid;if(in_valid)payload<=in_payload;end
 end
endmodule
