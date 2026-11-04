module status_sender #(parameter UART_DIV=50)(
 input wire clk,rst,request,input wire [223:0] snapshot,output wire tx
);
 reg [255:0] frame;reg [31:0] crc;reg [5:0] index;
 reg [2:0] state;reg tx_start;reg [7:0] tx_data;wire busy;
 uart_tx #(.DIV(UART_DIV)) sender(clk,rst,tx_data,tx_start,tx,busy);
 function [31:0] update_crc;
 input [31:0] old;input [7:0] b;reg [31:0] c;integer i;
 begin c=old^{24'd0,b};for(i=0;i<8;i=i+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;update_crc=c;end
 endfunction
 always @(posedge clk)begin
  if(rst)begin state<=0;tx_start<=0;index<=0;crc<=0;frame<=0;tx_data<=0;end
  else begin
   tx_start<=0;
   case(state)
    0:if(request)begin frame[223:0]<=snapshot;index<=0;crc<=32'hffffffff;state<=1;end
    1:begin crc<=update_crc(crc,frame[index*8+:8]);if(index==27)state<=2;else index<=index+1'b1;end
    2:begin frame[255:224]<=~crc;index<=0;state<=3;end
    3:begin tx_data<=index==0?8'hb4:index==1?8'h4b:frame[(index-2)*8+:8];tx_start<=1;state<=4;end
    4:if(busy)state<=5;
    5:if(!busy)begin if(index==33)state<=0;else begin index<=index+1'b1;state<=3;end end
    default:state<=0;
   endcase
  end
 end
endmodule
