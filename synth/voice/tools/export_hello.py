"""GPL-3.0-or-later. Dynamic ni2 hao3 parameter score, not audio samples.
Uses eSpeak NG spectral keyframes and its published peak-shape table.
"""
import json,math,re
from export_voice import ROOT,parse

def blend(a,b,u):
    return [{k:p[k]*(1-u)+q[k]*u for k in p} for p,q in zip(a,b)]

def trajectory(asset,u):
    frames=[f for f in parse(ROOT/'sources/espeak-ng/phsource'/asset)['frames'] if any(p['height'] for p in f['peaks'])]
    t=frames[0]['time']+max(0,min(1,u))*(frames[-1]['time']-frames[0]['time'])
    for a,b in zip(frames,frames[1:]):
        if t<=b['time']:
            return blend(a['peaks'],b['peaks'],(t-a['time'])/max(1e-9,b['time']-a['time']))
    return frames[-1]['peaks']

def main():
    source=(ROOT/'sources/espeak-ng/src/libespeak-ng/wavegen.c').read_text(encoding='utf-8')
    body=re.search(r'pk_shape1\[.*?\]\s*=\s*\{(.*?)\}',source,re.S).group(1)
    shape=[int(x) for x in re.findall(r'\d+',body)]
    assert len(shape)==257
    frames=[];rom=[]
    for frame in range(128):
        t=frame*10
        noise=0.;gain=0.;f0=140.
        if t<80:
            peaks=trajectory('n/_n',t/80);gain=.40*min(1,t/20);f0=135+10*t/80
        elif t<180:
            peaks=trajectory('n/ni',(t-80)/100);gain=.4+.6*(t-80)/100;f0=145+15*(t-80)/100
        elif t<450:
            peaks=trajectory('vowel/i',(t-180)/270);gain=min(1,(450-t)/40);f0=160+30*(t-180)/270
        elif t<530:
            peaks=trajectory('vowel/i',1)
        elif t<620:
            peaks=trajectory('vwl_zh/aau',0);noise=.65*min(1,(t-530)/20)*min(1,(640-t)/30)
            gain=max(0,(t-590)/30)*.7;f0=170
        elif t<1160:
            u=(t-620)/540
            # Keep an open /a/ nucleus, then continuously round toward /o,u/.
            morph=max(0,min(1,(u-.20)/.80))
            peaks=trajectory('vwl_zh/aau',morph)
            f0=170-60*min(1,u/.55)+45*max(0,(u-.55)/.45)
            gain=min(1,(1160-t)/90)
        else:
            peaks=trajectory('vwl_zh/aau',1)
        amps=[]
        for harmonic in range(1,65):
            freq=f0*harmonic;value=0.
            for p in peaks[:6]:
                width=max(40,p['left_width'] if freq<p['frequency'] else p['right_width'])
                index=int(abs(freq-p['frequency'])/width*256)
                if index<256:value+=shape[index]*max(0,p['height'])
            # eSpeak peak heights are in a square-root spectral representation.
            value+=max(0,1-freq/1000)*peaks[1]['height']*10
            amps.append(value*value if freq<18000 else 0.)
        scale=18000/max(sum(amps),1)
        coeffs=[round(a*scale*gain) for a in amps]
        assert sum(coeffs)<=18064
        rom.extend(coeffs)
        frames.append(dict(time_ms=t,pitch_hz=f0,gain=gain,noise_gain=noise,
                           phase_increment=round(f0/48000*2**32),peaks=peaks))
    lines=['// GPL-3.0-or-later eSpeak-derived dynamic parameters; no PCM.']
    lines += [f'hello_weights[{i}] = 16\'d{v};' for i,v in enumerate(rom)]
    for i,f in enumerate(frames):
        lines += [f'pitch_rom[{i}] = 32\'d{f["phase_increment"]};',
                  f'noise_rom[{i}] = 8\'d{round(f["noise_gain"]*255)};']
    (ROOT.parent/'rtl/hello_rom.vh').write_text('\n'.join(lines)+'\n',encoding='ascii')
    (ROOT/'generated/hello_score.json').write_text(json.dumps(dict(frame_ms=10,frames=frames),indent=2)+'\n',encoding='utf-8')
    print('128 dynamic frames, 64 harmonics, ni2 hao3, 1.28 seconds; no waveform samples')

if __name__=='__main__':main()
