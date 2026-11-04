"""Build the report from its editable Word template and exact current evidence.

The template contains the complete design text; it is intentionally delivered
with the generator. Render/visually review the resulting DOCX before release.
"""
from pathlib import Path
import json,hashlib,re,datetime,copy
from docx import Document
from docx.shared import Pt
from delivery_evidence import read,best_band_record,host_test_count
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[3];BAND=ROOT/'synth/band'
OUT=ROOT/'output/final_workstation_20261022';OUT.mkdir(parents=True,exist_ok=True)
doc=Document(BAND/'assets/report_template.docx')
hardware_path=BAND/'evidence/hardware_band.json'
hardware=json.loads(hardware_path.read_text()) if hardware_path.exists() else {}
selected=read(BAND/'CURRENT_RELEASE.json')
if selected:
    selected_manifest=read(BAND/'release'/selected['release']/'manifest.json')
    hardware=best_band_record(BAND,selected_manifest['bitstream_sha256'])
diagnostic=read(BAND/'evidence/hardware_diagnostic_37888.json')
autoplay=read(BAND/'evidence/hardware_offline_autoplay.json')
hardware_ok=hardware.get('status')=='passed'
failed_board_hashes=set()
for path in (BAND/'evidence').glob('hardware_band*.json'):
    record=json.loads(path.read_text())
    if record.get('status')=='failed':failed_board_hashes.add(record.get('bitstream_sha256'))
for p in doc.paragraphs:
    if '生成时间：' in p.text:p.text=re.sub(r'生成时间：.*?。','生成时间：'+datetime.datetime.now().strftime('%Y-%m-%d %H:%M')+'。',p.text)
    if p.text.startswith('代码包按原目录结构保存。'):p.text=p.text.replace('和 STATUS.json','、STATUS.json 和 PROTOCOL.txt')
    if p.text.startswith('电脑端提供十六轨控制'):
        p.text+=' 合唱可按四分之一拍编辑五元音事件，并在空白合唱区插入四拍元音乐句，作用于后续新起音符；本地压力垫实测校准参数可随作品保存和脱机导出，实物校准仍待接线。'
    if p.text.startswith('band_renderer 以每槽'):p.text+=' 音符授权和声部分配之间另有一个完整事件寄存级，冻结全部身份字段，并使轨道释放与起音保持有序。'
    if p.text.startswith('停止开发的标准'):
        p.text='最终验收以可复现证据为准：数字计算、实物声音、交互延迟、脱机启动和稳定性分别检查。当前工程候选版提供完整源码与已完成验证，尚缺的实物测试列入后续接手清单。'
    if p.text.startswith('先使当前乐队候选版达到') and hardware_ok:
        p.text='当前乐队候选版已完成时序及板端数字验收。下一步接入两个真实演奏席和标准 I2S DAC，测量模拟音质、输入到输出延迟及长时稳定性；再完善非易失作品保存与独立舞台硬件。上位机舞台页已有16轨回传与失联显示，尚不等于独立屏幕或灯光硬件。麦克风声码器、有限歌词扩展和视觉指挥融合按独立模块验收。'
    if p.text.startswith('器件核查入口：'):
        p.text='器件依据：MCP3208（DS21298E）、PCM5102A、Gowin GW5AST 原语及 Sipeed 138K Pro 原理图。外设管脚与电气条件按实物核对。新增第三方模块须保留许可证、来源和修改记录。'
    if p.text.startswith('本报告同时交代最终目标与当前代码证据。'):
        p.text='本报告区分最终目标、已实现代码与实际验证。交付为工程候选版，软件验收和板级数字测试分别记录。尚未完成实物确认的外设管脚、模拟音质、端到端延迟、任意歌词歌唱、声码器、视觉识别及运行中 Flash 作品保存，不计为已完成能力。'
    if p.text.startswith('SRAM 下载脚本不会写 Flash。'):
        p.text='SRAM 下载脚本不会写 Flash。用户已在 2026 年 10 月 23 日重连硬件，下载器成功读到器件 ID。'+('本轮已完成与发布位流身份一致的板端数字测试，详见第 10 节。' if hardware_ok else '板端完整验收尚未通过，具体进展和错误见 evidence/hardware_band.json（存在时）。')+'静音测试不等于模拟声音、音箱音量或外置 I2S DAC 验收，后续须分别测量。'

evidence=Document()
def p(text):return evidence.add_paragraph(text)
def table(headers,rows,widths=None):
    t=evidence.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for c,x in zip(t.rows[0].cells,headers):c.text=str(x)
    for row in rows:
        for c,x in zip(t.add_row().cells,row):c.text=str(x)
    for i,row in enumerate(t.rows):
        for c in row.cells:
            for paragraph in c.paragraphs:
                paragraph.paragraph_format.space_after=Pt(4)
                for r in paragraph.runs:r.font.size=Pt(9.5);r.bold=i==0
    return t

evidence.add_heading('10 当前证据索引',1)
p('以下记录按源码快照区分仿真、布局布线和板级实测。旧版本成绩不会自动覆盖当前代码；软件验收汇总见 evidence/software_acceptance.json。硬件已按用户重连消息恢复验证。')
p('当前上位机交互回归通过 '+str(host_test_count(BAND))+' 项，包含合唱元音编排、参数保存/导出、压力垫定点校准和精确音符删除。外设尚未连接，软件及 RTL 通过不等于实物输入验收。')
selected_path=BAND/'CURRENT_RELEASE.json'
if selected_path.exists():
    selected=json.loads(selected_path.read_text())
    resources=selected.get('resource_usage',{})
    usage='；'.join(label+' '+str(resources[key][0])+'/'+str(resources[key][1]) for key,label in [('Logic','逻辑'),('Register','寄存器'),('BSRAM','BSRAM'),('DSP','DSP')] if key in resources)
    p('本轮演出候选：'+selected['release']+'；50 MHz 约束下报告 Fmax '+str(selected.get('fmax_mhz','见报告'))+' MHz，余量有限。资源（已用 / 总量）：'+usage+'。时钟通用布线警告保留在日志；外部接口时序与长时稳定性仍须实测。')
p('实物 USB-UART 裸突发回传出现过截尾；最小工程和 D2XX 对照也复现。当前电脑端以每帧后 64 个零字节、每 5 ms 最多 4 个事件限定发送，GUI 上限 800 事件/秒；协议帧自身仍是 34 字节，CRC 不变。640 微秒保护间隔降低控制吞吐，实际端到端延迟须另测，不能宣称任意高速突发可用。失败原始字节流与限定配置的复测记录均保留。')
rows=[]
for path in sorted((BAND/'release').glob('*/manifest.json')):
    m=json.loads(path.read_text(encoding='utf-8'))
    if m.get('setup_violations')==0 and m.get('hold_violations')==0:
        on_board=hardware_ok and hardware.get('bitstream_sha256')==m.get('bitstream_sha256')
        level='PnR / 板端数字通过' if on_board else 'PnR 通过；板测失败' if m.get('bitstream_sha256') in failed_board_hashes else 'PnR 通过；未上板'
        if diagnostic.get('status')=='passed' and diagnostic.get('bitstream_sha256')==m.get('bitstream_sha256'):level='PnR / 板端调度通过'
        rows.append((path.parent.name,level,m.get('bitstream_sha256','')[:16]))
table(['候选目录','证据等级','位流 SHA256 前十六位'],rows)

rtl=BAND/'evidence/rtl_tests.json'
if rtl.exists():
    tests=json.loads(rtl.read_text());good=[]
    for t in tests:
        match=all((ROOT/Path(n.replace('\\','/'))).exists() and hashlib.sha256((ROOT/Path(n.replace('\\','/'))).read_bytes()).hexdigest()==h for n,h in t['sources'].items())
        if match and t['returncode']==0 and 'PASS' in t['output']:good.append(t['test'])
    p('与当前源码一致的模块回归通过项：'+('、'.join(good) or '暂无；查看正在执行的记录')+'。完整哈希和时间见 evidence/rtl_tests.json。')
renders=[]
for path in (BAND/'evidence').glob('band_*.json'):
    try:m=json.loads(path.read_text())
    except (ValueError,UnicodeError):continue
    current=bool(m.get('source_hashes'))
    for filename,digest in m.get('source_hashes',{}).items():
        source=next((p for p in [BAND/'rtl'/filename,BAND/'tests'/filename,ROOT/'synth/rtl'/filename] if p.exists()),None)
        if source is None or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:current=False
    if m.get('status')=='passed' and current and (m.get('duration_seconds',0)>=60 or m.get('mode') in ('matrix','audition_fast')):renders.append((path.name,m))
rows=[]
for name,m in renders:
    metrics=dict(re.findall(r'(\w+)=(\d+)',m.get('log','')))
    label={'fast':'整曲加速仿真','full':'整曲逐时钟仿真','stress':'持续满载与释放','matrix':'音区与力度矩阵','audition_fast':'音色、元音和弯音'}.get(m['mode'],m['mode'])
    rows.append((label,str(m['duration_seconds'])+' 秒',metrics.get('max_voices','—'),metrics.get('max_cycles','—'),'缺样 '+metrics.get('missing','—')+'；削波 '+metrics.get('clips','—')))
if rows:table(['当前源码测试','模拟时长','峰值声部','最大周期','数字结果'],rows)
if hardware:
    p('板端数字验收状态：'+str(hardware.get('status'))+'；选定位流 SHA256：'+hardware.get('bitstream_sha256','未记录')+'。')
    if hardware_ok:
        p('已验证固件身份、独立音符身份与旧释放、32 槽分配、断链释放、256 槽持续负载、自动整曲及停止。满载时长 '+str(hardware.get('stress_seconds'))+' 秒；整曲观察 '+str(hardware.get('automatic_test_seconds'))+' 秒。声音开关：'+str(hardware.get('audible_test_enabled'))+'。这些结果来自板端回传，不是模拟输出测量。')
    else:p('尚未通过的原因：'+str(hardware.get('error','测试未结束'))+'。失败记录不计为上板成功。')
p('运行中、被替代中止、磁盘写入失败及未通过时序的记录均不计为成功。试听文件是实际 RTL 仿真输出，仅用于检查，不能作为比赛的预录音源。波形分析通过不等于模拟音质或主观听感验收。')
if diagnostic.get('status')=='passed':p('独立 37888 分量配置完成 '+str(diagnostic['duration_seconds'])+' 秒板端调度测试，最大 '+str(diagnostic['max_cycles'])+' 周期，期限及 CRC 错误为零；最后一个地址可独立静音并恢复。此固件没有内嵌构建 ID，依据下载日志和哈希关联；没有板端模拟频谱证据，也不代表完整乐队并发容量。')
if autoplay.get('status')=='passed':p('独立静音导出配置完成板端自主整曲：未发送播放或音符命令，关闭串口 10 秒后进度继续，最终到达 '+str(autoplay['final_sample'])+' 个样本。位流哈希见 hardware_offline_autoplay.json。此结果是 SRAM 配置后的自启动，不是 Flash 物理断电验收。')
if read(BAND/'evidence/hardware_diagnostic_43008.json').get('status')=='passed':p('后续独立性能配置已扩至 43008 分量：336/340 RAM，86/298 DSP，50 MHz 时序通过，Fmax 50.173 MHz；60 秒真板调度最大1030周期。厂商双端口ROM模型对照986835个样本逐位相同，等价行为模型验证43008个谱峰。原语比较、行为模型频谱、真板调度是三类证据，不是板端音质或整乐队容量；见 diagnostic43008 及 hardware_diagnostic_43008.json。')
if read(BAND/'evidence/hardware_ensemble.json').get('status')=='passed':p('整曲协作新增真板验证：软件模拟两个演奏席，经实际GUI/UART/FPGA完成同时接管、单席归还、另一席租约断链与重连；96秒曲谱自然结束，CRC、期限违例、削波及拒绝计数为零。不是实物MIDI或音质验收。舞台页显示16轨回传，超时与断链时隐藏过期值。有限元音乐句的四次起音、元音、移调和结束恢复另经导出RTL验证。')

start=next(p._p for p in doc.paragraphs if p.text.startswith('10 当前证据索引'))
end=next(p._p for p in doc.paragraphs if p.text.startswith('11 队友复现和接手步骤'))
body=doc.element.body
node=start
while node is not end:
    following=node.getnext();body.remove(node);node=following
for node in evidence.element.body:
    if node.tag!=qn('w:sectPr'):end.addprevious(copy.deepcopy(node))

for t in doc.tables:
    if diagnostic.get('status')=='passed':
        for row in t.rows:
            for cell in row.cells:
                if '仅是此诊断配置的仿真与' in cell.text and '未上板' in cell.text:
                    cell.text='已有此诊断配置的仿真、PnR 与 60 秒板端调度测试；不证明模拟谱峰、完整乐队并发或芯片绝对上限'
    for ri,row in enumerate(t.rows):
        pr=row._tr.get_or_add_trPr()
        if pr.find(qn('w:cantSplit')) is None:pr.append(OxmlElement('w:cantSplit'))
        if ri==0 and pr.find(qn('w:tblHeader')) is None:pr.append(OxmlElement('w:tblHeader'))
        for c in row.cells:
            for paragraph in c.paragraphs:
                if ri==0:paragraph.paragraph_format.keep_with_next=True
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
doc.styles['Normal'].paragraph_format.space_after=Pt(3)
in_sources=False
for paragraph in doc.paragraphs:
    if paragraph.text.startswith('13 '):
        in_sources=True
        paragraph.paragraph_format.page_break_before=True
    elif in_sources:
        paragraph.paragraph_format.space_after=Pt(2)
        paragraph.paragraph_format.line_spacing=1.0
        for run in paragraph.runs:run.font.size=Pt(9)
target=OUT/'星群最终目标与实施方案_V5_工程候选.docx'
doc.save(target);print(target)
