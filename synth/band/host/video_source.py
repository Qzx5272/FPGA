"""Attach a pixel consumer to the existing workstation spectrum, without a second FFT."""
from offline import replace_once

def adapt_workstation_video(source):
    source=replace_once(source,'module band_workstation_top #(','module band_workstation_video_top #(')
    source=replace_once(source,' input wire analysis_clk,display_clk,display_read,display_release,input wire[10:0]display_address,',
        ''' input wire analysis_clk,pixel_clk,
 output wire[23:0]video_rgb,output wire video_hsync_n,video_vsync_n,video_active,video_valid,
 output wire[31:0]video_frame_count,''')
    source=replace_once(source,' wire [63:0] held;',
        ''' wire display_clk=pixel_clk;wire display_read,display_release;wire[10:0]display_address;
 wire [63:0] held;''')
    source=replace_once(source,'endmodule', ''' // Asynchronous assertion, two-pixel-clock release including stopped clocks.
 wire video_async_reset=rst||panic||audio_stop;
 (* ASYNC_REG="TRUE" *)reg[1:0]video_reset_hold=2'b11;
 always @(posedge pixel_clk or posedge video_async_reset)
  if(video_async_reset)video_reset_hold<=2'b11;
  else video_reset_hold<={video_reset_hold[0],1'b0};
 wire video_reset=video_reset_hold[1];
 wire[9:0]video_x,video_y;wire video_boundary;wire[23:0]bar_rgb;
 video_timing_640x480 raster(pixel_clk,video_reset,video_x,video_y,
  video_active,video_hsync_n,video_vsync_n,video_boundary);
 spectrum_bars bars(.clk(pixel_clk),.rst(video_reset),.frame_start(video_boundary),
  .pixel_x(video_x),.pixel_y(video_y),.frame_available(display_available),
  .read_valid(spectrum_valid),.read_real(spectrum_real),.read_imag(spectrum_imag),
  .read_enable(display_read),.read_address(display_address),.release_frame(display_release),
  .rgb(bar_rgb),.display_valid(video_valid),.displayed_frames(video_frame_count));
 assign video_rgb=video_active?bar_rgb:24'd0;
endmodule''')
    assert source.count(' pcm_spectrum_buffered #(')==1
    return '// GENERATED logical RGB variant; no PLL/HDMI/physical acceptance.\n'+source
