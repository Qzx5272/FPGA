// Video-only DVI-compatible TMDS words. No HDMI audio/data islands/PHY/PLL.
// RGB is conventional R[23:16],G[15:8],B[7:0]; lane0 carries blue and sync.
module dvi_symbols(
 input pixel_clk,resetn,active_video,hsync_n,vsync_n,input[23:0]rgb,
 output[9:0]blue,green,red
);
 starcluster_tmds_encoder b(pixel_clk,resetn,active_video,{vsync_n,hsync_n},rgb[7:0],blue);
 starcluster_tmds_encoder g(pixel_clk,resetn,active_video,2'b00,rgb[15:8],green);
 starcluster_tmds_encoder r(pixel_clk,resetn,active_video,2'b00,rgb[23:16],red);
endmodule
