import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
try:
    from audit_pt8211_onboard import expected_clocks
finally:
    sys.path.pop(0)

class ClockProfileTests(unittest.TestCase):
    def test_source_constraint_pairing(self):
        hashes = ['9a4636932e77a4ccb38951684d901288dae3e69cf6a91fdd598158060924ecd7',
                  'b58db7ac2ef8fbd1942b158513faba8bc7b5fa296f5222e7b5ee0a1a5d328e0a']
        commands = ['create_generated_clock -name serial_clk -source [get_ports {clk}] '+r+
                    ' [get_pins {workstation/video_output/video_clocks/pll/CLKOUT0}]'
                    for r in ['-multiply_by 63 -divide_by 25', '-multiply_by 121 -divide_by 48']]
        for index in (0, 1):
            clocks = expected_clocks(hashes[index], [commands[index]], bool(index))
            self.assertAlmostEqual(clocks['display_clk'], clocks['serial_clk']*5)
            with self.assertRaises(ValueError):
                expected_clocks(hashes[index], [commands[1-index]], bool(index))
            with self.assertRaises(ValueError):
                expected_clocks(hashes[1-index], [commands[index]], bool(index))
            with self.assertRaises(ValueError):
                expected_clocks('unreviewed', [commands[index]], bool(index))
