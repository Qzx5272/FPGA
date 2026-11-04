"""Build the dated team handoff from checked-in evidence; render separately."""
from pathlib import Path
import json, datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

root=Path(__file__).resolve().parents[3]
band=root/'synth/band'
def read(name):return json.loads((band/name).read_text(encoding='utf-8'))
selected=read('CURRENT_RELEASE.json')
short=read(selected['hardware_evidence'])
ensemble=read(selected['collaboration_evidence'])
autoplay=read(selected['flash_autoplay_evidence'])
assert all(r['status']=='passed' for r in (short,ensemble,autoplay))
assert all(r['bitstream_sha256']==selected['bitstream_sha256'] for r in (short,ensemble,autoplay))
long=read('evidence/hardware_81232ed690d3_1h.json')
doc=Document();section=doc.sections[0]
section.page_width=Inches(8.5);section.page_height=Inches(11)
section.top_margin=section.bottom_margin=Inches(.7)
section.left_margin=section.right_margin=Inches(.8)
for name,size in [('Normal',11),('Title',23),('Heading 1',16),('Heading 2',12)]:
 style=doc.styles[name];style.font.name='Microsoft YaHei';style.font.size=Pt(size)
 style.font.color.rgb=RGBColor(0,0,0)
 style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Microsoft YaHei')
 style.paragraph_format.space_after=Pt(7)
doc.styles['Normal'].paragraph_format.line_spacing=1.15
header=section.header.paragraphs[0];header.text='星群 FPGA 乐队工作站  团队工程交接';header.style='Caption'
footer=section.footer.paragraphs[0];footer.alignment=2
footer.add_run('工程候选  ·  第 ')
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field);footer.add_run(' 页')
doc.core_properties.title='星群 FPGA 乐队工作站整机交接报告'
doc.core_properties.author='星群项目组'
def p(text):doc.add_paragraph(text)
def h(text):doc.add_heading(text,1)
def page(title):doc.add_page_break();h(title)
def table(headers,rows,widths):
 t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
 for col,width in zip(t.columns,widths):col.width=Inches(width)
 for c,text in zip(t.rows[0].cells,headers):c.text=text
 repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
 for values in rows:
  cells=t.add_row().cells
  for c,text in zip(cells,values):c.text=str(text)
 for row in t.rows:
  props=row._tr.get_or_add_trPr();keep=OxmlElement('w:cantSplit');props.append(keep)
  for c,width in zip(row.cells,widths):
   c.width=Inches(width);c.vertical_alignment=1
   margins=OxmlElement('w:tcMar')
   for edge in ('top','left','bottom','right'):
    el=OxmlElement('w:'+edge);el.set(qn('w:w'),'95');el.set(qn('w:type'),'dxa');margins.append(el)
   c._tc.get_or_add_tcPr().append(margins)
   for para in c.paragraphs:
    para.paragraph_format.space_after=Pt(4)
 for c in t.rows[0].cells:
  for run in c.paragraphs[0].runs:run.bold=True
 p('')

doc.add_paragraph('星群 FPGA 乐队工作站\n整机交接报告',style='Title')
p('交接对象：项目队友　　记录时间：'+datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
p('当前工程已完成新版时序、短满载、整曲、模拟多人协作及 Flash 校验后自主演出。最终目标仍是一套能演奏、编排、协作、脱机并测出可用性能极限的 FPGA 电子乐队，尚未完成全部实物验收。')
p('本报告说明如何接手当前工程，以及哪些结论可以用于演示。完整代码在工程包中；本报告不复制数千个源码文件，也不把历史实验成绩当成当前整机成绩。')
h('当前交付基线')
table(['项目','当前结果'],[
 ('默认固件',selected['release']),('构建标识',selected['build_id']),
 ('板卡声音输出','板载 PT8211；与标准 I2S 分开验收'),
 ('上电镜像','新版已写入 Flash 并校验，JTAG 重载自主演出通过'),
 ('已校验历史包','V5.33，共 8582 文件，包内上位机 68 项复测通过'),
 ('包后更新','元音乐句恢复预设修复，上位机 69 项回归；43008 固定节拍诊断通过'),
 ('最终验收','未完成；以 FINAL_READINESS.json 为准')],[1.25,5.65])
p('V5.33 之后的改动不会自动出现在旧压缩包中。当前源码目录保留最新修复，后续交付须包含这些更新及已完成的新测试。')
p(('新版一小时满载及整曲测试已通过。' if long['status']=='passed' and not long.get('cleanup_error') else '新版一小时满载测试仍在运行，尚未计为通过。')+' 旧版八小时成绩仅属于旧固件 062a，不能迁移到新版。')

page('启动与排练')
p('解压后进入 project 目录，安装 Python 3.11 与工程依赖。以下命令在该目录执行：')
for line in ['py -3.11 -m venv .venv','.venv\\Scripts\\python -m pip install -r synth\\band\\requirements-host.txt','.venv\\Scripts\\python synth\\band\\host\\app.py']:
 para=doc.add_paragraph(line);para.paragraph_format.space_after=Pt(4)
 for run in para.runs:run.font.name='Consolas';run.font.size=Pt(10)
p('环境建立后可双击“启动星群演奏台.cmd”。上位机发送控制事件，声音由 FPGA 实时生成。不要在板测独占 COM12 时另开串口。实际串口号以设备管理器和上位机枚举为准。')
for text in ['连接串口并确认构建标识为 3735635258。先从较低音量开始；“开始演出”会应用界面的音量与音色参数。',
 '选择演奏席和乐队角色。ASDFGHJK 为八个音阶入口，可调整调、模式和八度；MIDI 设备按席独立连接与学习。',
 '开始 96 秒曲谱。人工接管某轨时，其他机器乐手继续；最后一个触点释放后申请在小节边界归还。',
 '用固定总停音按钮或 Ctrl+Space 停止。视觉窗口也支持空格总停音。S0/S1/S2 的播放、停止、总停音已有仿真，实体按钮尚待验收。',
 '编辑器保存事件曲谱 JSON。上传到 RAM 的曲谱断电丢失；脱机持久化需导出工程、重新构建、通过检查后烧录。']:
 doc.add_paragraph(text,style='List Number')
h('视觉与人声入口')
p('视觉页由操作者明确点击开启摄像头。单个红色标记稳定约 0.8 秒后，需要确认才改变某演奏席的后续角色；不会仅凭视觉候选抢占正在演奏的轨。当前真实相机准确率和时延未验收。')
p('合唱轨支持 A E I O U 元音标记和有限四拍乐句。元音标记影响后续新起音符，不改变已持续的声部。第 16 轨是麦克风声码器；当前板级麦克风输入未接，不能当成已具备现场歌唱。')

page('架构与源码导航')
p('Part 表示音乐轨道及控制归属，Voice 表示带生命周期的发声实例，Partial 表示独立振荡分量。六类音乐角色不等于六个声部；256 槽是乐队共享的音符计算容量，43008 是另一套诊断配置。')
table(['目录或文件','接手用途'],[
 ('synth/band/rtl','基础 RTL 与扩展模块；实际发布重建优先使用冻结来源'),
 ('synth/band/host','Qt 上位机、曲谱、协议、MIDI 映射、视觉入口'),
 ('synth/band/assets','事件曲谱、音色与初始化数据'),
 ('synth/band/tests','RTL 驱动、上位机回归与数值参考'),
 ('synth/band/tools','构建、审查、下载、板测、交付脚本'),
 ('synth/band/release/'+selected['release'],'位流、manifest、冻结 source_snapshot、审查工具及报告'),
 ('CURRENT_RELEASE.json','在 synth/band 下，决定默认下载版本'),
 ('FINAL_READINESS.json','在 synth/band 下，逐项证据与未完成边界')],[2.6,4.3])
p('完整外设顶层保留压力 ADC、脚踏、麦克风、标准 I2S 等接口，但当前板载 PT8211 与 DVI 封装将未接输入固定为空闲。保留接口不等于实际外设已经可用。')
h('控制与恢复')
p('UART 使用帧外 64 个零字节保护，每 5 ms 最多发送 4 个事件。总停音优先处理，过期序号不能关闭新音符，断连租约会回收控制权。自写控制端应遵循 PROTOCOL.txt，不能直接无限突发发送。')
p('SRAM 下载只影响当前运行配置；Flash 下载替换开机镜像。使用现有下载脚本执行来源、位流、时序和管脚检查。历史失败候选仅供研究，不能绕过检查直接烧录。')

page('验证结果与适用范围')
table(['验证项','已取得证据','仍不能证明'],[
 ('新版物理时序','建立、保持、脉宽违例均 0；18 固定管脚及复位路径审查','模拟质量、温升、冷启动'),
 ('新版满载与控制','256 槽一小时及整曲通过；32 次调参后总停音归零，整曲恢复；最坏 966 周期','256 个独立可闻谱峰或音频端到端延迟'),
 ('多人协作','实际 FPGA 与模拟两席；冲突、归还、掉线和重加入通过','真人多设备手感'),
 ('脱机演出','Flash 校验后 JTAG 重载；串口关闭约 10 秒仍演奏','物理断电启动'),
 ('100 秒音频渲染','4800000 帧；前 96 秒优化前后 PCM 相同','最新整机模拟录音'),
 ('43008 分量诊断','48 kHz 固定节拍 135168 帧；43008 谱峰；最大延迟 1032 周期','完整乐队容量或现场频谱')],[1.3,3.0,2.6])
p('新版布线资源为 69484 逻辑、38209 寄存器、48965 CLS、252 RAM、158 DSP。相比旧版逻辑减少 7.39%，DSP 减少 13.19%。不同版本存在多处变化，不能将全部减少归因于单个算法。')
p('43008 历史诊断固件占用 336/340 块 RAM。保持每通道结构不变，再加一通道将需要 344 块；这是当前结构的容量约束，不是芯片绝对上限。诊断结果与乐队资源表必须分别展示。')
p('100 秒渲染使用合成麦克风及指定混音参数。最后 100 ms 峰值仍有 1 LSB 残留，不能声称尾音严格全零。有限元音、麦克风声码器和任意歌词自然歌唱是不同能力，最后一项未实现。')

page('剩余验收与证据索引')
table(['工作','需要的实际条件'],[
 ('声音质量','接音箱或耳机试听，记录不同音区、力度、尾音、效果和噪声'),
 ('多人交互','至少两席真实 MIDI 或本地输入，检验接管冲突及拔线恢复'),
 ('扩展输入','确认麦克风、压力 ADC、脚踏型号、供电与接线后再适配固定管脚'),
 ('舞台及视觉','真实显示器、灯光、摄像头环境及融合演奏'),
 ('低延迟和极限','真实事件到音频测量；纯合成、完整乐队、长稳极限分别记录'),
 ('冷启动和恢复','物理断电测试、配置恢复与无爆音检查；JTAG 重载不能替代')],[1.4,5.5])
p('队友负责接线或焊接时，按实际器件手册核对供电、电平、时钟和引脚。当前标准 I2S 外设尚未接入；板载 PT8211 使用自己的串行格式，不能仅修改名称就当成标准 I2S 验收。')
h('相对工程根目录的关键证据')
for label,path in [('新版一小时及整曲',selected['one_hour_evidence']),('协作与视觉合成输入',selected['collaboration_evidence']),('Flash 重载自主曲谱',selected['flash_autoplay_evidence']),('旧版八小时摘要','evidence/endurance_central256_20261026/summary.json'),('43008 当前固定节拍','evidence/pool_clocked_3cbf52402956.json')]:
 p(label+'：synth/band/'+path)
p('V5.33 完整包 SHA256：\n09323b1b6721db08b1ca88ad6a0e2058d078e75f2d5ebc632fc537caa431b295')
p('本报告是工程交接，不是最终验收证书。提交或演示时，应把尚未接入和尚未实测的部分明确列为待验收。')
out=root/'output/final_workstation_20261022/星群整机交接报告_20261027.docx'
for tree in (doc.styles.element,doc.element):
 for border in list(tree.iter(qn('w:pBdr'))):border.getparent().remove(border)
doc.save(out);print(out)
