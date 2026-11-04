// Byte-level two UART ingress plus local panel. Reuses the production CRC parser.
// Packet sources stay separate until parsed; never wire two TX pins together.
module dual_uart_events(
 input wire clk,rst,input wire[7:0] pc_data,ble_data,input wire pc_valid,ble_valid,
 input wire panel_valid,output wire panel_ready,input wire[223:0] panel_payload,
 output wire valid,input wire ready,output wire[223:0] payload,
 output wire panic,output wire[31:0] crc_errors,overflow
);
 wire[1:0] v,r,p;wire[223:0] d0,d1;wire[31:0] c0,c1,o0,o1;
 event_receiver pc(clk,rst||panic,pc_data,pc_valid,v[0],r[0],d0,p[0],c0,o0);
 event_receiver ble(clk,rst||panic,ble_data,ble_valid,v[1],r[1],d1,p[1],c1,o1);
 reg[1:0] cursor;reg locked;reg[1:0] grant;reg[1:0] selected;reg found;integer i,index;
 always @*begin
  selected=cursor;found=0;
  for(i=0;i<3;i=i+1)begin
   index=cursor+i;if(index>=3)index=index-3;
   if(!found&&((index==0&&v[0])||(index==1&&v[1])||(index==2&&panel_valid)))begin selected=index;found=1;end
  end
  if(locked)begin selected=grant;found=1;end
 end
 assign valid=found&&!panic;
 assign payload=selected==0?d0:selected==1?d1:panel_payload;
 assign r[0]=ready&&valid&&selected==0;
 assign r[1]=ready&&valid&&selected==1;
 assign panel_ready=ready&&valid&&selected==2;
 assign panic=|p;
 assign crc_errors=c0+c1;assign overflow=o0+o1;
 always @(posedge clk)begin
  if(rst||panic)begin cursor<=0;locked<=0;grant<=0;end
  else if(valid)begin
   if(ready)begin cursor<=selected==2?0:selected+1'b1;locked<=0;end
   else begin locked<=1;grant<=selected;end
  end
 end
endmodule
