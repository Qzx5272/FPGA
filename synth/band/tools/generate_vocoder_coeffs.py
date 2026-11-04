"""Reproducible Q20 envelope LPF; stdlib only, no silent SOS underflow.

LPF formula: https://www.w3.org/TR/audio-eq-cookbook/
Retains the 16 MIT-licensed VOXOS band filters; upstream/LICENSE applies.
"""
from pathlib import Path
import math, cmath, json, hashlib

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'experimental/vocoder'
Q = 1 << 20

def signed(x):
    v = int(x, 16)
    return v if v < 2**31 else v - 2**32

def response(row, hz):
    z = cmath.exp(-2j * math.pi * hz / 48000)
    h = 1
    for k in (0, 5):
        b0,b1,b2,a1,a2 = [x/Q for x in row[k:k+5]]
        h *= (b0+b1*z+b2*z*z)/(1+a1*z+a2*z*z)
    return abs(h)

def pole_radius(row):
    radii=[]
    for k in (0,5):
        a,b = row[k+3]/Q,row[k+4]/Q
        d=cmath.sqrt(a*a-4*b)
        radii.extend([abs((-a+d)/2),abs((-a-d)/2)])
    return max(radii)

def generate():
    original = SRC/'upstream/coeffs.mem'
    rows = [[signed(x) for x in line.split()] for line in original.read_text().splitlines() if line.strip()]
    assert len(rows)==17 and all(len(r)==10 for r in rows)
    envelope=[]
    for quality in (1/(2*math.cos(math.pi/8)),1/(2*math.cos(3*math.pi/8))):
        w=2*math.pi*100/48000
        alpha=math.sin(w)/(2*quality)
        a1=round(-2*math.cos(w)/(1+alpha)*Q)
        a2=round((1-alpha)/(1+alpha)*Q)
        # Each section has exact unit DC gain after denominator quantization.
        numerator=Q+a1+a2
        b0=round(numerator/4)
        envelope.extend([b0,numerator-2*b0,b0,a1,a2])
    corrected=rows[:16]+[envelope]
    assert response(rows[-1],0)==0
    assert abs(response(envelope,0)-1)<1e-10
    assert .68 < response(envelope,100) < .74
    assert response(envelope,1000)<.0002
    audits=[]
    grid=[20*(12000/20)**(k/4095) for k in range(4096)]
    for i,row in enumerate(corrected):
        radius=pole_radius(row)
        assert radius<1
        peak=max(grid,key=lambda hz:response(row,hz))
        audits.append(dict(index=i,max_pole_radius=radius,peak_hz=peak,
                           dc_gain=response(row,0),gain_100hz=response(row,100),gain_1khz=response(row,1000)))
    assert all(audits[i]['peak_hz']<audits[i+1]['peak_hz'] for i in range(15))
    target=SRC/'ported/coeffs.mem'
    target.write_text('\n'.join(' '.join(f'{x&0xffffffff:08X}' for x in row) for row in corrected)+'\n',encoding='ascii')
    result=dict(status='passed',scope='Quantized coefficients and linear transfer functions only; not fixed-point limit cycles or hardware audio',
                upstream_envelope_dc_gain=0,upstream_defect='Generator writes highpass row17 but omits lowpass row18; filterbank uses row17 as envelope LPF',
                sample_rate=48000,coefficient_fraction_bits=20,filters=audits,
                upstream_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                corrected_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    out=ROOT/'evidence/vocoder_coefficients';out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':generate()
