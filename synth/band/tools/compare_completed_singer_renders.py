"""Compare completed source-bound singer renders; never inspect running PCM as acceptance."""
from pathlib import Path
import argparse,hashlib,json,struct,wave

def load(path):
    d=json.loads(path.read_text(encoding='utf-8'))
    if d.get('status')!='passed':raise ValueError('Render not completed/passed: '+str(path))
    with wave.open(d['wav'],'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000)
        pcm=w.readframes(w.getnframes())
    assert hashlib.sha256(pcm).hexdigest()==d['pcm_sha256'], 'PCM hash mismatch'
    assert len(pcm)==d['score_contract']['frames']*4, 'Frame count mismatch'
    return d,pcm

def binding(d,suffix):
    values=[h for p,h in d['source_hashes'].items() if p.replace('\\','/').endswith(suffix)]
    assert len(values)==1, ('Missing/ambiguous source binding',suffix)
    return values[0]

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('reference',type=Path);ap.add_argument('candidate',type=Path);a=ap.parse_args()
    before,x=load(a.reference);after,y=load(a.candidate)
    for suffix in ('/project.json','/tests/singer_render.cpp','/rtl/song_events.vh','/rtl/song_storage_init.vh','/rtl/offline_patch_defaults.vh'):
        assert binding(before,suffix)==binding(after,suffix), ('Different render inputs',suffix)
    assert len(y)>=len(x), 'Candidate shorter than reference'
    same=y[:len(x)]==x
    record={'status':'passed_exact_prefix' if same else 'different_pcm','frames_compared':len(x)//4,
            'candidate_extra_frames':(len(y)-len(x))//4,'reference_report_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),
            'candidate_report_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
            'scope':'Exact completed PCM comparison for same score, patch and render driver; not physical audio, whole-top or timing acceptance'}
    if not same:
        first=next(i for i,(u,v) in enumerate(zip(x,y)) if u!=v)//4
        record.update(first_different_frame=first,reference_stereo=struct.unpack_from('<hh',x,first*4),candidate_stereo=struct.unpack_from('<hh',y,first*4))
    out=a.candidate.with_name(a.candidate.stem+'_prefix_comparison.json');out.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
    raise SystemExit(not same)
