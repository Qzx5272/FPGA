"""Analytic ROM and independent analytic test vectors, not sampled audio."""
from pathlib import Path
import math,random,json
p=Path(__file__).resolve().parent/'deep'/'rtl';p.mkdir(exist_ok=True)
lut=[round(131071*math.sin(2*math.pi*i/4096)) for i in range(4096)]
maximum=max(abs(lut[(i+1)%4096]-lut[i]) for i in range(4096))
assert maximum<=202
(p/'sine4096.hex').write_text('\n'.join(f'{v&0x3ffff:05x}' for v in lut)+'\n')
quarter=[round(131071*math.sin(math.pi*i/2048)) for i in range(1025)]
(p/'sine_quarter.bin').write_text('\n'.join(f'{(quarter[i+1]<<17)|quarter[i]:034b}' for i in range(1024))+'\n')
r=random.Random(138)
phases=[0,1,0x3fffffff,0x40000000,0x40000001,0x7fffffff,0x80000000,0xbfffffff,0xc0000000,0xffffffff]
phases += [((i<<20)+j)&0xffffffff for i in range(4096) for j in (0,1,524288,1048575)]
phases += [r.getrandbits(32) for _ in range(100000)]
(p/'sine_vectors.txt').write_text('\n'.join(f'{v:08x} {round(131071*math.sin(2*math.pi*v/2**32))}' for v in phases)+'\n')
(p/'fixture_summary.json').write_text(json.dumps({'vectors':len(phases),'max_adjacent_delta':maximum,'seed':138,'oracle':'rounded analytic math.sin, independent of interpolation'},indent=2))
print('Generated',len(phases),'analytic vectors; max LUT delta',maximum)
