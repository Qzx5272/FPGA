"""Check the RTL piano/reed register and velocity audition; not a listening verdict."""
import sys,json,wave,hashlib
from pathlib import Path
import numpy as np

p=Path(sys.argv[1])
with wave.open(str(p),'rb') as f:
    fs=f.getframerate(); x=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2).astype(float)
assert fs==48000 and len(x)==18*fs
rows=[]
for i in range(18):
    y=x[i*fs:(i+1)*fs,0]; note=45+24*((i%9)//3)
    s=np.abs(np.fft.rfft(y[4800:24000]*np.hanning(19200)))
    freq=np.fft.rfftfreq(19200,1/fs); expected=440*2**((note-69)/12)
    # A harmonic can exceed the fundamental; assess the fundamental's own bin neighborhood.
    bins=np.where((freq>expected*.97)&(freq<expected*1.03))[0]
    k=int(bins[np.argmax(s[bins])]); log=np.log(np.maximum(s[k-1:k+2],1e-9))
    delta=.5*(log[0]-log[2])/(log[0]-2*log[1]+log[2])
    rms=lambda a,b:float(np.sqrt(np.mean(y[a:b]**2)))
    rows.append(dict(instrument='piano' if i<9 else 'reed',midi_note=note,velocity=[32,80,127][i%3],
                     rms=rms(4800,24000),early_rms=rms(2400,7200),held_rms=rms(30000,36000),
                     tail_rms=rms(47000,48000),fundamental_hz=float((k+delta)*fs/19200),expected_hz=expected))
checks={'all_notes_audible_digital':all(r['rms']>5 for r in rows),
        'velocity_monotonic_each_register':all(rows[i]['rms']<rows[i+1]['rms']<rows[i+2]['rms'] for i in range(0,18,3)),
        'fundamental_pitch':all(abs(r['fundamental_hz']/r['expected_hz']-1)<.01 for r in rows),
        'released_tails_decay':all(r['tail_rms']<r['rms']*.1 for r in rows),
        'piano_decays_while_held':all(r['held_rms']<r['early_rms']*.75 for r in rows[:9]),
        'reed_sustains_while_held':all(r['held_rms']>r['early_rms']*.8 for r in rows[9:]),
        'no_integer_clip':not bool(np.any(np.abs(x)>=32767))}
record=dict(status='passed' if all(checks.values()) else 'failed',evidence_level='RTL waveform numerical checks, not board or perceptual acceptance',
            wav_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),checks=checks,segments=rows)
p.with_suffix('.analysis.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
