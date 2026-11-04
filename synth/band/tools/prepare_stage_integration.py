"""Compose full experimental local seats/pedals + microphone singer/PT8211 top."""
from pathlib import Path
import subprocess,sys
b=Path(__file__).resolve().parents[1];s=b/'experimental/vocoder/integration'
subprocess.run([sys.executable,str(b/'tools/prepare_local_pedal.py')],check=True)
out=b/'experimental/stage';out.mkdir(exist_ok=True)
engine=(s/'band_singer_board_engine.sv').read_text()
assert 'assign host_control=accepted&&kind==11&&source_ok;' in engine
# kind11 always has packet_ready=1, so accepted's unrelated manual-ready path
# is unnecessary here. This removes a false combinational dependency, not checks.
engine=engine.replace('assign host_control=accepted&&kind==11&&source_ok;','assign host_control=packet_valid&&kind==11&&source_ok;')
engine=engine.replace('  pad_frontend pads(', '  stage_pad_frontend pads(')
engine=engine.replace('module band_singer_board_engine #(', 'module band_stage_engine #(parameter PEDAL_STABLE_CYCLES=250000,')
engine=engine.replace(' output wire transport_sample_tick);',' output wire transport_sample_tick,\n input wire [3:0] pedal_raw,output wire [3:0] pedal_down,output wire [15:0] deferred_returns);')
engine=engine.replace('  local_performer performer(', '  local_pedal_performer #(.STABLE_CYCLES(PEDAL_STABLE_CYCLES)) performer(')
engine=engine.replace('local_denied,local_held);','local_denied,local_held,pedal_raw,pedal_down,deferred_returns);')
engine=engine.replace(' end else begin:no_local_inputs',' end else begin:no_local_inputs\n  assign pedal_down=0;assign deferred_returns=0;')
assert 'local_pedal_performer #' in engine
(out/'band_stage_engine.sv').write_text(engine)
top=(s/'band_microphone_top.sv').read_text()
top=top.replace('module band_microphone_top #(', 'module band_stage_top #(parameter PEDAL_STABLE_CYCLES=250000,')
top=top.replace(' output wire microphone_stale,',' input wire [9:0] adc_dout,output wire adc_cs_n,adc_sclk,adc_din,\n input wire play_button,stop_button,panic_button,input wire [3:0] root,input wire minor_mode,\n input wire [3:0] pedal_raw,output wire [3:0] pedal_down,seat_led,output wire [15:0] deferred_returns,\n output wire microphone_stale,')
top=top.replace(' wire rst,panic,tick;', ' wire [63:0] held;assign seat_led={|held[63:48],|held[47:32],|held[31:16],|held[15:0]};\n wire rst,panic,tick;')
top=top.replace(' wire rst,panic,tick;', ' wire rst,panic,tick;wire [4:0] selected_scale;\n stable_selector selector(clk,rst,{minor_mode,root},selected_scale);')
top=top.replace('band_singer_board_engine #(.COEFF_FILE(COEFF_FILE))','band_stage_engine #(.LOCAL_INPUTS(1),.COEFF_FILE(COEFF_FILE),.PEDAL_STABLE_CYCLES(PEDAL_STABLE_CYCLES))')
top=top.replace('.adc_dout(10\'d0),.adc_cs_n(),.adc_sclk(),.adc_din(),', '.adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),')
top=top.replace(".local_play(1'b0),.local_stop(1'b0),.local_panic(1'b0),.local_root(4'd0),.local_minor(1'b0),.local_held(),",'.local_play(play_button),.local_stop(stop_button),.local_panic(panic_button),.local_root(root),.local_minor(minor_mode),.local_held(held),')
top=top.replace('.local_root(root),.local_minor(minor_mode)', '.local_root(selected_scale[3:0]),.local_minor(selected_scale[4])')
top=top.replace('.transport_sample_tick(tick));','.transport_sample_tick(tick),.pedal_raw(pedal_raw),.pedal_down(pedal_down),.deferred_returns(deferred_returns));')
(out/'band_stage_top.sv').write_text(top)
