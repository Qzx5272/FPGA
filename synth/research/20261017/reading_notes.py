"""Section-level evidence ledger. Does not equate retrieval with complete reading."""
from pathlib import Path
import json
from sources import PAPERS,PATENTS,PRODUCTS
base={r[0]:r for r in PAPERS}
notes=[]
def add(id,sections,finding,decision,limit,*,title=None,venue=None,year=None,url=None,kind='journal'):
    r=base.get(id)
    notes.append(dict(id=id,title=title or r[1],authors=r[2] if r else '',doi=r[5] if r and not (year or title) else '',venue=venue or r[4],year=year or r[3],url=url or r[6],kind=kind,
                      inspected_sections=sections,finding=finding,design_decision=decision,limitation=limit))
add('P01','NIME 2002 早期版，第 1-2、4-5 页；映射与演奏者经验',
    '复杂映射可能让初学更难，却能增加熟练者的表达空间。','每个音色保存手势映射；入门音阶约束和演奏自由模式分别配置。',
    '核读的是 2002 会议版，不冒充 2003 期刊全文，也不重复计数。',year='2002',venue='NIME',kind='conference',url='https://www.nime.org/proceedings/2002/nime2002_088.pdf')
add('P02','Contexts of Collaborative Musical Experiences，第 3-5 页；协作系统比较',
    '协作目标、角色与听见自身贡献的能力影响新手共同演奏。','每席有清晰声部和灯色；跨人调制须可见、可撤回。',
    '这是相关会议论文，与原目录的期刊文章不是同一篇。',title='Contexts of Collaborative Musical Experiences',year='2003',venue='NIME',kind='conference',url='https://www.jamodrum.net/Articles/Nime03BF.pdf')
add('P03','作者稿第 10-14 页，网络拓扑与社会组织',
    '连接关系包含控制权结构；中心式与平等式组织产生不同音乐关系。','轨道租约之外设置独立的调制许可矩阵，不把所有控制集中给一人。','理论及作品分析，不提供 FPGA 通信性能。')
add('P05','第 3-5 页，64 个异步乐手及 setphrasebehavior/setresponse',
    'Voyager 的乐手可以模仿、对照或独立活动，机器并非只重复输入。','以确定性规则实现呼应、留白、独奏和密度调节；行为变化用小节边界提交。','借鉴主体关系，不复制其 64 路 MIDI 系统或声称获得相同艺术效果。')
add('P06','NIME 2001 版全文，延迟、带宽、时间戳与控制映射',
    '亲密的乐器控制同时依赖延迟、稳定性和可学习的映射。','传感器事件带采样时间；音频处理固定截止期；分别测扫描与数字链延迟。',
    '此处为 2001 会议版；不把缓冲减少抖动误写成缓冲没有延迟。',year='2001',venue='NIME',kind='conference',url='https://arxiv.org/pdf/2010.01570')
add('P07','第 12-15 页，Table 5 与长期使用主题分析',
    '受访者对新声音之外的可靠性、兼容性和渐进掌握也有要求。','断连保音策略、恢复、校准和保存演出配置纳入验收。','85 名受访者中 62 名电子乐器使用者；编码百分比不是总体市场份额。')
add('P09','第 3-7 页，级联/并联声道、谐振器差分式、清浊音与噪声路径',
    '浊音、气流和摩擦噪声的注入位置及滤波不同。','歌声链分声门源、气声、摩擦辅音与鼻音支路；参数每 5 ms 更新并插值。','原模型及参数面向语音；普通话唱词和自然度仍需独立数据与试听。')
add('P10','第 17-18 页声质测量与相关性讨论，并核读摘要及研究范围',
    '气声感受涉及第一谐波相对强度和有声段噪声等多个因素。','音色的气声宏同时约束源谱、噪声和声道，避免只改 F0。','小样本语音实验；不能直接推导歌唱自然度或性别分类规则。')
add('P11','第 4-7 页，时间滞后、时长约束、音高残差、颤音和声码器',
    '音素时长在音符总长度下分配；颤音可与音符基准音高分开建模。','实现有上下限的整数采样时长编译器，元音延展、连音不重复声母。','采用其控制分解思想，不把神经声码器替换为 FPGA 简单滤波后宣称同等音质。')
add('P12','1977 授权重印版第 1-8 页；FM 公式、时变指数与乐器示例',
    '调制指数随时间改变频谱，是合成动态音色的关键参数。','电钢琴和钟声使用可独立包络的 FM 算子；按算子统计，不按边带计数。','原刊为 1973 JAES；重印不重复计数，边带混叠仍须约束。')
add('P13','原文第 3-7 页，平均反馈、随机初值、衰减伸缩和调音限制',
    '基础两点平均造成半采样延迟，高频衰减与整数周期限制明显。','随机激励仅作为算法初值；引入损耗设计、分数延迟及每次触发参数。','不能把简单 KS 的听感等同于完整吉他模型。',url='https://users.soe.ucsc.edu/~karplus/papers/digitar.pdf')
add('P14','作者重印第 2、7-13 页；SDL、拾音位置、双偏振与耦合',
    '拾音和拨弦位置产生不同梳状滤波；双偏振与单向耦合可产生拍频及同情共振。','8 条延迟线定义为 4 个双偏振弦声部；主偏振仅馈入接收偏振，避免跨弦闭环。','原文的聚合录音激励不直接采用；改用数学激励与显式琴体模型。',url='https://aaltodoc.aalto.fi/bitstreams/26192418-6b82-4009-a04e-ec035f173856/download')
add('P15','第 1-3、10-12 页；确定性分量、残差与随机合成',
    '音色既有可跟踪的正弦分量，也有宽带残差；二者时变行为不同。','谐波和噪声参数独立保存，噪声滤波及音头形状参与音色制作。','参数提取不等于可播放整段残差音频；本方案不用整段 PCM。')
add('P16','作者稿 PDF 第 8-10 页，数字波导、FDN、Zita-Rev1 个案',
    '先建立无损反馈骨架，再用幅频增益受限的滤波器引入衰减。','选择 8 路正交 Householder FDN；每条损耗滤波全频带增益小于 1。','自定义短 FDN 不是 Zita-Rev1 复刻，其长延迟与全套滤波未计入。')
add('P17','第 3-6、9-10 页；积分插值、PolyBLEP 表格与感知评价',
    '非连续波形需要带限修正；所谓不可闻混叠依赖频率、声压和评价模型。','基础音色采用显式谐波截断；虚拟模拟分支另做 PolyBLEP 与扫频验收。','不把论文 44.1 kHz、96 dB SPL 条件的阈值照搬为本板实测指标。')
add('P18','全文方法 1.2、2.1；三类同步模型、实验顺序与刺激',
    '研究比较了线性纠错、Kuramoto 和延迟耦合的三人同步。','默认稳定主拍；可选有界跟拍，以相位误差缓慢修正下一拍，不追逐每个音符。','48 名有训练成人、24 组；固定实验顺序等限制需保留，不外推所有合奏。')
add('P20','第 3.3、4.1-4.2 节，式 15-25 与讨论',
    '模态间能量转移需要非增能约束；非线性更新含除法、平方根及零态分支。','先实现线性耦合旋转模态核，非线性耦合单独预算和验证。','不能仅加随机反馈就声称实现原文能量稳定模型。')
add('P21','第 2-3 页，fit/finish/independent 与 Strummi 个案',
    '作品应能被实际使用者独立使用，其材料、手感与情境也属于研究对象。','比赛作品要包含校准、持久化配置、导引和完整演出流程。','research product 不等同已商业化产品；论文明确区分二者。',kind='conference')
add('P22','第 4-7 页，SMS、包络平滑、滤波器设计、编码器及数据集',
    '可解释 DSP 可由模型预测参数；音频级振荡和慢参数控制需要平滑衔接。','RK3588 只提供可选参数学习/编曲，板上保留可审计合成。','原实验主要单声源、16 kHz；不能据此证明本系统复音或 48 kHz 音质。',kind='conference')
add('P23','第 3-4 页，窗、压缩、损失地形及训练结果',
    '多尺度频谱损失的局部变化可能由泄漏和对数压缩主导。','音准、频谱误差、瞬态和主观评价分开记录，不用单一损失给音色打包合格。','未复现论文训练；实验结论的参数域不能无限推广。')
add('P24','第 2-3 页模型、第 5-6 页实验设置与评价',
    '声门波表、清浊音分支与可微 LPC 相结合；原系统包含学习控制器。','借鉴声源/声道分离与稳定参数化，简化 FPGA 版需重新测试。','24 kHz、22 阶 IIR 等原始规格不能被改写成 5 共振峰 HDL 已达到原音质。',kind='conference')
add('P25','第 6-9 页；非线性 SDL、稀疏伸长估计与分析/合成',
    '张力随振动变化可产生音高漂移和缺失谐波；伸长估计比基础环路昂贵。','把力度相关的张力调制列为拨弦增强，固定空间抽样数并校验其误差。','非线性下交换律不普遍成立，不能无条件沿用预合并琴体激励。',title='Modeling of Tension Modulation Nonlinearity in Plucked Strings',venue='IEEE Transactions on Speech and Audio Processing',year='2000',url='https://aaltodoc.aalto.fi/bitstreams/c2cca37f-c7f8-4401-a508-1b85a4d85435/download')
add('P26','第 5-10 页，式 12-23、全通调音、损耗与力度滤波',
    '调衰减也改变相位延迟；全通系数应避开单位圆抵消，力度改变频谱而不仅音量。','先量化损耗形状，再求全通补偿；高音长衰减不可达时调整滤波而非让反馈增益超过 1。','环路基频调准不必然等于感知音高完全一致。',title='Extensions of the Karplus-Strong Plucked-String Algorithm',venue='Computer Music Journal',year='1983',url='https://musicweb.ucsd.edu/~trsmyth/papers/KSExtensions.pdf')
add('P27','第 6-8、12-13 页；FOF、参数文件与规则层',
    '声道共振也可表示为重叠的指数衰减正弦颗粒；可复用的参数与规则是声音设计资产。','保留 FOF 作为后续与递归声道比较的实现路径；先预算每个基频下的最大重叠数。','FOF 不是把每个元音存在一张录音表；本文不声称已实现 CHANT 的完整歌声。',title='The CHANT Project: From the Synthesis of the Singing Voice to Synthesis in General',venue='Computer Music Journal',year='1984',url='https://www.ee.columbia.edu/~dpwe/papers/RodetPB84-CHANT.pdf')
add('P28','PDF 第 5-8、11-12 页；耦合、FDTD 稳定条件与局限',
    '军鼓的膜、响弦和三维声场耦合很复杂；简化活塞腔体可能严重影响听感。','比赛基线使用可控模态打击音加噪声支路，明确称作合成鼓；三维仿真另设研究分支。','没有把完整三维 FDTD 塞进当前资源预算，也不宣称模态近似完全再现军鼓。',title='Time Domain Simulation and Sound Synthesis for the Snare Drum',venue='Journal of the Acoustical Society of America',year='2012',url='https://www.pure.ed.ac.uk/ws/portalfiles/portal/14078222/BILBAO_S_Time_domain_simulation_and_sound_synthesis_for_the_snare_drum.pdf')
add('P29','第 2-3、8-9 页，非线性激励与弓弦滞回',
    '弓力过大引起的黏滑滞回会影响音高，非线性激励并非一个静态音色标签。','弓弦与吹管先采用明确标注的声学近似；真正物理模型需要激励状态及稳定区域映射。','未逐项重建附录模型，不能把锯齿滤波标成完整小提琴物理模型。',title='On the Oscillations of Musical Instruments',venue='Journal of the Acoustical Society of America',year='1983',url='https://www.damtp.cam.ac.uk/user/mem2/papers/MUS-ACOUST/mci-schu-woodh-jasa83.pdf')

extra_authors={'P25':'Tero Tolonen; Vesa Välimäki; Matti Karjalainen',
               'P26':'David A. Jaffe; Julius O. Smith',
               'P27':'Xavier Rodet; Yves Potard; Jean-Baptiste Barrière',
               'P28':'Stefan Bilbao',
               'P29':'M. E. McIntyre; R. T. Schumacher; J. Woodhouse'}
for note in notes:
    if note['id'] in extra_authors:note['authors']=extra_authors[note['id']]

patent_notes=[
 ('T01','权利要求 1-14，特别是 3、5；动态 FM 运算描述','载波、调制波和时变指数的硬件组织','参数随包络演进；FM 算子有独立状态，不把边带计为振荡器。'),
 ('T02','权利要求 1-16；波导支路、连接与数字混响','关注网络拓扑及散射，不泛化为所有物理建模','本项目选择论文支持的正交 FDN，不据此给出自由实施法律结论。'),
 ('T03','权利要求 1-5；歌词单元、音符及参数修正','离线分析录制单元，再按歌曲修改并合成','只借鉴控制分层；参数分析与直接 PCM 播放必须区分，比赛展示完整实时链。'),
 ('T04','权利要求 1-19；感力层、中间层排气孔、叠层和三维输入','机械层叠会改变触感、空气阻尼和力传递','做压力均匀性、邻垫串扰和回弹测试；普通 FSR 垫不冒充逐指 XY 传感器。'),
 ('T05','权利要求 1-14，特别是 5-7；STZ 历史和 XYZ 扫描','触点跨分区时的连续身份与区域扫描','contact slot 保留到抬手；音高滑动不自动拆成重复 NoteOn。'),
 ('T06','A1 权利要求 1-19；分段作用力、导数和铰接结构','行程、压力及其变化率可以形成不同表达信号','速度初估与持续压力分离，设置阈值和迟滞；未将 A1 视作授权 B1 权利要求。')]
patents=[]
for id,sections,finding,decision in patent_notes:
    r=next(x for x in PATENTS if x[0]==id)
    patents.append(dict(id=id,number=r[1],title=r[2],url=r[3],inspected_sections=sections,finding=finding,design_decision=decision))

if __name__=='__main__':
    out={'scope':'关键方法/权利要求核读记录；不是所有页面逐字阅读或完整复现的声明',
         'counts':{'papers_with_method_reading':len(notes),'journal_papers':sum(n['kind']=='journal' for n in notes),'conference_versions':sum(n['kind']=='conference' for n in notes),'patents':len(patents)},
         'ranking_note':'优先 JASA、IEEE/ACM TASLP、IEEE SPL、JAES、CMJ 等领域期刊；另列 NIME、ICLR、ISMIR。未伪称所有期刊属于同一顶刊分区。专利不属于期刊。',
         'papers':notes,'patents':patents,
         'abstract_only_not_counted':['P01 2003期刊版','P02 2003期刊版','P04','P06 2002期刊版','P08','P19'],
         'products':[dict(id=r[0],name=r[1],url=r[2],decision=r[3]) for r in PRODUCTS]}
    (Path(__file__).resolve().parent/'deep'/'reading_notes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(out['counts'])
