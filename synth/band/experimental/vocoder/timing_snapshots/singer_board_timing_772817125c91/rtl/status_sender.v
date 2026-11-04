module status_sender #(parameter UART_DIV=50)(
 input wire clk,rst,request,input wire [223:0] snapshot,output wire tx
);
 // Separate CRC traversal from transmission. The outgoing frame is immutable
 // once launched; a fixed low-byte shift avoids a wide variable-index mux.
 reg [223:0] payload,crc_shift;
 reg [271:0] wire_frame;
 reg [31:0] crc;reg [5:0] crc_count,bytes_left;
 reg [2:0] state;reg tx_start;reg [7:0] tx_data;wire busy;
 uart_tx #(.DIV(UART_DIV)) sender(clk,rst,tx_data,tx_start,tx,busy);
 function [31:0] update_crc;
 input [31:0] old;input [7:0] b;reg [31:0] c;integer i;
 begin c=old^{24'd0,b};for(i=0;i<8;i=i+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;update_crc=c;end
 endfunction
 always @(posedge clk)begin
  if(rst)begin state<=0;tx_start<=0;crc_count<=0;bytes_left<=0;crc<=0;payload<=0;crc_shift<=0;wire_frame<=0;tx_data<=0;end
  else begin
   tx_start<=0;
   case(state)
    0:if(request)begin payload<=snapshot;crc_shift<=snapshot;crc_count<=28;crc<=32'hffffffff;state<=1;end
    1:begin crc<=update_crc(crc,crc_shift[7:0]);crc_shift<={8'd0,crc_shift[223:8]};crc_count<=crc_count-1'b1;if(crc_count==1)state<=2;end
    2:begin wire_frame<={~crc,payload,16'h4bb4};bytes_left<=34;state<=3;end
    3:begin tx_data<=wire_frame[7:0];tx_start<=1;state<=4;end
    4:if(busy)state<=5;
    5:if(!busy)begin if(bytes_left==1)state<=0;else begin wire_frame<={8'd0,wire_frame[271:8]};bytes_left<=bytes_left-1'b1;state<=3;end end
    default:state<=0;
   endcase
  end
 end
endmodule
