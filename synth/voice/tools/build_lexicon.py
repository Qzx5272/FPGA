"""Build local SQLite lexicon and an auditable eSpeak Mandarin reference index."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from lexicon import ROOT, normalize

def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def entries(path):
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = line.split('#', 1)[0].strip()
        if line:
            key, value = line.split(':', 1)
            yield number, key.strip(), value.strip()

def main():
    locks = json.loads((ROOT/'sources.lock.json').read_text(encoding='utf-8'))
    verified = 0
    for source in locks:
        base = ROOT/'sources'/source['repository'].rsplit('/', 1)[1]
        for item in source['files']:
            assert hashlib.sha256((base/item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
            verified += 1
    out = ROOT/'generated'
    out.mkdir(exist_ok=True)
    chars, phrases, syllables = {}, {}, set()
    for _, key, value in entries(ROOT/'sources/pinyin-data/pinyin.txt'):
        char = chr(int(key.removeprefix('U+'), 16))
        chars[char] = value.split(',')
        syllables.update(chars[char])
    for line, word, value in entries(ROOT/'sources/phrase-pinyin-data/pinyin.txt'):
        reading = value.split()
        if len(reading) != len(word):
            raise ValueError(f'Phrase alignment error line {line}: {word}')
        alternatives = phrases.setdefault(word, [])
        if reading not in alternatives:
            alternatives.append(reading)
        syllables.update(reading)
    con = sqlite3.connect(out/'lexicon.sqlite3')
    with con:
        con.execute('DROP TABLE IF EXISTS characters')
        con.execute('DROP TABLE IF EXISTS phrases')
        con.execute('CREATE TABLE characters(character TEXT PRIMARY KEY, readings TEXT NOT NULL)')
        con.execute('CREATE TABLE phrases(word TEXT PRIMARY KEY, readings TEXT NOT NULL)')
        con.executemany('INSERT INTO characters VALUES (?,?)', [(k,json.dumps(v,ensure_ascii=False)) for k,v in chars.items()])
        con.executemany('INSERT INTO phrases VALUES (?,?)', [(k,json.dumps(v,ensure_ascii=False)) for k,v in phrases.items()])
    assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    con.close()
    save(out/'syllables.json', [normalize(p) for p in sorted(syllables)])
    cmn = ROOT/'sources/espeak-ng/phsource/ph_cmn'
    data = cmn.read_text(encoding='utf-8')
    blocks = []
    for match in re.finditer(r'^phoneme\s+(\S+)(.*?)^endphoneme', data, re.M | re.S):
        body = match.group(2)
        refs = re.findall(r'\b(FMT|WAV|VowelStart|VowelEnding|AddWav)\s*\(\s*([^,)\s]+)', body)
        blocks.append({'phoneme': match.group(1), 'line': data[:match.start()].count('\n')+1,
                       'references': [{'kind':kind, 'asset':asset} for kind,asset in refs],
                       'uses_recorded_sample_directly': any(kind in ('WAV','AddWav') for kind,_ in refs),
                       'body':body.strip(), 'fpga_ready':False})
    save(out/'mandarin_phoneme_reference.json', {'source':'sources/espeak-ng/phsource/ph_cmn',
         'warning':'Reference only. Imports and calls need transitive review. No FPGA coefficients generated.',
         'phonemes':blocks})
    report = {'verified_source_files':verified,'characters':len(chars),'phrases':len(phrases),
              'marked_readings':len(syllables),'mandarin_phoneme_blocks':len(blocks),
              'direct_sample_blocks':sum(b['uses_recorded_sample_directly'] for b in blocks),
              'acoustic_parameters_ready':False}
    save(out/'validation.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
