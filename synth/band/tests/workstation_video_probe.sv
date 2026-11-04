// Probe only: production sources remain byte-identical to the export manifest.
module workstation_video_probe(input clk,audio_clk,pixel_clk,
 output[23:0]rgb,output hs,vs,de,dv,output[31:0]video_frames,
 output pcm_valid,output signed[15:0]left_out,right_out,
 output playing,resetting,clock_fault,display_available,
 output[31:0]position,drops,underruns,deadline,clips,fft_clips,rejected_bins,
 output[15:0]voices,cycles);
 offline_workstation_top dut(.clk(clk),.audio_clk(audio_clk),.uart_rx_pin(1'b1),
 .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),.adc_dout(10'd0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),
 .root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),
 .pixel_clk(pixel_clk),.video_rgb(rgb),.video_hsync_n(hs),.video_vsync_n(vs),.video_active(de),.video_valid(dv));
 assign video_frames=dut.band.video_frame_count;
 assign display_available=dut.band.display_available;
 assign pcm_valid=dut.band.pcm_valid;
 assign left_out=dut.band.pcm_left;assign right_out=dut.band.pcm_right;
 assign playing=dut.band.engine.playing;assign position=dut.band.engine.song_position;
 assign resetting=dut.band.rst;assign clock_fault=dut.band.audio_clock_fault;
 assign drops=dut.band.i2s_dropped;assign underruns=dut.band.i2s_underruns;
 assign deadline=dut.band.engine.deadline_miss;assign clips=dut.band.engine.clips;
 assign voices=dut.band.engine.active_voices;assign cycles=dut.band.engine.render_cycles;
 assign fft_clips=dut.band.fft_clips;assign rejected_bins=dut.band.rejected_bins;
endmodule
