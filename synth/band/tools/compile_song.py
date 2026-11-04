"""Original 96-second event score; no waveform/PCM in FPGA song memory."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
FS=48000;BPM=120;BARS=48
ROLES=['kick','snare','hat','bass','electric_piano','held_reed','lead','vowel_choir']

def compose(rules=True):
    events=[];serial=0;decisions=[]
    def note(part,pitch,beat,length,velocity):
        nonlocal serial
        serial+=1
        for kind,time,vel in [(0,beat,velocity),(1,beat+length,0)]:
            events.append(dict(sample=round(time*FS*60/BPM),kind=kind,part=part,note=pitch,velocity=vel,serial=serial))
    previous=(60,64,67)
    progression=[(0,(0,4,7)),(9,(0,3,7)),(5,(0,4,7)),(7,(0,4,7))]
    melody=[0,4,7,9,7,4,2,0]
    for bar in range(BARS):
        base=bar*4;root,intervals=progression[(bar//2)%4]
        lead=16<=bar<44 and bar%4!=3
        choir=24<=bar<44
        breathing=choir and bar%4==3
        ending=bar>=44
        # Bass intensity follows the actual kick accent, not a free random control.
        kick_accents=[112,84,104,88]
        for beat in range(4):
            if not ending or beat in (0,2):note(0,36,base+beat,.16,kick_accents[beat])
            if bar>=2 and beat in (1,3) and bar<47:note(1,38,base+beat,.12,96)
        if bar<46:
            for eighth in range(8):note(2,42,base+eighth*.5,.07,66 if eighth%2 else 83)
        if breathing and rules:
            for offset in (3.25,3.5,3.75):note(1,38,base+offset,.08,63+int(offset*8))
            decisions.append(dict(bar=bar,rule='breath_fill',cause='choir breath and lead rests'))
        if bar>=4:
            for b in (0,1.5,2,3.5):
                pitch=36+root+(7 if b==3.5 and not ending else 0)
                velocity=kick_accents[int(b)]-8 if rules else 96
                note(3,pitch,base+b,.4 if b%1 else .75,velocity)
        if 8<=bar<46:
            candidates=[]
            for octave in (48,60):
                chord=tuple(sorted(octave+root+i for i in intervals))
                for inversion in range(3):
                    candidate=tuple(sorted(chord[i]+(12 if i<inversion else 0) for i in range(3)))
                    if max(candidate)<=79:candidates.append(candidate)
            chord=min(candidates,key=lambda c:sum(abs(a-b) for a,b in zip(c,previous)))
            previous=chord
            for b in (0,2):
                for pitch in chord:note(4,pitch,base+b,.6 if lead and rules else 1.6,62 if lead and rules else 83)
            if 12<=bar<44:
                for pitch in chord:note(5,pitch,base,3.7,44)
            if lead and rules:decisions.append(dict(bar=bar,rule='leave_space',cause='active lead phrase',chord=list(chord)))
        if lead:
            for i,interval in enumerate(melody):note(6,72+root+interval,base+i*.5,.34,96 if i%2==0 else 78)
        if choir and not breathing:
            serial+=1
            events.append(dict(sample=round(base*FS*60/BPM),kind=2,part=7,note=(bar-24)%5,velocity=0,serial=serial))
            for interval in (0,7):note(7,60+root+interval,base,3.4,60)
    events.sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
    return dict(format='starcluster-score-1',sample_rate=FS,bpm=BPM,bars=BARS,duration_samples=BARS*4*FS*60//BPM,
        title='星群·合流',origin='Original deterministic event composition for this project; no recorded audio',roles=ROLES,rules_enabled=rules,decisions=decisions,events=events)

def validate(score):
    live={};max_live=0;last=-1
    for e in score['events']:
        assert e['sample']>=last;last=e['sample']
        identity=(e['part'],e['note'],e['serial'])
        if e['kind']==0:
            assert identity not in live and 0<e['velocity']<=127
            live[identity]=e;max_live=max(max_live,len(live))
        elif e['kind']==1:assert live.pop(identity,None) is not None
        else:assert e['kind']==2 and e['note']<=4
    assert not live and last<=score['duration_samples']
    assert 90<=score['duration_samples']/FS<=120
    return {'events':len(score['events']),'maximum_held_notes':max_live,'duration_seconds':score['duration_samples']/FS,'all_note_identities_released':True}

def main():
    assets=ROOT/'assets';assets.mkdir(exist_ok=True)
    score=compose();check=validate(score)
    (assets/'confluence.json').write_text(json.dumps(score,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['// Generated musical events only. Timestamp32 + identity32 + controls32.'];storage=[]
    for i,e in enumerate(score['events']):
        control=e['kind']|(e['part']<<2)|(e['note']<<6)|(e['velocity']<<13)
        word=(e['sample']<<64)|(e['serial']<<32)|control
        lines.append(f"song_rom[{i}]=96'h{word:024x};")
        storage.append(f"controls[{i}]=32'h{control:08x};identities[{i}]=32'd{e['serial']};times[{i}]=32'd{e['sample']};")
    (ROOT/'rtl/song_events.vh').write_text('\n'.join(lines)+'\n',encoding='ascii')
    (ROOT/'rtl/song_storage_init.vh').write_text('\n'.join(storage)+'\n',encoding='ascii')
    (ROOT/'rtl/song_config.vh').write_text(f"`define SONG_EVENTS {len(score['events'])}\n`define SONG_LENGTH {score['duration_samples']}\n",encoding='ascii')
    check['rules_on_vs_off_event_difference']=score['events']!=compose(False)['events']
    check['score_sha256']=hashlib.sha256((assets/'confluence.json').read_bytes()).hexdigest()
    (ROOT/'evidence/song_compile.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
    print(json.dumps(check))
if __name__=='__main__':main()
