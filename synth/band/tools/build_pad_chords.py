"""Export the FPGA guide pad ordering for the ESP32-C3 performance seat."""
from rehearsal_rom import BAND, FILES, load
from pathlib import Path

def write():
    rows = []
    for name in FILES:
        groups = {}
        for e in load(BAND / "assets" / (name+".json"))["events"]:
            if e["kind"]==0:
                groups.setdefault((e["part"],e["sample"]),[]).append(e["note"])
        parts=[]
        for part in range(16):
            chords=sorted({tuple(sorted(notes)) for (p,_),notes in groups.items() if p==part})
            assert len(chords)<=16 and all(len(c)<=4 for c in chords)
            parts.append("{"+",".join("{"+",".join(map(str,(len(c),*c)))+"}" for c in chords)+"}")
        rows.append("{"+",\n".join(parts)+"}")
    dest=BAND/"bridges/esp32c3_pad/src/rehearsal_pads.h"
    dest.write_text("// Generated from the five event scores by build_pad_chords.py.\n#pragma once\nstatic constexpr uint8_t chordPads[5][16][16][5]={\n"+",\n".join(rows)+"};\n")

if __name__=="__main__":
    write()
