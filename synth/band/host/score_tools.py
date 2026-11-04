"""Non-destructive score articulation, clipboard, history and loop operations."""
import copy
from score import validate


def articulate(score, gate=.97, max_gap_beats=.25, parts=(3,4,5,6,7,8,9,10,11,12,13,14)):
    if not .1 <= gate <= 1.15 or not 0 <= max_gap_beats <= 2:raise ValueError('非法门控或补缝范围')
    result=copy.deepcopy(score)
    spb=score['sample_rate']*60/score['bpm']
    groups={}
    offs={(e['part'],e['note'],e['serial']):e for e in result['events'] if e['kind']==1}
    for e in result['events']:
        if e['kind']==0 and e['part'] in parts:groups.setdefault(e['part'],[]).append(e)
    for part,notes in groups.items():
        onsets=sorted(set(e['sample'] for e in notes))
        next_at={a:b for a,b in zip(onsets,onsets[1:])}
        for e in notes:
            off=offs[(part,e['note'],e['serial'])]
            following=next_at.get(e['sample'])
            if following is None:continue
            gap=following-off['sample']
            # Preserve intentional phrase rests. Do not shorten existing sustained chords.
            if 0 < gap <= max_gap_beats*spb:
                target=e['sample']+round((following-e['sample'])*gate)
                off['sample']=min(result['duration_samples']-1,max(off['sample'],target))
    result['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
    result['edited']=True
    result['decisions']=[]
    return validate(result)


def section(score, start_beat, end_beat):
    if not 0 <= start_beat < end_beat:raise ValueError('循环起止非法')
    spb=score['sample_rate']*60/score['bpm']
    start,end=round(start_beat*spb),min(score['duration_samples'],round(end_beat*spb))
    if end<=start:raise ValueError('循环范围超出曲谱')
    result=copy.deepcopy(score);events=[]
    ons={};markers={}
    for e in score['events']:
        key=(e['part'],e['note'],e['serial'])
        if e['kind']==0:ons[key]=e
        elif e['kind']==1:
            on=ons.pop(key)
            if on['sample'] < end and e['sample'] > start:
                a=copy.deepcopy(on);b=copy.deepcopy(e)
                a['sample']=max(start,a['sample'])-start
                b['sample']=min(end-1,e['sample'])-start
                if b['sample']>a['sample']:events.extend((a,b))
        elif e['sample']<start:markers[e['part']]=e
        elif e['sample']<end:
            n=copy.deepcopy(e);n['sample']-=start;events.append(n)
    for part,e in markers.items():
        if not any(n['kind']==2 and n['part']==part and n['sample']==0 for n in events):
            n=copy.deepcopy(e);n['sample']=0;events.append(n)
    if not any(e['kind']==0 for e in events):raise ValueError('此段没有音符')
    result['duration_samples']=end-start
    result['events']=sorted(events,key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
    return validate(result)


def coverage(score):
    boundaries=[];starts={};durations=[]
    for e in score['events']:
        key=(e['part'],e['note'],e['serial'])
        if e['kind']==0:starts[key]=e['sample'];boundaries.append((e['sample'],1))
        elif e['kind']==1:
            durations.append(e['sample']-starts.pop(key));boundaries.append((e['sample'],-1))
    active=0;last=0;gaps=[]
    for t,delta in sorted(boundaries):
        if not active and t>last:gaps.append((last/48000,t/48000))
        active+=delta;last=t
    return dict(notes=len(durations),duration_s=score['duration_samples']/48000,
                event_silence_windows_s=gaps,scope='Note gates only; release tails and waveform loudness are not measured')


def with_metronome(score):
    """Append a quiet HDL hat click per beat; undo removes the generated clicks."""
    result=copy.deepcopy(score)
    serial=max(e['serial'] for e in result['events'])+1
    step=round(score['sample_rate']*60/score['bpm'])
    clicks=[]
    for beat,at in enumerate(range(0,score['duration_samples']-1,step)):
        end=min(at+1200,score['duration_samples']-1)
        for kind,sample in [(0,at),(1,end)]:
            clicks.append(dict(kind=kind,sample=sample,part=2,note=84 if beat%4==0 else 72,
                               velocity=(42 if beat%4==0 else 28) if kind==0 else 0,serial=serial))
        serial+=1
    if len(clicks)+len(result['events'])>4096:raise ValueError('添加节拍器将超出4096事件，请先选取较短循环段')
    result['events'].extend(clicks)
    result['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
    return validate(result)


class History:
    def __init__(self):self.undo_stack=[];self.redo_stack=[]
    def remember(self,score):
        self.undo_stack.append(copy.deepcopy(score));self.undo_stack=self.undo_stack[-100:];self.redo_stack=[]
    def undo(self,score):
        if not self.undo_stack:return score
        self.redo_stack.append(copy.deepcopy(score));return self.undo_stack.pop()
    def redo(self,score):
        if not self.redo_stack:return score
        self.undo_stack.append(copy.deepcopy(score));return self.redo_stack.pop()
