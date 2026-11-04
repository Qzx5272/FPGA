"""Experimental UART/ownership/singer/DAC engine; microphone is core-clock PCM.

No physical microphone pins or released bitstream are implied by this wrapper.
"""
from pathlib import Path
import hashlib,json
b=Path(__file__).resolve().parents[1];src=b/'rtl/band_board_engine.v'
s=src.read_text();out=b/'experimental/vocoder/integration'
def change(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Baseline changed: '+old[:80])
 s=s.replace(old,new)
change('module band_board_engine #(parameter LOCAL_INPUTS=0,parameter EXTERNAL_AUDIO=0)',
       'module band_singer_board_engine #(parameter LOCAL_INPUTS=0,parameter EXTERNAL_AUDIO=0,parameter COEFF_FILE="coeffs.mem")')
change('pcm_valid,reset_out,panic_out);','''pcm_valid,reset_out,panic_out,
 input wire signed [23:0] microphone_sample,input wire [6:0] singer_mix,
 output wire [31:0] dac_dropped,dac_underruns,
 output wire singer_gate,output wire [6:0] singer_note,
 output wire transport_sample_tick);''')
change(' band_core core(', ' wire [31:0] singer_drop_count,singer_stale_count;\n band_singer_core #(.COEFF_FILE(COEFF_FILE)) core(')
change(' assign sample_tick=EXTERNAL_AUDIO?external_sample_tick:debug_tick;',
       ' assign sample_tick=EXTERNAL_AUDIO?external_sample_tick:debug_tick;\n assign transport_sample_tick=sample_tick;')
change('host_control?packet[205:192]:local_xvalue,,);',
       'host_control?packet[205:192]:local_xvalue,,,microphone_sample,singer_mix,singer_gate,singer_note,singer_drop_count,singer_stale_count);')
change(' audio_serial #(.MODE_I2S(0)) dac(clk,rst,left,right,HP_BCK,HP_WS,HP_DIN,debug_tick);',
''' // Queue completion frames: render latency changes with voice load.
 wire dac_ready;wire [2:0] dac_queued;
 audio_pt8211_queue dac(clk,rst,panic||stop,audio_valid,left,right,
  dac_ready,debug_tick,HP_BCK,HP_WS,HP_DIN,dac_dropped,dac_underruns,dac_queued);''')
# Bit31 explicitly marks experimental identity; no production feature contract.
change('FEATURE_FLAGS=32\'d28|', "FEATURE_FLAGS=32'h8000003c|")
change('reg status_request,upload_status,identity_status;', 'reg status_request,upload_status,identity_status,singer_status;')
change('if(rst)begin wet<=32;', 'if(rst)begin singer_status<=0;wet<=32;')
change('identity_status<=kind==18;', 'identity_status<=kind==18;singer_status<=kind==19;')
change(' reg pending_status;', ''' wire [223:0] singer_snapshot={32'd0,32'd0,dac_underruns,dac_dropped,
  singer_stale_count,singer_drop_count,{1'b0,singer_note},{7'd0,singer_gate},8'ha2,8'd4};
 reg pending_status;''')
change('telemetry_snapshot<=identity_status?identity_snapshot:upload_status?upload_snapshot:status_snapshot;',
       'telemetry_snapshot<=identity_status?identity_snapshot:singer_status?singer_snapshot:upload_status?upload_snapshot:status_snapshot;')
target=out/'band_singer_board_engine.sv';target.write_text('// GENERATED experimental wrapper; not a physical pin assignment.\n'+s,encoding='utf-8')
(out/'board_engine_manifest.json').write_text(json.dumps(dict(status='experimental wrapper, requires compile/test and physical top constraints',baseline_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),generated_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),microphone_contract='Signed PCM24 stable in clk domain; bridge/watchdog required for actual ADC',controls='singer_mix is integration input, not a new UART control'),indent=2))
print(target)
