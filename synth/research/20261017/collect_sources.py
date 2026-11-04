"""Download public references for local study; retain failures and content hashes."""
import concurrent.futures, hashlib, json, re, urllib.request
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
from sources import PAPERS, PATENTS, PRODUCTS
ROOT = Path(__file__).resolve().parent
class Plain(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip=0; self.text=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip+=1
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self, data):
        if not self.skip and data.strip(): self.text.append(data.strip())
def collect(item):
    key,url=item; entry={'id':key,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research reference archiving)'})
        with urllib.request.urlopen(req,timeout=30) as response:
            data=response.read(25000000); entry['resolved_url']=response.url
        pdf=data.startswith(b'%PDF'); path=ROOT/'cache'/(key+('.pdf' if pdf else '.html'))
        path.write_bytes(data); entry.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),file=str(path.relative_to(ROOT)))
        if pdf:
            from pypdf import PdfReader
            pages=PdfReader(path).pages
            plain='\n'.join(f'=== PAGE {i+1} ===\n'+p.extract_text() for i,p in enumerate(pages)); entry['pages']=len(pages)
        else:
            parser=Plain(); parser.feed(data.decode('utf-8',errors='replace')); plain='\n'.join(parser.text)
        (ROOT/'text'/(key+'.txt')).write_text(plain,encoding='utf-8'); entry['text_characters']=len(plain); entry['status']='downloaded_not_automatically_read'
    except Exception as error: entry.update(status='failed',error=str(error))
    return entry
if __name__=='__main__':
    (ROOT/'cache').mkdir(exist_ok=True); (ROOT/'text').mkdir(exist_ok=True)
    urls=[(r[0],r[6]) for r in PAPERS]+[(r[0],r[3]) for r in PATENTS]+[(r[0],r[2]) for r in PRODUCTS]
    urls += [('R01','https://www.gowinsemi.com.cn/university/match2026')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(collect,urls))
    (ROOT/'download_manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in x.items() if k in ('id','status','bytes','pages','error')} for x in results],ensure_ascii=False,indent=2))
