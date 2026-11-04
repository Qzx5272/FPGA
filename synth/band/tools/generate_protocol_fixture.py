import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'host'))
from protocol import Event,Decoder
packets=[Event(0,source=2,part=6,contact=180,note=69,velocity=111,epoch=123,serial=456).encode(),Event(127).encode()]
(root/'assets/protocol_fixture.hex').write_text('\n'.join(f'{b:02x}' for p in packets for b in p)+'\n')
d=Decoder();assert not d.feed(b'junk'+packets[0][:13]);assert d.feed(packets[0][13:])==[packets[0][2:]]
bad=bytearray(packets[0]);bad[10]^=1;assert d.feed(bad+packets[1])==[packets[1][2:]];assert d.bad_crc==1
print('PASS Python protocol CRC, split input, noise and resynchronization')
board=[Event(4,source=1,part=4,flags=0),Event(0,part=4,note=69,epoch=2,serial=1),Event(1,part=4,note=69,velocity=0,epoch=2,serial=1),Event(5),Event(5,flags=1),Event(127),Event(18)]
(root/'assets/board_fixture.hex').write_text('\n'.join(f'{b:02x}' for e in board for b in e.encode())+'\n')
