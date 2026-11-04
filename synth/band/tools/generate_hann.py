"""Periodic Hann coefficients, unsigned Q15, inclusive exact unity at N/2."""
from pathlib import Path
import math
s=Path(__file__).resolve().parents[1]/'experimental/audio_visual'
for n in (16,512,2048):
 values=[round(32768*(0.5-0.5*math.cos(2*math.pi*i/n))) for i in range(n)]
 assert min(values)==0 and max(values)==32768
 (s/f'hann_{n}.mem').write_text('\n'.join(f'{v:04x}' for v in values)+'\n')
