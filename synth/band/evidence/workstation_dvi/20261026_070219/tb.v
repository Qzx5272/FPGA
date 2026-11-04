`timescale 1ns/1ps
module tb;
reg clk=0,ac=0;always #10 clk=~clk;always #20.345833 ac=~ac;
wire cp,cn,dv;wire[2:0]dp,dn;integer fp,fs,frames=0,peak=0,stalled_start,n=0;reg capture=0;
GSR GSR(.GSRI(1'b1));
offline_workstation_top dut(.clk(clk),.audio_clk(ac),.uart_rx_pin(1'b1),
 .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),.adc_dout(10'd0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),
 .tmds_clk_p(cp),.tmds_clk_n(cn),.tmds_d_p(dp),.tmds_d_n(dn),.video_valid(dv));
always @(posedge clk)begin
 if(dut.band.engine.playing)begin
  if(dut.band.i2s_dropped||dut.band.i2s_underruns||dut.band.engine.deadline_miss||dut.band.engine.clips||dut.band.fft_clips||dut.band.rejected_bins)$fatal(1,"audio/analyzer counters");
  if(dut.band.pcm_valid)begin frames=frames+1;
   if($signed(dut.band.pcm_left)>peak)peak=$signed(dut.band.pcm_left);
  end
 end
end
always @(posedge dut.video_output.serial_clk or negedge dut.video_output.serial_clk)begin
 #1;if(capture)begin
  if(cp!==dut.pixel_clk||cn!==!dut.pixel_clk||dn!==~dp)$fatal(1,"differential pins");
  $fdisplay(fs,"%b",dp);
 end
end
initial begin
 fp=$fopen("pixels.txt","w");fs=$fopen("serial.txt","w");
 wait(dv);wait(dut.band.video_y==400&&dut.band.video_x==640);
 @(negedge dut.pixel_clk);capture=1;
 for(n=0;n<1200;n=n+1)begin
  $fdisplay(fp,"%b %b %b %h",dut.video_active,dut.video_hsync_n,dut.video_vsync_n,dut.video_rgb);
  @(negedge dut.pixel_clk);
 end
 repeat(16)@(negedge dut.pixel_clk);capture=0;$fclose(fp);$fclose(fs);
 if(frames<2048||peak==0)$fatal(1,"no real band PCM");
 stalled_start=frames;force dut.video_ready=0;#1;
 if(dv||dut.band.display_available)$fatal(1,"display ready loss did not clear stale picture");
 repeat(5000)@(negedge clk);
 if(frames-stalled_start<4||!dut.band.engine.playing||dv)$fatal(1,"display fault stalled audio");
 release dut.video_ready;repeat(20)@(negedge dut.pixel_clk);
 if(dv)$fatal(1,"old frame reappeared immediately");
 $display("PASS actualband DVI frames=%0d peak=%0d audio_during_display_reset=%0d",frames,peak,frames-stalled_start);$finish;
end
initial begin #120000000;$fatal(1,"whole DVI timeout");end
endmodule
