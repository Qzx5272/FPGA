"""Actual PCM/Hann/FFT/snapshot/pixel consumer, with three independent clocks."""
from pathlib import Path
import os,subprocess,json,hashlib,datetime
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/audio_visual'
o=b/'evidence/pcm_spectrum_display'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');o.mkdir(parents=True)
tb=r'''`timescale 1ns/1ps
module tb;
reg ac=0,fc=0,dc=0,run=1;always #7 ac=~ac;always #5 fc=~fc;always #19 if(run)dc=~dc;
reg rst=1,pv=0,frame_start=0;reg[9:0]x=336,y=439;reg signed[15:0]l=0,r=0;
wire[23:0]rgb;wire dv;wire[31:0]frames,skips,clips,rejects;
integer i,count=0,audio_count=0,before_count,fd;
pcm_spectrum_display #(.TWIDDLE_FILE("@TW@"),.WINDOW_FILE("@WIN@")) dut(
 .audio_clk(ac),.analysis_clk(fc),.display_clk(dc),.rst(rst),.pcm_valid(pv),.pcm_left(l),.pcm_right(r),
 .frame_start(frame_start),.pixel_x(x),.pixel_y(y),.rgb(rgb),.display_valid(dv),.displayed_frames(frames),
 .visualization_skipped(skips),.fft_clips(clips),.rejected_bins(rejects));
always @(posedge ac)if(pv&&!rst)audio_count=audio_count+1;
always @(posedge fc)if(!rst&&dut.analyzer.valid&&dut.analyzer.ready&&count<2048)begin
 if(dut.analyzer.bin!=count)$fatal(1,"producer order");
 $fdisplay(fd,"%04x %04x",dut.analyzer.re,dut.analyzer.im);count=count+1;
end
task swap;begin @(negedge dc);frame_start=1;@(negedge dc);frame_start=0;end endtask
initial begin
 fd=$fopen("fft_bins.txt","w");
 repeat(4)@(negedge dc);rst=0;run=0;
 for(i=0;i<2048;i=i+1)begin @(negedge ac);pv=1;l=(i%32<16)?16000:-16000;r=1234;end
 @(negedge ac);l=0;r=0;
 wait(count==2048);$fclose(fd);repeat(250000)@(negedge fc);
 if(dut.analyzer.ready||!dut.analyzer.valid||skips==0)$fatal(1,"stopped display did not stall analysis");
 before_count=audio_count;run=1;wait(dut.view.pending);
 if(dv||frames)$fatal(1,"published pixels before frame boundary");
 swap();if(!dv||frames!=1||rgb==24'h080c16)$fatal(1,"first display frame/pitch band");
 fd=$fopen("display_heights.txt","w");
 for(i=0;i<32;i=i+1)$fdisplay(fd,"%0d",(15*dut.view.levels1[i]));$fclose(fd);
 wait(dut.view.pending);repeat(10)@(negedge dc);
 if(rgb==24'h080c16||frames!=1)$fatal(1,"tearing while silence frame pending");
 swap();#1;if(rgb!=24'h080c16||frames!=2)$fatal(1,"silence not displayed atomically");
 if(audio_count<=before_count||clips||rejects)$fatal(1,"continuity/counter error");
 @(negedge dc);run=0;rst=1;pv=0;repeat(4)@(negedge ac);rst=0;
 if(dv||dut.frame_available)$fatal(1,"stopped display reset");
 run=1;repeat(100)@(negedge dc);
 if(dv||dut.frame_available)$fatal(1,"stale display after restart");
 $display("PASS PCM->Hann2048FFT->snapshot->32pixel bars;three clocks,stalled display,continued PCM,two atomic frames,stopped-clock reset");$finish;
end
initial begin #100000000;$fatal(1,"timeout");end
endmodule
'''.replace('@TW@',(s/'fft_twiddle_2048.mem').as_posix()).replace('@WIN@',(s/'hann_2048.mem').as_posix())
(o/'tb.v').write_text(tb)
names=('pcm_snapshot.v','fft_fixed.v','pcm_spectrum.v','spectrum_snapshot.v','pcm_spectrum_buffered.v','spectrum_bars.v','pcm_spectrum_display.v')
files=[s/n for n in names]+[o/'tb.v'];binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];logs=[]
for cmd in ([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(o/'test.vvp'),*map(str,files)],[str(binary/'vvp.exe'),str(o/'test.vvp')]):
    p=subprocess.run(cmd,cwd=o,env=env,capture_output=True,text=True,timeout=120);logs.append(p.stdout+p.stderr)
    if p.returncode:break
log=''.join(logs);ok=p.returncode==0 and 'PASS PCM' in log
ends=[1,2,3,4,5,6,7,9,11,14,17,21,26,32,39,48,59,72,88,108,132,161,197,241,294,359,438,535,653,797,923,1023]
expected=[];actual=[]
if ok:
    signed=lambda n:n-65536 if n>=32768 else n
    bins=[tuple(signed(int(n,16)) for n in line.split()) for line in (o/'fft_bins.txt').read_text().splitlines()]
    assert len(bins)==2048
    start=1
    for end in ends:
        peak=max(min(65535,abs(re)+abs(im)) for re,im in bins[start:end+1]);expected.append(peak.bit_length()*15);start=end+1
    actual=list(map(int,(o/'display_heights.txt').read_text().split()))
    ok=actual==expected
record=dict(status='passed' if ok else 'failed',scope='Synthetic PCM through actual Hann/FFT/frozen spectrum/pixel consumer;32 heights independently computed from actual FFT bins. No band-top integration,video timing,HDMI or physical acceptance',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[s/'fft_twiddle_2048.mem',s/'hann_2048.mem',Path(__file__)]},expected_heights=expected,actual_heights=actual,log=log)
(o/'result.json').write_text(json.dumps(record,indent=2));print(log);print('height comparison:',ok);raise SystemExit(not ok)
