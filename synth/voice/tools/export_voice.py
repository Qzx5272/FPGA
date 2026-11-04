"""GPL-3.0-or-later: adapted from eSpeak NG spectral format (spect.c).
Exports selected formant envelopes into a new 32-partial additive model.
This is not a bit-identical port of the eSpeak waveform generator.
"""
import json, math, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ['vowel/a','vowel/i','vowel/u_bck','vdiph2/o_oo','vowel/3_2','vowel/y_2','n/_n']

def parse(path):
    data=path.read_bytes(); pos=8
    kind={b'SPECTSEQ':0,b'SPECTSEK':1,b'SPECTSQ2':2}[data[:8]]
    def unpack(fmt):
        nonlocal pos
        size=struct.calcsize(fmt); value=struct.unpack_from(fmt,data,pos);pos+=size
        return value
    def extended():
        nonlocal pos
        se, mantissa=struct.unpack_from('>HQ',data,pos);pos+=10
        return (-1 if se&32768 else 1)*math.ldexp(mantissa, (se&32767)-16383-63) if mantissa else 0.
    n=unpack('<I')[0];name=data[pos:pos+n].decode(errors='replace');pos+=n
    count,amp,_,_=unpack('<hhhh');frames=[]
    for _ in range(count):
        time,pitch,length,dx=[extended() for _ in range(4)]
        nx,markers,adjust=unpack('<hhh')
        if kind==2:unpack('<hh')
        peaks=[]
        for _ in range(9):
            vals=unpack('<'+'h'*(9 if kind==2 else 6))
            peaks.append(dict(frequency=vals[2],height=vals[3],left_width=vals[4],right_width=vals[5]))
        if kind:unpack('<'+'h'*14)
        pos+=nx*2 # analysed spectrum is not used as audio or synthesis data
        frames.append(dict(time=time,length=length,peaks=peaks,markers=markers))
    assert pos<=len(data)
    return dict(name=name,amplitude=amp,frames=frames)

def main():
    profiles=[]
    for asset in ASSETS:
        parsed=parse(ROOT/'sources/espeak-ng/phsource'/asset)
        frames=[f for f in parsed['frames'] if any(p['height']>0 for p in f['peaks'])]
        chosen=frames[len(frames)//2]
        profiles.append(dict(asset=asset,selected_frame=chosen,all_frames=parsed['frames']))
    (ROOT/'generated/formant_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n',encoding='utf-8')
    words=[0]*16384
    for unit,profile in enumerate(profiles):
        for octv in range(2,7):
            for key,semi in enumerate([0,2,4,5,7,9,11,12]):
                f0=440*2**(((octv+1)*12+semi-69)/12)
                weights=[]
                for harmonic in range(1,33):
                    freq=f0*harmonic
                    value=0
                    for p in profile['selected_frame']['peaks']:
                        width=max(50,p['left_width'] if freq<p['frequency'] else p['right_width'])
                        value+=max(0,p['height'])/(1+((freq-p['frequency'])/width)**2)**2
                    weights.append(value if freq<20000 else 0)
                scale=12000/max(sum(weights),1)
                for h,w in enumerate(weights):
                    words[unit*2048+((octv-2)*8+key)*32+h]=round(w*scale)
    dest=ROOT.parent/'rtl/voice_rom.vh'
    dest.write_text('// GPL-3.0-or-later; derived from eSpeak NG formant data. See voice/sources/espeak-ng/COPYING.\n'+
                    '\n'.join(f'weights[{i}] = 16\'d{v};' for i,v in enumerate(words))+'\n',encoding='ascii')
    print('Exported 7 spectral profiles, 40 pitches, 32 harmonics, no PCM.')

if __name__=='__main__':main()
