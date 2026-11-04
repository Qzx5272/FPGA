module score_display(input clk,rst,active,frame_start,input[9:0]x,y,input[127:0]state,
 input[127:0]bands,input[383:0]left_trace,right_trace,input[5:0]peak_l,peak_r,
 input[27:0]faders,input seat,solo,input[6:0]progress,input[2:0]count_in,input[31:0]lookahead,
 output reg[23:0]rgb,output reg de);
 `include "score_layout.vh"
 reg[23:0]pixels[0:PIX_SIZE-1] /* synthesis syn_romstyle="block_rom" */;
 initial begin $readmemh("score_pixels.mem",pixels);end
 wire[1:0]page=state[108:107];wire[2:0]song={state[98],state[125:124]};
 wire[3:0]part=state[49:46],target=state[96:93];wire waiting=state[97];
 wire[1:0]mode=state[110:109]==3?3:seat?2:solo?1:0;
 reg[15:0]address;integer n,ox,oy,val,place,dx,idx,level0,level1,curve,axis,fx,fy;
 reg[2:0]accent;reg overlay;reg[7:0]digits[0:255];
 initial for(integer i=0;i<256;i=i+1)digits[i]={4'((i/10)%10),4'(i%10)};
 task number(input integer value,base_x,base_y,width);
  integer digit_pos,digit_id;
  begin
   if(x>=base_x&&x<base_x+16*width&&y>=base_y&&y<base_y+32)begin
    digit_pos=width-1-((x-base_x)>>4);
    case(digit_pos)0:digit_id=digits[value][3:0];1:digit_id=digits[value][7:4];default:digit_id=value>=200?2:value>=100?1:0;endcase
    address=DIGIT_BASE+digit_id*8+((y-base_y)>>3)*2+(((x-base_x)>>3)&1);
   end
  end
 endtask
 // Convert the latched frame parameter over 14 pixel clocks before its row is drawn.
 reg[13:0]attack_sample,attack_shift;
 reg[19:0]attack_work,attack_decimal,adjusted;
 reg[3:0]remaining;
 always @*begin
  adjusted=attack_work;
  for(integer k=0;k<5;k=k+1)
   if(attack_work[4*k+:4]>=5)adjusted[4*k+:4]=attack_work[4*k+:4]+4'd3;
 end
 always @(posedge clk)begin
  if(rst)begin attack_sample<=0;attack_decimal<=0;remaining<=0;attack_work<=0;attack_shift<=0;end
  else if(attack_sample!=state[80:67])begin
   attack_sample<=state[80:67];attack_shift<=state[80:67];attack_work<=0;remaining<=14;
  end else if(remaining!=0)begin
   attack_work<={adjusted[18:0],attack_shift[13]};
   attack_shift<=attack_shift<<1;remaining<=remaining-1'b1;
   if(remaining==1)attack_decimal<={adjusted[18:0],attack_shift[13]};
  end
 end
 // Refresh a small XY bitmap once per video frame; all writes finish before row 169.
 reg xy[0:4095];reg[12:0]cursor;reg[5:0]px,py;reg[383:0]xl,xr;
 always @(posedge clk)begin
  if(rst||frame_start)begin cursor<=0;end
  else if(cursor<4096)begin xy[cursor[11:0]]<=0;cursor<=cursor+1'b1;end
  else if(cursor==4096)begin xl<=left_trace;xr<=right_trace;cursor<=4097;end
  else if(cursor==4097)begin px<=xl[5:0];py<=xr[5:0];cursor<=4098;end
  else if(cursor<4162)begin
   xy[{~py,px}]<=1;
   if(px==xl[5:0]&&py==xr[5:0])begin xl<=xl>>6;xr<=xr>>6;cursor<=cursor+1'b1;end
   else begin if(px!=xl[5:0])px<=px<xl[5:0]?px+1'b1:px-1'b1;if(py!=xr[5:0])py<=py<xr[5:0]?py+1'b1:py-1'b1;end
  end
 end
 // Prepare one column per clock during vertical blank. A sequential read
 // replaces two wide variable selects and a multiply in the pixel path.
 reg[383:0]wave_shift;reg[127:0]band_shift;reg[9:0]column;
 reg signed[13:0]height,delta;
 reg[8:0]plot[0:511];reg[8:0]plot_y;reg[9:0]plot_screen_y;reg plot_in_view;reg wide_plot;
 wire signed[11:0]wave_start=$signed({1'b0,wave_shift[5:0]})-32;
 wire signed[11:0]wave_delta=$signed({1'b0,wave_shift[11:6]})-$signed({1'b0,wave_shift[5:0]});
 wire signed[11:0]band_start=$signed({1'b0,band_shift[3:0]})*10;
 wire signed[11:0]band_delta=($signed({1'b0,band_shift[7:4]})-$signed({1'b0,band_shift[3:0]}))*10;
 wire signed[13:0]plot_value=page==1?(column[3:0]==0?372-band_start:372-(height>>>4)):(column[2:0]==0?262-wave_start:262-(height>>>3));
 always @(posedge clk)begin
  if(column<512)plot[column[8:0]]<=plot_value[8:0];
  plot_y<=plot[(x-10'd144)&9'h1ff];plot_screen_y<=y;wide_plot<=page==1;
  plot_in_view<=x>=144&&((page==0&&x<648&&y>=216&&y<314)||(page==1&&x<640&&y>=200&&y<=375));
 end
 wire plot_hit=plot_in_view&&(plot_screen_y==plot_y||plot_screen_y==plot_y+1'b1||(wide_plot&&plot_screen_y+1'b1==plot_y));
 always @(posedge clk)begin
  if(rst||frame_start)begin column<=1023;end
  else if(column==1023)begin
   wave_shift<=left_trace;band_shift<=bands;column<=0;
  end else if(column<512)begin
   column<=column+1'b1;
   if(page==1)begin
    if(column[3:0]==0)begin
     height<=(band_start<<<4)+band_delta;
     delta<=band_delta;band_shift<=band_shift>>4;
    end else begin height<=height+delta;end
   end else begin
    if(column[2:0]==0)begin
     height<=(wave_start<<<3)+wave_delta;
     delta<=wave_delta;wave_shift<=wave_shift>>6;
    end else begin height<=height+delta;end
   end
  end
 end
 always @*begin
  address=page*6000+(y>>3)*100+(x>>3);overlay=0;accent=6;dx=0;idx=0;level0=0;level1=0;curve=0;axis=0;fx=0;fy=0;
  number(state[7:1],264,8,3);
  if(page==0)begin
   number(state[123:117],144,80,3);
   number(state[84:81],608,112,2);
   if(y>=72&&y<104&&x>=608&&x<688)begin
    case(x[6:4])
     3'd6:idx=attack_decimal[19:16];
     3'd7:idx=attack_decimal[15:12];
     3'd0:idx=attack_decimal[11:8];
     3'd1:idx=attack_decimal[7:4];
     default:idx=attack_decimal[3:0];
    endcase
    address=DIGIT_BASE+idx*8+((y-72)>>3)*2+x[3];
   end
   if(x>=280&&x<520&&y>=72&&y<136)address=PART_BASE+part*240+((y-72)>>3)*30+((x-280)>>3);
   number(part,432,136,2);if(x>=136&&x<200&&y>=176&&y<208)address=NOTE_BASE+state[38:32]*32+((y-176)>>3)*8+((x-136)>>3);number(state[45:39],392,176,3);number(state[15:8],656,176,3);
   for(integer j=0;j<4;j=j+1)begin
    fx=114+(j%2)*375;fy=332+(j/2)*60;
    if(x>=fx&&x<=fx+faders[j*7+:7]*2&&y>=fy-1&&y<=fy+1)overlay=1;
   end
  end else if(page==2)begin
   if(x>=88&&x<344&&y>=169&&y<425)overlay=xy[((y-169)>>2)*64+((x-88)>>2)];
   if(y<398&&((x>=469&&x<502&&y>=398-peak_l*2)||(x>=629&&x<662&&y>=398-peak_r*2)))overlay=1;
  end else if(page==3)begin
   if(x>=224&&x<576&&y>=64&&y<128)address=SONG_BASE+song*352+((y-64)>>3)*44+((x-224)>>3);
   if(x>=424&&x<584&&y>=256&&y<288)address=MODE_BASE+mode*80+((y-256)>>3)*20+((x-424)>>3);
   if(lookahead[31])begin
    number(lookahead[30:27]+1,432,216,2);
    if(x>=488&&x<552&&y>=216&&y<248)address=NOTE_BASE+lookahead[26:20]*32+((y-216)>>3)*8+((x-488)>>3);
    if(lookahead[19])number(lookahead[18:15]+1,520,368,2);
    if(y>=414&&y<=426&&x>=460+lookahead[14:8]*2&&x<465+lookahead[14:8]*2)overlay=1;
   end
   if(count_in!=0)number(count_in,688,256,1);
   if(y>=347&&y<=349&&x>=430&&x<430+progress*2)overlay=1;
   fx=50+target[1:0]*76;fy=172+(3-target[3:2])*62;
   if(waiting&&x>=fx&&x<fx+66&&y>=fy&&y<fy+54&&
      (x<fx+3||x>=fx+63||y<fy+3||y>=fy+51))begin overlay=1;accent=7;end
  end
 end
 reg[10:0]block_id;reg[2:0]slot;
 reg[11:0]tile;reg[11:0]row_id;reg[23:0]row;reg[5:0]offset1,offset2;reg[2:0]cx3,cx4;
 reg[3:0]act,overlay_pipe;reg[11:0]colors;
 wire[12:0]block_address=active?address[15:3]:0;
 `include "block_banks.vh"
 wire[13:0]tile_address={block_id,slot};
 `include "tile_banks.vh"
 wire[14:0]row_address={tile,offset2[5:3]};
 `include "row_banks.vh"
 wire[2:0]color=overlay_pipe[3]?colors[11:9]:row[cx4*3+:3];
 always @(posedge clk)begin
  slot<=address[2:0];offset1<={y[2:0],x[2:0]};
  offset2<=offset1;
  cx3<=offset2[2:0];
  row<=pixels[row_id];cx4<=cx3;
  act<={act[2:0],active&&!rst};de<=act[3];overlay_pipe<={overlay_pipe[2:1],overlay_pipe[0]||plot_hit,overlay};colors<={colors[8:0],accent};
  case(color)
   0:rgb<=24'hFAF5E9;1:rgb<=24'hE9DFCF;2:rgb<=24'hD5C7B3;3:rgb<=24'h84796B;
   4:rgb<=24'h292722;5:rgb<=24'hD49B86;6:rgb<=24'hA33727;7:rgb<=24'hFAC751;
  endcase
 end
endmodule

