// Observes ingress without backpressure. Highlight means received strike,
// not an acknowledgement from the voice allocator. Actual voices is separate.
module ui_state(input clk,rst,panic,input accepted,input[223:0]packet,
 input playing,input[6:0]master,input[7:0]tempo,input[15:0]voices,
 output wire[127:0]snapshot);
 reg[18:0]divider;reg[7:0]alive;reg[4:0]flash[0:15];
 reg[6:0]note,velocity;reg[3:0]part;reg[31:0]strikes;wire[15:0]mask;
 integer i;genvar g;
 generate for(g=0;g<16;g=g+1)begin assign mask[g]=flash[g]!=0;end endgenerate
 wire[7:0]kind=packet[15:8],source=packet[23:16];wire[6:0]pitch=packet[46:40];
 always @(posedge clk)begin
  if(rst)begin divider<=0;alive<=0;note<=60;velocity<=0;part<=8;strikes<=0;for(i=0;i<16;i=i+1)flash[i]<=0;end
  else begin
   if(divider==499999)begin divider<=0;if(alive!=0)alive<=alive-1'b1;
    for(i=0;i<16;i=i+1)if(flash[i]!=0)flash[i]<=flash[i]-1'b1;
   end else divider<=divider+1'b1;
   if(accepted&&source==2)begin
    alive<=100;
    if(kind==0)begin note<=pitch;velocity<=packet[54:48];part<=packet[27:24];strikes<=strikes+1'b1;
     if(pitch>=60&&pitch<=75)flash[pitch-60]<=20;
    end
   end
   if(panic)for(i=0;i<16;i=i+1)flash[i]<=0;
  end
 end
 assign snapshot={29'd0,strikes,(alive!=0),mask,part,velocity,note,voices,tempo,master,playing};
endmodule

// Bundled-data handshake. Source stays frozen until display acknowledges;
// display only commits the snapshot at a frame boundary, preventing tearing.
module ui_snapshot(input source_clk,pixel_clk,source_rst,pixel_rst,frame_start,
 input[127:0]source_data,output reg[127:0]display_data);
 reg[127:0]held;reg request=0,ack=0;
 (* ASYNC_REG="TRUE" *)reg ack1=0,ack2=0,req1=0,req2=0;
 always @(posedge source_clk)begin
  if(source_rst)begin held<=0;request<=0;ack1<=0;ack2<=0;end
  else begin ack1<=ack;ack2<=ack1;if(ack2==request)begin held<=source_data;request<=~request;end end
 end
 always @(posedge pixel_clk)begin
  if(pixel_rst)begin display_data<=0;ack<=0;req1<=0;req2<=0;end
  else begin req1<=request;req2<=req1;if(frame_start&&req2!=ack)begin display_data<=held;ack<=req2;end end
 end
endmodule
