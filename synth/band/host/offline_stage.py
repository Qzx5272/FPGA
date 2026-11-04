"""Export an editable score into the complete local-seat/singer stage source."""
from pathlib import Path
import hashlib,json,shutil,datetime
from offline_singer import export_singer_project
from offline import replace_once

def export_stage_project(score,destination,autoplay=True):
    if score.get('engine_profile')!='singer-v1':raise ValueError('融合顶层需要明确的 singer-v1 作品角色配置')
    target=export_singer_project(score,destination,autoplay);rtl=target/'rtl';band=Path(__file__).resolve().parents[1]
    # Start from the exported engine, preserving the user's startup, song and presets.
    engine=(rtl/'band_singer_board_engine.sv').read_text()
    engine=replace_once(engine,'assign host_control=accepted&&kind==11&&source_ok;','assign host_control=packet_valid&&kind==11&&source_ok;')
    engine=replace_once(engine,'  pad_frontend pads(', '  stage_pad_frontend pads(')
    engine=replace_once(engine,'module band_singer_board_engine #(', 'module band_stage_engine #(parameter PEDAL_STABLE_CYCLES=250000,')
    engine=replace_once(engine,' output wire transport_sample_tick);',' output wire transport_sample_tick,\n input wire [3:0] pedal_raw,output wire [3:0] pedal_down,output wire [15:0] deferred_returns);')
    engine=replace_once(engine,'  local_performer performer(', '  local_pedal_performer #(.STABLE_CYCLES(PEDAL_STABLE_CYCLES)) performer(')
    engine=replace_once(engine,'local_denied,local_held);','local_denied,local_held,pedal_raw,pedal_down,deferred_returns);')
    engine=replace_once(engine,' end else begin:no_local_inputs',' end else begin:no_local_inputs\n  assign pedal_down=0;assign deferred_returns=0;')
    (rtl/'band_stage_engine.sv').write_text(engine)
    for name in ('local_pedal_performer.v','pedal_command_gate.v'):shutil.copy2(band/'experimental/local_pedal'/name,rtl/name)
    shutil.copy2(band/'experimental/stage/band_stage_top.sv',rtl/'band_stage_top.sv')
    shutil.copy2(band/'experimental/stage/stable_selector.sv',rtl/'stable_selector.sv')
    shutil.copy2(band/'experimental/stage/stage_pad_frontend.sv',rtl/'stage_pad_frontend.sv')
    # The stage replaces pad_frontend; carry startup calibration into that module
    # as logical defaults, without resetting every RAM word into registers.
    from calibration_model import normalize
    calibration=normalize(score.get('performance',{}).get('pad_calibration',{}))
    if calibration:
        lines=['function [28:0] offline_stage_calibration; input [6:0] channel; begin case(channel)']
        for channel,values in sorted(calibration.items()):
            packed=(int(values['invert'])<<28)|(values['gain']<<12)|values['baseline']
            lines.append(f"7'd{channel}:offline_stage_calibration=29'h{packed:08x};")
        lines.append("default:offline_stage_calibration={1'b0,16'd127,12'd0};endcase end endfunction")
        p=rtl/'stage_pad_frontend.sv';text=p.read_text()
        text=replace_once(text,' localparam CHANNELS=CHIPS*8;','\n'.join(lines)+'\n localparam CHANNELS=CHIPS*8;')
        text=replace_once(text,"configured[address]?calibration[address]:{1'b0,16'd127,12'd0}","configured[address]?calibration[address]:offline_stage_calibration(address)")
        p.write_text(text)
    (rtl/'offline_stage_top.sv').write_text('''// Physical constraints and external timing must be supplied before building.
module offline_stage_top(input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,
 input [9:0] adc_dout,output adc_cs_n,adc_sclk,adc_din,
 input play_button,stop_button,panic_button,input [3:0] root,input minor_mode,
 input [3:0] pedal_raw,output [3:0] seat_led);
 band_stage_top band(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
 .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(play_button),.stop_button(stop_button),.panic_button(panic_button),.root(root),.minor_mode(minor_mode),
 .pedal_raw(pedal_raw),.seat_led(seat_led),.pedal_down(),.deferred_returns(),
 .microphone_stale(),.mic_received(),.mic_repeated(),.mic_skipped(),.mic_timeouts());
endmodule
''')
    signals=['adc_cs_n','adc_sclk','adc_din','play_button','stop_button','panic_button','minor_mode']+[f'{name}[{i}]' for name,n in [('adc_dout',10),('root',4),('pedal_raw',4),('seat_led',4)] for i in range(n)]
    (target/'constraints/stage.cst.example').write_text('// Assign verified IO_LOC/IO_PORT for every stage signal below. No guessed pins.\n'+'\n'.join('// '+x for x in signals)+'\n')
    (target/'constraints/stage.sdc.example').write_text('# Supply ADC serial input/output delays, asynchronous button/selector synchronization constraints and verified peripheral clock assumptions.\n')
    # Validate pin declarations in Python as well as the Tcl missing-file gate.
    (target/'check_stage_pins.py').write_text('''from pathlib import Path
import re
root=Path(__file__).resolve().parent
required='''+repr(signals)+'''
text=(root/'constraints/stage.cst').read_text()
for signal in required:
 if not re.search(r'(?m)^\\s*IO_LOC\\s+"'+re.escape(signal)+r'"\\s+[A-Z]+[0-9]+\\s*;',text):raise RuntimeError('Missing explicit stage pin: '+signal)
print('Stage pin declarations present; electrical/timing review still required')
''')
    build=(target/'build.tcl').read_text().replace('set_device -name', '''foreach f {constraints/stage.cst constraints/stage.sdc} {
 if {![file exists $f]} {error "Stage pin/timing constraints missing: $f; see READ_ME.txt"}
}
exec python check_stage_pins.py
set_device -name''').replace('set_option -top_module offline_singer_top','set_option -top_module offline_stage_top').replace('constraints/microphone.sdc} {add_file','constraints/microphone.sdc constraints/stage.cst constraints/stage.sdc} {add_file')
    (target/'build.tcl').write_text(build)
    verify=(target/'verify_build.py').read_text().replace("('microphone.cst','microphone.sdc')","('microphone.cst','microphone.sdc','stage.cst','stage.sdc')")
    (target/'verify_build.py').write_text(verify)
    with (target/'READ_ME.txt').open('a',encoding='utf-8') as f:f.write('\n本工程为完整融合顶层：增加本地ADC四席、脚踏保持控制权、实体按钮和舞台席位灯。请另外提供stage.cst/stage.sdc；build.tcl使用PATH中的python检查所有新增引脚声明，再调用综合。该检查不证明电压、引脚冲突或外部时序正确。脱机曲谱与音色参数已保留；root/minor为本地压力垫的实体调式选择。尚无整机管脚、时序、实物验收。\n')
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh')).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record=dict(format='starcluster-offline-export-2',engine_profile='singer-v1',hardware_profile='stage-v1',created=datetime.datetime.now().isoformat(),autoplay=autoplay,build_id=int(digest[:8],16),status='source_only_all_peripheral_constraints_pending',events=len(score['events']),sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='export_manifest.json'})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return target
