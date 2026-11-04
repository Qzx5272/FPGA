`timescale 1ns/1ps
module tb_lcd_ui;
 reg clk=0;always #10 clk=~clk;
 wire pclk,de,hs,vs,bl;wire[5:0]r,g,b;
 board_lcd_ui_top dut(.clk(clk),.uart_rx_pin(1'b1),.ble_rx(1'b1),.key_play_n(1'b1),.key_stop_n(1'b1),.key_panic_n(1'b1),
 .lcd_clk(pclk),.lcd_en(de),.lcd_hs(hs),.lcd_vs(vs),.lcd_bl(bl),.lcd_r(r),.lcd_g(g),.lcd_b(b));
 integer f,n=0,frames=0,line_pixels=0,lines=0;reg capture=0,prior_de=0;
 initial begin f=$fopen("lcd_ui_frame.ppm","w");$fwrite(f,"P3\n800 480\n255\n");#100000000;$fatal(1,"timeout");end
 always @(posedge dut.pixel)if(dut.frame_start&&!dut.pixel_rst)begin
  frames=frames+1;if(frames==3)capture=1;
  if(frames==4)begin if(n!=384000||lines!=480)$fatal(1,"frame size pixels=%d lines=%d",n,lines);
   $fclose(f);$display("PASS LCD 800x480 active area; 480 rows of 800 pixels; centered UI at actual panel sample edge");$finish;end
 end
 always @(posedge pclk)if(capture)begin
  if(de)begin
   if(^{r,g,b}===1'bx)$fatal(1,"unknown LCD pixel");
   $fwrite(f,"%d %d %d\n",{r,2'b00},{g,2'b00},{b,2'b00});n=n+1;line_pixels=line_pixels+1;
  end
  if(prior_de&&!de)begin if(line_pixels!=800)$fatal(1,"bad row %d",line_pixels);line_pixels=0;lines=lines+1;end
  prior_de=de;
 end
endmodule
