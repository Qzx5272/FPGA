"""Compare numerical remedies; CPU model, never a board/audio quality claim."""
import json, math
from pathlib import Path

FS=48000
def rnd(v,q):
    return (v+(1<<(q-1)))>>q if v>=0 else -((-v+(1<<(q-1)))>>q)

def run(f,bw,frac,form,save_error=False):
    q=21;r=math.exp(-math.pi*bw/FS);th=2*math.pi*f/FS;s=1<<q
    if form=='direct':
        a,b,g=round(2*r*math.cos(th)*s),round(-r*r*s),round((1-r)*2*abs(math.sin(th))*s)
    else:
        a,b,g=round(r*math.cos(th)*s),round(r*math.sin(th)*s),round((1-r)*s)
    u=v=err=0;peak=tail=0
    for n in range(FS*3):
        x=(1<<(frac-2)) if n==0 else 0
        if form=='direct':
            wide=g*x+a*u+b*v+(err if save_error else 0)
            out=rnd(wide,q);err=wide-(out<<q);u,v=out,u
        else:
            un=rnd(a*u-b*v+g*x,q);vn=rnd(b*u+a*v,q);u,v=un,vn;out=u
        peak=max(peak,abs(out))
        if n>=FS*3-4800:tail=max(tail,abs(out))
    return {'f_hz':f,'bw_hz':bw,'state_fraction_bits':frac,'form':form,
            'fraction_saving':save_error,'peak_fs':peak/(1<<frac),
            'tail_peak_fs':tail/(1<<frac),'tail_dbfs':20*math.log10(max(tail/(1<<frac),1e-20))}

if __name__=='__main__':
    results=[]
    for f,b in [(50.7947,6.303),(83.2049,214.265),(50,5),(100,10),(440,20),(800,80),(3000,100),(16000,1000)]:
        for frac in (23,32):
            results.extend(run(f,b,frac,form,save) for form,save in [('direct',False),('direct',True),('coupled',False)])
    out={'scope':'3-second impulse response; no parameter transitions; not acoustic validation', 'results':results}
    p=Path(__file__).resolve().parent/'deep'/'filter_mitigation.json';p.write_text(json.dumps(out,indent=2))
    for r in results:print(r)
