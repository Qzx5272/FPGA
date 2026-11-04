// GW5AST-138B, UG306-1.0.7E sections4.3 and5.1.
// PFD=50MHz; VCO=50*(15+1/8)=756.25MHz (138K range650..1300MHz).
// VCO/6=126.0416667MHz serial; CLKDIV5 gives coherent25.2083333MHz pixels.
// This configuration still requires physical PnR/clock/IO validation.
module gowin_video_clock(
 input clk50,resetn,output serial_clk,pixel_clk,locked,ready
);
 PLL #(.FCLKIN("50"),.IDIV_SEL(1),.FBDIV_SEL(1),.MDIV_SEL(15),.MDIV_FRAC_SEL(1),
  .ODIV0_SEL(6),.ODIV0_FRAC_SEL(0),.CLKFB_SEL("INTERNAL"),.CLKOUT0_EN("TRUE"),
  .CLKOUT1_EN("FALSE"),.CLKOUT2_EN("FALSE"),.CLKOUT3_EN("FALSE"),
  .CLKOUT4_EN("FALSE"),.CLKOUT5_EN("FALSE"),.CLKOUT6_EN("FALSE")) pll(
  .CLKIN(clk50),.CLKFB(1'b0),.RESET(!resetn),.PLLPWD(1'b0),.RESET_I(1'b0),.RESET_O(1'b0),
  .CLKOUT0(serial_clk),.CLKOUT1(),.CLKOUT2(),.CLKOUT3(),.CLKOUT4(),.CLKOUT5(),.CLKOUT6(),.CLKFBOUT(),.LOCK(locked),
  .ENCLK0(1'b1),.ENCLK1(1'b1),.ENCLK2(1'b1),.ENCLK3(1'b1),.ENCLK4(1'b1),.ENCLK5(1'b1),.ENCLK6(1'b1),
  .FBDSEL(6'd0),.IDSEL(6'd0),.MDSEL(7'd0),.MDSEL_FRAC(3'd0),.ODSEL0(7'd0),.ODSEL0_FRAC(3'd0),
  .ODSEL1(7'd0),.ODSEL2(7'd0),.ODSEL3(7'd0),.ODSEL4(7'd0),.ODSEL5(7'd0),.ODSEL6(7'd0),
  .DT0(4'd0),.DT1(4'd0),.DT2(4'd0),.DT3(4'd0),.PSSEL(3'd0),.PSDIR(1'b0),.PSPULSE(1'b0),
  .SSCPOL(1'b0),.SSCON(1'b0),.SSCMDSEL(7'd0),.SSCMDSEL_FRAC(3'd0),.ICPSEL(6'd0),.LPFRES(3'd0),.LPFCAP(2'd0));
 wire release_reset=locked&&resetn;
 CLKDIV #(.DIV_MODE("5")) divider(.HCLKIN(serial_clk),.RESETN(release_reset),.CALIB(1'b0),.CLKOUT(pixel_clk));
 (* ASYNC_REG="TRUE" *)reg[2:0]settle=0;
 reg ready_state=0;
 assign ready=ready_state;
 always @(posedge pixel_clk or negedge release_reset)
  if(!release_reset)begin settle<=0;ready_state<=0;end
  else begin settle<={settle[1:0],1'b1};ready_state<=settle[2];end
endmodule
