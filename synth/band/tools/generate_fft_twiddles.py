"""Generate deterministic signedQ17 exp(-j*2*pi*k/N) coefficients, not audio."""
from pathlib import Path
import math
b=Path(__file__).resolve().parents[1]/'experimental/audio_visual'
for n in (16,512,2048):
 values=[]
 for k in range(n//2):
  real=max(-131072,min(131071,round(131072*math.cos(2*math.pi*k/n))))
  imag=max(-131072,min(131071,round(-131072*math.sin(2*math.pi*k/n))))
  values.append(f'{((real&0x3ffff)<<18)|(imag&0x3ffff):09x}')
 (b/f'fft_twiddle_{n}.mem').write_text('\n'.join(values)+'\n')
