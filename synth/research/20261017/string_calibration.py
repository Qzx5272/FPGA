"""Quantized loop-phase calibration, not a rendered/listening test."""
import math,cmath,json
from pathlib import Path
FS=48000
def design(f,s,t60):
    # Quantize the weighted two-tap loss shape before solving tuning.
    s=round(s*(1<<17))/(1<<17);omega=2*math.pi*f/FS
    shape=(1-s)+s*cmath.exp(-1j*omega)
    delay_loss=-cmath.phase(shape)/omega
    n=math.floor(FS/f-delay_loss-.5);d=FS/f-n-delay_loss
    rho=math.tan(omega*d/2)/math.tan(omega/2)
    a=(1-rho)/(1+rho);a=round(a*(1<<21))/(1<<21)
    requested_gain=10**(-3/(f*t60))/abs(shape)
    gain=min(requested_gain,1-2**-21);gain=math.floor(gain*(1<<21))/(1<<21)
    def phase(fq):
        w=2*math.pi*fq/FS;lp=-cmath.phase((1-s)+s*cmath.exp(-1j*w))
        ap=2*math.atan(((1-a)/(1+a))*math.tan(w/2))
        return n*w+lp+ap
    lo=f*.98;hi=f*1.02
    for _ in range(60):
        mid=(lo+hi)/2
        if phase(mid)<2*math.pi:lo=mid
        else:hi=mid
    fq=(lo+hi)/2;loop_gain=gain*abs(shape)
    effective=-3/(f*math.log10(loop_gain))
    return {'f_hz':f,'loss_weight':s,'requested_t60_s':t60,'integer_delay':n,
            'allpass_a':a,'frequency_from_loop_phase_hz':fq,
            'error_cents':1200*math.log2(fq/f),'gain_clamped':requested_gain>=1-2**-21,
            'estimated_effective_t60_s':effective,'gain':gain}
if __name__=='__main__':
    rows=[design(440*2**((m-69)/12),s,t) for m in range(21,109) for s in [.05,.2,.5,.8] for t in [.2,.5,2,10]]
    out={'scope':'loop-phase and loop-magnitude calculation; excludes dynamic pitch, rounding noise and perceptual pitch',
         'cases':len(rows),'worst_abs_pitch_error_cents':max(abs(r['error_cents']) for r in rows),
         'clamped_requested_decay_cases':sum(r['gain_clamped'] for r in rows),
         'max_integer_delay':max(r['integer_delay'] for r in rows),'examples':[design(f,s,t) for f,s,t in [(82.4069,.5,3),(440,.5,3),(1760,.5,3),(1760,.05,3)]],
         'all_cases':rows}
    (Path(__file__).resolve().parent/'deep'/'string_calibration.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!='all_cases'},indent=2))
