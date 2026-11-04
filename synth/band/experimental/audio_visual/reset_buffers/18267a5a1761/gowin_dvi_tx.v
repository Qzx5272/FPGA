// GW5A video-only DVI transmitter. Clocks must be phase-related 1:5.
// Clock generation and electrical/board timing acceptance are separate.
module gowin_dvi_tx(
 input pixel_clk,serial_clk,resetn,active_video,hsync_n,vsync_n,input[23:0]rgb,
 output tmds_clk_p,tmds_clk_n,output[2:0]tmds_d_p,tmds_d_n
);
 wire[9:0]symbol[0:2];wire[2:0]serial;
 dvi_symbols encoder(pixel_clk,resetn,active_video,hsync_n,vsync_n,rgb,
                     symbol[0],symbol[1],symbol[2]);
 // Keep serializer reset until the encoder's three registers are flushed.
 reg[3:0]warmup=0;
 always @(posedge pixel_clk or negedge resetn)
  if(!resetn)warmup<=0;else warmup<={warmup[2:0],1'b1};
 // Assert immediately; release synchronously in the pixel domain only after
 // the pixel encoder warm-up. Never drive OSER reset directly from ready.
 wire serializer_reset_request=!resetn||!warmup[3];
 // Experimental: reset release uses the falling edge of the phase-related pixel clock.
 // No fabric registers clocked at FCLK. OSER recovery/removal must still pass STA.
 reg[1:0]pixel_release=0;
 always @(negedge pixel_clk or posedge serializer_reset_request)
  if(serializer_reset_request)pixel_release<=0;
  else pixel_release<={pixel_release[0],1'b1};
 wire serial_ready=pixel_release[1];
 // Experimental reset hold repair. SUG550-2.4E sections5.5/5.9.
 // Propagation must be checked at fast/slow corners after routing; no assumed ns delay.
 wire reset_route_0 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 assign reset_route_0=!serial_ready;
 wire reset_route_1 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_1(.I0(reset_route_0),.F(reset_route_1));
 wire reset_route_2 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_2(.I0(reset_route_1),.F(reset_route_2));
 wire reset_route_3 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_3(.I0(reset_route_2),.F(reset_route_3));
 wire reset_route_4 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_4(.I0(reset_route_3),.F(reset_route_4));
 wire reset_route_5 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_5(.I0(reset_route_4),.F(reset_route_5));
 wire reset_route_6 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_6(.I0(reset_route_5),.F(reset_route_6));
 wire reset_route_7 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_7(.I0(reset_route_6),.F(reset_route_7));
 wire reset_route_8 /* synthesis syn_keep=1 syn_dont_touch=1 */;
 LUT1 #(.INIT(2'h1)) reset_buffer_8(.I0(reset_route_7),.F(reset_route_8));
 genvar lane;
 generate for(lane=0;lane<3;lane=lane+1)begin:channels
  OSER10 serializer(.Q(serial[lane]),
   .D0(symbol[lane][0]),.D1(symbol[lane][1]),.D2(symbol[lane][2]),
   .D3(symbol[lane][3]),.D4(symbol[lane][4]),.D5(symbol[lane][5]),
   .D6(symbol[lane][6]),.D7(symbol[lane][7]),.D8(symbol[lane][8]),.D9(symbol[lane][9]),
   .PCLK(pixel_clk),.FCLK(serial_clk),.RESET(reset_route_8));
  ELVDS_OBUF output_buffer(.I(serial[lane]),.O(tmds_d_p[lane]),.OB(tmds_d_n[lane]));
 end endgenerate
 ELVDS_OBUF clock_buffer(.I(pixel_clk),.O(tmds_clk_p),.OB(tmds_clk_n));
endmodule
