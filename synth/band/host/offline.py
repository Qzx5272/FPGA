"""Export a complete frozen HDL project with an event score and boot presets.
This creates files only. It never builds, programs, or changes the source project.
"""
from pathlib import Path
import json,hashlib,shutil,datetime
from score import validate

def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('离线导出模板已变化，请更新导出器：'+old[:60])
    return text.replace(old,new,1)

def export_project(score,destination,autoplay=False):
    validate(score);band=Path(__file__).resolve().parents[1];root=band.parents[1]
    if score.get('engine_profile')=='singer-v1':
        from offline_singer import export_singer_project
        return export_singer_project(score,destination,autoplay)
    target=Path(destination).resolve()
    # Export into a fresh directory only; never mutate a user's existing project.
    if target.exists() and any(target.iterdir()):raise ValueError('请选择空目录，以免覆盖已有工程')
    if target==band or band in target.parents:raise ValueError('请将离线工程导出到开发源码目录以外')
    target.mkdir(parents=True,exist_ok=True);rtl=target/'rtl';rtl.mkdir()
    for p in (band/'rtl').glob('*'):
        if p.is_file():shutil.copy2(p,rtl/p.name)
    for name in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v'):
        shutil.copy2(root/'synth/rtl'/name,rtl/name)
    constraints=target/'constraints';shutil.copytree(root/'synth/constraints',constraints)
    events=score['events'];storage=[];rom=[]
    for i,e in enumerate(events):
        c=e['kind']|(e['part']<<2)|(e['note']<<6)|(e['velocity']<<13)
        storage.append(f"controls[{i}]=32'h{c:08x};identities[{i}]=32'd{e['serial']};times[{i}]=32'd{e['sample']};")
        packed=(e['sample']<<64)|(e['serial']<<32)|c;rom.append(f"song_rom[{i}]=96'h{packed:024x};")
    (rtl/'song_storage_init.vh').write_text('\n'.join(storage)+'\n')
    (rtl/'song_events.vh').write_text('\n'.join(rom)+'\n')
    (rtl/'song_config.vh').write_text(f"`define SONG_EVENTS {len(events)}\n`define SONG_LENGTH {score['duration_samples']}\n")
    performance=score.get('performance',{});patches={int(p):{int(k):int(v) for k,v in values.items()} for p,values in performance.get('patches',{}).items()}
    from calibration_model import normalize
    calibration=normalize(performance.get('pad_calibration',{}))
    if calibration:
        functions=[]
        for name,width,default in [('baseline',12,0),('gain',16,127)]:
            functions.append(f'function [{width-1}:0] offline_pad_{name}; input integer channel; begin case(channel)')
            functions.extend(f"{ch}:offline_pad_{name}={width}'d{values[name]};" for ch,values in sorted(calibration.items()))
            functions.append(f"default:offline_pad_{name}={width}'d{default};endcase end endfunction")
        (rtl/'offline_pad_calibration.vh').write_text('\n'.join(functions)+'\n')
        p=rtl/'pad_frontend.v';text=p.read_text()
        text=replace_once(text,' localparam CHANNELS=CHIPS*8;',' `include "offline_pad_calibration.vh"\n localparam CHANNELS=CHIPS*8;')
        mask=sum(1<<ch for ch,c in calibration.items() if c['invert'])
        text=replace_once(text,'inversions<=0;',f"inversions<=80'h{mask:020x};")
        text=replace_once(text,'baselines[k]<=0;gains[k]<=127;','baselines[k]<=offline_pad_baseline(k);gains[k]<=offline_pad_gain(k);')
        p.write_text(text)
    functions=[]
    defaults={0:127,1:8192,2:0,4:None,5:13,6:None,7:8}
    for parameter in defaults:
        lines=[f'function [15:0] offline_parameter_{parameter};input [3:0] part;begin case(part)']
        for part in range(16):
            fallback=defaults[parameter]
            if parameter==4:fallback=256 if part>=5 else 8192
            if parameter==6:fallback=16383 if part>=5 else 0
            value=patches.get(part,{}).get(parameter,fallback)
            if parameter==0:value=128 if value>=127 else value
            if parameter==1:value>>=6
            if parameter==4:value=max(1,value)
            if parameter==6:value=value<<2 if parameter in patches.get(part,{}) else (65535 if part>=5 else 0)
            lines.append(f"4'd{part}:offline_parameter_{parameter}=16'd{value};")
        lines+=['default:offline_parameter_'+str(parameter)+"=16'd0;endcase end endfunction"]
        functions+=lines
    (rtl/'offline_patch_defaults.vh').write_text('\n'.join(functions)+'\n')
    p=rtl/'voice_bank.v';text=p.read_text()
    text=replace_once(text,' localparam PARTS=16>>BANK_BITS;',' `include "offline_patch_defaults.vh"\n localparam PARTS=16>>BANK_BITS;')
    assignments={'expression':'offline_parameter_0','target_expression':'offline_parameter_0','bend':'offline_parameter_1','target_bend':'offline_parameter_1','vowel':'offline_parameter_2','attack':'offline_parameter_4','decay':'offline_parameter_5','sustain':'offline_parameter_6','release_rate':'offline_parameter_7'}
    start='  if(rst)for(i=0;i<PARTS;i=i+1)begin '
    line=next(line for line in text.splitlines() if line.startswith(start))
    replacement=start+''.join(f'{name}[i]<={fn}((i<<BANK_BITS)|BANK_ID);' for name,fn in assignments.items())+'end'
    p.write_text(replace_once(text,line,replacement))
    p=rtl/'band_board_engine.v';text=p.read_text()
    old='wet<=32;master<=96;tempo<=120;transpose<=0;'
    new=f"wet<={performance.get('wet',32)};master<={performance.get('master',96)};tempo<={performance.get('tempo',120)};transpose<={performance.get('root',0)};"
    text=replace_once(text,old,new)
    if autoplay:
        text=replace_once(text,' reg rst=1;always @(posedge clk)rst<=!(&startup);',''' reg rst=1;always @(posedge clk)rst<=!(&startup);
 reg [13:0] offline_wait;reg offline_started,offline_play;
 always @(posedge clk)begin
  if(rst)begin offline_wait<=0;offline_started<=0;offline_play<=0;end
  else begin
   offline_play<=0;
   if(!offline_started)begin
    if(offline_wait==9000)begin offline_started<=1;offline_play<=1;end
    else offline_wait<=offline_wait+1'b1;
   end
  end
 end''')
        text=replace_once(text,'||local_play_pulse;','||local_play_pulse||offline_play;')
    p.write_text(text)
    p=rtl/'band_core.v';text=p.read_text();p.write_text(replace_once(text,'collaboration_enabled<=1;',f"collaboration_enabled<={int(performance.get('collaboration',True))};"))
    # Relative paths make the exported vendor project independent of this PC.
    tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
foreach f [glob rtl/*.v] {add_file $f}
add_file constraints/board.cst
add_file constraints/board.sdc
set_option -output_base_name offline_band
run all
'''
    (target/'build.tcl').write_text(tcl)
    (target/'project.json').write_text(json.dumps(score,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(band/'tools/verify_fs.py',target/'verify_fs.py')
    digest=hashlib.sha256(json.dumps(score,sort_keys=True).encode()+b''.join(p.read_bytes() for p in sorted(rtl.iterdir()))).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record=dict(format='starcluster-offline-export-1',created=datetime.datetime.now().isoformat(),autoplay=autoplay,
        build_id=int(digest[:8],16),
        evidence_level='source export only; requires synthesis, timing and physical acceptance',events=len(events),
        persistent_parameters=['score','tempo','transpose','master','wet','collaboration','per-part expression/bend/vowel/ADSR','local pressure pad baseline/gain/inversion'],
        host_only_parameters=['MIDI pad mapping','MIDI seat assignment','manual keyboard scale/octave'],
        sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file()})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    verifier='''from pathlib import Path
import json,re,hashlib,shutil
from verify_fs import verify_fs
root=Path(__file__).resolve().parent
export=json.loads((root/'export_manifest.json').read_text(encoding='utf-8'))
for name,digest in export['sources'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Export source changed: '+name)
pnr=root/'impl/pnr';timing=(pnr/'offline_band_tr_content.html').read_text()
for kind in ('Setup','Hold'):
 m=re.search('Numbers of '+kind+r' Violated Endpoints</td>\\s*<td>(\\d+)</td>',timing)
 if not m or int(m[1]):raise RuntimeError(kind+' timing not clean')
release=root/'release';release.mkdir(exist_ok=True)
verify_fs(pnr/'offline_band.fs')
shutil.copy2(pnr/'offline_band.fs',release/'starcluster_band.fs')
manifest=dict(configuration='offline exported event score and presets',evidence_level='PnR only, not board acceptance',build_id=export['build_id'],setup_violations=0,hold_violations=0,source_sha256=export['sources'],bitstream_sha256=hashlib.sha256((release/'starcluster_band.fs').read_bytes()).hexdigest())
(release/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
'''
    (target/'verify_build.py').write_text(verifier)
    (target/'READ_ME.txt').write_text('星群离线工程\n\n这是完整 HDL 工程导出，不代表已经构建或烧录。\n在 Gowin V1.9.12.03 中运行 build.tcl，再运行 python verify_build.py 检查 50 MHz Setup 和 Hold 均无违例并生成 release。\n先 SRAM 下载并做静音协议、单音、整曲测试，再另行决定 Flash 固化。\n'+('本工程上电后自动开始演出；请先降低外部音箱音量。\n' if autoplay else '本工程等待播放命令；板载试听顶层没有实体播放键。\n')+'MIDI 映射和手动键盘音阶保存在 project.json，仅由主机使用。\n新增外设仍需以 workstation_top 重新约束和验收。\n',encoding='utf-8')
    return target
