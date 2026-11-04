"""Export the combined I2S/spectrum workstation with preserved score and presets."""
from pathlib import Path
import json,hashlib,shutil,datetime,re
from offline_stage import export_stage_project
from offline import replace_once
from i2s_source import adapt_stage_engine

def export_workstation_project(score,destination,autoplay=True):
    target=export_stage_project(score,destination,autoplay);rtl=target/'rtl'
    band=Path(__file__).resolve().parents[1];visual=band/'experimental/audio_visual'
    engine=adapt_stage_engine((rtl/'band_stage_engine.sv').read_text())
    if autoplay:
        # First boot waits for clock qualification; a later outage must not
        # clear offline_started and unexpectedly restart the performance.
        engine=replace_once(engine,'if(!offline_started)begin','if(!offline_started)begin\n    if(transport_fault)offline_wait<=0;\n    else')
    (rtl/'band_stage_i2s_engine.sv').write_text(engine)
    for name in ('band_workstation_top.sv','pcm_snapshot.v','pcm_spectrum.v','pcm_spectrum_buffered.v','spectrum_snapshot.v','fft_fixed.v'):
        shutil.copy2(visual/name,rtl/name)
    for name in ('fft_twiddle_2048.mem','hann_2048.mem'):shutil.copy2(visual/name,target/name)
    (rtl/'offline_workstation_top.sv').write_text('''// Source-only integration boundary; all new physical pins/timing required.
module offline_workstation_top(input clk,uart_rx_pin,audio_clk,mic_bck,mic_ws,mic_sd,
 output uart_tx_pin,i2s_bck,i2s_ws,i2s_sd,PA_EN,
 input[9:0]adc_dout,output adc_cs_n,adc_sclk,adc_din,
 input play_button,stop_button,panic_button,input[3:0]root,input minor_mode,
 input[3:0]pedal_raw,output[3:0]seat_led,
 input display_clk,display_read,display_release,input[10:0]display_address,
 output display_available,spectrum_valid,output signed[15:0]spectrum_real,spectrum_imag);
 assign PA_EN=0; // External I2S DAC selected; keep onboard amplifier disabled.
 band_workstation_top band(.clk(clk),.uart_rx_pin(uart_rx_pin),.uart_tx_pin(uart_tx_pin),
 .audio_clk(audio_clk),.i2s_bck(i2s_bck),.i2s_ws(i2s_ws),.i2s_sd(i2s_sd),
 .mic_bck(mic_bck),.mic_ws(mic_ws),.mic_sd(mic_sd),
 .adc_dout(adc_dout),.adc_cs_n(adc_cs_n),.adc_sclk(adc_sclk),.adc_din(adc_din),
 .play_button(play_button),.stop_button(stop_button),.panic_button(panic_button),.root(root),.minor_mode(minor_mode),
 .pedal_raw(pedal_raw),.seat_led(seat_led),
 .analysis_clk(clk),.display_clk(display_clk),.display_read(display_read),.display_release(display_release),.display_address(display_address),
 .display_available(display_available),.spectrum_valid(spectrum_valid),.spectrum_real(spectrum_real),.spectrum_imag(spectrum_imag));
endmodule
''')
    cst=target/'constraints/board.cst'
    cst.write_text('\n'.join(line for line in cst.read_text().splitlines() if not re.search(r'"HP_(BCK|WS|DIN)"',line))+'\n')
    signals=['audio_clk','i2s_bck','i2s_ws','i2s_sd','display_clk','display_read','display_release','display_available','spectrum_valid']
    signals += [f'{name}[{i}]' for name,n in [('display_address',11),('spectrum_real',16),('spectrum_imag',16)] for i in range(n)]
    (target/'constraints/workstation.cst.example').write_text('// Supply actual external DAC and display-reader interface pins.\n'+'\n'.join('// '+name for name in signals)+'\n')
    (target/'constraints/workstation.sdc.example').write_text('# Declare actual24.576MHz audio_clk and display_clk; constrain I2S outputs,display read/write interface and CDC boundaries.\n# analysis_clk is tied to core clk in this wrapper; no extra analysis clock pin. No assumed DAC delays.\n')
    (target/'check_workstation_pins.py').write_text('''from pathlib import Path
import re
root=Path(__file__).resolve().parent
required='''+repr(signals)+r'''
text=(root/'constraints/workstation.cst').read_text()
for signal in required:
 if not re.search(r'(?m)^\s*IO_LOC\s+"'+re.escape(signal)+r'"\s+[A-Z]+[0-9]+\s*;',text):raise RuntimeError('Missing explicit workstation pin: '+signal)
print('Declarations present only; electrical/clock/CDC/physical review still required')
''')
    tcl=(target/'build.tcl').read_text()
    tcl=replace_once(tcl,'cd $here','''cd $here
foreach f {constraints/workstation.cst constraints/workstation.sdc} {
 if {![file exists $f]} {error "Workstation pin/timing constraints missing: $f; see READ_ME.txt"}
}
exec python check_workstation_pins.py''')
    tcl=tcl.replace('top_module offline_stage_top','top_module offline_workstation_top').replace('constraints/stage.sdc} {add_file','constraints/stage.sdc constraints/workstation.cst constraints/workstation.sdc} {add_file')
    (target/'build.tcl').write_text(tcl)
    p=target/'verify_build.py';p.write_text(p.read_text().replace("'stage.cst','stage.sdc')","'stage.cst','stage.sdc','workstation.cst','workstation.sdc')"))
    (target/'READ_ME.txt').write_text('''合并工作站脱机源码工程，尚未通过最终硬件验收。
本地ADC/脚踏、乐队/歌手、标准I2S队列、断钟保护与2048点Hann/FFT缓存位于同一顶层。保留作品事件、音色和校准参数。运行时RAM上传不等于Flash保存。
外部audio_clk必须为已验证的24.576MHz；源PCM只有16位有效精度，低8位补零后通过24位I2S发送。板载PT8211功放被禁用，I2S信号不沿用PT8211引脚。
上电自动演出等待音频时钟健康后再等待9000核心周期，仅自动启动一次；演出中断钟会清场，恢复后须人工重新播放。
display接口是冻结频谱RAM读取协议，不是HDMI像素输出：available后按地址读取，read_valid时取实/虚数据，读完release；停读只阻塞分析，不阻塞音频。分析使用核心时钟，显示读取时钟由实际接口提供。
按真实接线补齐microphone、stage、workstation的CST/SDC。默认构建拒绝缺少引脚/时序文件；声明检查不证明电压、引脚冲突、CDC或外部时序正确。
需重新综合、布局布线、全曲/满载和实物测试，不能直接把本工程称为已验收固件。没有替你生成PLL或指定未知外设管脚。
''',encoding='utf-8')
    if not autoplay:
        p=target/'READ_ME.txt';p.write_text(p.read_text(encoding='utf-8').replace('上电自动演出等待音频时钟健康后再等待9000核心周期，仅自动启动一次；','本导出关闭自动演出，等待播放命令；'),encoding='utf-8')
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh')).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record=dict(format='starcluster-offline-export-2',engine_profile='singer-v1',hardware_profile='workstation-i2s-spectrum-v1',created=datetime.datetime.now().isoformat(),autoplay=autoplay,build_id=int(digest[:8],16),status='source_only_all_peripheral_constraints_pending',events=len(score['events']),sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='export_manifest.json'})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return target
