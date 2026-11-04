from pathlib import Path
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
import shutil

root=Path(__file__).parent
out=root/'output'/'latex'
out.mkdir(exist_ok=True)
shutil.copyfile(root/'assets/official_top.png',out/'official_top.png')
doc=Document(root/'output/Tang_Mega_138K_Pro_开发指南.docx')
def esc(s):
    mp={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}','→':r'\(\rightarrow\)','↓':r'\(\downarrow\)','≥':r'\(\geq\)'}
    return ''.join(mp.get(c,c) for c in s)
def text(s):
    lines=[]
    for line in s.splitlines():
        bits=re.split(r'(https?://\S+)',line)
        lines.append(''.join(r'\url{'+b+'}' if b.startswith(('https://','http://')) else esc(b) for b in bits))
    return r'\newline '.join(lines)
parts=[r'''% !TeX program = xelatex
% Compile with XeLaTeX twice. Keep official_top.png beside this file.
\documentclass[UTF8,a4paper,zihao=5,fontset=fandol]{ctexart}
\usepackage[margin=20mm,top=19mm,bottom=20mm]{geometry}
\usepackage{graphicx,booktabs,longtable,array,xcolor,amsmath,fancyhdr,fvextra,tikz}
\usepackage[unicode,hidelinks]{hyperref}
\usetikzlibrary{arrows.meta,positioning}
\definecolor{tablehead}{HTML}{DDE8EF}
\usepackage{colortbl}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\setlength{\headheight}{15pt}
\renewcommand{\arraystretch}{1.24}
\setlength{\tabcolsep}{5pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small Tang Mega 138K Pro 开发与时序入门}
\fancyfoot[R]{\small Tang Mega 138K Pro\quad|\quad\thepage}
\renewcommand{\headrulewidth}{0pt}
\hypersetup{pdftitle={Tang Mega 138K Pro 开发指南}}
\setcounter{secnumdepth}{0}
\emergencystretch=2em
\begin{document}
''']
for el in doc.element.body:
    if el.tag==qn('w:tbl'):
        t=Table(el,doc)
        widths=[c.width.cm for c in t.columns]
        total=sum(widths)
        specs=''.join('>{\\raggedright\\arraybackslash}p{'+f'{(17.0-.36*len(widths))*w/total:.2f}cm'+'}' for w in widths)
        parts.append(r'\begingroup\small'+'\n'+r'\begin{longtable}{'+specs+'}\n'+r'\toprule'+'\n')
        for j,row in enumerate(t.rows):
            cells=[text(c.text).replace('\n',r'\newline ') for c in row.cells]
            if j==0:
                parts.append(r'\rowcolor{tablehead} '+' & '.join(r'\textbf{'+c+'}' for c in cells)+r'\\\midrule'+'\n'+r'\endfirsthead'+'\n')
                parts.append(r'\toprule\rowcolor{tablehead} '+' & '.join(r'\textbf{'+c+'}' for c in cells)+r'\\\midrule\endhead'+'\n')
            else:parts.append(' & '.join(cells)+r'\\'+'\n')
        parts.append(r'\bottomrule\end{longtable}\endgroup'+'\n')
        continue
    if el.tag!=qn('w:p'):continue
    pa=Paragraph(el,doc);s=pa.text.strip()
    if el.xpath('.//w:drawing'):
        parts.append(r'\begin{center}\includegraphics[width=\linewidth]{official_top.png}\end{center}'+'\n');continue
    if not s:continue
    style=pa.style.name
    if style=='Title':parts.append(r'{\LARGE\bfseries '+esc(s).replace('\n',r'\\[4pt]')+r'\par}\vspace{5pt}'+'\n');continue
    if style=='Subtitle':parts.append(r'{\large '+text(s)+r'\par}'+'\n');continue
    if style.startswith('Heading'):
        if pa.paragraph_format.page_break_before:parts.append(r'\clearpage'+'\n')
        cmd='section' if style=='Heading 1' else 'subsection'
        parts.append('\\'+cmd+'{'+esc(s)+'}\n');continue
    if s.startswith('阅读顺序：'):
        s='阅读顺序：先对照实物图识别接口，再阅读第二部分的开发环境，最后从第三部分理解运行流程。逻辑门与时序的专门说明见第 3.2 至 3.5 节。'
    if s.startswith('发送寄存器 Q'):
        parts.append(r'''\begin{center}
\begin{tikzpicture}[node distance=6mm,block/.style={draw,rounded corners=2pt,align=center,minimum height=10mm,font=\small},>=Stealth]
\node[block](q){发送寄存器\\Q};
\node[block,right=of q](l){LUT\\组合逻辑};
\node[block,right=of l](w){布线};
\node[block,right=of w](d){接收寄存器\\D};
\draw[->](q)--(l);\draw[->](l)--(w);\draw[->](w)--(d);
\node[below=13mm of l](clk){同一时钟的相邻有效边沿};
\draw[->](clk.west)-|(q.south);\draw[->](clk.east)-|(d.south);
\end{tikzpicture}\end{center}
''');continue
    if s.startswith('忽略时钟偏斜时的建立'):
        parts.append(r'''忽略时钟偏斜时的建立时间预算：
\[T_{\mathrm{clk}}\ge t_{\mathrm{CQ,max}}+t_{\mathrm{logic,max}}+t_{\mathrm{route,max}}+t_{\mathrm{setup}}+\text{裕量}\]
忽略时钟偏斜时的保持时间条件：
\[t_{\mathrm{CQ,min}}+t_{\mathrm{logic,min}}+t_{\mathrm{route,min}}\ge t_{\mathrm{hold}}\]
''');continue
    if s.startswith('等待时间 ='):
        parts.append(r'\[\text{等待时间}=\frac{\text{计数周期数}}{\text{时钟频率}},\qquad 0.5\,\mathrm{s}=\frac{25\,000\,000}{50\,000\,000\,\mathrm{Hz}}\]'+'\n');continue
    if any(r.font.name=='Consolas' for r in pa.runs):
        parts.append(r'\begin{Verbatim}[fontsize=\small,breaklines=true]'+'\n'+s+'\n'+r'\end{Verbatim}'+'\n');continue
    if s=='↓':parts.append(r'\begin{center}$\downarrow$\end{center}'+'\n');continue
    if s.startswith('https://'):parts.append(text(s)+'\n\n');continue
    if re.match(r'^\[\d+\]',s):parts.append('{\\footnotesize '+text(s)+r'\par}'+'\n');continue
    iscap=s.startswith(('图 1','图 2','图 3','资料核对日期','并非所有'))
    parts.append(('{\\small\\color{black!70} '+text(s)+r'\par}') if iscap else text(s)+'\par')
    parts.append('\n\n')
parts.append(r'\end{document}')
(out/'Tang_Mega_138K_Pro_开发指南.tex').write_text(''.join(parts),encoding='utf-8')
print(out)
