"""Export one band/FFT with an on-chip PLL and video-only DVI transmitter."""
from pathlib import Path
import json,hashlib,shutil,re,datetime
from offline import replace_once
from offline_video import export_video_project

def export_dvi_project(score,destination,autoplay=True):
    target=export_video_project(score,destination,autoplay);rtl=target/'rtl'
    source=Path(__file__).resolve().parents[1]/'experimental/audio_visual/dvi'
    for p in source.glob('*.v'):shutil.copy2(p,rtl/p.name)
    for name in ('SOURCE.json','LICENSE.Sipeed.txt','README.txt'):
        shutil.copy2(source/name,target/'licenses'/('dvi_'+name))
    p=rtl/'band_workstation_video_top.sv';text=p.read_text()
    text=replace_once(text,'input wire analysis_clk,pixel_clk,','input wire analysis_clk,pixel_clk,video_link_ready,')
    text=replace_once(text,'wire video_async_reset=rst||panic||audio_stop;',
        'wire video_async_reset=rst||panic||audio_stop||!video_link_ready;')
    text=replace_once(text,'.display_clk(display_clk),.rst(rst||panic||audio_stop),',
        '.display_clk(display_clk),.rst(rst||panic||audio_stop||!video_link_ready),')
    p.write_text(text)
    p=rtl/'offline_workstation_top.sv';text=p.read_text()
    text=replace_once(text,'input pixel_clk,output[23:0]video_rgb,output video_hsync_n,video_vsync_n,video_active,video_valid);',
        'output tmds_clk_p,tmds_clk_n,output[2:0]tmds_d_p,tmds_d_n,output video_valid);')
    text=replace_once(text,' assign PA_EN=0;', ''' wire pixel_clk,video_ready,video_active,video_hsync_n,video_vsync_n;
 wire[23:0]video_rgb;
 reg[3:0]video_por=4'hf;
 always @(posedge clk)video_por<={video_por[2:0],1'b0};
 gowin_dvi_output video_output(.clk50(clk),.resetn(!video_por[3]),
  .active_video(video_active),.hsync_n(video_hsync_n),.vsync_n(video_vsync_n),.rgb(video_rgb),
  .pixel_clk(pixel_clk),.video_ready(video_ready),.tmds_clk_p(tmds_clk_p),.tmds_clk_n(tmds_clk_n),
  .tmds_d_p(tmds_d_p),.tmds_d_n(tmds_d_n));
 assign PA_EN=0;''')
    text=replace_once(text,'.pixel_clk(pixel_clk),.video_rgb(video_rgb),',
        '.pixel_clk(pixel_clk),.video_link_ready(video_ready),.video_rgb(video_rgb),')
    p.write_text(text)
    signals=['audio_clk','i2s_bck','i2s_ws','i2s_sd','tmds_clk_p','video_valid']+[f'tmds_d_p[{i}]' for i in range(3)]
    p=target/'check_workstation_pins.py';text,n=re.subn(r'(?m)^required=.*$',lambda _:'required='+repr(signals),p.read_text());assert n==1;p.write_text(text)
    (target/'constraints/workstation.cst.example').write_text((source/'reference_HDMI0.cst.example').read_text()+'\n// Also assign actual audio_clk,I2S outputs and video_valid; negative TMDS pins use paired IO_LOC syntax.\n')
    (target/'constraints/workstation.sdc.example').write_text('''# Source-only candidate. Validate generated clock paths against the actual netlist.
# clk50=50MHz, PLL CLKOUT0=126MHz, CLKDIV5 pixel=25.2MHz, same source.
# Add real audio24.576MHz/microphone clocks, external IO delays and reviewed CDC constraints.
# Previous external-pixel-clock PnR is NOT a result for this PLL/serializer top.
''')
    (target/'READ_ME.txt').write_text('''DVI视频融合候选：乐队+本地席/脚踏+麦克风+I2S+Hann/FFT+频谱柱图+PLL/串行视频。
从板载50MHz生成同源126MHz/25.2MHz显示时钟，输出仅视频DVI兼容TMDS；没有HDMI音频、DDC/HPD或任意屏幕兼容性保证。音频仍由外置I2S DAC播放，需要24.576MHz音频时钟，板载PT8211功放保持关闭。
显示ready丢失复位可视化，音频不受显示背压；PCM/频谱缓存各时钟域独立同步解除复位。
HDMI0引脚模板来自固定提交的官方Pro Dock示例，必须检查实际板卡。所有音频/麦克风/演奏席引脚、生成时钟、IO时序仍需填写并验证。默认构建拒绝缺少约束。不是已上板固件；旧RGB或频谱读取版本的时序/整曲结果不能直接替代本版本整机验收。
来源和许可证见licenses/dvi_SOURCE.json、编码器头部ISC声明及dvi_LICENSE.Sipeed.txt。未改写Flash。
''',encoding='utf-8')
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rtl.iterdir()) if p.name!='build_identity.vh')).hexdigest()
    (rtl/'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    record=dict(format='starcluster-offline-export-2',engine_profile='singer-v1',hardware_profile='workstation-i2s-dvi-v1',created=datetime.datetime.now().isoformat(),autoplay=autoplay,build_id=int(digest[:8],16),status='source_candidate_not_integrated_accepted',events=len(score['events']),sources={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='export_manifest.json'})
    (target/'export_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return target
