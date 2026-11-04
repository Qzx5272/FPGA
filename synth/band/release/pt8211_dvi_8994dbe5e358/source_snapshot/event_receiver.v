// Framed 32-byte V4 payload + CRC32/IEEE. Panic bypasses the pending event slot.
module event_receiver(
 input wire clk,rst,input wire [7:0] data,input wire byte_valid,
 output reg event_valid,input wire event_ready,output reg [223:0] payload,
 output reg panic,output reg [31:0] crc_errors,overflow
);
 reg [1:0] state;reg [5:0] index;reg [255:0] frame;reg [31:0] crc;
 reg [19:0] timeout;
 function [31:0] update_crc;
 input [31:0] old;input [7:0] b;reg [31:0] c;integer i;
 begin c=old^{24'd0,b};for(i=0;i<8;i=i+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;update_crc=c;end
 endfunction
 always @(posedge clk)begin
  if(rst)begin state<=0;index<=0;event_valid<=0;payload<=0;panic<=0;crc_errors<=0;overflow<=0;timeout<=0;crc<=32'hffffffff;end
  else begin
   panic<=0;
   if(event_valid&&event_ready)event_valid<=0;
   if(state!=0)begin
    if(&timeout)begin state<=0;timeout<=0;end else timeout<=timeout+1'b1;
   end
   if(byte_valid)begin
    timeout<=0;
    case(state)
     0:if(data==8'hb4)state<=1;
     1:if(data==8'h4b)begin state<=2;index<=0;crc<=32'hffffffff;end else state<=data==8'hb4 ? 1:0;
     2:begin
      frame[index*8+:8]<=data;
      if(index<28)crc<=update_crc(crc,data);
      if(index==31)begin
       state<=0;
       if({data,frame[247:224]}==~crc&&frame[7:0]==4&&frame[31:24]<16&&frame[159:128]==0&&frame[191:160]==0)begin
        if(frame[15:8]==127)begin panic<=1;event_valid<=0;end
        else if(!event_valid||event_ready)begin payload<=frame[223:0];event_valid<=1;end
        else begin overflow<=overflow+1'b1;panic<=1;event_valid<=0;end
       end else crc_errors<=crc_errors+1'b1;
      end else index<=index+1'b1;
     end
     default:state<=0;
    endcase
   end
  end
 end
endmodule
