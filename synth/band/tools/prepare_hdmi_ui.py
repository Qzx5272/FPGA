"""Create an isolated HDMI UI candidate, retaining verified audio/UART pins."""
from pathlib import Path
import hashlib,json,shutil
band=Path(__file__).resolve().parents[1]
base=Path('D:/StarclusterBuilds/phone_uart_20261031_a')
out=Path('D:/StarclusterBuilds/hdmi_ui_20261031_a');assert not out.exists()
record=json.loads((base/'candidate.json').read_text())
for name,h in record['sources'].items():
 p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
 q=out/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def change(name,old,new):
 p=out/'rtl'/name;s=p.read_text();assert s.count(old)==1,(name,old);p.write_text(s.replace(old,new))
assets=band/'experimental/hdmi_ui'
for name in ['instrument_ui.v','ui_state.v','ui_glyphs.vh']:shutil.copy2(assets/name,out/'rtl'/name)
for name in ['ui_font.mem','ui_tiles.mem','ui_names.mem']:shutil.copy2(assets/name,out/name)
change('band_stage_pt8211_engine.sv','output HP_BCK,HP_WS,HP_DIN,output PA_EN,','output HP_BCK,HP_WS,HP_DIN,output PA_EN,output wire[127:0]ui_snapshot_data,')
change('band_stage_pt8211_engine.sv','wire debug_tick;', '''ui_state ui_observer(.clk(clk),.rst(rst),.panic(panic),.accepted(accepted),.packet(packet),
 .playing(playing),.master(master),.tempo(tempo),.voices(active_voices),.snapshot(ui_snapshot_data));
 wire debug_tick;''')
change('band_workstation_pt8211_top.sv','wire display_clk=pixel_clk;', 'wire[127:0]ui_core,ui_display;wire raster_active,raster_hs,raster_vs;\n wire display_clk=pixel_clk;')
change('band_workstation_pt8211_top.sv','.HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),','.HP_BCK(HP_BCK),.HP_WS(HP_WS),.HP_DIN(HP_DIN),.PA_EN(PA_EN),.ui_snapshot_data(ui_core),')
change('band_workstation_pt8211_top.sv','video_active,video_hsync_n,video_vsync_n,video_boundary);','raster_active,raster_hs,raster_vs,video_boundary);')
change('band_workstation_pt8211_top.sv',"assign video_rgb=video_active?bar_rgb:24'd0;",'''ui_snapshot ui_cdc(.source_clk(clk),.pixel_clk(pixel_clk),.source_rst(rst),.pixel_rst(video_reset),
 .frame_start(video_boundary),.source_data(ui_core),.display_data(ui_display));
 instrument_ui dashboard(.clk(pixel_clk),.rst(video_reset),.x(video_x),.y(video_y),
 .active(raster_active),.hsync_n(raster_hs),.vsync_n(raster_vs),.state(ui_display),
 .rgb(video_rgb),.de(video_active),.hs(video_hsync_n),.vs(video_vsync_n));''')
(out/'rtl/build_identity.vh').write_text("`define BAND_BUILD_ID 32'h20261041\n")
# Analyzer has no remaining board-visible consumers after replacing bar_rgb.
# Its special hold exception cannot target cells swept by synthesis.
sdc=out/'board.sdc'
sdc.write_text('\n'.join(line for line in sdc.read_text().splitlines() if 'analyzer/display_frame/ack1' not in line)+'\n')
sources={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
(out/'candidate.json').write_text(json.dumps({'baseline':record['baseline'],'parent_build':str(base),'build_id':0x20261041,'features':record['features'],'sources':sources,'status':'prepared_not_programmed'},indent=2))
print(out)
