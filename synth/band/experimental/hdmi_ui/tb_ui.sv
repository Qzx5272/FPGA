module tb_ui;
 reg clk=0;always #5 clk=~clk;
 reg rst=1;reg[9:0]x=0,y=0;reg active=0,hin=1,vin=1;reg[127:0]state=0;
 wire[23:0]rgb;wire de,hs,vs;
 instrument_ui dut(clk,rst,x,y,active,hin,vin,state,rgb,de,hs,vs);
 reg[2:0]ap=0,hp=7,vp=7;
 always @(posedge clk)begin
  if(rst)begin ap=0;hp=7;vp=7;end
  else begin ap={ap[1:0],active};hp={hp[1:0],hin};vp={vp[1:0],vin};#1;
   if(de!==ap[2]||hs!==hp[2]||vs!==vp[2])$fatal(1,"RGB/sync pipeline mismatch");
   if(!de&&rgb!==0)$fatal(1,"blanking RGB not zero");
  end
 end
 integer file,n=0,xx,yy;
 initial begin
  file=$fopen("ui_frame.ppm","w");$fwrite(file,"P3\n640 480\n255\n");
  state[7:1]=64;state[15:8]=120;state[31:16]=2;state[38:32]=70;state[45:39]=98;state[49:46]=8;state[65:50]=16'h0420;state[66]=1;
  repeat(4)@(negedge clk);rst=0;
  for(yy=0;yy<480;yy=yy+1)for(xx=0;xx<640;xx=xx+1)begin @(negedge clk);x=xx;y=yy;active=1;hin=(xx%127)>3;vin=(yy%127)>3;end
  @(negedge clk);active=0;repeat(5)@(negedge clk);
  if(n!=307200)$fatal(1,"pixel count %d",n);$fclose(file);$display("PASS UI 640x480 pipeline and frame");$finish;
 end
 always @(negedge clk)if(de)begin
  if(^rgb===1'bx)$fatal(1,"unknown pixel");
  $fwrite(file,"%d %d %d\n",rgb[23:16],rgb[15:8],rgb[7:0]);n=n+1;
 end
endmodule
