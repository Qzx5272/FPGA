`timescale 1ns/1ps
module tb;
 reg ac=0,dc=0,rst=1,dc_run=1;always #10 ac=~ac;always #13 if(dc_run)dc=~dc;
 reg bv=0;wire br;reg[10:0]bi=0;reg signed[15:0]re=0,im=0;
 reg[31:0]source_frame=1;wire available,rv,read_en,rel;wire[10:0]addr;
 wire signed[15:0]rr,ri;wire[31:0]rejected;
 reg frame_start=0;reg[9:0]pixel_x=0,pixel_y=0;wire[23:0]rgb;
 wire display_valid;wire[31:0]displayed_frames;
 spectrum_snapshot snapshot(.analysis_clk(ac),.display_clk(dc),.rst(rst),
 .bin_valid(bv),.bin_ready(br),.bin_index(bi),.bin_real(re),.bin_imag(im),
 .input_frame(source_frame),.input_last_sample(32'd2047),.input_peak_left(17'd1000),.input_peak_right(17'd1000),
 .read_enable(read_en),.read_address(addr),.release_frame(rel),.frame_available(available),.read_valid(rv),
 .read_real(rr),.read_imag(ri),.rejected_bins(rejected));
 spectrum_bars dut(.clk(dc),.rst(rst),.frame_start(frame_start),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .frame_available(available),.read_valid(rv),.read_real(rr),.read_imag(ri),
 .read_enable(read_en),.read_address(addr),.release_frame(rel),.rgb(rgb),
 .display_valid(display_valid),.displayed_frames(displayed_frames));
 reg[31:0]bin_data[0:2047];reg[7:0]heights[0:31];integer k,j,count=0;
 always @(posedge dc)if(!rst&&read_en)begin
  if(addr<1||addr>1023)$fatal(1,"invalid positive-bin address");count=count+1;
 end
 task publish(input integer which);integer n;begin
  for(n=0;n<2048;n=n+1)begin
   @(negedge ac);while(!br)@(negedge ac);
   bv=1;bi=n;{re,im}=which==0?bin_data[n]:32'd0;
  end
  @(negedge ac);bv=0;
 end endtask
 task swap;begin @(negedge dc);frame_start=1;@(negedge dc);frame_start=0;end endtask
 initial begin
  $readmemh("bins.mem",bin_data);$readmemh("heights.mem",heights);
  repeat(4)@(negedge dc);rst=0;
  publish(0);wait(dut.pending);repeat(5)@(negedge dc);
  if(display_valid||displayed_frames||count!=1023)$fatal(1,"premature visible/reader count");
  for(j=0;j<32;j=j+1)if(dut.bars1[j]!==heights[j])$fatal(1,"band%0d expected%0d actual%0d",j,heights[j],dut.bars1[j]);
  source_frame=2;publish(1);wait(available);
  repeat(100)@(negedge dc);
  if(count!=1023||!dut.pending)$fatal(1,"pending frame overwritten or reader not stalled");
  swap();
  if(!display_valid||displayed_frames!=1)$fatal(1,"missing first frame swap");
  for(j=0;j<32;j=j+1)begin
   pixel_x=64+j*16;pixel_y=439;#1;
   if(rgb!==(heights[j]>=210?24'hff9e40:24'h35d8c2))$fatal(1,"bar pixel%0d",j);
   pixel_x=64+j*16+14;#1;if(rgb!==24'h080c16)$fatal(1,"gap pixel");
   pixel_x=64+j*16;pixel_y=439-heights[j];#1;if(rgb!==24'h080c16)$fatal(1,"bar upper edge");
  end
  wait(dut.pending);repeat(5)@(negedge dc);
  if(displayed_frames!=1||count!=2046)$fatal(1,"second frame count");
  pixel_x=64;pixel_y=439;#1;if(rgb===24'h080c16)$fatal(1,"tearing before video boundary");
  swap();#1;if(rgb!==24'h080c16||displayed_frames!=2)$fatal(1,"silence frame swap");
  @(negedge dc);rst=1;repeat(3)@(negedge dc);
  if(display_valid||read_en||rel||displayed_frames)$fatal(1,"reset did not clear display");
  rst=0;source_frame=3;publish(0);wait(read_en);repeat(20)@(negedge dc);rst=1;
  repeat(4)@(negedge dc);rst=0;repeat(30)@(negedge dc);
  if(display_valid||dut.pending||available||rejected)$fatal(1,"interrupted scan survived reset");
  source_frame=4;publish(0);wait(dut.pending);swap();
  if(!display_valid)$fatal(1,"missing frame before stopped-clock reset");
  @(negedge dc);dc_run=0;#5;rst=1;#20;rst=0;#50;
  if(display_valid||dut.pending||read_en||rel||available)$fatal(1,"stopped-clock reset left stale display");
  dc_run=1;repeat(100)@(negedge dc);
  if(display_valid||available)$fatal(1,"stale display after clock restart");
  $display("PASS32 bands exact height/pixels;actual snapshot;frame-boundary swap,stall,no tearing,silence,midscan and stopped-clock reset");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
