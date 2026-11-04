"""Generate external-clock paced stage; no PT8211/standard-I2S pin aliasing."""
from pathlib import Path
import subprocess,sys
b=Path(__file__).resolve().parents[1];out=b/'experimental/audio_input'
subprocess.run([sys.executable,str(b/'tools/prepare_stage_integration.py')],check=True)
engine=(b/'experimental/stage/band_stage_engine.sv').read_text()
def replace(s,old,new):
 assert s.count(old)==1,old
 return s.replace(old,new)
sys.path.insert(0,str(b/'host'))
from i2s_source import adapt_stage_engine
engine=adapt_stage_engine(engine)
(out/'band_stage_i2s_engine.sv').write_text(engine)
s=(b/'experimental/stage/band_stage_top.sv').read_text()
s=replace(s,'module band_stage_top #(', 'module band_stage_i2s_top #(parameter AUDIO_CLOCK_TIMEOUT=50000,')
s=replace(s,'output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,', 'input wire audio_clk,output wire uart_tx_pin,i2s_bck,i2s_ws,i2s_sd,\n output wire[31:0]i2s_dropped,i2s_underruns,')
s=replace(s,' wire rst,panic,tick;', ' wire signed[15:0]pcm_left,pcm_right;wire pcm_valid,i2s_tick,audio_stop;\n wire rst,panic,tick;')
s=replace(s,'output wire[31:0]i2s_dropped,i2s_underruns,','output wire[31:0]i2s_dropped,i2s_underruns,audio_clock_losses,output wire audio_clock_fault,')
s=replace(s,'band_stage_engine #(.LOCAL_INPUTS(1),','band_stage_i2s_engine #(.EXTERNAL_AUDIO(1),.LOCAL_INPUTS(1),')
s=replace(s,'.HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),','.HP_BCK(),.HP_WS(),.HP_DIN(),.PA_EN(),')
s=replace(s,".external_sample_tick(1'b0),.pcm_left(),.pcm_right(),.pcm_valid(),",'.external_sample_tick(i2s_tick),.pcm_left(pcm_left),.pcm_right(pcm_right),.pcm_valid(pcm_valid),')
s=replace(s,'.transport_sample_tick(tick),','.transport_fault(audio_clock_fault),.transport_sample_tick(tick),.audio_stop(audio_stop),.external_dropped(i2s_dropped),.external_underruns(i2s_underruns),')
s=replace(s,'endmodule',''' audio_clock_watchdog #(.TIMEOUT_CYCLES(AUDIO_CLOCK_TIMEOUT)) clock_watch(
 .core_clk(clk),.audio_clk(audio_clk),.rst(rst),.fault(audio_clock_fault),.losses(audio_clock_losses));
 i2s24_queue_bridge output_audio(.core_clk(clk),.audio_clk(audio_clk),.rst(rst),.panic(panic||audio_stop),
 .frame_valid(pcm_valid),.left_in({pcm_left,8'd0}),.right_in({pcm_right,8'd0}),
 .frame_ready(),.sample_tick(i2s_tick),.bck(i2s_bck),.ws(i2s_ws),.sd(i2s_sd),
 .dropped_frames(i2s_dropped),.underruns_audio_domain(),.underruns_core_domain(i2s_underruns));
endmodule''')
(out/'band_stage_i2s_top.sv').write_text('// GENERATED. External24.576MHz clock and DAC pins/constraints REQUIRED;16effective bits.\n'+s)
