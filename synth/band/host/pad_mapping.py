"""Validated per-seat MIDI pad maps; legacy maps remain a shared fallback."""
import json
import os
import tempfile
from pathlib import Path

def normalize_mapping(value):
    if not isinstance(value, dict):raise ValueError('Pad mapping must be an object')
    result={}
    for note,pad in value.items():
        try:key=int(note)
        except (ValueError,TypeError):raise ValueError('Invalid MIDI note') from None
        if isinstance(note,bool) or (not isinstance(note,(str,int))) or not 0<=key<128 or type(pad) is not int or not 0<=pad<16 or key in result:
            raise ValueError('Invalid or duplicate pad mapping')
        result[key]=pad
    return result

def normalize_seats(value):
    if not isinstance(value,dict):raise ValueError('Seat mappings must be an object')
    result={}
    for seat,mapping in value.items():
        try:key=int(seat)
        except (ValueError,TypeError):raise ValueError('Invalid seat') from None
        if isinstance(seat,bool) or not isinstance(seat,(str,int)) or key not in (1,2,3,4) or key in result:
            raise ValueError('Invalid or duplicate seat')
        result[key]=normalize_mapping(mapping)
    return result

def read_maps(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data,dict) and data.get('version')==2:
        return normalize_mapping(data['default']),normalize_seats(data['seats'])
    return normalize_mapping(data),{}

def save_maps(path,default,seats):
    data=dict(version=2,default=normalize_mapping(default),seats=normalize_seats(seats))
    path=Path(path)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
