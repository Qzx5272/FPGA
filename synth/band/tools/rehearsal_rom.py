"""Emit five on-chip event scores. The first note of each simultaneous chord
carries its cue flag and pad index in the otherwise unused high serial bits.
Note-on and note-off retain identical identities throughout the allocator.
"""
from pathlib import Path
import struct
import zlib
from build_rehearsal import BAND, FILES, load

def emit(out):
    words, descriptions = [], []
    for index, name in enumerate(FILES):
        score = load(BAND / "assets" / (name + ".json"))
        groups = {}
        for event in score["events"]:
            if event["kind"] == 0:
                groups.setdefault((event["part"],event["sample"]), []).append(event)
        tags = {}
        for part in range(16):
            chords = [g for (v,_),g in groups.items() if v == part]
            signature = lambda g: tuple(sorted(e["note"] for e in g))
            pads = sorted(set(map(signature,chords)))
            assert len(pads)<=16
            for g in chords:
                tags[g[0]["serial"]] = (1<<31) | pads.index(signature(g))<<27
        data=[]
        bpm=score.get("performance",{}).get("tempo",120)
        timing=lambda sample: round(sample*120/bpm)
        for e in score["events"]:
            assert 0<e["serial"]<1<<27
            data.extend([e["kind"] | e["part"]<<2 | e["note"]<<6 | e["velocity"]<<13,
                         e["serial"]|tags.get(e["serial"],0),timing(e["sample"])])
        duration=timing(score["duration_samples"])
        if index==0:
            (out/"rtl/song_config.vh").write_text(f"`define SONG_EVENTS {len(data)//3}\n`define SONG_LENGTH {duration}\n")
            (out/"rtl/song_storage_init.vh").write_text("".join(f"controls[{i}]=32'h{c:08x};identities[{i}]=32'h{s:08x};times[{i}]=32'd{t};\n" for i,(c,s,t) in enumerate(zip(data[::3],data[1::3],data[2::3]))))
        crc=zlib.crc32(struct.pack(f"<{len(data)}I",*data))
        descriptions.append(f"{index}:library_description={{32'd{len(words)},32'd{len(data)},32'd{duration},32'd{crc}}};")
        words.extend(data)
    (out/"song_library_words.mem").write_text("".join(f"{w:08x}\n" for w in words))
    (out/"rtl/song_library_config.vh").write_text(f"localparam LIBRARY_WORDS={len(words)},LIBRARY_SONGS={len(FILES)};\nfunction[127:0]library_description;input[7:0]song;begin case(song)\n"+"\n".join(descriptions)+"\ndefault:library_description=0;endcase end endfunction\n")
