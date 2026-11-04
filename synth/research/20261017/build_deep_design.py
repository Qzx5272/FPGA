"""Build V3 from engineering narrative and live, explicitly labelled evidence."""
from pathlib import Path
from xml.sax.saxutils import escape
from datetime import datetime,timezone,timedelta
import json
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether
from deep_chapters import CHAPTERS
from design_figures import architecture,schedule,voice,tailchart
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parents[2]/'output'/'pdf';OUT.mkdir(exist_ok=True,parents=True)
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/msyhbd.ttc',subfontIndex=0))
ink=colors.HexColor('#163A48');blue=colors.HexColor('#146D8A')
styles={
 'title':ParagraphStyle('title',fontName='CNB',fontSize=29,leading=40,textColor=ink,spaceAfter=20),
 'h':ParagraphStyle('h',fontName='CNB',fontSize=18,leading=27,textColor=ink,spaceAfter=17),
 'sub':ParagraphStyle('sub',fontName='CNB',fontSize=11,leading=17,textColor=blue,spaceAfter=8),
 'body':ParagraphStyle('body',fontName='CN',fontSize=12,leading=21.5,wordWrap='CJK',spaceAfter=15),
 'small':ParagraphStyle('small',fontName='CN',fontSize=9.5,leading=14.5,wordWrap='CJK',spaceAfter=8),
 'cell':ParagraphStyle('cell',fontName='CN',fontSize=9,leading=14,wordWrap='CJK'),
}
story=[];plain=[]
def par(s,style='body'):
 plain.append(s);return Paragraph(escape(str(s)).replace('\n','<br/>'),styles[style])
def add(s,style='body'):story.append(par(s,style))
def page(title):
 if story:story.append(PageBreak())
 add(title,'h')
def link(title,url):
 plain.append(title+' '+url)
 story.append(Paragraph('<link href="'+escape(url,{'"':'&quot;'})+'" color="#146D8A">'+escape(title)+'</link>',styles['small']))
def table(head,rows,widths):
 t=Table([[par(c,'cell') for c in head]]+[[par(str(c),'cell') for c in row] for row in rows],colWidths=widths,repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DDECF0')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#B7CDD3')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t);story.append(Spacer(1,12))
def read(name):return json.loads((ROOT/'deep'/name).read_text(encoding='utf-8'))
ledger=read('reading_notes.json');budget=read('architecture_budget.json');stress=read('filter_stress_progress.json')
now=datetime.now(timezone.utc);local=now.astimezone(timezone(timedelta(hours=8)))
add('星群 ORCHESTRA138\nFPGA 乐团的可实施设计','title')
add('V3 · 深入研究、定点架构与验证证据','sub')
add('2026 高云选题二 | 手动演奏 · 自动伴奏 · 参数歌唱 · 多人协作')
add('本轮工作起点：2026-10-17 20:14:52（北京时间）。本文件生成：'+local.strftime('%Y-%m-%d %H:%M:%S')+'。')
add('核心音频全部由 FPGA HDL 实时生成。RK3588 是可选编辑与参数准备端；完整离线作品不能依赖它播放成品音频。')
table(['证据层级','本次状态'],[
 ('研究核读','26 篇方法核读：20 篇期刊、6 篇会议/早期版本；6 件专利；8 个官方产品/艺术项目。'),
 ('独立 RTL','HQ DDS、模态旋转、余数包络核完成仿真与高云综合；标准 I2S 核完成仿真；尚未并入整机。'),
 ('控制与算术','有限多人身份、音素时长、拨弦调音/衰减、DDS 频谱、定点尾值和资源预算可复算。'),
 ('长时数值试验',stress['status']+'；累计 %.1f 分钟，%s 个新参数试次。不是上板演奏测试。'%(stress['elapsed_seconds']/60,format(stress['trials'],','))),
 ('尚待完成','整机集成、普通话音素资产、上板截止期、模拟音质、歌声可懂度及真实多人排练。')],[105,400])
add('这份报告不再把容量、音色名称或摘要当成完成证据。每项设计给出数据结构、运算路径、约束或验收方法；尚未验证的内容明确保留为设计。','small')
page('阅读导航与证据口径')
for i in range(0,len(CHAPTERS),2):
 add(' / '.join(c[0] for c in CHAPTERS[i:i+2]),'small')
add('附录 A：资源预算；附录 B：验证结果；附录 C：26 篇论文方法证据；附录 D：6 件专利；附录 E：产品来源与交付索引。')
add(ledger['ranking_note'])
add('阅读口径：核读相关正文方法、公式、实验设置、讨论或权利要求，不宣称每篇所有页逐字复现。只有摘要或机构书目的条目不算入 26 篇方法核读；会议早期版本与期刊版本不重复计数。')
link('官方赛事入口','https://www.gowinsemi.com.cn/university/match2026')
link('GW5AST 官方器件资料 DS1239E','https://cdn.gowinsemi.com.cn/DS1239E.pdf')
link('Arora V 时钟与复位要求 UG306','https://cdn.gowinsemi.com.cn/UG306E.pdf')
link('PCM5102A I2S、时钟及滤波延迟','https://www.ti.com/lit/gpn/PCM5102A')
for title,paragraphs in CHAPTERS:
 page(title)
 for s in paragraphs:add(s)
 if title.startswith('03 '):
  page('结构图 / FPGA 是发声与协作的本体');story.append(architecture());add('音频不经过 RK3588 渲染。控制与素材准备可在外部完成，完整曲目装载后由 FPGA 独立运行。','small')
 if title.startswith('05 '):
  page('时序图 / 依赖路径必须落在样本截止期内');story.append(schedule());add('加法声源之后还要做歌声声道和效果处理，因此不能只检查 512 次分量扫描。流水线各级需要携带地址和有效位，状态 RAM 只允许已预算的读写。')
 if title.startswith('07 '):
  page('数值图 / 从“极点稳定”到“静音干净”');story.append(tailchart());add('32 位状态小数与旋转结构明显降低了此案例的零输入尾值。它说明定点实现会改变声音，不能把浮点论文直接搬成低位宽 RTL。更完整的随机切换试验另列，二者覆盖范围不同。')
 if title.startswith('11 '):
  page('歌声图 / 歌词控制与音频生成分层');story.append(voice());add('普通话自然度取决于音素资产、上下文过渡和声源声道参数。框图和时长程序仅证明实现路径，不能替代实际合成与盲听。','small')
page('附录 A / 两档资源预算')
profiles=budget['profiles']
table(['项目','4096 / 8 lane','8192 / 16 lane'],[
 ('音符槽',64,256),('BSRAM 总数 / 340',profiles[0]['bsram_total'],profiles[1]['bsram_total']),
 ('基础 DSP 预算 / 298',profiles[0]['dsp_total'],profiles[1]['dsp_total']),
 ('最坏依赖周期预算',profiles[0]['sample_cycles_required'],profiles[1]['sample_cycles_required']),('1041 周期内余量',profiles[0]['cycle_margin'],profiles[1]['cycle_margin']),('改为半秒立体声延迟的 BSRAM',profiles[0]['with_half_second_stereo_delay_bram_total'],profiles[1]['with_half_second_stereo_delay_bram_total']),
 ('振荡器采样吞吐目标','196.608 M/s','393.216 M/s')],[215,145,145])
table(['BSRAM 用途','基线','扩展'],[(k,profiles[0]['bsram18k'][k],profiles[1]['bsram18k'][k]) for k in profiles[0]['bsram18k']],[345,80,80])
add('DDS、模态与包络核有本轮独立综合证据；整条 lane 与其他功能仍含工程估算。资源数可放下不等于端口、布线与实时性已满足。整机 LUT/FF、接口 IP 和约束仍要综合验收。','small')
page('附录 B / 验证证据与复现入口')
for name in ['hq_quarter_test.log','modal_test.log','envelope_test.log','i2s24_test.log']:
 add((ROOT/'deep'/'rtl'/name).read_text(encoding='utf-8').strip(),'small')
for name in ['finite_control_results.json','song_timing_results.json']:
 d=read(name);add(name+'：'+json.dumps(d,ensure_ascii=False),'small')
cal=read('string_calibration.json')
add('拨弦环路计算：%d 组，最大相位闭环基频偏差 %.6f cents，%d 组请求衰减必须受限。这里测的是量化系数的环路相位，不含动态滑音、定点递推或听觉音高。'%(cal['cases'],cal['worst_abs_pitch_error_cents'],cal['clamped_requested_decay_cases']))
table(['长时试验项目','实际记录'],[
 ('状态 / 持续时间',stress['status']+' / %.3f 秒'%stress['elapsed_seconds']),
 ('参数试次 / 样本计算',format(stress['trials'],',')+' / '+format(stress['samples_evaluated'],',')),
 ('静态极点不稳 / 状态饱和',str(stress['unstable_static_cases'])+' / '+str(stress['saturated_cases'])),
 ('尾值超过 -80 dBFS 的试次',format(stress['tail_warning_cases'],',')),
 ('内部最大峰值 / 最大尾值','%.6f / %.8f FS'%(stress['max_peak_fs'],stress['max_tail_peak_fs']))],[230,275])
add('原始随机试验交替使用 15/21 位系数小数、23 位状态小数，探索参数切换与尾值。它用于找问题，不代表 V3 的 32 位状态实现已经完整长时验证。没有静态极点越界或饱和也不等于没有量化极限环。')
page('附录 B / 追加的生命周期与音乐验证')
env=read('envelope_results.json')
add('指数包络 21 组：覆盖 1 ms 至 60 s。10 s 释放使用 17 位系数小数且无余数时停在约 -57.71 dBFS；只加宽为 24 位仍停在 -56.18 dBFS；保留余数后为 -80.02 dBFS。余数方案与量化系数浮点曲线的终点差在 2 LSB 内。阶段终止另有有限斜坡与明确零态。')
add('包络核高云综合：1 个 MULT27X36（折合 2 个基础 DSP）、258 FF、114 LUT 与 106 ALU；综合估计 Fmax 132.848 MHz。该数不是布局布线结果，更不是板上频率认证。')
arr=read('arranger_results.json')
add('90 秒规则乐团样例：36 小节、%d 事件，包含鼓/贝斯/和声/呼应、四歌声音符及模拟双人输入。最大占用 %d 个含尾音声部、%d 个分量；5 ms 内最多 %d 个事件。拒绝 %d 个旧所有者事件，前端断开后仍产生 %d 次起音，结束无残留活跃音符。'%(arr['event_count'],arr['maximum_simultaneous_slots_including_release'],arr['maximum_reserved_partials_including_release'],arr['maximum_events_in_5ms'],arr['stale_events_rejected'],arr['starts_after_frontend_disconnect']))
add('机机关系在参考代码中有明确因果：鼓重音决定贝斯力度；歌声换气状态开放鼓填空；和声转位以最小移动避开主奏音区。它们是可解释的有限规则，不冒充神经网络即兴。')
add('这只是确定性事件容量与控制验证；没有把模拟输入说成真人排练，也没有把歌声音符事件说成可懂歌词。真正的音素资产、交互演奏和自然度仍待完成。')
add('声道追加检查：三组工程起始元音参数及鼻音极零节共 16 节，量化静态极点均在单位圆内、系数落在指定范围。频响与脉冲响应估算只用于初步余量分配，不替代时变定点链测试。')
page('附录 B / 拨弦与混响的追加数值证据')
string_time=read('string_time_domain_results.json');fdn=read('fdn_results.json')
add('拨弦追加 %d 组时域递推，每组 8 秒，量化系数配合浮点状态；FFT 峰值估计最大偏差 %.6f cents。它核对环路调音与延迟索引，不能替代状态量化、动态滑音或真人听觉音高测试。'%(string_time['cases'],string_time['max_abs_rendered_peak_error_cents']))
table(['设定混响 T60 / 秒','T30 外推 T60 / 秒','状态饱和次数'],[(r['requested_t60_s'],'%.6f'%r['schroeder_t30_extrapolated_t60_s'],r['saturations']) for r in fdn['results']],[175,200,130])
add('FDN 使用固定延迟、固定损耗及 32 位状态小数，脉冲输入后递推 8 秒；衰减拟合区间为 -5 至 -35 dB。该测试没有启用频率相关阻尼、动态改参，也不是房间真实度或模拟信噪比证明。')
analysis=read('filter_stress_analysis.json')
table(['系数小数位','切换样本数','尾值告警 / 分组试次'],[(r['coefficient_fraction_bits'],r['transition_samples'],str(r['tail_warnings_in_flushed_log'])+' / '+str(r['trials_at_checkpoint'])) for r in analysis['groups']],[130,140,235])
add('两种系数精度使用独立随机参数；分组比例不能当成同参数成对实验。尾值问题说明状态精度、递推结构与零态策略都要验证。详细参数保存在 filter_stress_anomalies.jsonl，最差案例另见 filter_stress_analysis.json。','small')
add('复现命令集中在 V3_REPRODUCE.txt。数值脚本、输入参数与结果均保留；RTL 有 DDS、模态、包络、I2S 四套测试，前三者另有 Gowin 独立综合脚本。','small')
for start in range(0,len(ledger['papers']),3):
 page('附录 C / 方法核读 %02d-%02d'%(start+1,min(start+3,len(ledger['papers']))))
 for r in ledger['papers'][start:start+3]:
  add(r['id']+' | '+r['title'],'sub');add(r['authors']+' | '+r['venue']+' · '+r['year']+' · '+r['kind'],'small')
  add('核读位置：'+r['inspected_sections'],'small')
  add('原文要点：'+r['finding']+'\n设计落点：'+r['design_decision']+'\n边界：'+r['limitation'],'small')
  link('原始来源 / 作者稿',r['url']);story.append(Spacer(1,9))
for start in range(0,6,3):
 page('附录 D / 专利技术核读 %d-%d'%(start+1,start+3))
 for r in ledger['patents'][start:start+3]:
  add(r['number']+' | '+r['title'],'sub');add('核读：'+r['inspected_sections'],'small')
  add('技术要点：'+r['finding']+'\n工程选择：'+r['design_decision'],'small');link('公开文本',r['url']);story.append(Spacer(1,9))
 add('本节是技术结构研究，不是专利有效性、侵权或自由实施意见；公开申请与授权版本明确区分。','small')
page('附录 E / 官方产品来源')
for r in ledger['products']:
 add(r['id']+' '+r['name']+'：'+r['decision'],'small');link('官方来源',r['url'])
link('LinnStrument：逐音控制、量化与释放设置','https://www.rogerlinndesign.com/support/linnstrument-support-panel-settings')
link('Push：表达控制手册','https://www.ableton.com/en/push/manual/')
link('Pianoteq：模型与参数手册','https://www.modartt.com/user_manual?product=pianoteq')
page('附录 F / 交付与状态')
add('所有新增研究文件保存在 synth/research/20261017。原生产 RTL 未被这些候选替换，未烧录板卡；因此本报告的模块证据不能被误读为整机已完成。')
table(['文件 / 目录','用途'],[
 ('deep/reading_notes.json','26 篇论文、6 件专利的方法位置、设计决策与边界'),
 ('deep/rtl/hq_sine_quarter.v','已仿真/综合的数学正弦插值核'),
 ('deep/rtl/modal_rotation.v','已仿真/综合的宽位模态状态更新核'),
 ('deep/rtl/envelope_step.v','已仿真/综合的带余数指数包络核'),
 ('deep/rtl/i2s24_tx.v','已仿真的标准 24 位 / 32 时隙 I2S 发送核'),
 ('deep/rtl/impl/gwsynthesis','Gowin 独立综合网表与报告'),
 ('deep/*results.json / *_calibration.json','控制、数值和预算结果'),
 ('deep/song_control_example.json','原创短句的音符/音素控制示例，不含音频'),
 ('deep/arranger_90s_events.json','90 秒规则乐团与模拟双人接管事件样例'),
 ('deep/filter_stress_progress.json','两小时实验实际时长、试次数与完成状态'),
 ('V3_REPRODUCE.txt','环境、参考模型、RTL 仿真、综合与报告构建入口'),
 ('deep_chapters.py / build_deep_design.py','可编辑正文与本 PDF 的可复现构建')],[245,260])
add('完成定义：比赛作品必须以板上真实发声、可懂歌词、多人控制、标准 I2S 与可测延迟证明自己。研究、预算和独立模块提供路线与证据，不能替代这个最终验收。')
def footer(c,doc):
 c.saveState();c.setStrokeColor(colors.HexColor('#C4D9DE'));c.line(45,43,550,43)
 c.setFont('CN',8);c.setFillColor(ink);c.drawString(45,29,'ORCHESTRA138 · V3 · 研究 / 设计 / 验证分层')
 c.drawRightString(550,29,str(doc.page));c.restoreState()
target=OUT/'ORCHESTRA138_V3_FPGA_Engineering.pdf'
SimpleDocTemplate(str(target),pagesize=(595.28,841.89),rightMargin=45,leftMargin=45,topMargin=45,bottomMargin=57,title='星群 ORCHESTRA138 V3 FPGA 工程设计',author='Codex').build(story,onFirstPage=footer,onLaterPages=footer)
target.with_suffix('.txt').write_text('\n\n'.join(plain),encoding='utf-8')
print(target)
