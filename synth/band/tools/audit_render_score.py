"""Decode the actual boot event memory and compare it to the rendered project."""
from pathlib import Path
import argparse
import hashlib
import json
import re


def audit(export):
    score = json.loads((export / 'project.json').read_text(encoding='utf-8'))
    rtl = export / 'rtl'
    storage = (rtl / 'song_storage_init.vh').read_text()
    pattern = r"controls\[(\d+)\]=32'h([0-9a-fA-F]+);identities\[(\d+)\]=32'd(\d+);times\[(\d+)\]=32'd(\d+);"
    matches = list(re.finditer(pattern, storage))
    if re.sub(pattern, '', storage).strip():
        raise ValueError('Unrecognized boot-memory statement')
    decoded = []
    for index, match in enumerate(matches):
        ci, control, ii, serial, ti, sample = match.groups()
        if (int(ci), int(ii), int(ti)) != (index, index, index):
            raise ValueError('Noncontiguous or inconsistent boot-memory address')
        c = int(control, 16)
        if c >> 20:
            raise ValueError('Reserved control bits set')
        decoded.append(dict(sample=int(sample), serial=int(serial), kind=c & 3,
                            part=(c >> 2) & 15, note=(c >> 6) & 127,
                            velocity=(c >> 13) & 127))
    if decoded != score['events']:
        raise ValueError('Project and actual boot event memory differ')
    config = (rtl / 'song_config.vh').read_text()
    for name, expected in [('SONG_EVENTS', len(decoded)), ('SONG_LENGTH', score['duration_samples'])]:
        values = re.findall(r'`define\s+' + name + r'\s+(\d+)', config)
        if values != [str(expected)]:
            raise ValueError('Boot score size mismatch: ' + name)
    store = (rtl / 'song_store.v').read_text()
    if store.count('`include "song_storage_init.vh"') != 1:
        raise ValueError('Boot memory include missing or duplicated')
    singer = [e for e in decoded if e['part'] == 15 and e['kind'] == 0]
    files = [export / 'project.json', rtl / 'song_storage_init.vh', rtl / 'song_config.vh', rtl / 'song_store.v']
    return dict(status='passed_score_memory_identity', export=str(export.resolve()),
                events=len(decoded), singer_note_ons=len(singer),
                first_singer_sample=singer[0]['sample'] if singer else None,
                source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                scope='Decoded boot event array equals project events; not playback, timing or sound acceptance')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = audit(args.export)
    if args.report.exists():
        raise ValueError('Preserve existing evidence')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
