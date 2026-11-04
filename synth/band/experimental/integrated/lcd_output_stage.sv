// RGB and DE receive the same one-pixel delay; forwarded clock is unchanged.
module lcd_output_stage(input wire pixel,reset,input wire de,
 input wire[17:0]rgb,output reg out_de,output reg[17:0]out_rgb);
 always @(posedge pixel)begin
  out_de<=!reset&&de;
  out_rgb<=!reset&&de?rgb:18'd0;
 end
endmodule
