"""Known Gowin readmemh limitation; structural guard, not netlist verification."""
from pathlib import Path
import re

def check_vocoder_rom(path):
    path=Path(path)
    source=path.read_text(encoding='utf-8')
    declaration=re.search(r'\bCOEFFS\s*((?:\[[^\]]+\]\s*)+);',source)
    if not declaration or len(re.findall(r'\[[^\]]+\]',declaration[1]))!=1:
        raise ValueError('Vocoder coefficient ROM must be one-dimensional: Gowin1.9.12.03 misloads the original2D readmemh array. Use explicit row*10+column;post-synthesis numeric validation is still required.')
    core=path.parent/'vocoder_core.sv'
    if core.is_file():
        width=re.search(r'\.COEFF_WIDTH\((\d+)\)',core.read_text(encoding='utf-8'))
        if width:
            coeff=path.parent/'coeffs.mem'
            if not coeff.is_file():coeff=path.parent.parent/'coeffs.mem'
            check_coefficient_width(coeff,int(width[1]))

def check_coefficient_width(path,width):
    if not 1<=width<=32:raise ValueError('Invalid coefficient width')
    values=[int(x,16) for x in Path(path).read_text(encoding='ascii').split()]
    if not values:raise ValueError('Empty coefficient file')
    for i,raw in enumerate(values):
        value=raw if raw<2**31 else raw-2**32
        if not 0<=raw<2**32 or not -(1<<(width-1))<=value<(1<<(width-1)):
            raise ValueError(f'Coefficient {i} does not fit signed {width} bits; refusing lossy truncation')

if __name__=='__main__':
    check_vocoder_rom(Path(__file__).resolve().parent/'rtl/filterbank.sv')
    print('Flat coefficient ROM declaration checked;not functional/timing acceptance')
