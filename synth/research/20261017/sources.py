"""Research register. Dates are publication years, not crawler dates."""
PAPERS = [
('P01','The Importance of Parameter Mapping in Electronic Instrument Design','Hunt; Wanderley; Paradis','2003','Journal of New Music Research','10.1076/jnmr.32.4.429.18853','https://www.tandfonline.com/doi/abs/10.1076/jnmr.32.4.429.18853','手势到声音的映射是乐器本体的一部分；设计按乐器分开的表达映射。','摘要；不能据此声称某种映射已被本项目验证'),
('P02','Collaborative Musical Experiences for Novices','Blaine; Fels','2003','Journal of New Music Research','10.1076/jnmr.32.4.411.18850','https://www.tandfonline.com/doi/abs/10.1076/jnmr.32.4.411.18850','以受约束的音阶、角色与节奏帮助新手合奏，并保留进阶入口。','摘要；新手易用与高手自由度存在取舍'),
('P03','Interconnected Musical Networks: Toward a Theoretical Framework','Weinberg','2005','Computer Music Journal','','https://opera.media.mit.edu/publications/weinberg_cmj2005_interconnected_musical_networks.pdf','网络拓扑与控制权影响音乐协作；为跨人调制设置授权与深度限制。','全文重点章节；并非网络协议性能测试'),
('P04','Displaced Soundscapes: A Survey of Network Systems for Music and Sonic Art Creation','Barbosa','2003','Leonardo Music Journal','10.1162/096112104322750791','https://ciencia.ucp.pt/en/publications/displaced-soundscapes-a-survey-of-network-systems-for-music-and-s/','区分同地实时合奏、远程协作与异步作品交换。','机构摘要和书目信息；不支持远程零延迟承诺'),
('P05','Too Many Notes: Computers, Complexity and Culture in Voyager','George E. Lewis','2000','Leonardo Music Journal','','https://eamusic.dartmouth.edu/~larry/algoCompClass/readings/george%20lewis/lewis.too_many_notes.pdf','机器即兴既回应人也可有独立行为；以呼应、留白与角色设计机器乐手。','全文重点章节；艺术实践不等同于商业产品验证'),
('P06','Problems and Prospects for Intimate Musical Control of Computers','Wessel; Wright','2002','Computer Music Journal','10.1162/014892602320582945','https://cnmat.berkeley.edu/sites/default/files/attachments/2002_problems-and-prospects-for-intimate-musical-control-of-computers.pdf','低而稳定的延迟、易入门但可练习精进、清晰映射应同时设计。','全文重点章节；本板延迟仍须实测'),
('P07','Surveying Digital Musical Instrument Use in Active Practice','Sullivan; Guastavino; Wanderley','2021卷期 / 2022在线','Journal of New Music Research','10.1080/09298215.2022.2029912','https://www.johnnyvenom.com/publication/sullivan-2022/sullivan-2022.pdf','声音、可靠性、适配真实演出、长期可掌握性决定持续使用。','全文重点章节；85名受访者中62人使用电子乐器，不能当市场份额'),
('P08','From Fiction to Function: Imagining New Instruments through Design Workshops','Sullivan; Wanderley; Guastavino','2022卷期 / 2023在线','Computer Music Journal','10.1162/comj_a_00644','https://www.idmil.org/publication/from-fiction-to-function-imagining-new-instruments-through-design-workshops/','让演奏者从实际演出构想需求，再把艺术意图转为可操作规格。','作者机构摘要；未获取完整实验细节'),
('P09','Software for a Cascade/Parallel Formant Synthesizer','Dennis H. Klatt','1980','Journal of the Acoustical Society of America','','https://www.fon.hum.uva.nl/david/ma_ssp/doc/Klatt-1980-JAS000971.pdf','采用声源和声道分离，辅音用噪声和并联谐振，参数随时间变化。','全文重点章节；英文语音参数不能直接视为普通话歌声库'),
('P10','Analysis, Synthesis, and Perception of Voice Quality Variations Among Female and Male Talkers','Dennis H. Klatt; Laura C. Klatt','1990','Journal of the Acoustical Society of America','10.1121/1.398894','https://www.fon.hum.uva.nl/david/ma_ssp/doc/Klatt-1990-JAS000820.pdf','气声、谱倾斜和声门行为共同影响音质；增加声音个性不能只改基频。','全文重点章节；说话样本实验不能保证歌唱自然度'),
('P11','Sinsy: A Deep Neural Network-Based Singing Voice Synthesis System','Hono; Hashimoto; Oura; Nankaku; Tokuda','2021','IEEE/ACM Transactions on Audio, Speech, and Language Processing','10.1109/TASLP.2021.3104165','https://arxiv.org/pdf/2108.02776','歌词时长、乐谱音高与颤音需要分别建模；RK3588可离线生成控制参数。','作者稿；神经音频渲染不能替代参赛HDL发声链'),
('P12','The Synthesis of Complex Audio Spectra by Means of Frequency Modulation','John M. Chowning','1973','Journal of the Audio Engineering Society','','https://web.uvic.ca/~aschloss/course_mat/MU307/MUS307_MATERIALS/Chowning_FM.pdf','动态调制指数能以较少算子产生丰富时变频谱。','全文重点章节；FM边带不是独立振荡器计分'),
('P13','Digital Synthesis of Plucked-String and Drum Timbres','Karplus; Strong','1983','Computer Music Journal','10.2307/3680062','https://citeseerx.ist.psu.edu/document?doi=1df6f2bf31d82a334c98e94464e490d1984dcbf8&repid=rep1&type=pdf','激励、延迟与损耗反馈构成高效率拨弦模型。','全文重点章节；整数延迟的音准和衰减耦合需修正'),
('P14','Plucked-String Models: From the Karplus-Strong Algorithm to Digital Waveguides and Beyond','Karjalainen; Välimäki; Tolonen','1998','Computer Music Journal','','https://research.aalto.fi/en/publications/plucked-string-models-from-the-karplus-strong-algorithm-to-digita/','把简单拨弦扩为可调音准、损耗和共鸣的模型体系。','机构书目；具体模型公式需另从作者原文核验'),
('P15','Spectral Modeling Synthesis: A Sound Analysis/Synthesis System Based on a Deterministic Plus Stochastic Decomposition','Serra; Smith','1990','Computer Music Journal','10.2307/3680788','https://www.upf.edu/web/mtg/sms-tools','谐波与噪声分开描述；音色参数拟合与板上合成分离。','作者项目页及论文链接；尚未完成该篇全文核读'),
('P16','Fifty Years of Artificial Reverberation','Välimäki; Parker; Savioja; Smith; Abel','2012','IEEE Transactions on Audio, Speech, and Language Processing','10.1109/TASL.2012.2189567','https://aaltodoc.aalto.fi/server/api/core/bitstreams/97ed04a8-cb88-461f-b1a3-e72da5129256/content','区分延迟网络、卷积和物理房间模型；FPGA先选有界反馈延迟网络。','作者稿重点章节；混响不能修复不好的干声'),
('P17','Perceptually Informed Synthesis of Bandlimited Classical Waveforms Using Integrated Polynomial Interpolation','Välimäki; Pekonen; Nam','2012','Journal of the Acoustical Society of America','10.1121/1.3651227','https://mac.kaist.ac.kr/pubs/ValimakiPeknenNam-jasa2012.pdf','在不连续点使用多项式带限修正，减少虚拟模拟振荡器混叠。','全文重点章节；论文特定条件的频率上限不能照搬到本实现'),
('P18','Virtual Partners Improve Synchronization in Human-Machine Trios','Van Kerrebroeck; Wanderley; Demos; Palmer','2025','Cognitive Science','10.1111/cogs.70040','https://onlinelibrary.wiley.com/doi/10.1111/cogs.70040','伴奏可适度跟随人的拍点；默认锁拍、可选跟拍，避免无限追逐。','全文重点章节；48名受训成人、24组三人任务，不代表所有演出'),
('P19','User Experience with Digital Musical Instruments: A Transferable Method for Longitudinal Evaluation','Reimer; Gupta; Guastavino; Wanderley','2025','Journal of New Music Research','','https://www.idmil.org/publication/user-experience-with-digital-musical-instruments-a-transferable-method-for-longitudinal-evaluation/','把首次体验、练习后和排练中的评价分开记录。','作者机构摘要；研究本身为小样本和压缩周期示范'),
('P20','A Simplified and Controllable Model of Mode Coupling for Addressing Nonlinear Phenomena in Sound Synthesis Processes','Poirot; Bilbao; Kronland-Martinet','2024','EURASIP Journal on Audio, Speech, and Music Processing','10.1186/s13636-024-00358-2','https://link.springer.com/article/10.1186/s13636-024-00358-2','为金属与打击音保留非线性模态耦合的升级路线。','开放全文重点章节；定点稳定性和算力还未验证'),
('P21','Digital Musical Instruments as Research Products','Jack; Harrison; McPherson','2020','NIME会议','10.5281/zenodo.4813465','https://www.nime.org/proceedings/2020/nime2020_paper86.pdf','完整性、真实场景适配与独立使用能力应成为验收对象。','全文重点章节；会议论文，不列作顶刊'),
('P22','DDSP: Differentiable Digital Signal Processing','Engel et al.','2020','ICLR会议','','https://arxiv.org/pdf/2001.04643','离线学习可解释DSP参数，板上仍用可审计的实时生成器。','待读作者稿；会议论文，不列作期刊'),
]
PATENTS = [
('T01','US4018121A','Method of synthesizing a musical sound','https://patents.google.com/patent/US4018121A/en','载波、调制频率和时变调制指数；用于理解动态FM。'),
('T02','US4984276A','Digital signal processing using waveguide networks','https://patents.google.com/patent/US4984276A/en','权利要求1具体涉及数字混响系统的波导支路和连接，不能概括成所有拨弦算法的独占权。'),
('T03','US6304846B1','Singing voice synthesis','https://patents.google.com/patent/US6304846B1/en','乐谱、歌词与音乐控制；权利要求还包括已录制语言单元的离线分析，不整套导入比赛音源。'),
('T04','US10496208B2','User interface device having depressible input surface','https://patents.google.com/patent/US10496208B2/en','感力层、可压表面与含排气孔中间层；机械叠层会改变手感及串扰。'),
('T05','US9779709B2','Polyphonic multi-dimensional controller with sensor having force-sensing potentiometers','https://patents.google.com/patent/US9779709B2/en','分区扫描三轴表情；借鉴校准目标，不复制传感器结构。'),
('T06','EP3745391A1','A controller for producing control signals','https://patents.google.com/patent/EP3745391A1/en','铰接琴键的表达控制；熟悉的动作与新增维度可以共存。'),
]
PRODUCTS = [
('B01','Ableton Push 3','https://www.ableton.com/en/push/tech-specs/','64个带XY传感器的MPE垫、演奏/片段操作；本项目只借鉴工作流，不声称普通压力垫等同逐指XY。'),
('B02','Expressive E Osmose','https://www.expressivee.com/2-osmose','连续按压、侧向弯音与音源联动；给每个乐器设计专属动作响应。'),
('B03','LinnStrument','https://www.rogerlinndesign.com/linnstrument','等距布局及多维触控；分区、音阶显示、校准与开源控制经验。'),
('B04','Synthstrom Deluge','https://synthstrom.com/product/deluge/','网格音序与完整编排；借鉴Clip和段落，不导入采样播放链。'),
('B05','Pianoteq','https://www.modartt.com/pianoteq','物理模型、连续力度变化、同情共振；要求干声和演奏细节一起评审。'),
('B06','Synthesizer V','https://dreamtonics.com/synthesizerv/','音符+歌词+表情编辑；作为歌唱交互标杆，不等于可在FPGA复制其声音质量。'),
('B07','Ableton Link','https://www.ableton.com/en/link/','共享节拍与相位的协作；外部时钟适配不代表网络传输无延迟。'),
('B08','Reactable','https://www.upf.edu/web/mtg/reactable','多人围绕可见声部关系共同演奏；借鉴可理解的连接与角色。'),
]

# Read-depth records distinguish inspected sections from unavailable full texts.
_levels = {
'P03':'作者稿引言、社会组织与拓扑章节重点阅读；非网络性能实测',
'P06':'摘要与作者书目；原全文链接失效',
'P09':'作者稿摘要、声源声道模型章节重点阅读；附录程序未逐行复核',
'P10':'作者稿摘要与研究范围；未复核全部实验和附录',
'P11':'作者稿系统结构、评价与结论重点阅读；未复现模型',
'P12':'核读1977年CMJ授权重印版的引言、时变调制及铜管/木管实例；原刊1973年JAES；未逐式复现',
'P13':'作者稿首页与引言；未完成全部公式核验',
'P16':'作者稿首页和摘要；未完成全文核读',
'P17':'作者稿摘要与结论重点阅读；未复现感知模型',
'P18':'开放全文引言和实验设计重点阅读；未复核全部统计',
'P20':'开放全文引言、讨论及结论重点阅读；定点实现未验证',
'P22':'作者稿摘要、合成模型及问题定义重点阅读；未复现训练',
}
PAPERS = [r[:-1]+(_levels.get(r[0],r[-1]),) for r in PAPERS]
_base='https://www.audiolabs-erlangen.de/content/05_fau/professor/00_mueller/02_teaching/2024s-sarntal/02_group_SYNTH/'
PAPERS = [r[:6]+(_base+'1990_SerraS_SpectralModelingSynthesis_CMJ.pdf',r[7],'作者稿引言与确定性/随机性分解章节重点阅读') if r[0]=='P15' else r for r in PAPERS]
PAPERS += [
('P23','Multi-Scale Spectral Loss Revisited','Schwär; Müller','2023','IEEE Signal Processing Letters','10.1109/LSP.2023.3333205',_base+'2023_SchwaerM_MSSLossRevisited_IEEE-SPL.pdf','频谱损失对频率误差的梯度并不总可靠；音准、听感和频谱必须分开验收。','开放作者稿摘要、引言重点阅读；不把单一损失当音质保证'),
('P24','Singing Voice Synthesis Using Differentiable LPC and Glottal-Flow-Inspired Wavetables','Yu; Fazekas','2023','ISMIR会议','',_base+'2023_YuF_GlottalFlowSVS_ISMIR.pdf','可解释声门源、清浊音门控和稳定IIR参数化可启发板上歌声；训练与推理须分层。','作者稿模型和实验设置重点阅读；原实验24kHz，不证明48kHz定点FPGA效果'),
]
