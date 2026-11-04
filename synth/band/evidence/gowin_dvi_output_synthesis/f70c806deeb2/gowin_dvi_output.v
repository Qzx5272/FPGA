// Clocked video output boundary. Feed RGB/sync synchronously to pixel_clk;
// reset the upstream raster/visualization whenever video_ready is low.
module gowin_dvi_output(
 input clk50,resetn,active_video,hsync_n,vsync_n,input[23:0]rgb,
 output pixel_clk,video_ready,
 output tmds_clk_p,tmds_clk_n,output[2:0]tmds_d_p,tmds_d_n
);
 wire serial_clk,locked;
 gowin_video_clock clocking(clk50,resetn,serial_clk,pixel_clk,locked,video_ready);
 gowin_dvi_tx transmitter(pixel_clk,serial_clk,video_ready&&resetn,
  active_video,hsync_n,vsync_n,rgb,tmds_clk_p,tmds_clk_n,tmds_d_p,tmds_d_n);
endmodule
