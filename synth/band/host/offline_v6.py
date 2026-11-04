"""Export the V6 I2S/panel/DVI source configuration, never program hardware."""
from pathlib import Path
import datetime,json,re,shutil,struct,zlib
from score import validate,load
from offline import replace_once


def export_v6_project(score,destination,autoplay=False,compact16=False,usb16=False):
    validate(score)
    if compact16 and usb16:raise ValueError('请选择一种面板配置')
    if score.get('engine_profile')!='singer-v1':
        raise ValueError('V6扩展第16轨为电子歌手，请先明确设置作品角色')
    band=Path(__file__).resolve().parents[1];target=Path(destination).resolve()
    if target==band or band in target.parents:raise ValueError('请导出到源码目录以外的空目录')
    if target.exists() and any(target.iterdir()):raise ValueError('请选择空目录，不覆盖已有工程')
    template=band/'experimental/panel_v6/export_template'
    if not(template/'workstation_v6_complete_top.sv').exists():raise ValueError('缺少V6完整导出模板')
    target.mkdir(parents=True,exist_ok=True);rtl=target/'rtl';rtl.mkdir()
    for p in template.iterdir():
        if p.is_file():shutil.copy2(p,target/p.name if p.suffix=='.mem' else rtl/p.name)
    events=score['events'];performance=score.get('performance',{})
    patches={int(k):{int(p):v for p,v in values.items()} for k,values in performance.get('patches',{}).items()}
    storage=[];rom=[]
    for i,e in enumerate(events):
        control=e['kind']|(e['part']<<2)|(e['note']<<6)|(e['velocity']<<13)
        storage.append(f"controls[{i}]=32'd{control};identities[{i}]=32'd{e['serial']};times[{i}]=32'd{e['sample']};")
        rom.append(f"song_rom[{i}]=96'h{(e['sample']<<64)|(e['serial']<<32)|control:024x};")
    (rtl/'song_storage_init.vh').write_text('\n'.join(storage)+'\n')
    (rtl/'song_events.vh').write_text('\n'.join(rom)+'\n')
    (rtl/'song_config.vh').write_text(f"`define SONG_EVENTS {len(events)}\n`define SONG_LENGTH {score['duration_samples']}\n")

    p=rtl/'offline_patch_defaults.vh';defaults=p.read_text()
    for part,params in patches.items():
        for parameter,value in params.items():
            if parameter not in (0,1,2,4,5,6,7):continue
            if parameter==0:value=128 if value>=127 else value
            elif parameter==1:value>>=6
            elif parameter==4:value=max(1,value)
            elif parameter==6:value<<=2
            pattern=rf"4'd{part}:offline_parameter_{parameter}=16'd\d+;"
            defaults,count=re.subn(pattern,f"4'd{part}:offline_parameter_{parameter}=16'd{value};",defaults)
            if count!=1:raise ValueError('音色默认值模板已变化')
    for parameter in (8,9):
        defaults+=f'\nfunction [15:0] offline_parameter_{parameter};input [3:0] part;begin case(part)\n'
        for part in range(16):
            value=patches.get(part,{}).get(parameter,part if parameter==8 else 64)
            defaults+=f"4'd{part}:offline_parameter_{parameter}=16'd{value};\n"
        defaults+=f"default:offline_parameter_{parameter}=0;endcase end endfunction\n"
    p.write_text(defaults)
    p=rtl/'shared_role_controls.v';text=p.read_text()
    p.write_text(replace_once(text,'instrument[i]<=i;pan[i]<=64;target_pan[i]<=64;',
      'instrument[i]<=offline_parameter_8(i);pan[i]<=offline_parameter_9(i);target_pan[i]<=offline_parameter_9(i);'))

    mix=performance.get('mixer',{});muted=set(mix.get('muted',[]));solo=mix.get('solo')
    if solo is not None:muted.update(p for p in range(15) if p!=solo)
    p=rtl/'track_ownership.v';p.write_text(replace_once(p.read_text(),'mutes<=0;returns<=0;',f"mutes<=16'h{sum(1<<n for n in muted):04x};returns<=0;"))
    p=rtl/'workstation_expansion_engine.sv';text=p.read_text()
    wet=0 if mix.get('bypass',False) else performance.get('wet',24)
    text=replace_once(text,'effect_mode<=0;singer_status<=0;wet<=24;master<=64;tempo<=120;transpose<=0;',
      f"effect_mode<={performance.get('effect_mode',0)};singer_status<=0;wet<={wet};master<={performance.get('master',64)};tempo<={performance.get('tempo',120)};transpose<={performance.get('root',0)};")
    if autoplay:text=replace_once(text,'if(offline_wait==9000)begin offline_started<=1;offline_play<=0;','if(offline_wait==9000)begin offline_started<=1;offline_play<=1;')
    p.write_text(text)

    if compact16:
        # Two MCP3208s scan pads 0..15; the third scans eight analog controls.
        # Keep the existing ten-lane scanner schedule, tying absent DOUTs low.
        p=rtl/'workstation_v6_complete_top.sv';text=p.read_text()
        text=replace_once(text,'input wire[9:0]adc_dout,','input wire[2:0]adc_dout,')
        text=replace_once(text,'.adc_dout(adc_dout),','.adc_dout({7\'d0,adc_dout}),');p.write_text(text)
        p=rtl/'workstation_expansion_engine.sv';text=p.read_text()
        text=replace_once(text,'stage_pad_frontend pads(', 'stage_pad_frontend #(.PADS(16)) pads(')
        p.write_text(text)
        p=rtl/'local_expression.v';text=p.read_text()
        text=replace_once(text,'if(sample_valid&&channel<4)for(k=0;k<2;k=k+1)begin',
            'if(sample_valid)for(k=0;k<1;k=k+1)begin')
        text=replace_once(text,'address=k*4+channel;raw=samples[(8+k)*12+:12];',
            'address=channel;raw=samples[2*12+:12];')
        p.write_text('// Compact16: ADC2 CH0..7 maps all eight continuous controls.\n'+text)
    if usb16:
        # Existing USB pad -> Teensy UART; encoders stay on FPGA. No ADC IO.
        p=rtl/'workstation_v6_complete_top.sv';text=p.read_text()
        text=replace_once(text,'input wire[7:0]enc_a,enc_b,input wire[3:0]pedal_raw,input wire[9:0]adc_dout,',
            'input wire[7:0]enc_a,enc_b,')
        text=replace_once(text,' output wire adc_cs_n,adc_sclk,adc_din,\n','')
        text=replace_once(text,'.pedal_raw(pedal_raw),.adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),',
            '.pedal_raw(4\'d0),.adc_dout(10\'d0),.adc_cs_n(),.adc_sclk(),.adc_din(),')
        p.write_text(text)
        p=rtl/'workstation_expansion_top.sv'
        p.write_text(replace_once(p.read_text(),'.EXTERNAL_AUDIO(1),.LOCAL_INPUTS(1)', '.EXTERNAL_AUDIO(1),.LOCAL_INPUTS(0)'))
    p=rtl/'band_singer_core.sv';text=p.read_text()
    text=replace_once(text,'collaboration_enabled<=1;',f"collaboration_enabled<={int(performance.get('collaboration',True))};")
    text=replace_once(text,'singer_expression<=80;',f"singer_expression<={patches.get(15,{}).get(0,80)};")
    p.write_text(text)

    from calibration_model import normalize
    calibration=normalize(performance.get('pad_calibration',{}))
    if calibration:
        lines=['function [28:0] offline_stage_calibration;input [6:0] channel;begin case(channel)']
        for channel,values in sorted(calibration.items()):
            value=(int(values['invert'])<<28)|(values['gain']<<12)|values['baseline']
            lines.append(f"7'd{channel}:offline_stage_calibration=29'h{value:08x};")
        lines.append("default:offline_stage_calibration={1'b0,16'd127,12'd0};endcase end endfunction")
        p=rtl/'stage_pad_frontend.sv';text=replace_once(p.read_text(),' localparam CHANNELS=CHIPS*8;','\n'.join(lines)+'\n localparam CHANNELS=CHIPS*8;')
        text=replace_once(text,"configured[address]?calibration[address]:{1'b0,16'd127,12'd0}","configured[address]?calibration[address]:offline_stage_calibration(address)")
        p.write_text(text)

    words=[];descriptions=[]
    songs=[score,load(band/'assets/four_families_demo.json'),load(band/'assets/scale_chord_practice.json')]
    for song in songs:
        data=[];base=len(words)
        for e in song['events']:data.extend((e['kind']|(e['part']<<2)|(e['note']<<6)|(e['velocity']<<13),e['serial'],e['sample']))
        descriptions.append((base,len(data),song['duration_samples'],zlib.crc32(struct.pack('<'+'I'*len(data),*data))));words.extend(data)
    (target/'song_library_words.mem').write_text('\n'.join(f'{v:08x}' for v in words)+'\n')
    config=f'localparam LIBRARY_WORDS={len(words)},LIBRARY_SONGS=3;\nfunction[127:0]library_description;input[7:0]song;begin case(song)\n'
    for i,values in enumerate(descriptions):config+=f'{i}:library_description={{'+','.join(f"32'd{v}" for v in values)+'};\n'
    (rtl/'song_library_config.vh').write_text(config+'default:library_description=0;endcase end endfunction\n')
    (target/'project.json').write_text(json.dumps(score,ensure_ascii=False,indent=2),encoding='utf-8')
    build_id=zlib.crc32(json.dumps(score,sort_keys=True).encode()+b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh'))
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
    tcl='''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module workstation_v6_complete_top
set_option -verilog_std sysv2017
foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}
set_option -output_base_name workstation_v6_export
'''
    (target/'synthesis_only.tcl').write_text(tcl+'run syn\n')
    (target/'constraints').mkdir()
    (target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
foreach f {constraints/expansion.cst constraints/expansion.sdc} {
 if {![file exists $f]} {error "Expansion pins/timing are unreviewed; supply and review $f before any place/route"}
}
'''+tcl+'add_file constraints/expansion.cst\nadd_file constraints/expansion.sdc\nset_option -cst_warn_to_error 1\nrun all\n')
    licenses=target/'licenses';licenses.mkdir()
    for source,name in ((band/'experimental/vocoder/upstream/LICENSE','VOXOS_MIT_LICENSE.txt'),(band/'experimental/vocoder/PROVENANCE.json','VOXOS_PROVENANCE.json')):shutil.copy2(source,licenses/name)
    (target/'export_manifest.json').write_text(json.dumps(dict(format='starcluster-v6-expansion-export-1',created=datetime.datetime.now().isoformat(),
      build_id=build_id,status='source_only_unpinned_requires_PnR_and_board_acceptance',autoplay=autoplay,events=len(events),
      top='workstation_v6_complete_top',persistent_parameters=['event score','ADSR/expression/bend/vowel','instrument/pan','mixer mute/solo/bypass','effect mode','ADC calibration'],
      panel_profile='usb16_no_adc' if usb16 else 'compact16_three_adc' if compact16 else 'full64_ten_adc',
      physical_adc_chips=0 if usb16 else 3 if compact16 else 10,physical_pressure_pads=0 if usb16 else 16 if compact16 else 64,
      nominal_audio_clock_hz=24576000,physical_pins_reviewed=False),ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'READ_ME.txt').write_text('V6扩展源码工程：标准I2S、面板、麦克风、三曲ROM与FFT/DVI。没有已审核CST；build.tcl在缺管脚/时序约束时明确拒绝布局布线。只可先运行synthesis_only.tcl，不得把扩展下载到未知接线的板卡。每次修改曲谱/预设都需重新综合、布线和实板验收，当前已选位流与验收结论不自动继承。\n',encoding='utf-8')
    return target
