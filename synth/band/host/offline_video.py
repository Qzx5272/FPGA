"""Export the complete band with one shared FFT and logical 640x480 RGB video."""
from pathlib import Path
import hashlib,json,datetime,re,shutil
from offline import replace_once
from offline_workstation import export_workstation_project
from video_source import adapt_workstation_video

def export_video_project(score,destination,autoplay=True):
    target=export_workstation_project(score,destination,autoplay);rtl=target/'rtl'
    visual=Path(__file__).resolve().parents[1]/'experimental/audio_visual'
    (rtl/'band_workstation_video_top.sv').write_text(adapt_workstation_video((rtl/'band_workstation_top.sv').read_text()))
    for name in ('spectrum_bars.v','video_timing_640x480.v'):shutil.copy2(visual/name,rtl/name)
    p=rtl/'offline_workstation_top.sv';text=p.read_text()
    text=replace_once(text,''' input display_clk,display_read,display_release,input[10:0]display_address,
 output display_available,spectrum_valid,output signed[15:0]spectrum_real,spectrum_imag);''',
        ''' input pixel_clk,output[23:0]video_rgb,output video_hsync_n,video_vsync_n,video_active,video_valid);''')
    text=replace_once(text,' band_workstation_top band(',' band_workstation_video_top band(')
    text=replace_once(text,''' .analysis_clk(clk),.display_clk(display_clk),.display_read(display_read),.display_release(display_release),.display_address(display_address),
 .display_available(display_available),.spectrum_valid(spectrum_valid),.spectrum_real(spectrum_real),.spectrum_imag(spectrum_imag));''',
        ''' .analysis_clk(clk),.pixel_clk(pixel_clk),.video_rgb(video_rgb),.video_hsync_n(video_hsync_n),
 .video_vsync_n(video_vsync_n),.video_active(video_active),.video_valid(video_valid),.video_frame_count());''')
    p.write_text(text)
    # Frame count stays inside the FPGA; do not consume32 external diagnostic pins.
    signals=['audio_clk','i2s_bck','i2s_ws','i2s_sd','pixel_clk','video_hsync_n','video_vsync_n','video_active','video_valid']
    signals += [f'video_rgb[{i}]' for i in range(24)]
    (target/'constraints/workstation.cst.example').write_text('// Declare actual I2S, pixel clock and logical parallel RGB pins; NOT HDMI differential pins.\n'+'\n'.join('// '+v for v in signals)+'\n')
    (target/'constraints/workstation.sdc.example').write_text('# Core50MHz; actual audio_clk24.576MHz. pixel_clk25.2MHz gives60fps at800x525.\n# Define real clock sources/IO delays/CDC. No PLL, serializer, electrical timing or pins are inferred.\n')
    p=target/'check_workstation_pins.py';text,n=re.subn(r'(?m)^required=.*$',lambda _: 'required='+repr(signals),p.read_text());assert n==1;p.write_text(text)
    (target/'READ_ME.txt').write_text('''完整乐队与逻辑RGB视频导出，开发候选，禁止直接视为实物验收固件。
本地席/脚踏、歌手/乐队、I2S输出和频谱柱图共享一个2048点Hann/FFT及频谱缓存，没有重复分析器。
video_rgb/hsync_n/vsync_n/active是并行逻辑视频，不是HDMI/TMDS。pixel_clk需由已验证硬件提供；25.2MHz时800x525总时序为60fps，有效640x480。未生成PLL或串行器。video_valid表示已有完整频谱画面。
audio_clk仍需24.576MHz；24位I2S中16位PCM有效，板载PT8211功放关闭，不能套用旧DAC接线。
显示停顿只影响可视化；总停音/音频故障清除画面，显示域复位异步置位、两拍释放。
保留作品、音色、校准参数。RAM上传不会自动写Flash。按实际接线提供microphone/stage/workstation的CST/SDC；默认构建拒绝缺少文件/引脚声明，声明检查不等于电气或时序验收。
旧频谱读取版本的时序结果不能作为本视频版本结果；本版本仍需独立整机仿真、PnR、全曲/满载及实际显示/音质验收。
'''+('上电等待音频时钟健康及9000核心周期后自动演出一次，断钟恢复后需显式重启。\n' if autoplay else '自动演出关闭，等待播放命令。\n'),encoding='utf-8')
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh')).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record=dict(format='starcluster-offline-export-2',engine_profile='singer-v1',hardware_profile='workstation-i2s-rgb-v1',created=datetime.datetime.now().isoformat(),autoplay=autoplay,build_id=int(digest[:8],16),status='source_only_all_peripheral_constraints_pending',events=len(score['events']),sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='export_manifest.json'})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return target
