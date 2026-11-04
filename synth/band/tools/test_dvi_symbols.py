"""Independent TMDS coding/decoding oracle over RGB lanes, sync and resets."""
from pathlib import Path
import random,hashlib,json,os,subprocess,datetime
r=Path(__file__).resolve().parents[3];b=r/'synth/band';src=b/'experimental/audio_visual/dvi'
out=b/'evidence/dvi_symbols'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
control=[0b1101010100,0b0010101011,0b0101010100,0b1010101011]
def encode(value,disparity):
    xnor=value.bit_count()>4 or (value.bit_count()==4 and not value&1)
    bits=[value&1]
    for i in range(1,8):bits.append(bits[-1]^((value>>i)&1)^xnor)
    q=sum(int(bit)<<i for i,bit in enumerate(bits));q8=int(not xnor)
    balance=2*q.bit_count()-8
    if disparity==0 or balance==0:
        invert=1-q8;disparity+=balance if q8 else -balance
    elif (disparity>0 and balance>0) or (disparity<0 and balance<0):
        invert=1;disparity+=2*q8-balance
    else:
        invert=0;disparity+=balance-2*(1-q8)
    word=(invert<<9)|(q8<<8)|(q^(255 if invert else 0))
    # Separately reverse transition coding to prove the original byte survives.
    restored=(word&255)^(255 if word&512 else 0)
    decoded=restored&1
    for i in range(1,8):decoded|=(((restored>>i)^(restored>>(i-1))^(1-q8))&1)<<i
    assert decoded==value
    return word,disparity
rng=random.Random(1380252);stimuli=[];expected=[];disparities=[0,0,0];history=[];max_disparity=0
for i in range(20000):
    resetn=i>=4 and i%997 not in (0,1,2)
    de=i%23 not in (0,1,2,3)
    hs=i&1;vs=(i>>1)&1
    rgb=((i&255)<<16)|(((255-i)&255)<<8)|((i*17)&255) if i<1024 else rng.randrange(1<<24)
    words=[]
    for lane in range(3):
        if not resetn:word=0;disparities[lane]=0
        elif not de:word=control[(vs*2+hs) if lane==0 else 0];disparities[lane]=0
        else:word,disparities[lane]=encode((rgb>>(lane*8))&255,disparities[lane])
        words.append(word);max_disparity=max(max_disparity,abs(disparities[lane]))
    stimuli.append((int(resetn)<<27)|(int(de)<<26)|(hs<<25)|(vs<<24)|rgb)
    history.append(sum(word<<(lane*10) for lane,word in enumerate(words)))
    expected.append(history[-3] if i>=2 else 0)
(out/'stimulus.hex').write_text(''.join(f'{x:07x}\n' for x in stimuli))
(out/'expected.hex').write_text(''.join(f'{x:08x}\n' for x in expected))
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg[27:0]s;reg[27:0]stimulus[0:19999];reg[29:0]expected[0:19999];
wire[9:0]blue,green,red;integer i;
dvi_symbols dut(clk,s[27],s[26],s[25],s[24],s[23:0],blue,green,red);
initial begin
$readmemh("stimulus.hex",stimulus);$readmemh("expected.hex",expected);s=0;
for(i=0;i<20000;i=i+1)begin
 @(negedge clk);s=stimulus[i];@(posedge clk);#1;
 if(i>=2&&{red,green,blue}!==expected[i])$fatal(1,"TMDS RGB/sync mismatch index%0d got%h expected%h",i,{red,green,blue},expected[i]);
end
$display("PASS 20000 cycles:3 RGB lanes,sync controls,reset flush,disparity coding");$finish;
end
endmodule
'''
(out/'tb.v').write_text(tb)
for name in ('starcluster_tmds_encoder.v','dvi_symbols.v'):(out/name).write_bytes((src/name).read_bytes())
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
compile=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o','sim.vvp','tb.v','dvi_symbols.v','starcluster_tmds_encoder.v'],cwd=out,env=env,capture_output=True,text=True)
run=subprocess.run([str(binary/'vvp.exe'),'sim.vvp'],cwd=out,env=env,capture_output=True,text=True) if compile.returncode==0 else None
record=dict(status='passed' if run and run.returncode==0 else 'failed',scope='20000 cycles three TMDS word lanes;independent encode/decode oracle,all byte values/sync controls/reset/2edge pipeline. No serializer/PLL/pins/display acceptance.',maximum_oracle_disparity=max_disparity,compile_log=compile.stdout+compile.stderr,simulation_log=(run.stdout+run.stderr) if run else None,sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*out.glob('*.v'),*out.glob('*.hex'),Path(__file__)]})
(out/'result.json').write_text(json.dumps(record,indent=2));print(out);print(json.dumps(record,indent=2));raise SystemExit(record['status']!='passed')
