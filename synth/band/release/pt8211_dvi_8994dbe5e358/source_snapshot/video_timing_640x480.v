// 800x525 total pixels, 640x480 active, negative sync pulses.
// A supplied 25.2MHz pixel clock gives 60 frames/s. No PLL/PHY is implied.
module video_timing_640x480(
 input pixel_clk,rst,output reg[9:0]pixel_x,pixel_y,
 output wire active_video,hsync_n,vsync_n,frame_boundary
);
 always @(posedge pixel_clk or posedge rst)begin
  if(rst)begin pixel_x<=0;pixel_y<=0;end
  else if(pixel_x==799)begin
   pixel_x<=0;if(pixel_y==524)pixel_y<=0;else pixel_y<=pixel_y+1'b1;
  end else pixel_x<=pixel_x+1'b1;
 end
 assign active_video=!rst&&pixel_x<640&&pixel_y<480;
 assign hsync_n=!(pixel_x>=656&&pixel_x<752);
 assign vsync_n=!(pixel_y>=490&&pixel_y<492);
 // Swap the pending image at the edge immediately BEFORE active pixel(0,0).
 assign frame_boundary=!rst&&pixel_x==799&&pixel_y==524;
endmodule
