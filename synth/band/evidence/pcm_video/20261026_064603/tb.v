`timescale 1ns/1ps
module tb;
reg ac=0,fc=0,pc=0,run=1;always #7 ac=~ac;always #5 fc=~fc;always #20 if(run)pc=~pc;
reg rst=1,pv=0;reg signed[15:0]l=0,r=0;
wire[23:0]rgb;wire hs,vs,de,dv;wire[31:0]frames,skips,clips,rejects;
integer i,n,ex,ey,active_count=0,hs_count=0,vs_count=0,boundaries=0,color_count=0,expected_colors=0;
pcm_video_640x480 #(.TWIDDLE_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/fft_twiddle_2048.mem"),.WINDOW_FILE("C:/Users/Qzx/Documents/ChatGPT/FPGA/synth/band/experimental/audio_visual/hann_2048.mem")) dut(
 .audio_clk(ac),.analysis_clk(fc),.pixel_clk(pc),.rst(rst),.pcm_valid(pv),.pcm_left(l),.pcm_right(r),
 .rgb(rgb),.hsync_n(hs),.vsync_n(vs),.active_video(de),.display_valid(dv),.displayed_frames(frames),
 .visualization_skipped(skips),.fft_clips(clips),.rejected_bins(rejects));
initial begin
 repeat(4)@(negedge pc);rst=0;
 // Capture accepts data after its two-clock synchronous reset release.
 repeat(3)@(negedge ac);
 for(i=0;i<2048;i=i+1)begin @(negedge ac);pv=1;l=(i%32<16)?16000:-16000;r=0;end
 @(negedge ac);pv=0;
 wait(dv);@(negedge pc);
 if(dut.x!=0||dut.y!=0||frames!=1)$fatal(1,"swap was not at first active pixel");
 for(i=0;i<32;i=i+1)expected_colors=expected_colors+14*(15*dut.display.view.levels1[i]);
 for(n=0;n<420000;n=n+1)begin
  ex=n%800;ey=n/800;
  if(dut.x!=ex||dut.y!=ey)$fatal(1,"pixel address%0d",n);
  if(de!==(ex<640&&ey<480)||hs!==(!(ex>=656&&ex<752))||vs!==(!(ey>=490&&ey<492)))$fatal(1,"sync/de%0d",n);
  if(dut.frame_boundary!==(n==419999))$fatal(1,"frame boundary%0d",n);
  if(!de&&rgb!==0)$fatal(1,"nonblack blanking%0d",n);
  if(de)begin
   active_count=active_count+1;
   if(rgb!=24'h080c16)begin
    if(ex<64||ex>=576||ey<200||ey>=440||((ex-64)%16)>=14)$fatal(1,"colored pixel outside bars");
    if(rgb!=24'hff9e40&&rgb!=24'h35d8c2)$fatal(1,"unexpected color");
    color_count=color_count+1;
   end
  end
  if(!hs)hs_count=hs_count+1;if(!vs)vs_count=vs_count+1;
  if(dut.frame_boundary)boundaries=boundaries+1;
  @(negedge pc);
 end
 if(active_count!=307200||hs_count!=50400||vs_count!=1600||boundaries!=1||color_count!=expected_colors||color_count==0||frames!=1||clips||rejects)$fatal(1,"raster totals or unstable front frame");
 run=0;#5;rst=1;#20;
 if(dv||rgb||de||dut.x||dut.y)$fatal(1,"asserted stopped video reset");
 rst=0;#50;
 if(dv||rgb!==24'h080c16||de!==1'b1||dut.x||dut.y)$fatal(1,"released stopped video reset");
 run=1;repeat(100)@(negedge pc);if(dv)$fatal(1,"stale picture after restart");
 $display("PASS420000 pixel raster:active=%0d hsync_low=%0d vsync_low=%0d colored=%0d;actual PCM/FFT,atomic frame,black blanking,stopped-clock reset",active_count,hs_count,vs_count,color_count);$finish;
end
initial begin #50000000;$fatal(1,"timeout");end
endmodule
