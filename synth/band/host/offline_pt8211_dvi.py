"""Onboard PT8211 audio with the existing band, stage, FFT and DVI pipeline."""
from pathlib import Path
import datetime, hashlib, json, re, shutil
from offline import replace_once
from offline_dvi import export_dvi_project


def export_pt8211_dvi_project(score, destination, autoplay=True):
    target = export_dvi_project(score, destination, autoplay)
    rtl = target/'rtl'
    band = Path(__file__).resolve().parents[1]
    # Preserve the exported song, patches, calibration and original PT8211 queue.
    engine = (rtl/'band_stage_engine.sv').read_text()
    engine = replace_once(engine, 'module band_stage_engine #(', 'module band_stage_pt8211_engine #(')
    engine = replace_once(engine, 'output wire transport_sample_tick,',
                          'output wire transport_sample_tick,output wire audio_stop,')
    engine = replace_once(engine, 'assign pcm_left=left;', 'assign audio_stop=stop;assign pcm_left=left;')
    (rtl/'band_stage_pt8211_engine.sv').write_text(engine)

    source = (rtl/'band_workstation_video_top.sv').read_text()
    source = replace_once(source, 'module band_workstation_video_top #(', 'module band_workstation_pt8211_top #(')
    source = replace_once(source, ' input wire audio_clk,output wire uart_tx_pin,i2s_bck,i2s_ws,i2s_sd,',
                          ' output wire uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,')
    source = replace_once(source, ' output wire[31:0]i2s_dropped,i2s_underruns,audio_clock_losses,output wire audio_clock_fault,',
                          ' output wire[31:0]dac_dropped,dac_underruns,')
    source = source.replace('wire pcm_valid,i2s_tick,audio_stop;', 'wire pcm_valid,audio_stop;')
    source = replace_once(source, 'band_stage_i2s_engine #(.EXTERNAL_AUDIO(1),',
                          'band_stage_pt8211_engine #(.EXTERNAL_AUDIO(0),')
    source = replace_once(source, '.HP_BCK(),.HP_WS(),.HP_DIN(),.PA_EN(),',
                          '.HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),')
    source = replace_once(source, '.external_sample_tick(i2s_tick)', '.external_sample_tick(1\'b0)')
    source = replace_once(source, '.dac_dropped(),.dac_underruns()', '.dac_dropped(dac_dropped),.dac_underruns(dac_underruns)')
    source = replace_once(source, '.transport_fault(audio_clock_fault),', '')
    source = replace_once(source, '.external_dropped(i2s_dropped),.external_underruns(i2s_underruns),', '')
    start = source.index(' audio_clock_watchdog #(')
    end = source.index(' pcm_spectrum_buffered #(', start)
    source = source[:start]+source[end:]
    source = '// PT8211 integration; core-clock audio queue, no external DAC clock.\n'+source[source.index('module '):]
    assert 'i2s_tick' not in source and 'audio_clock_fault' not in source
    (rtl/'band_workstation_pt8211_top.sv').write_text(source)

    p = rtl/'offline_workstation_top.sv'
    wrapper = p.read_text()
    wrapper = replace_once(wrapper, 'input clk,uart_rx_pin,audio_clk,mic_bck,mic_ws,mic_sd,',
                           'input clk,uart_rx_pin,mic_bck,mic_ws,mic_sd,')
    wrapper = replace_once(wrapper, 'output uart_tx_pin,i2s_bck,i2s_ws,i2s_sd,PA_EN,',
                           'output uart_tx_pin,HP_BCK,HP_WS,HP_DIN,PA_EN,')
    wrapper = replace_once(wrapper, ' assign PA_EN=0;', '')
    wrapper = wrapper.replace('// External I2S DAC selected; keep onboard amplifier disabled.', '')
    wrapper = replace_once(wrapper, 'band_workstation_video_top band(', 'band_workstation_pt8211_top band(')
    wrapper = replace_once(wrapper, '.audio_clk(audio_clk),.i2s_bck(i2s_bck),.i2s_ws(i2s_ws),.i2s_sd(i2s_sd),',
                           '.HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),')
    p.write_text(wrapper)
    shutil.copy2(band.parents[1]/'synth/constraints/board.cst', target/'constraints/board.cst')
    signals = ['tmds_clk_p','video_valid']+[f'tmds_d_p[{i}]' for i in range(3)]
    p = target/'check_workstation_pins.py'
    text, n = re.subn(r'(?m)^required=.*$', lambda _: 'required='+repr(signals), p.read_text())
    assert n == 1
    p.write_text(text)
    (target/'constraints/workstation.cst.example').write_text(
        (band/'experimental/audio_visual/dvi/reference_HDMI0.cst.example').read_text()+
        '\n// Assign video_valid only if exported as a physical debug pin.\n')
    (target/'constraints/workstation.sdc.example').write_text(
        '# PT8211 clock derives from core50MHz; no external audio_clk input.\n'
        '# Constrain126MHz serializer/25.2MHz pixel generated clocks and actual microphone/ADC IO.\n')
    (target/'READ_ME.txt').write_text('''板载PT8211＋乐队/歌手/声码器＋本地席/脚踏＋FFT/DVI开发候选。
复用原板载音频队列，从核心50MHz产生平均48kHz音频时序，不需要外部24.576MHz时钟或I2S DAC。
PT8211与标准I2S帧格式不同，不得互换接口；有效PCM精度保持16位。显示背压不阻塞音频。
完整扩展顶层仍包含麦克风、ADC、实体按钮与脚踏接口。未接外设需在具体板级封装中明确禁用或补全实际引脚；默认构建仍拒绝缺少扩展接口约束。
保留作品、音色、有限人声、校准及接管逻辑。不是已通过整机时序或实物验收的固件，不能沿用外置I2S版本的验证结论；未烧录或写Flash。
''', encoding='utf-8')
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh')).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record = dict(format='starcluster-offline-export-2', engine_profile='singer-v1',
                  hardware_profile='workstation-pt8211-dvi-v1', created=datetime.datetime.now().isoformat(),
                  autoplay=autoplay, build_id=int(digest[:8],16), status='source_candidate_not_integrated_accepted',
                  events=len(score['events']), sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(target.rglob('*')) if p.is_file() and p.name!='export_manifest.json'})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return target
