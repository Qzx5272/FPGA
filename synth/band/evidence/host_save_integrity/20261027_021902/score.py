"""Editable event score and atomic-upload encoder; no audio samples."""
import json,struct,zlib,os,tempfile
from pathlib import Path
from protocol import Event
def validate(score):
    if score.get('format') not in ('starcluster-score-1','starcluster-score-2') or score.get('sample_rate')!=48000:raise ValueError('需要 48 kHz 的星群事件曲谱')
    if score.get('engine_profile','band-v1') not in ('band-v1','singer-v1'):raise ValueError('未知乐队角色配置')
    if score.get('engine_profile')=='singer-v1' and score.get('format')!='starcluster-score-2':raise ValueError('电子歌手作品需要第二版文件格式，防止旧上位机误读角色')
    if score.get('bpm')!=120:raise ValueError('事件文件当前使用 120 BPM 时间基准；其他速度需要先转换事件时间')
    events=score['events'];duration=score['duration_samples']
    if not isinstance(duration,int) or not 0<duration<2**31 or not 0<len(events)<=4096:raise ValueError('曲谱长度或事件数量超出范围')
    live={};last=-1
    for e in events:
        for k in ('sample','kind','part','note','velocity','serial'):
            if not isinstance(e.get(k),int):raise ValueError('事件字段必须为整数')
        if not last<=e['sample']<duration or not 0<=e['part']<16 or not 0<=e['note']<128 or not 0<=e['velocity']<128 or not 0<e['serial']<2**32:raise ValueError('非法事件或时间顺序')
        identity=(e['part'],e['note'],e['serial']);last=e['sample']
        if e['kind']==0:
            if not e['velocity'] or identity in live:raise ValueError('重复起音或零力度起音')
            live[identity]=e
        elif e['kind']==1:
            if identity not in live or live.pop(identity)['sample']>=e['sample']:raise ValueError('缺少起音或零时长音符')
        elif e['kind']==2:
            if score.get('engine_profile')=='singer-v1' and e['part']==15:raise ValueError('电子歌手轨不支持元音预设事件，请使用第8轨合唱')
            if e['note']>4 or e['velocity']!=0:raise ValueError('元音事件必须为 0–4，力度字段为零')
        else:raise ValueError('不支持的事件类型')
    if live:raise ValueError('曲谱末尾存在未释放音符')
    p=score.get('performance',{})
    if not isinstance(p,dict):raise ValueError('演出参数必须为对象')
    for key,lo,hi in [('tempo',40,240),('root',0,11),('mode',0,2),('octave',1,7),('master',0,127),('wet',0,127)]:
        if key in p and(type(p[key]) is not int or not lo<=p[key]<=hi):raise ValueError('非法演出参数：'+key)
    if 'collaboration' in p and type(p['collaboration']) is not bool:raise ValueError('协作开关必须为布尔值')
    if 'pad_calibration' in p:
        from calibration_model import normalize
        normalize(p['pad_calibration'])
    if 'seat_parts' in p:
        seats={int(k):v for k,v in p['seat_parts'].items()}
        if set(seats)!={1,2,3,4} or any(type(v) is not int or not 0<=v<16 for v in seats.values()):raise ValueError('演奏席映射非法')
    from pad_mapping import normalize_mapping,normalize_seats
    normalize_mapping(p.get('pad_mapping',{}))
    normalize_seats(p.get('seat_pad_mappings',{}))
    limits={0:127,1:16383,2:4,4:16383,5:15,6:16383,7:15}
    for part,params in p.get('patches',{}).items():
        if not 0<=int(part)<16:raise ValueError('音色轨道非法')
        for key,value in params.items():
            key=int(key)
            if score.get('engine_profile')=='singer-v1' and int(part)==15 and key!=0:raise ValueError('电子歌手轨目前仅支持表情音色参数')
            if key not in limits or type(value) is not int or not 0<=value<=limits[key]:raise ValueError('音色参数非法')
    return score

def validate_target(score,features):
    """Keep part15 meaning stable across firmware profiles before transmitting."""
    validate(score)
    p=score.get('performance',{})
    uses=any(e['part']==15 for e in score['events']) or any(int(k)==15 for k in p.get('patches',{})) or 15 in p.get('seat_parts',{}).values()
    if features is None:
        if uses or score.get('engine_profile')=='singer-v1':raise ValueError('请等待固件身份回传后再上传含第16轨的作品')
        return score
    if score.get('engine_profile','band-v1')=='singer-v1':
        if not features&32:raise ValueError('此作品第16轨为电子歌手，目标固件未声明支持')
    elif features&32:
        if uses:raise ValueError('此作品第16轨为旧扩展音色，目标为电子歌手；请明确修改作品角色后再上传')
    return score
def load(path):return validate(json.loads(Path(path).read_text(encoding='utf-8')))

def edit_vowel(score,sample,vowel,part=7):
    """Return a validated edit; None removes the marker without touching notes."""
    import copy
    validate(score)
    if type(sample) is not int or not 0<=sample<score['duration_samples']:raise ValueError('元音位置超出曲谱')
    if type(part) is not int or not 0<=part<16:raise ValueError('元音轨道非法')
    if vowel is not None and (type(vowel) is not int or not 0<=vowel<=4):raise ValueError('元音必须为 0–4')
    edited=copy.deepcopy(score)
    edited['events']=[e for e in edited['events'] if not(e['kind']==2 and e['part']==part and e['sample']==sample)]
    if vowel is not None:
        serial=max((e['serial'] for e in edited['events']),default=0)+1
        edited['events'].append(dict(sample=sample,kind=2,part=part,note=vowel,velocity=0,serial=serial))
    edited['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
    edited['edited']=True;edited['decisions']=[]
    return validate(edited)
def insert_vowel_phrase(score,sample,syllables,velocity=90):
    """Insert (vowel0..4, MIDI pitch, integer sample duration) into empty choir space.

    Articulate each syllable with a 90% gate; restore the previous vowel after
    the phrase so unrelated later notes do not inherit its final vowel.
    """
    import copy
    validate(score)
    if type(sample) is not int or sample<0 or not syllables:raise ValueError('乐句起点或音节为空')
    if type(velocity) is not int or not 1<=velocity<=127:raise ValueError('力度必须为1–127')
    for vowel,pitch,duration in syllables:
        if any(type(v) is not int for v in (vowel,pitch,duration)) or not 0<=vowel<=4 or not 0<=pitch<=127 or duration<2:raise ValueError('非法元音、音高或时长')
    end=sample+sum(s[2] for s in syllables)
    if end>=score['duration_samples']:raise ValueError('乐句与恢复标记必须位于作品内')
    patches={int(k):v for k,v in score.get('performance',{}).get('patches',{}).items()}
    choir_patch={int(k):v for k,v in patches.get(7,{}).items()}
    notes={};prior=choir_patch.get(2,0)
    for event in score['events']:
        if event['part']!=7:continue
        if event['kind']==2:
            if sample<=event['sample']<end:raise ValueError('此处已有合唱元音，请选择空白区域')
            if event['sample']<sample:prior=event['note']
        elif event['kind']==0:notes[(event['note'],event['serial'])]=event['sample']
        elif notes.pop((event['note'],event['serial']))<end and event['sample']>sample:
            raise ValueError('此处已有合唱音符或跨入的延长音符，请选择空白区域')
    edited=copy.deepcopy(score);serial=max(e['serial'] for e in edited['events'])+1;at=sample
    for vowel,pitch,duration in syllables:
        for kind,t,note,vel in ((2,at,vowel,0),(0,at,pitch,velocity),(1,at+max(1,duration*9//10),pitch,0)):
            edited['events'].append(dict(sample=t,kind=kind,part=7,note=note,velocity=vel,serial=serial))
        serial+=1;at+=duration
    if not any(e['kind']==2 and e['part']==7 and e['sample']==end for e in edited['events']):
        edited['events'].append(dict(sample=end,kind=2,part=7,note=prior,velocity=0,serial=serial))
    edited['events'].sort(key=lambda e:(e['sample'],e['kind']==0,e['part'],e['serial']))
    edited['edited']=True;edited['decisions']=[]
    return validate(edited)

def save(path,score):
    validate(score)
    content=json.dumps(score,ensure_ascii=False,indent=2)
    p=Path(path)
    fd,tmp=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def upload_events(score):
    validate(score);words=[]
    for e in score['events']:
        control=e['kind']|(e['part']<<2)|(e['note']<<6)|(e['velocity']<<13)
        words.extend((control,e['serial'],e['sample']))
    crc=zlib.crc32(struct.pack('<'+'I'*len(words),*words))
    yield Event(13,flags=3,epoch=len(score['events']),serial=score['duration_samples'],parameter=crc)
    for i,word in enumerate(words):yield Event(13,flags=i%3,epoch=i//3,serial=word)
    yield Event(13,flags=4)
    yield Event(14)
