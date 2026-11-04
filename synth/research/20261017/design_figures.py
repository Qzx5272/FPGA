"""Vector diagrams and data charts for the engineering report."""
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
from reportlab.lib import colors
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INK=colors.HexColor('#163A48');BLUE=colors.HexColor('#197B98');TEAL=colors.HexColor('#DCEFEA');PALE=colors.HexColor('#E8F0F4');ORANGE=colors.HexColor('#CA793C')
def text(d,x,y,s,size=10,anchor='start',color=INK):d.add(String(x,y,s,fontName='CN',fontSize=size,textAnchor=anchor,fillColor=color))
def box(d,x,y,w,h,lines,fill=PALE):
 d.add(Rect(x,y,w,h,rx=6,ry=6,fillColor=fill,strokeColor=BLUE,strokeWidth=.7))
 for i,s in enumerate(lines):text(d,x+w/2,y+h/2+(len(lines)-1)*7-i*14,s,9,'middle')
def arrow(d,x1,y1,x2,y2):
 d.add(Line(x1,y1,x2,y2,strokeColor=BLUE,strokeWidth=1.1));theta=math.atan2(y2-y1,x2-x1)
 a=6;pts=[x2,y2,x2-a*math.cos(theta-.45),y2-a*math.sin(theta-.45),x2-a*math.cos(theta+.45),y2-a*math.sin(theta+.45)]
 d.add(Polygon(pts,fillColor=BLUE,strokeColor=BLUE))
def architecture():
 d=Drawing(505,500)
 box(d,20,422,140,56,['自研演奏席','压力 / 触条 / 踏板'])
 box(d,345,422,140,56,['RK3588 可选前端','乐谱 / 歌词 / 参数'])
 box(d,182,422,140,56,['FPGA 脱机作品库','事件 / 音素 / 音色'],TEAL)
 box(d,80,327,345,60,['统一采样时间 + 有限事件调度','轨道所有权 / 规则乐手 / 音符生命周期'],TEAL)
 for x in [90,252,415]:arrow(d,x,422,x,387)
 text(d,420,400,'仅控制数据',8,'middle')
 box(d,5,212,115,70,['加法 / FM','分量私有状态','8 / 16 lane'])
 box(d,132,212,115,70,['声门源 / 辅音','共享分量池','声道级联'])
 box(d,259,212,115,70,['双偏振弦','8 条延迟单元','显式琴体'])
 box(d,386,212,114,70,['模态打击','128 状态槽','复用旋转核'])
 for x in [62,189,316,443]:arrow(d,x if x>=80 and x<=425 else (80 if x<80 else 425),327,x,282)
 box(d,80,111,345,58,['声部混音 / 效果发送 / 8 路 FDN','宽位累加 / 64 样本前瞻限幅'],TEAL)
 for x in [62,189,316,443]:arrow(d,x,212,max(80,min(425,x)),169)
 box(d,155,15,195,54,['异步 FIFO -> 标准 I2S','48 kHz / 24 bit -> DAC'])
 arrow(d,252,111,252,69)
 text(d,15,90,'遥测：截止期、欠载、饱和、身份、实际活跃单元',9)
 return d
def schedule():
 d=Drawing(505,310);x0=30;scale=445/1041
 for row,(name,parts) in enumerate([('4096 分量 / 8 lane',[512,48,18,144,160,159]),('8192 分量 / 16 lane',[512,96,18,144,160,111])]):
  y=210-row*95;text(d,x0,y+38,name,11);x=x0
  for width,col in zip(parts,[BLUE,colors.HexColor('#3F9B9A'),colors.HexColor('#A2CED2'),ORANGE,colors.HexColor('#777FAA'),colors.HexColor('#E8EEEE')]):
   d.add(Rect(x,y,width*scale,25,fillColor=col,strokeColor=colors.white,strokeWidth=.4))
   if width>80:text(d,x+width*scale/2,y+8,str(width),8,'middle',colors.white if col!=colors.HexColor('#E8EEEE') else INK)
   x+=width*scale
  for tick in [0,256,512,768,1041]:text(d,x0+tick*scale,y-16,str(tick),8,'middle')
 text(d,30,72,'扫描 -> 声像 -> 冲刷流水线 -> 歌声声道 -> 后处理 -> 余量',9)
 text(d,30,45,'50 MHz / 48 kHz；1 个样本最少 1041 周期',10)
 text(d,30,23,'这些是整机依赖路径预算；独立算术核证据不能替代整机时序。',9)
 return d
def voice():
 d=Drawing(505,395)
 box(d,15,320,145,55,['歌词 / 音符 / 连音','离线编译控制记录'])
 box(d,195,320,290,55,['样本时间戳 + 音素持续时间','F0 / 清浊音 / 共振峰 / 噪声 / 表情'],TEAL)
 arrow(d,160,347,195,347)
 box(d,15,218,135,55,['数学声门谐波源','H <= floor(0.45Fs/F0)'])
 box(d,185,218,135,55,['气流噪声','声门开闭调制'])
 box(d,355,218,135,55,['摩擦 / 爆破噪声','独立时段与频带'])
 for x in [82,252,422]:arrow(d,252,320,x,273)
 box(d,65,112,250,57,['五节声道共振 + 鼻音支路','S(36,32) 状态 / 平滑系数'],TEAL)
 box(d,355,112,135,57,['辅音并联滤波','音素交叉过渡'])
 arrow(d,82,218,125,169);arrow(d,252,218,255,169);arrow(d,422,218,422,169)
 box(d,160,15,190,53,['歌声混音总线','与器乐并发 / 表情可接管'])
 arrow(d,190,112,225,68);arrow(d,422,112,310,68)
 return d
def tailchart():
 data=json.loads((ROOT/'deep/filter_mitigation.json').read_text())['results']
 chosen=[r for r in data if r['f_hz']==50.7947 and not r['fraction_saving']]
 d=Drawing(505,290);chart=HorizontalBarChart();chart.x=145;chart.y=60;chart.width=320;chart.height=170
 chart.data=[[max(-180,r['tail_dbfs']) for r in chosen]]
 chart.categoryAxis.categoryNames=[('直接型' if r['form']=='direct' else '旋转型')+' / '+str(r['state_fraction_bits'])+' 小数位' for r in chosen]
 chart.categoryAxis.labels.fontName='CN';chart.categoryAxis.labels.fontSize=9
 chart.categoryAxis.visibleLabels=False
 chart.valueAxis.valueMin=-180;chart.valueAxis.valueMax=0;chart.valueAxis.valueStep=30;chart.valueAxis.labels.fontName='CN';chart.valueAxis.labels.fontSize=8
 chart.bars[0].fillColor=BLUE;chart.bars[0].strokeColor=None;d.add(chart)
 for i,r in enumerate(chosen):
  y=60+(i+.5)*170/len(chosen)-3
  label=('直接型' if r['form']=='direct' else '旋转型')+' / '+str(r['state_fraction_bits'])+' 小数位'
  text(d,137,y,label,9,'end')
  left=145+(max(-180,r['tail_dbfs'])+180)/180*320
  text(d,left+5,y,'%.1f dBFS'%r['tail_dbfs'],8,'start',colors.white)
 text(d,10,263,'零输入尾值：50.7947 Hz / BW 6.303 Hz',11)
 text(d,145,35,'尾值峰值 dBFS（更低更小；CPU 模型）',9)
 text(d,10,10,'不同结构的激励归一化不同；图用于观察极限环，不比较音色品质。',8)
 return d
