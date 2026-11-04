// Three-stage pixel pipeline; sync/de are delayed with RGB, never independently.
module instrument_ui(input clk,rst,input[9:0]x,y,input active,hsync_n,vsync_n,
 input[127:0]state,output reg[23:0]rgb,output reg de,hs,vs);
 `include "ui_glyphs.vh"
 reg[7:0]tiles[0:2047];reg[15:0]font[0:4095];reg[7:0]names[0:63];
 initial begin $readmemh("ui_tiles.mem",tiles);$readmemh("ui_font.mem",font);$readmemh("ui_names.mem",names);end
 wire[5:0]col=x[9:4];wire[4:0]row=y[8:4];
 reg[9:0]x1,y1,x2,y2;reg a1,h1,v1,a2,h2,v2;reg[7:0]tile;
 wire[5:0]c=x1[9:4];wire[4:0]r=y1[8:4];
 wire[6:0]volume=state[7:1],note=state[38:32],velocity=state[45:39];
 wire[7:0]bpm=state[15:8];wire[15:0]voices=state[31:16],hits=state[65:50];
 reg[7:0]glyph;reg[15:0]fontrow;reg[23:0]background,foreground,bg2,fg2;
 function[7:0]digit(input[15:0]v,input[1:0]place);
 begin case(place)0:digit=48+(v%10);1:digit=48+((v/10)%10);default:digit=48+((v/100)%10);endcase end endfunction
 integer k,rr,cc;
 always @*begin
  glyph=tile;background=24'h0b1424;foreground=24'hd9e5f2;
  if(y1<64)background=24'h13283c;
  if(r==1)foreground=24'h58dcc5;
  if(y1>=64&&y1<144)background=24'h17283b;
  if(x1>=360&&y1>=160&&y1<352)background=24'h142438;
  if(y1>=360)begin background=24'h101f31;foreground=24'h94acc3;end
  if(r==29)foreground=24'hf2b768;
  if(r==5&&c>=7&&c<11)begin glyph=names[{state[49:46],2'b00}+(c-7)];foreground=24'h58dcc5;end
  if(r==7&&c>=7&&c<=9)glyph=digit({9'd0,note},9-c);
  if(r==7&&c>=15&&c<=17)glyph=digit({9'd0,velocity},17-c);
  if(r==7&&c>=25&&c<=27)glyph=digit(voices,27-c);
  if(r==12&&c==27)begin glyph=state[66]?GLYPH_ON:GLYPH_OFF;foreground=state[66]?24'h58dcc5:24'hf2b768;end
  if(r==12&&c==28)glyph=GLYPH_LINE;
  if(r==14&&c==27)glyph=state[0]?GLYPH_PLAY:GLYPH_STOP;
  if(r==14&&c==28)glyph=state[0]?GLYPH_PLAY2:GLYPH_STOP2;
  if(r==16&&c>=27&&c<=29)glyph=digit({9'd0,volume},29-c);
  if(r==18&&c>=27&&c<=29)glyph=digit({8'd0,bpm},29-c);
  for(k=0;k<16;k=k+1)begin
   rr=10+(k/4)*3;cc=1+(k%4)*5;
   if(x1>=cc*16&&x1<(cc+4)*16&&y1>=rr*16&&y1<(rr+2)*16)begin
    background=hits[k]?24'h3dcdb3:24'h20354b;foreground=hits[k]?24'h081b22:24'hd9e5f2;
    if(x1==cc*16||y1==rr*16||x1==(cc+4)*16-1||y1==(rr+2)*16-1)background=24'h3d586e;
   end
  end
 end
 always @(posedge clk)begin
  if(rst)begin x1<=0;y1<=0;x2<=0;y2<=0;a1<=0;a2<=0;h1<=1;h2<=1;v1<=1;v2<=1;tile<=32;fontrow<=0;bg2<=0;fg2<=0;rgb<=0;de<=0;hs<=1;vs<=1;end
  else begin
   tile<=tiles[active?row*40+col:0];x1<=x;y1<=y;a1<=active;h1<=hsync_n;v1<=vsync_n;
   fontrow<=font[{glyph,y1[3:0]}];bg2<=background;fg2<=foreground;x2<=x1;y2<=y1;a2<=a1;h2<=h1;v2<=v1;
   rgb<=a2?(fontrow[15-x2[3:0]]?fg2:bg2):24'd0;de<=a2;hs<=h2;vs<=v2;
  end
 end
endmodule
