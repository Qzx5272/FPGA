"""Compare congestion failures and timing failures from actual Gowin reports."""
import argparse
from collections import Counter
from pathlib import Path
import re

def inspect(b):
    p=b/'impl/pnr'
    log=(p/'integrated.log').read_text(errors='replace') if (p/'integrated.log').exists() else ''
    physical=p/'integrated.rpt.txt'
    resources={}
    if physical.exists():
        for key in ('Logic','BSRAM','DSP'):
            m=re.search(r'^\s*'+key+r'\s*\|\s*([\d./]+)\s*\|',physical.read_text(),re.M)
            if m:resources[key]=m[1]
    timing=p/'integrated_tr_content.html'
    failed=re.findall(r'(\d+) unrouted nets',log)
    if failed:return [b.name,'布线失败',failed[-1],'—','—','—',*map(lambda k:resources.get(k,'—'),('Logic','BSRAM','DSP'))],None
    if not timing.exists():
        driver=(b/'build.log').read_text(errors='replace') if (b/'build.log').exists() else ''
        shortage=re.search(r'number\((\d+)\) of (\w+) .*resource limit\((\d+)\)',driver,re.I)
        status=(f'{shortage[2]} 超额 {shortage[1]}/{shortage[3]}' if shortage else
                '实现失败' if re.search(r'ERROR +\(',driver) else '尚无最终报告')
        return [b.name,status,'—','—','—','—','—','—','—'],None
    t=timing.read_text()
    counts=[re.search('Numbers of '+k+r' Violated Endpoints\s*</td>\s*<td[^>]*>\s*(\d+)',t)[1] for k in ('Setup','Hold')]
    paths=[q.strip().splitlines() for q in (p/'integrated.timing_paths').read_text().split('=====') if q.strip()]
    top=[v for v in paths if v[0]=='SETUP']
    def modules(v):
        nodes=[s for s in v[4:] if '/' in s]
        return nodes[0].rsplit('/',1)[0]+' → '+nodes[-1].rsplit('/',1)[0]
    groups=Counter(modules(q) for q in top)
    return [b.name,'时序违规' if counts!=['0','0'] else '时序通过','0',*counts,top[0][1],*map(lambda k:resources.get(k,'—'),('Logic','BSRAM','DSP'))],groups

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('builds',nargs='+',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    rows=[];details=[]
    for b in a.builds:
        row,groups=inspect(b);rows.append(' | '.join(row))
        if groups:details.append('**'+b.name+'**\n\n'+'\n'.join('- '+k+'，'+str(n)+' 条' for k,n in groups.most_common(3)))
    a.out.write_text('# Gowin 布线与时序核查\n\n| 构建 | 状态 | 未布通网络 | Setup 违规端点 | Hold 违规端点 | 最差 Setup 余量/ns | Logic | BSRAM | DSP |\n|---|---|---:|---:|---:|---:|---|---|---|\n'+'\n'.join('| '+r+' |' for r in rows)+'\n\n## 最差路径分布\n\n每份报告仅统计列出的最差路径，不能据此推算全部违规端点的分布。\n\n'+'\n\n'.join(details)+'\n',encoding='utf8')
