"""Offline pronunciation lookup. No audio synthesis and no serial output."""
import argparse
import json
from pathlib import Path
import sqlite3
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
TONES = {'\u0304': 1, '\u0301': 2, '\u030c': 3, '\u0300': 4}

def normalize(reading):
    tone = 5
    letters = []
    for char in unicodedata.normalize('NFD', reading.lower()):
        if char in TONES:
            tone = TONES[char]
        else:
            letters.append(char)
    base = unicodedata.normalize('NFC', ''.join(letters))
    return {'marked': reading, 'syllable': base, 'tone': tone,
            'numbered': base + str(tone)}

def lookup(text, db=None):
    connection = sqlite3.connect(db or ROOT / 'generated' / 'lexicon.sqlite3')
    output = []
    try:
        max_len = connection.execute('SELECT max(length(word)) FROM phrases').fetchone()[0] or 1
        pos = 0
        while pos < len(text):
            matched = False
            for length in range(min(max_len, len(text)-pos), 1, -1):
                word = text[pos:pos+length]
                row = connection.execute('SELECT readings FROM phrases WHERE word=?', (word,)).fetchone()
                if row:
                    alternatives = json.loads(row[0])
                    output.append({'text': word, 'offset': pos, 'source': 'phrase',
                                   'readings': [[normalize(p) for p in r] for r in alternatives],
                                   'needs_review': len(alternatives) > 1})
                    pos += length
                    matched = True
                    break
            if matched:
                continue
            char = text[pos]
            row = connection.execute('SELECT readings FROM characters WHERE character=?', (char,)).fetchone()
            if row:
                readings = json.loads(row[0])
                output.append({'text': char, 'offset': pos, 'source': 'character',
                               'readings': [[normalize(p)] for p in readings],
                               'needs_review': len(readings) > 1})
            else:
                category = unicodedata.category(char)
                pause = char.isspace() or category.startswith('P')
                output.append({'text': char, 'offset': pos, 'source': 'pause' if pause else 'unknown',
                               'readings': [], 'needs_review': not pause})
            pos += 1
    finally:
        connection.close()
    return {'text': text, 'method': 'longest phrase match; ambiguous character readings preserved',
            'acoustic_parameters_ready': False, 'tokens': output}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('text')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(lookup(args.text), ensure_ascii=False, indent=2)+'\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result)
