"""PT8211 PCM serial equality andactual FFT/DVI pixels inone exported top."""
from pathlib import Path
import os,sys,subprocess,json,hashlib,datetime,shutil,time
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
sys.path.insert(0,str(b/'reference'));from tmds_reference import encode,control
export=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else r/'output/final_workstation_20261022/offline_workstation_pt8211_dvi_confluence'
manifest=json.loads((export/'export_manifest.json').read_text(encoding='utf-8'))
assert manifest['hardware_profile']=='workstation-pt8211-dvi-v1'
for name,h in manifest['sources'].items():assert hashlib.sha256((export/name).read_bytes()).hexdigest()==h,name
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out=b/'evidence/workstation_pt8211_dvi'/stamp;out.mkdir(parents=True)
build=Path('D:/StarclusterBuilds')/('workstation_pt8211_dvi_'+stamp);shutil.copytree(export/'rtl',build)
for p in export.glob('*.mem'):shutil.copy2(p,build/p.name)
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
wire hp_bck,hp_ws,hp_din,pa_en;wire cp,cn,dv;wire[2:0]dp,dn;integer fp,fs,frames=0,peak=0,stalled_start,n=0;reg capture=0;
GSR GSR(.GSRI(1'b1));
offline_workstation_top dut(.clk(clk),.uart_rx_pin(1'b1),.HP_BCK(hp_bck),.HP_WS(hp_ws),.HP_DIN(hp_din),.PA_EN(pa_en),
 .mic_bck(1'b0),.mic_ws(1'b0),.mic_sd(1'b0),.adc_dout(10'd0),
 .play_button(1'b0),.stop_button(1'b0),.panic_button(1'b0),.root(4'd0),.minor_mode(1'b0),.pedal_raw(4'd0),
 .tmds_clk_p(cp),.tmds_clk_n(cn),.tmds_d_p(dp),.tmds_d_n(dn),.video_valid(dv));
reg[31:0]expected_pcm[0:8191];integer pcm_tail=0,pcm_head=0,dac_bits=0,dac_checked=0;
reg[31:0]dac_shift=0;reg dac_aligned=0;
always @(posedge clk)begin
 if(dut.band.rst)begin pcm_tail=0;end
 else if(dut.band.pcm_valid)begin
  if(pcm_tail>=8192)$fatal(1,"PCM scoreboard overflow");
  expected_pcm[pcm_tail]={dut.band.pcm_right,dut.band.pcm_left};pcm_tail=pcm_tail+1;
 end
end
always @(posedge hp_bck)if(!dut.band.rst)begin
 dac_shift={dac_shift[30:0],hp_din};dac_bits=dac_bits+1;
 if(dac_bits==16&&hp_ws!==0)$fatal(1,"PT8211 right WS");
 if(dac_bits==32)begin
  if(hp_ws!==1)$fatal(1,"PT8211 left WS");dac_bits=0;
  if(!dac_aligned&&dac_shift!==32'd0)begin
   while(pcm_head<pcm_tail&&expected_pcm[pcm_head]===32'd0)pcm_head=pcm_head+1;
   dac_aligned=1;
  end
  if(dac_aligned)begin
   if(pcm_head>=pcm_tail||dac_shift!==expected_pcm[pcm_head])$fatal(1,"PT8211 PCM mismatch head=%0d got=%h expected=%h",pcm_head,dac_shift,expected_pcm[pcm_head]);
   pcm_head=pcm_head+1;dac_checked=dac_checked+1;
  end
 end
end
always @(posedge clk)begin
 if(dut.band.engine.playing)begin
  if(dut.band.dac_dropped||dut.band.dac_underruns||dut.band.engine.deadline_miss||dut.band.engine.clips||dut.band.fft_clips||dut.band.rejected_bins)$fatal(1,"audio/analyzer counters");
  if(dut.band.pcm_valid)begin frames=frames+1;
   if($signed(dut.band.pcm_left)>peak)peak=$signed(dut.band.pcm_left);
  end
 end
end
always @(posedge dut.video_output.serial_clk or negedge dut.video_output.serial_clk)begin
 #1;if(capture)begin
  if(cp!==dut.pixel_clk||cn!==!dut.pixel_clk||dn!==~dp)$fatal(1,"differential pins");
  $fdisplay(fs,"%b",dp);
 end
end
initial begin
 fp=$fopen("pixels.txt","w");fs=$fopen("serial.txt","w");
 wait(dv);wait(dut.band.video_y==400&&dut.band.video_x==640);
 @(negedge dut.pixel_clk);capture=1;
 for(n=0;n<1200;n=n+1)begin
  $fdisplay(fp,"%b %b %b %h",dut.video_active,dut.video_hsync_n,dut.video_vsync_n,dut.video_rgb);
  @(negedge dut.pixel_clk);
 end
 repeat(16)@(negedge dut.pixel_clk);capture=0;$fclose(fp);$fclose(fs);
 if(frames<2048||peak==0||dac_checked<2048)$fatal(1,"no real band PCM");
 stalled_start=frames;force dut.video_ready=0;#1;
 if(dv||dut.band.display_available)$fatal(1,"display ready loss did not clear stale picture");
 repeat(5000)@(negedge clk);
 if(frames-stalled_start<4||!dut.band.engine.playing||dv)$fatal(1,"display fault stalled audio");
 release dut.video_ready;repeat(20)@(negedge dut.pixel_clk);
 if(dv)$fatal(1,"old frame reappeared immediately");
 $display("PT8211 decoded_stereo_frames=%0d",dac_checked);
 $display("PASS actualband DVI frames=%0d peak=%0d audio_during_display_reset=%0d",frames,peak,frames-stalled_start);$finish;
end
initial begin #120000000;$fatal(1,"whole DVI timeout");end
endmodule
'''
(build/'tb.v').write_text(tb);(out/'tb.v').write_text(tb)
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v');binary=r/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
record=dict(status='running',build=str(build),export=str(export),scope='Actual exported PT8211 PCM serial equality plusband/PLL/HannFFT/32bars/OSER serial pixels;synthetic no microphone/no external sensors. Display-ready loss injected at interface,not physical PLL failure. No fullsong/full-load/PnR/physical claim.',sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*build.glob('*.v'),*build.glob('*.sv'),*build.glob('*.vh'),*build.glob('*.mem'),vendor,b/'reference/tmds_reference.py',Path(__file__)]})
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(build,flush=True)
try:
 compiled=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-I',str(build),'-s','tb','-o','sim.vvp',*map(str,build.glob('*.v')),*map(str,build.glob('*.sv')),str(vendor)],cwd=build,env=env,capture_output=True,text=True)
 record['compile_log']=compiled.stdout+compiled.stderr;assert compiled.returncode==0,record['compile_log']
 start=time.monotonic()
 with (out/'run.log').open('w') as log:run=subprocess.run([str(binary/'vvp.exe'),'sim.vvp'],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
 record['elapsed_seconds']=time.monotonic()-start;record['log']=(out/'run.log').read_text();assert run.returncode==0,record['log']
 pixels=[line.split() for line in (build/'pixels.txt').read_text().splitlines()];samples=(build/'serial.txt').read_text().splitlines()
 assert len(pixels)==1200 and pixels[0][0]=='0'
 color_count=sum(int(row[3],16) in (0x35d8c2,0xff9e40) for row in pixels);assert color_count>0
 offsets=[]
 for lane in range(3):
  disparity=0;words=[]
  for de,hs,vs,rgb in pixels:
   if de=='0':word=control[int(vs)*2+int(hs) if lane==0 else 0];disparity=0
   else:word,disparity=encode((int(rgb,16)>>(lane*8))&255,disparity)
   words.append(word)
  expected=''.join(''.join(str((word>>bit)&1) for bit in range(10)) for word in words)
  bits=''.join(row[2-lane] for row in samples);offset=bits.find(expected);assert 0<=offset<=120,(lane,offset)
  offsets.append(offset)
 assert len(set(offsets))==1,offsets
 record.update(status='passed',colored_input_pixels=color_count,serial_bits_checked_per_lane=12000,serial_offsets=offsets)
except Exception as e:record.update(status='failed',error=str(e));raise
finally:
 for name in ('pixels.txt','serial.txt'):
  if (build/name).exists():shutil.copy2(build/name,out/name)
 report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k not in ('sources','compile_log')},indent=2))
