// PC + BLE + USB Host bridge + local panel. Four independent event producers.
module three_uart_events(
 input wire clk,rst,input wire[7:0]pc_data,ble_data,usb_data,
 input wire pc_valid,ble_valid,usb_valid,
 input wire panel_valid,output wire panel_ready,input wire[223:0]panel_payload,
 output wire valid,input wire ready,output wire[223:0]payload,
 output wire panic,output wire[31:0]crc_errors,overflow,output wire remote,output wire[1:0]remote_route);
 wire[2:0]v,r,p;wire[223:0]d0,d1,d2;wire[31:0]c0,c1,c2,o0,o1,o2;
 event_receiver pc(clk,rst||panic,pc_data,pc_valid,v[0],r[0],d0,p[0],c0,o0);
 event_receiver ble(clk,rst||panic,ble_data,ble_valid,v[1],r[1],d1,p[1],c1,o1);
 event_receiver usb(clk,rst||panic,usb_data,usb_valid,v[2],r[2],d2,p[2],c2,o2);
 reg[1:0]cursor,selected,grant;reg locked,found;integer i,index;
 always @*begin
  found=0;selected=cursor;
  for(i=0;i<4;i=i+1)begin
   index=(cursor+i)&3;
   if(!found&&((index==0&&v[0])||(index==1&&v[1])||(index==2&&v[2])||(index==3&&panel_valid)))begin
    found=1;selected=index;
   end
  end
  if(locked)begin selected=grant;found=1;end
 end
 assign valid=found&&!panic;assign panic=|p;
 assign remote=selected!=0;
 assign remote_route=selected==0?2'd0:selected-1'b1;
 assign payload=selected==0?d0:selected==1?d1:selected==2?d2:panel_payload;
 assign r[0]=ready&&valid&&selected==0;assign r[1]=ready&&valid&&selected==1;assign r[2]=ready&&valid&&selected==2;
 assign panel_ready=ready&&valid&&selected==3;
 assign crc_errors=c0+c1+c2;assign overflow=o0+o1+o2;
 always @(posedge clk)begin
  if(rst||panic)begin cursor<=0;locked<=0;grant<=0;end
  else if(valid)begin
   if(ready)begin cursor<=selected+1'b1;locked<=0;end
   else begin locked<=1;grant<=selected;end
  end
 end
endmodule
