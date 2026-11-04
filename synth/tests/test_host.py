import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from protocol import Controls,TelemetryParser

class ProtocolTests(unittest.TestCase):
    def test_state_packet(self):
        p=Controls(keys=255,attack_ms=1,release_ms=100).packet(19)
        self.assertEqual(len(p),15)
        self.assertEqual(p[:4],bytes([165,90,19,255]))
        self.assertEqual(int.from_bytes(p[9:11],'little'),1365)
        self.assertEqual(int.from_bytes(p[11:13],'little'),14)
        x=0
        for b in p[2:]:x^=b
        self.assertEqual(x,0)
    def test_partial_noise_and_checksum(self):
        body=bytes([3,255,8,1,2,1,1]);c=0
        for b in body:c^=b
        packet=b'\x5a\xa5'+body+bytes([c])
        parser=TelemetryParser()
        self.assertEqual(parser.feed(b'noise'+packet[:4]),[])
        r=parser.feed(packet[4:]);self.assertEqual(r[0]['voices'],8)
        self.assertEqual(r[0]['peak'],513)
        self.assertEqual(parser.feed(packet[:-1]+bytes([c^1])),[])
        self.assertEqual(len(parser.feed(packet)),1)

if __name__=='__main__':unittest.main()
