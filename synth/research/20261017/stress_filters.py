"""Bounded randomized numerical stress of proposed fixed-point resonators.

This is a CPU design experiment, not FPGA certification or a listening test.
Each trial explores a NEW deterministic random pair of resonances, bandwidths,
coefficient precisions and transition lengths. No wall-clock sleeps are used.
Checkpoints distinguish completed sample calculations from wall-clock duration.
"""
import argparse, json, math, random, time
from datetime import datetime, timezone
from pathlib import Path

def coeff(f,b,frac):
    r=math.exp(-math.pi*b/48000)
    theta=2*math.pi*f/48000
    return tuple(round(v*(1<<frac)) for v in
                 ((1-r)*2*abs(math.sin(theta)),2*r*math.cos(theta),-r*r))

def jury(c,q):
    _,b,c=c;s=1<<q
    return min(s-b-c,s+b-c,s+c)>0

def trial(rng,index):
    q=(15,21)[index%2]
    f0=10**rng.uniform(math.log10(50),math.log10(18000))
    f1=10**rng.uniform(math.log10(50),math.log10(18000))
    bw0=10**rng.uniform(math.log10(5),math.log10(3000))
    bw1=10**rng.uniform(math.log10(5),math.log10(3000))
    a=coeff(f0,bw0,q);b=coeff(f1,bw1,q)
    if not jury(a,q) or not jury(b,q):
        return {'kind':'unstable_quantized_poles','q':q,'f':[f0,f1],'bw':[bw0,bw1],'samples':0}
    # 3 s at 48 kHz: short excitation, two transitions, then zero-input decay.
    n=144000;steps=(1,16,240,960)[(index//2)%4]
    state1=state2=0;signal_frac=23;limit=(1<<26)-1;peak=0;saturations=0
    tail_peak=0;g,fb1,fb2=a;prng=rng.getrandbits(32)
    rounder=1<<(q-1)
    for j in range(n):
        if 24000 <= j < 24000+steps:
            pos=j-24000+1
            g=a[0]+(b[0]-a[0])*pos//steps
            fb1=a[1]+(b[1]-a[1])*pos//steps
            fb2=a[2]+(b[2]-a[2])*pos//steps
        elif 48000 <= j < 48000+steps:
            pos=j-48000+1
            g=b[0]+(a[0]-b[0])*pos//steps
            fb1=b[1]+(a[1]-b[1])*pos//steps
            fb2=b[2]+(a[2]-b[2])*pos//steps
        if j<4096:
            prng=(1664525*prng+1013904223)&0xffffffff
            x=((prng>>16)-32768)*4  # <0.016 FS, deterministic broadband input
        elif j==24000 or j==48000: x=1<<(signal_frac-2)
        else:x=0
        # Symmetric round-to-nearest, ties away from zero; explicit saturation.
        z=g*x+fb1*state1+fb2*state2
        v=(z+rounder)>>q if z>=0 else -((-z+rounder)>>q)
        if v>limit:v=limit;saturations+=1
        elif v< -limit-1:v=-limit-1;saturations+=1
        state2,state1=state1,v
        av=abs(v)
        if av>peak:peak=av
        if j>=n-4800 and av>tail_peak:tail_peak=av
    return {'kind':'dynamic_resonator','q':q,'f':[f0,f1],'bw':[bw0,bw1],
            'transition_samples':steps,'samples':n,'peak_fs':peak/(1<<signal_frac),
            'tail_peak_fs':tail_peak/(1<<signal_frac),'saturations':saturations}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=7200)
    parser.add_argument('--seed',type=int,default=1382026);args=parser.parse_args()
    root=Path(__file__).resolve().parent/'deep';root.mkdir(exist_ok=True)
    rng=random.Random(args.seed);start=time.monotonic();stamp=datetime.now(timezone.utc).isoformat()
    summary={'scope':'CPU fixed-point numerical experiment; not board validation',
             'started_utc':stamp,'seed':args.seed,'requested_seconds':args.seconds,
             'trials':0,'samples_evaluated':0,'unstable_static_cases':0,'saturated_cases':0,
             'max_peak_fs':0,'max_tail_peak_fs':0,'tail_warning_cases':0,'status':'running'}
    last=0
    def save(done=False):
        summary['elapsed_seconds']=time.monotonic()-start
        summary['updated_utc']=datetime.now(timezone.utc).isoformat()
        summary['status']='completed' if done else 'running'
        temp=root/'filter_stress_progress.tmp';temp.write_text(json.dumps(summary,indent=2),encoding='utf-8')
        temp.replace(root/'filter_stress_progress.json')
    save()
    with (root/'filter_stress_anomalies.jsonl').open('w',encoding='utf-8') as log:
        while time.monotonic()-start<args.seconds:
            r=trial(rng,summary['trials']);summary['trials']+=1;summary['samples_evaluated']+=r['samples']
            if r['kind']=='unstable_quantized_poles':summary['unstable_static_cases']+=1;log.write(json.dumps(r)+'\n')
            else:
                summary['max_peak_fs']=max(summary['max_peak_fs'],r['peak_fs'])
                summary['max_tail_peak_fs']=max(summary['max_tail_peak_fs'],r['tail_peak_fs'])
                if r['saturations']:summary['saturated_cases']+=1;log.write(json.dumps(r)+'\n')
                if r['tail_peak_fs']>1e-4:summary['tail_warning_cases']+=1;log.write(json.dumps(r)+'\n')
            if time.monotonic()-last>30:save();log.flush();last=time.monotonic()
        save(True)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
