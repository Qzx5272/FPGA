from pathlib import Path
import sys,dataclasses,struct,zlib
b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b/'host'))
from score import upload_events
from protocol import Event
s=dict(format='starcluster-score-1',sample_rate=48000,bpm=120,duration_samples=480,events=[
 dict(sample=0,kind=2,part=7,note=4,velocity=0,serial=1),
 dict(sample=10,kind=0,part=7,note=57,velocity=100,serial=2),
 dict(sample=250,kind=1,part=7,note=57,velocity=0,serial=2)])
events=list(upload_events(s))[:-1] # begin, nine words, commit
assert len(events)==11
events+=[Event(5)]+[dataclasses.replace(e,parameter=e.parameter^1) if i==0 else e for i,e in enumerate(events)]
raw=b''.join(e.encode() for e in events)
(b/'assets/upload_fixture.hex').write_text('\n'.join(f'{x:02x}' for x in raw)+'\n')
# Reproduce the independent storage-unit test's Python CRC vector as well.
words=[(4<<2)|(60<<6)|(100<<13),1,10,1|(4<<2)|(60<<6),1,900]
words.append(zlib.crc32(struct.pack('<6I',*words)))
(b/'assets/store_fixture.hex').write_text('\n'.join(f'{x:08x}' for x in words)+'\n')
