"""Freeze a complete singer/microphone source project without guessing pins."""
from pathlib import Path
import copy,hashlib,json,shutil,datetime

def export_singer_project(score,destination,autoplay=False):
    from offline import export_project,replace_once
    from score import validate
    validate(score);band=Path(__file__).resolve().parents[1]
    from rom_contract import check_vocoder_rom
    check_vocoder_rom(band/'experimental/vocoder/ported/filterbank.sv')
    # Reuse the proven score/patch/calibration exporter, then replace the
    # engine before publishing the singer manifest. No synthesis/programming.
    base=copy.deepcopy(score);base['format']='starcluster-score-1';base['engine_profile']='band-v1'
    target=export_project(base,destination,autoplay);rtl=target/'rtl'
    standard_engine=(rtl/'band_board_engine.v').read_text()
    source=band/'experimental/vocoder'
    shutil.copy2(band/'host/rom_contract.py',target/'check_vocoder_rom.py')
    (target/'licenses').mkdir()
    shutil.copy2(source/'upstream/LICENSE',target/'licenses/VOXOS_MIT_LICENSE.txt')
    shutil.copy2(source/'PROVENANCE.json',target/'licenses/VOXOS_PROVENANCE.json')
    for folder in (source/'ported',source/'integration',band/'experimental/audio_input'):
        for p in folder.iterdir():
            if p.is_file() and p.suffix in ('.v','.sv','.vh','.mem'):
                shutil.copy2(p,target/'coeffs.mem' if p.suffix=='.mem' else rtl/p.name)
    p=score.get('performance',{});patches={int(k):{int(x):v for x,v in values.items()} for k,values in p.get('patches',{}).items()}
    core=rtl/'band_singer_core.sv';text=core.read_text()
    text=replace_once(text,'collaboration_enabled<=1;',f"collaboration_enabled<={int(p.get('collaboration',True))};")
    text=replace_once(text,'singer_expression<=127;',f"singer_expression<={patches.get(15,{}).get(0,127)};")
    core.write_text(text)
    engine=rtl/'band_singer_board_engine.sv';text=engine.read_text()
    text=replace_once(text,'wet<=32;master<=96;tempo<=120;transpose<=0;',f"wet<={p.get('wet',32)};master<={p.get('master',96)};tempo<={p.get('tempo',120)};transpose<={p.get('root',0)};")
    if autoplay:
        boot=standard_engine[standard_engine.index(' reg [13:0] offline_wait;'):standard_engine.index(' wire [7:0] byte_data;')]
        text=replace_once(text,' reg rst=1;always @(posedge clk)rst<=!(&startup);', ' reg rst=1;always @(posedge clk)rst<=!(&startup);\n'+boot)
        text=replace_once(text,'||local_play_pulse;','||local_play_pulse||offline_play;')
    engine.write_text(text)
    (rtl/'offline_singer_top.sv').write_text('''// Microphone pins must be supplied from the actual board/ADC wiring.
module offline_singer_top(input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,
 output uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN);
 band_microphone_top band(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),
 .HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),
 .microphone_stale(),.mic_received(),.mic_repeated(),.mic_skipped(),.mic_timeouts());
endmodule
''')
    (target/'constraints/microphone.cst.example').write_text('// Supply IO_LOC and IO_PORT for mic_bck, mic_ws and mic_sd from actual wiring.\n// No guessed pins are supplied. Save verified assignments as microphone.cst.\n')
    (target/'constraints/microphone.sdc.example').write_text('// Supply microphone BCK clock and actual ADC WS/SD input delays.\n// Profile: I2S24 in two32bit slots, nominal3.072MHz BCK/48kHz frames.\n// Define asynchronous core/BCK clock crossings appropriately for Gray FIFO.\n// This is not an ASRC; use matched clocks or implement rate conversion.\n')
    (target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
exec python check_vocoder_rom.py
foreach f {constraints/microphone.cst constraints/microphone.sdc} {
 if {![file exists $f]} {error "Microphone pin/timing constraints missing: $f; see READ_ME.txt"}
}
set handle [open constraints/microphone.cst r]
set pins [read $handle]
close $handle
foreach signal {mic_bck mic_ws mic_sd} {
 if {![regexp [format {(?m)^\\s*IO_LOC\\s+"%s"\\s+[A-Z]+[0-9]+\\s*;} $signal] $pins]} {error "Missing explicit microphone pin: $signal"}
}
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module offline_singer_top
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
set_option -netlist_hierarchy 0
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
foreach f {constraints/board.cst constraints/board.sdc constraints/microphone.cst constraints/microphone.sdc} {add_file $f}
set_option -output_base_name offline_band
run all
''')
    (target/'project.json').write_text(json.dumps(score,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'verify_build.py').write_text('''from pathlib import Path
import json,re,hashlib
from verify_fs import verify_fs
r=Path(__file__).resolve().parent
m=json.loads((r/'export_manifest.json').read_text(encoding='utf-8'))
for name,digest in m['sources'].items():
 if hashlib.sha256((r/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Source changed: '+name)
constraints={}
for name in ('microphone.cst','microphone.sdc'):
 p=r/'constraints'/name
 if not p.exists() or not p.read_text().strip():raise RuntimeError('Missing microphone constraints')
 constraints[name]=hashlib.sha256(p.read_bytes()).hexdigest()
timing=(r/'impl/pnr/offline_band_tr_content.html').read_text()
for kind in ('Setup','Hold'):
 match=re.search('Numbers of '+kind+r' Violated Endpoints</td>\\s*<td>(\\d+)</td>',timing)
 if not match or int(match[1]):raise RuntimeError(kind+' timing failed')
verify_fs(r/'impl/pnr/offline_band.fs')
result=dict(status='timing_only_requires_pin_clock_and_physical_review',build_id=m['build_id'],constraints=constraints,bitstream_sha256=hashlib.sha256((r/'impl/pnr/offline_band.fs').read_bytes()).hexdigest())
(r/'timing_review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
''')
    (target/'READ_ME.txt').write_text('电子歌手脱机源码工程（实验版）\n完整保留score2角色、事件ROM、音色及歌手表情、上电启动、麦克风CDC/断流和DAC队列。不是已验收位流。\n麦克风接口是外部提供BCK/WS的I2S24输入；本顶层不产生麦克风时钟。名义采样率48kHz、每声道32bit槽；非ASRC。\n依据实际板卡/ADC接线补齐constraints/microphone.cst和microphone.sdc。必须检查引脚冲突、电压、时钟来源及ADC数据时序；示例文件没有猜测接线。未配置时build.tcl拒绝启动。\n配置后在Gowin运行build.tcl，再运行python verify_build.py，只得到时序审查记录，不自动生成已验收release或烧录。外部时钟匹配、模拟音质、冷启动及麦克风实物验收仍待完成。\n'+('上电后自动开始事件演出。\n' if autoplay else '等待UART播放命令。\n')+'无麦克风有效帧时歌手淡出，其他乐队轨继续。标准乐队默认固件不支持本作品第16轨语义。\n',encoding='utf-8')
    digest=hashlib.sha256(json.dumps(score,sort_keys=True).encode()+b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh')).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record=dict(format='starcluster-offline-export-2',engine_profile='singer-v1',created=datetime.datetime.now().isoformat(),autoplay=autoplay,build_id=int(digest[:8],16),status='source_only_microphone_constraints_pending',events=len(score['events']),sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='export_manifest.json'})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return target
