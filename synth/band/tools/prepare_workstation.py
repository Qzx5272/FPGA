"""Combine stage roles/seats, queued I2S/watchdog and frozen spectrum reader."""
from pathlib import Path
import subprocess,sys
b=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(b/'tools/prepare_i2s_stage.py')],check=True)
s=(b/'experimental/audio_input/band_stage_i2s_top.sv').read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,old
 s=s.replace(old,new)
replace('module band_stage_i2s_top #(', 'module band_workstation_top #(parameter TWIDDLE_FILE="fft_twiddle_2048.mem",parameter WINDOW_FILE="hann_2048.mem",')
replace('output wire [31:0] mic_received,mic_repeated,mic_skipped,mic_timeouts', '''output wire [31:0] mic_received,mic_repeated,mic_skipped,mic_timeouts,
 input wire analysis_clk,display_clk,display_read,display_release,input wire[10:0]display_address,
 output wire display_available,spectrum_valid,output wire signed[15:0]spectrum_real,spectrum_imag,
 output wire[31:0]spectrum_frame,spectrum_last_sample,visualization_skipped,fft_clips,rejected_bins,
 output wire[16:0]spectrum_peak_left,spectrum_peak_right''')
replace('endmodule',''' pcm_spectrum_buffered #(.TWIDDLE_FILE(TWIDDLE_FILE),.WINDOW_FILE(WINDOW_FILE)) analyzer(
 .audio_clk(clk),.analysis_clk(analysis_clk),.display_clk(display_clk),.rst(rst||panic||audio_stop),
 .pcm_valid(pcm_valid),.pcm_left(pcm_left),.pcm_right(pcm_right),
 .read_enable(display_read),.read_address(display_address),.release_frame(display_release),
 .frame_available(display_available),.read_valid(spectrum_valid),.read_real(spectrum_real),.read_imag(spectrum_imag),
 .frame_number(spectrum_frame),.last_sample(spectrum_last_sample),.rejected_bins(rejected_bins),
 .peak_left(spectrum_peak_left),.peak_right(spectrum_peak_right),
 .visualization_skipped(visualization_skipped),.fft_clips(fft_clips));
endmodule''')
(b/'experimental/audio_visual/band_workstation_top.sv').write_text('// GENERATED combined workstation; no physical pin/clock assignment.\n'+s)
