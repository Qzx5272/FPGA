from pathlib import Path
import pypdfium2 as pdfium
from pypdf import PdfReader
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]
path=ROOT/'output/pdf/ORCHESTRA138_V3_FPGA_Engineering.pdf'
dest=ROOT/'tmp/pdfs/orchestra_v3';dest.mkdir(parents=True,exist_ok=True)
doc=pdfium.PdfDocument(str(path));reader=PdfReader(path)
print('pages',len(doc))
thumbs=[]
for i,page in enumerate(doc):
 im=page.render(scale=.6).to_pil().convert('RGB');im.thumbnail((298,421))
 tile=Image.new('RGB',(318,450),'#e8edf0');tile.paste(im,((318-im.width)//2,8));ImageDraw.Draw(tile).text((12,431),str(i+1),fill='black')
 thumbs.append(tile)
 text=reader.pages[i].extract_text()
 print(i+1,len(text),text[:45].replace('\n',' '))
 if len(text)<190:print('SPARSE',i+1)
for start in range(0,len(thumbs),12):
 sheet=Image.new('RGB',(954,1800),'white')
 for k,tile in enumerate(thumbs[start:start+12]):sheet.paste(tile,((k%3)*318,(k//3)*450))
 sheet.save(dest/f'current_{start//12+1}.png')
