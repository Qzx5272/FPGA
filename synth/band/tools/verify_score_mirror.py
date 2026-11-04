"""Compare host mirror with the five native RTL raster fixtures."""
from pathlib import Path
import sys,math
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from score_mirror import Artwork

def verify(build):
    art=Artwork(build)
    left=sum((32+int(22*math.sin(i*.22)))<<(6*i) for i in range(64))
    right=sum((32+int(17*math.sin(i*.22+.7)))<<(6*i) for i in range(64))
    bands=sum((15 if i==9 else 10 if i==15 else i%4)<<(4*i) for i in range(32))
    look=(1<<31)|(4<<27)|(67<<20)|(20<<15)|(18<<8)|2
    visual=(look<<948)|(bands<<820)|(left<<436)|(right<<52)|(22<<46)|(36<<40)|(((32<<21)+(64<<14)+(80<<7)+64)<<12)|(22<<3)
    for page in range(5):
        s=1+(64<<1)+(120<<8)+(4<<16)+(60<<32)+(100<<39)+(4<<46)+((3 if page==4 else page)<<107)+((3 if page==4 else 2)<<109)
        s+=(1024<<67)+(7<<81)+((110 if page==4 else 100)<<117)
        if page==4:s+=(1<<97)+(4<<93)
        diff=ImageChops.difference(art.render(s,visual),Image.open(build/f'ui_page_{page}.png').convert('RGB'))
        print(page,diff.getbbox());assert not diff.getbbox()
if __name__=='__main__':verify(Path(sys.argv[1]))
