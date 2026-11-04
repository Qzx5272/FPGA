"""A bounded, original 90-second event-score example, not audio or actual human input.

Chord voice-leading, rule-based rhythm, lease takeover, shared partial budget,
and tail occupancy are exercised together. No pretrained model or PCM.
"""
import json,itertools,collections,random
from pathlib import Path

FS=48000;BPM=96;BEAT=30000;BAR=4*BEAT;END=90*FS
ROOT=Path(__file__).resolve().parent/'deep'
CHORDS=[(0,(0,4,7)),(9,(0,3,7)),(5,(0,4,7)),(7,(0,4,7))]

def voicing(root,intervals,previous,melody_floor=76):
    candidates=[]
    for octaves in itertools.product(range(3,6),repeat=3):
        v=tuple(sorted(root+i+12*o for i,o in zip(intervals,octaves)))
        if min(v)<48 or max(v)>74 or len(set(v))<3:continue
        cost=sum(abs(a-b) for a,b in zip(v,previous))+8*sum(n>=melody_floor for n in v)
        cost+=max(0,v[-1]-v[0]-16)*2
        candidates.append((cost,v))
    assert candidates
    return min(candidates)[1],len(candidates)

def main():
    events=[];serial=collections.defaultdict(int);rng=random.Random(13890)
    # Partial cost is an explicit approximate patch allocation, not a sound-quality score.
    costs={0:32,1:48,2:64,3:128,4:64,5:64,6:64,7:64}
    def note(t,length,track,slot,pitch,velocity,epoch=0,source=0,tag='rule'):
        serial[(track,slot)]+=1;s=serial[(track,slot)]
        identity=[source,track,slot,epoch,s]
        events.append({'sample':int(t),'kind':'on','identity':identity,'pitch':pitch,
                       'velocity':velocity,'partial_cost':costs[track],'origin':tag})
        events.append({'sample':min(END,int(t+length)),'kind':'off','identity':identity})
    previous=(48,52,55);max_candidates=0
    for bar in range(36):
        t=bar*BAR;root,intervals=CHORDS[(bar//2)%4]
        voices,n=voicing(root,intervals,previous);previous=voices;max_candidates=max(max_candidates,n)
        # Accompaniment density increases by scene; local deterministic state remains active after frontend loss.
        density=1 if bar<6 else 2 if bar<20 else 3
        for beat in range(4):
            tick=t+beat*BEAT
            drum_accent=85 if beat%2==0 else 72
            note(tick,BEAT//5,0,beat%2,36 if beat%2==0 else 38,drum_accent)
            if density>=2:
                for sub in (0,BEAT//2):note(tick+sub,BEAT//8,0,2+(beat%2),42,52+rng.randrange(12))
            note(tick,BEAT*3//4,1,0,root+36+(7 if beat==3 and density==3 else 0),
                 55+drum_accent//4,tag='bass_velocity_follows_drum_accent')
            # Programmed vocal notes end at beat 3; their explicit breath state permits a fill.
            if 20<=bar<30 and beat==3:
                for j,p in enumerate((45,47,50)):
                    note(tick+j*BEAT//3,BEAT//6,0,4+j,p,70+j*4,tag='vocal_breath_permits_drum_fill')
        for slot,pitch in enumerate(voices):note(t,3*BEAT,2,slot,pitch,60)
        # A programmed reply only after the planned lead phrase, never an AI quality claim.
        if 6<=bar<12:
            for j,p in enumerate((72,76,79,76)):
                note(t+2*BEAT+j*BEAT//2,BEAT*2//5,4,0,p,75,tag='bounded_call_response')
        if 20<=bar<30:
            for singer in range(4):
                note(t,3*BEAT,3,singer,[72,67,64,60][singer]+(2 if bar%4==3 else 0),70,tag='planned_vocal_note_not_audio')
    # Two planned human roles share a pitch, with distinct identities.
    for who,track in [(1,5),(2,6)]:
        for k in range(32):note(30*FS+k*BEAT//2,BEAT*3//4,track,k%2,72+(k%5),80,source=who,tag='synthetic_performer_input')
    # Track 4 changes owner at 30 seconds; preloaded old epoch event must be rejected at dispatch.
    events.append({'sample':30*FS,'kind':'transfer','track':4,'source':1,'epoch':1})
    note(30*FS+100,BEAT,4,1,75,80,epoch=0,source=0,tag='deliberately_stale_autoplayer')
    note(30*FS+120,BEAT,4,1,75,80,epoch=1,source=1,tag='synthetic_takeover')
    events.append({'sample':75*FS,'kind':'frontend_disconnect','origin':'scripted_condition'})
    priority={'transfer':0,'off':1,'frontend_disconnect':2,'on':3}
    events.sort(key=lambda e:(e['sample'],priority[e['kind']]))
    owners={t:(0,0) for t in range(8)};owners[5]=(1,0);owners[6]=(2,0)
    active={};retired=[];max_slots=0;max_partials=0;rejected=0;starts_after_disconnect=0
    max_at_sample=0;counts=collections.Counter(e['sample'] for e in events)
    for e in events:
        now=e['sample'];retired=[r for r in retired if r[0]>now]
        if e['kind']=='transfer':
            owners[e['track']]=(e['source'],e['epoch'])
            for key in list(active):
                if key[1]==e['track']:retired.append((now+32,active.pop(key)))
        elif e['kind'] in ('on','off'):
            key=tuple(e['identity']);source,track,slot,epoch,ser=key
            if (source,epoch)!=owners[track]:rejected+=1;continue
            if e['kind']=='off':
                if key in active:retired.append((now+2400,active.pop(key))) # 50 ms release reservation
            else:
                active[key]=e['partial_cost']
                if now>=75*FS:starts_after_disconnect+=1
        slots=len(active)+len(retired);partials=sum(active.values())+sum(r[1] for r in retired)
        max_slots=max(max_slots,slots);max_partials=max(max_partials,partials)
        assert slots<=64 and partials<=4096,(now,slots,partials)
    # Conservation at the end: all finite notes are released; tails expire in <=50 ms.
    assert not active and starts_after_disconnect>0 and rejected==2
    max_events_5ms=max(sum(v for t,v in counts.items() if start<=t<start+240) for start in counts)
    result={'scope':'event reference with planned synthetic performer inputs; no audio, RTL or board performance claim',
            'duration_seconds':90,'bpm':BPM,'bars':36,'event_count':len(events),
            'maximum_voice_leading_candidates':max_candidates,'maximum_simultaneous_slots_including_release':max_slots,
            'maximum_reserved_partials_including_release':max_partials,'maximum_events_same_sample':max(counts.values()),
            'maximum_events_in_5ms':max_events_5ms,'stale_events_rejected':rejected,
            'starts_after_frontend_disconnect':starts_after_disconnect,'active_at_end':len(active),
            'release_tail_reservation_samples':2400,
            'machine_interaction_rules':['bass velocity follows drum accent',
                                         'vocal breath permits drum fill',
                                         'chord voices minimize bounded movement below lead register'],
            'limitations':['fixed 96 BPM score; tempo-change and following require separate tests',
                           'lyrics phonemes live in song_control_example.json; four vocal note tracks here do not synthesize words',
                           'partial allocations and 50 ms release are patch assumptions, not measured realism']}
    (ROOT/'arranger_results.json').write_text(json.dumps(result,indent=2))
    (ROOT/'arranger_90s_events.json').write_text(json.dumps({'meta':result,'events':events},indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
