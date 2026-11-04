"""V4 event wire format. Incompatible with the old V2 bitmap protocol."""
from dataclasses import dataclass
import struct,zlib
HEADER=b'\xb4\x4b'
UART_GUARD_BYTES=64
UART_BATCH_SIZE=4  # GUI pumps every 5 ms: at most 800 events/s.
@dataclass(frozen=True)
class Event:
    kind:int
    source:int=1
    part:int=0
    contact:int=0
    note:int=60
    velocity:int=100
    flags:int=0
    epoch:int=1
    serial:int=0
    sample:int=0
    parameter:int=0
    def encode(self):
        if self.kind not in (0,1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,20,21,22,23,127):raise ValueError('Unsupported event')
        if not 0<=self.source<255 or not 0<=self.part<16 or not 0<=self.contact<256:raise ValueError('Invalid identity')
        if not 0<=self.note<128 or not 0<=self.velocity<128 or not 0<=self.flags<256:raise ValueError('Invalid control')
        if self.sample!=0:raise ValueError('Scheduled external events are not implemented yet; use immediate sample=0')
        body=struct.pack('<8BIIQI',4,self.kind,self.source,self.part,self.contact,self.note,self.velocity,self.flags,self.epoch,self.serial,self.sample,self.parameter)
        return HEADER+body+struct.pack('<I',zlib.crc32(body))
    def encode_uart(self):
        """Out-of-frame zero guard bytes: 640 us at 1 Mbaud, 8N1.

        The current board link truncates reply tails under gapless requests.
        Keep encode() as the canonical 34-byte CRC frame for fixtures/storage.
        The FPGA ignores these zeros while searching for the next header.
        """
        return self.encode()+bytes(UART_GUARD_BYTES)

class Decoder:
    def __init__(self):self.buffer=bytearray();self.bad_crc=0
    def feed(self,data):
        self.buffer.extend(data);out=[]
        while len(self.buffer)>=2:
            i=self.buffer.find(HEADER)
            if i<0:
                self.buffer[:]=self.buffer[-1:] if self.buffer[-1:]==HEADER[:1] else b'';break
            del self.buffer[:i]
            if len(self.buffer)<34:break
            raw=bytes(self.buffer[2:34])
            if zlib.crc32(raw[:28])!=int.from_bytes(raw[28:],'little') or raw[0]!=4:
                self.bad_crc+=1;del self.buffer[0];continue
            del self.buffer[:34];out.append(raw)
        return out

def status(raw):
    if len(raw)!=32 or raw[0]!=4 or raw[1] not in (128,129,144,145):raise ValueError('Not V4 telemetry')
    return dict(profile='diagnostic' if raw[1]&16 else 'band',playing=bool(raw[1]&1),owner=raw[2],part=raw[3],voices=int.from_bytes(raw[4:6],'little'),cycles=int.from_bytes(raw[6:8],'little'),
        epoch=int.from_bytes(raw[8:12],'little'),song_sample=int.from_bytes(raw[12:16],'little'),rejected=int.from_bytes(raw[16:20],'little'),
        deadline_miss=int.from_bytes(raw[20:24],'little'),clips=int.from_bytes(raw[24:28],'little'))

def singer_status(raw):
    """Decode CRC-checked 0xA2 reply. Gate is held-note state, not loudness."""
    if len(raw)!=32 or raw[0]!=4 or raw[1]!=162:raise ValueError('Not singer telemetry')
    return dict(gate=bool(raw[2]&1),note=raw[3],dropped=int.from_bytes(raw[4:8],'little'),
        stale_off=int.from_bytes(raw[8:12],'little'),dac_dropped=int.from_bytes(raw[12:16],'little'),
        dac_underruns=int.from_bytes(raw[16:20],'little'))


def captured_event(raw):
    """CRC-checked expansion telemetry. Its sample field carries capture ticks."""
    if len(raw)!=32 or raw[0]!=4 or ((raw[1]&0xe0)!=0xc0 and raw[1]!=0xe0):raise ValueError('不是事件回传')
    version,kind,source,part,contact,note,velocity,flags,epoch,serial,ticks,parameter=struct.unpack('<8BIIQI',raw[:28])
    event=Event(127 if kind==0xe0 else kind&31,source,part,contact,note,velocity,flags,epoch,serial,0,parameter)
    if event.kind not in (0,1,2,7,10,11,15,16,127):raise ValueError('事件回传类型非法')
    event.encode()
    return event,ticks
