"""Version 2 controls: flags carry panic, board transport and tempo; no host audio."""
from dataclasses import dataclass
import struct

BAUD = 115200
SAMPLE_RATE = 48000


@dataclass
class Controls:
    keys: int = 0
    octave: int = 4
    tone: int = 0
    brightness: int = 80
    volume: int = 127
    velocity: int = 100
    attack_ms: int = 15
    release_ms: int = 350
    auto_play: bool = False
    bpm: int = 96

    def packet(self, sequence: int, panic: bool = False) -> bytes:
        attack = max(1, min(65535, round(65535 / (SAMPLE_RATE * self.attack_ms / 1000))))
        release = max(1, min(65535, round(65535 / (SAMPLE_RATE * self.release_ms / 1000))))
        body = bytes([sequence & 255, self.keys & 255, max(2, min(6, self.octave)),
                      max(0, min(3, self.tone)), self.brightness & 255,
                      max(0, min(127, self.volume)), max(0, min(127, self.velocity))])
        flags = int(panic) | (int(self.auto_play and not panic) << 1) | (max(0,min(63,(self.bpm-40)//2)) << 2)
        body += struct.pack('<HHB', attack, release, flags)
        checksum = 0
        for b in body:
            checksum ^= b
        return b'\xa5\x5a' + body + bytes([checksum])


class TelemetryParser:
    """Fixed 10-byte replies: 5A A5 seq keys voices peak_lo peak_hi flags version xor."""
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        result = []
        while len(self.buffer) >= 10:
            if self.buffer[:2] != b'\x5a\xa5':
                del self.buffer[0]
                continue
            p = self.buffer[:10]
            c = 0
            for b in p[2:9]:
                c ^= b
            if c != p[9]:
                del self.buffer[0]
                continue
            del self.buffer[:10]
            result.append(dict(sequence=p[2], keys=p[3], voices=p[4],
                               peak=p[5] | p[6] << 8, flags=p[7], version=p[8]))
        return result
