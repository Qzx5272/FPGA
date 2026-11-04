"""Deterministic fixed-point bend and additive vowel formant tables."""
from pathlib import Path
import math
rtl=Path(__file__).resolve().parents[1]/'rtl'
lines=['function [20:0] bend_ratio;','input [7:0] bend;','begin case(bend)']
for n in range(256):lines.append(f"8'd{n}:bend_ratio=21'd{round(2**(((n-128)/64)/12)*(1<<20))};")
lines+=['endcase end endfunction'];(rtl/'bend_ratio.vh').write_text('\n'.join(lines)+'\n')
formants=[(730,1090,2440),(530,1840,2480),(270,2290,3010),(570,840,2410),(300,870,2240)]
lines=['function [20:0] vowel_harmonics;','input [6:0] note;input [2:0] vowel;','begin case({vowel,note})']
for v,fs in enumerate(formants):
 for n in range(128):
  f0=440*2**((n-69)/12);h=[max(1,min(127,round(f/f0))) for f in fs]
  packed=h[0]|h[1]<<7|h[2]<<14
  lines.append(f"10'd{v*128+n}:vowel_harmonics=21'd{packed};")
lines+=['default:vowel_harmonics={7\'d10,7\'d5,7\'d3};','endcase end endfunction']
(rtl/'vowel_harmonics.vh').write_text('\n'.join(lines)+'\n')
