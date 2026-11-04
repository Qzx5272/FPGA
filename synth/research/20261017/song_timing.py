"""Score-to-phoneme timing reference; generates control data, never PCM.

Constrained Gaussian-duration solution inspired by Sinsy Eq. 16-17, extended
here with explicit bounds and exact integer sample totals. CPU score compiler;
HDL runtime needs only record fetch, counters, interpolation, and synthesis.
"""
from pathlib import Path
import json,math,random,unittest

def allocate(total,means,variances,lower,upper):
    n=len(means)
    if not n or any(len(x)!=n for x in (variances,lower,upper)):raise ValueError('shape')
    if any(v<=0 for v in variances):raise ValueError('positive variance required')
    if any(l<0 or l>u for l,u in zip(lower,upper)):raise ValueError('bounds')
    if total<sum(lower) or total>sum(upper):raise ValueError('note cannot fit phoneme bounds')
    lo=min((l-m)/v for l,m,v in zip(lower,means,variances))-1
    hi=max((u-m)/v for u,m,v in zip(upper,means,variances))+1
    for _ in range(80):
        mid=(lo+hi)/2
        d=[min(u,max(l,m+mid*v)) for m,v,l,u in zip(means,variances,lower,upper)]
        if sum(d)<total:lo=mid
        else:hi=mid
    d=[min(u,max(l,m+(lo+hi)/2*v)) for m,v,l,u in zip(means,variances,lower,upper)]
    out=[math.floor(x+1e-8) for x in d]
    remaining=total-sum(out)
    order=sorted(range(n),key=lambda i: (-(d[i]-out[i]),i))
    for i in order:
        if remaining and out[i]<upper[i]:out[i]+=1;remaining-=1
    if remaining:raise ArithmeticError('integer allocation failed')
    assert sum(out)==total and all(l<=d<=u for d,l,u in zip(out,lower,upper))
    return out

def example():
    fs=48000;bpm=96;quarter=round(fs*60/bpm)
    # Original demonstration words. This is a manually corrected phoneme plan,
    # not a claim of a complete Mandarin pronunciation lexicon.
    text=[('星',['x','i','ng'],[67]),('光',['g','u','ang'],[69,71]),
          ('照',['zh','ao'],[72]),('亮',['l','i','ang'],[71]),
          ('远',['y','uan'],[69,67]),('方',['f','ang'],[64])]
    time=fs;records=[];notes=[]
    for han,phones,pitches in text:
        length=quarter*len(pitches)
        n=len(phones);means=[.05*fs]+[length*.2]*(n-2)+[length*.7]
        variances=[(.012*fs)**2]+[(.035*fs)**2]*(n-2)+[(.10*fs)**2]
        lower=[round(.02*fs)]+[round(.025*fs)]*(n-1)
        upper=[round(.12*fs)]+[length]*(n-1)
        durations=allocate(length,means,variances,lower,upper)
        cursor=time
        for index,(ph,d) in enumerate(zip(phones,durations)):
            records.append({'syllable':han,'phoneme':ph,'start_sample':cursor,'duration_samples':d,
                            'voiced':ph not in ('x','g','zh','f'),'trajectory_id':'needs_licensed_or_self_designed_parameter_table'})
            cursor+=d
        for index,pitch in enumerate(pitches):
            notes.append({'start_sample':time+index*quarter,'duration_samples':quarter,'midi':pitch,
                          'syllable':han,'rearticulate_consonant':index==0})
        time+=length
    return {'scope':'control-only original phrase; no claim of intelligible rendered voice',
            'text':'星光照亮远方','fs':fs,'bpm':bpm,'pre_roll_samples':fs,'end_sample':time,
            'phonemes':records,'notes':notes,
            'limitations':['coarticulation trajectories and Mandarin parameter library remain to build',
                           'vowel-onset alignment must move initial consonants into available pre-roll',
                           'voiced flags are simplified design labels, not a linguistic ground-truth corpus']}

class Tests(unittest.TestCase):
    def test_unbounded_formula(self):
        self.assertEqual(allocate(100,[20,30],[1,4],[0,0],[100,100]),[30,70])
    def test_short_note_rejected(self):
        with self.assertRaises(ValueError):allocate(5,[4,4],[1,1],[3,3],[10,10])
    def test_clamped_consonant_and_vowel_extension(self):
        self.assertEqual(allocate(1000,[100,300],[1,1],[50,100],[120,2000]),[120,880])
    def test_random_bounds_exact_total(self):
        rng=random.Random(138)
        for _ in range(10000):
            n=rng.randrange(2,10);lo=[rng.randrange(0,100) for _ in range(n)]
            hi=[l+rng.randrange(1,2000) for l in lo];total=rng.randrange(sum(lo),sum(hi)+1)
            d=allocate(total,[rng.uniform(l,h) for l,h in zip(lo,hi)],
                       [rng.uniform(1,10000) for _ in lo],lo,hi)
            self.assertEqual(sum(d),total);self.assertTrue(all(l<=x<=h for x,l,h in zip(d,lo,hi)))
    def test_melisma_no_repeated_consonants(self):
        data=example();self.assertEqual(sum(n['rearticulate_consonant'] for n in data['notes']),6)
        self.assertEqual(sum(p['duration_samples'] for p in data['phonemes']),data['end_sample']-data['pre_roll_samples'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    root=Path(__file__).resolve().parent/'deep'
    (root/'song_control_example.json').write_text(json.dumps(example(),ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'song_timing_results.json').write_text(json.dumps({'scope':'CPU control compiler reference','tests':result.testsRun,'random_cases':10000,'failures':len(result.failures),'errors':len(result.errors)},indent=2))
    raise SystemExit(not result.wasSuccessful())
