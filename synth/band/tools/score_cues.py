"""Per-part cue lookahead from the exact ROM note groups used by the C3."""
from rehearsal_rom import BAND,FILES,load
def make(out):
    records=[]
    cases=[]
    for song,name in enumerate(FILES):
        score=load(BAND/'assets'/(name+'.json'))
        groups={}
        for e in score['events']:
            if e['kind']==0:
                groups.setdefault((e['part'],e['sample']),[]).append(e['note'])
        bpm=score.get('performance',{}).get('tempo',120)
        for part in range(16):
            events=[(round(t*120/bpm),tuple(sorted(notes))) for (v,t),notes in groups.items() if v==part]
            if not events:continue
            pads=sorted({c for t,c in events})
            cases.append(f"7'd{song*16+part}:range_info={{12'd{len(records)},12'd{len(events)}}};")
            for i,(t,c) in enumerate(events):
                p=pads.index(c)
                nxt=0 if i+1==len(events) else 16+pads.index(events[i+1][1])
                records.append((t<<16)|(p<<12)|(min(c)<<5)|nxt)
    assert len(records)<4096
    (out/'score_cues.mem').write_text(''.join(f'{r:010x}\n' for r in records))
    (out/'rtl/cue_ranges.vh').write_text('localparam CUE_WORDS='+str(len(records))+';\nfunction[23:0]range_info(input[6:0]part); begin case(part)\n'+'\n'.join(cases)+'\ndefault:range_info=0;endcase end endfunction\n')
