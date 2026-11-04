V5.18工作树（2026-10-26）：最终实物目标未完成，先读当前整机交接说明与FINAL_READINESS.json。
serialregs融合候选：006d0f90662f内部时序通过；98秒整曲及60秒256槽满载通过，自动IO禁止烧录。
最新视频导出offline_workstation_dvi_clockreset_confluence：PLL与复位修正；DVI边界e46eac9479a7 Setup/Hold0。新整机联调/综合运行中，整体时序及实屏尚未通过。
旧DVI配置虽仿真通过，但PFD非法被PnR拒绝；旧RGB两次布局布线错误退出，不得当作通过版本。详见experimental/audio_visual/dvi/README.txt。
普通上板版本仅以CURRENT_RELEASE.json为准；历史快照不能混用验证成绩。

星群 FPGA 乐队工作站 V5 工程候选
================================
请先阅读交付包 documents 中的完整方案与交接报告。
STATUS.json 记录本轮状态；evidence/software_acceptance.json 对应其中记录的基线源码与哈希，不能覆盖后来新增的 experimental 模块。
V5.5 的歌手控制、麦克风顶层与断流保护见 experimental/vocoder/README.txt 及各自 evidence 记录；尚未作为正式板端固件验收。
有硬件验收时，以 evidence/hardware_band.json 中的固件构建 ID、位流哈希和测试项为准。
不要用仿真通过替代模拟声音、真实传感器、端到端延迟或热稳定性验收。
串口采用 64 个帧外零字节保护、每 5 ms 最多 4 个事件；裸高速突发回传有已记录的截尾问题。
队友自写控制端须遵循 PROTOCOL.txt 的发送配置。该限制不改变 FPGA 音频样本计算吞吐。

启动上位机（在 project 目录运行）：
  py -3.11 -m venv .venv
  .venv\Scripts\python -m pip install -r synth\band\requirements-host.txt
  .venv\Scripts\python synth\band\host\app.py
也可运行 synth\band\launch.ps1。上位机仅发送事件，音频由 FPGA 合成。

第一次排练：
  本轮板测结束后保持主音量为零。连接后先移动主音量滑块，从低音量开始；
  “开始演出”会重新应用界面中的音量与音色参数。
  1. 选择已安装 V4 协议候选固件的串口，连接后核对构建 ID。
  2. 选择演奏席与角色，再连接 MIDI。另一 MIDI 设备选择另一演奏席连接。
  3. 八个键 ASDFGHJK 对应所选音阶；调、八度与模式可改。
  4. MIDI 垫可“重新学习八个实体垫”；鼓组入口会分配底鼓、军鼓和踩镲。
  5. “开始”运行 96 秒原创曲谱；单轨接管后，其他机器乐手继续。
  6. 最后一个触点释放后申请下一小节归还。重新按下会取消待归还。
  7. 用固定底栏总停音或 Ctrl+Space 停止所有发声；部分窗口也支持空格。
  8. 编辑器保存 JSON；上传校验通过后，下次重新开始启用新曲谱。
     上传 RAM 断电丢失。“导出脱机工程”提供完整可重建源码，需另行构建与下载。
  9. 编辑器可按四分之一拍设置合唱 A/E/I/O/U 元音；标记仅影响后续新起的合唱音符。
     单独的元音标记不会起音，已有持续音符不会中途换元音。
  10. “本地压力垫校准 / 保存”根据实测 ADC 值设置 0–63 号压力垫。
      先保存通道，再保存作品 JSON；零点、增益和反向设置也进入脱机导出工程。
      发送校准会先总停音；只在启用本地 ADC 的固件生效，不影响 MIDI 垫。
      当前没有实时 ADC 读数采集界面，不能用计算预览替代实物校准。

源码入口：
  rtl/band_top.v              板载 PT8211 试听顶层
  rtl/workstation_top.v       本地 ADC、实体按钮、标准 I2S 外设顶层（须补实物管脚）
  rtl/band_core.v             音序、所有权、事件寄存、声部组、混音与效果
  rtl/band_renderer.v         FM、持续簧音、合成鼓与有限元音
  rtl/diagnostic_top.v        独立分量吞吐诊断；不是完整乐队模式
  host/app.py                多席指挥台
  host/editor.py             事件曲谱编辑器
  host/offline.py             曲谱和默认参数导出
  host/calibration_editor.py  本地压力垫实测参数编辑、保存和发送
  PROTOCOL.txt               UART 事件、身份、上传和回传定义

复现验证（需要自行安装对应工具，压缩包不分发厂商软件）：
  python synth/band/tools/test_host.py
  python synth/band/tools/test_rtl.py
  python synth/band/tools/render_band.py 97 fast
  python synth/band/tools/render_band.py 97 full
  python synth/band/tools/render_band.py 60 stress
  python synth/band/tools/reconcile_renders.py
  python synth/band/tools/build_band.py
  python synth/band/tools/audit_releases.py
  python synth/band/tools/software_acceptance.py --require-pass
测试脚本使用 project/tmp/oss-cad-suite；C++ 编译需 MinGW g++。
Gowin 已验证版本 V1.9.12.03；工具脚本中的安装路径应改为接手电脑实际位置。
波形分析脚本另需 numpy。Word 报告生成需 python-docx，模板随 assets 一起交付。

发布与硬件：
  release 中每个目录都绑定精确源码，旧目录仅作历史候选。
  以 CURRENT_RELEASE.json（存在时）选定本轮位流，不要从 build 中任取 .fs。
  重建某个已发布快照：python synth/band/tools/prepare_release_rebuild.py <release目录> <新空目录>
  然后用 Gowin gw_sh 运行新目录的 build.tcl；该步骤只准备工程，重建结果仍须重新检查时序。
  tools/load_sram.ps1 只下载 SRAM，不写 Flash；tools/hardware_check.py 默认静音。
  检查时序、结构和哈希以后才能下载。Flash 固化与标准 I2S 外设验收单独进行。

基础发布版的范围与边界（实验融合版见后文及STATUS.json）：
  有限元音乐句：编排页可在空白合唱小节插入四拍上行、下行或呼应乐句；每拍一个元音与音高，90%门控，结束恢复原元音。不是自然歌词歌唱。
  整曲协作板测：软件模拟两席，经真实上位机/UART/FPGA完成同时接管、单席归还、另一席租约断链、重连与96秒自然结束；见hardware_ensemble.json。不是实体MIDI或音质实测。
  舞台实时状态 / 投屏：16轨控制归属、曲谱位置及全局工程计数。仅显示CRC有效回传。
  各轨超过2.5秒未更新即过期；断开立即清空；没有逐轨电平、静音或歌词回执，不模拟这些显示。
  舞台页可见时每100ms最多追加两条查询，上传及队列积压时暂停，不刷新其他演奏席租约。
  连接时身份查询每500ms限速重试；真实16轨轮询验证见evidence/hardware_stage.json。
  256 槽为八组各 32 槽的配额结构，Part 对 8 取模分组，不是自由共享池。
  基础发布版合唱为五个有限元音，不含麦克风声码器；实验融合版另有16带声码器，尚未完成实物麦克风验收。任意中文歌词自然歌唱未实现。
  外置 I2S 传输 24 位，当前声音链只有 16 位有效精度。
  37,888 独立分量是单独诊断配置；已完成 RTL 频谱、布局布线及 60 秒板端调度验证。
  该成绩不是乐队声部容量，也不是板端模拟频谱或可闻性证明，见 hardware_diagnostic_37888.json。
  自启动导出工程已完成一次 SRAM 配置后的自主整曲、关闭串口再连接验证，见 hardware_offline_autoplay.json。
  此自启动测试使用静音预设；尚未完成 Flash 物理断电启动验收。
  相同 MIDI 设备的厂商 RGB 协议、视觉识别、运行中 Flash 保存未纳入已完成项。

V5.5之后的作品角色兼容更新：编辑器增加“第16轨：扩展音色/电子歌手”。电子歌手作品使用starcluster-score-2并保存engine_profile=singer-v1，旧版上位机会拒绝该文件，而不是把歌手当成旧扩展音色播放。标准作品继续使用score-1。上传前检查目标能力；使用第16轨时也必须等到身份回传。电子歌手轨目前只支持音符/力度及表情参数，不接受元音预设或其他音色参数。
电子歌手作品现可保存、打开、上传及导出完整脱机源码，导出器保留角色、事件ROM、音色参数、歌手表情和上电播放。短曲冷启动RTL仿真及未配置引脚构建检查通过；麦克风引脚、输入时序、时钟匹配、最新顶层PnR和实物冷启动仍需完成。96秒示例见assets/confluence_singer.json及交付目录offline_singer_confluence：导出歌手核心96秒全时钟数字渲染及100秒含尾音版本已验证，另有60秒256持续槽+歌手/延迟满载仿真；均为合成麦克风输入，不等于融合整机或模拟音质验收。

MIDI 延音踏板（2026-10-25）
上位机支持 CC64：值>=64踩下，<64松开。每个演奏席、每个MIDI通道独立记录；踩下时松键保留音符，松踏板后释放。重复弹同一个音会先释放旧序号，再触发新序号。总停音、设备切换、断开串口会清除延音状态；串口断线由FPGA既有租约回收兜底。该功能依赖上位机接收MIDI，不代表本地GPIO脚踏或脱机脚踏已实现。板端仍负责音源实时合成。

融合顶层脱机导出（V5.7后新增）
  python synth/band/tools/export_stage.py synth/band/assets/confluence_singer.json <空目录>
默认上电自动演出，加--manual-start则等待播放操作。导出包含本地ADC/脚踏/麦克风歌手/乐队与PT8211队列；不更改板上固件。配置实际microphone.cst/.sdc和stage.cst/.sdc后才能构建，不能把输出源码当作已验收位流。短曲谱的实际导出顶层冷启动仿真见evidence/stage_offline/result.json。

作品编辑器现可直接点击“导出融合工程”；先将第16轨设为电子歌手。该入口导出完整融合源码并保留当前演奏参数，不构建、不烧录。缺少实际外设约束仍不能构建。

音频舞台反馈（V5.8后新增）
舞台实时状态窗口 -> 音频输入·波形/频谱/李萨如 -> 选择电脑音频输入 -> 开始监测。
默认不采集；停止、关闭监测窗口或关闭演奏台都会结束输入。Ctrl+Space或窗口内总停音直接调用FPGA总停音。
只保留短时内存窗口，不保存、不回放、不参与合成；超过0.5秒无新样本即清除旧图。
监测FPGA的模拟输出需要实际线路输入/声卡接线，选择其他麦克风不会自动代表FPGA。立体声显示前两个声道；单声道复制波形并注明无立体声相位信息。频谱为1024点Hann FFT，不是高分辨率分量性能验收。
已验证分块PCM、1500Hz谱峰及幅度、四种PCM格式、非有限浮点数、容量限制、过期、关闭与总停音；尚未实测真实设备采集/延迟/校准。
Qt接口依据：https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QAudioSource.html

合并工作站导出（2026-10-26）：编辑器选择电子歌手角色后，可点“导出 I2S 工作站”，或运行tools/export_workstation.py <作品.json> <空目录>。此配置使用外部24.576MHz时钟和I2S DAC，包含断钟清场及冻结频谱RAM读取接口；不是现成HDMI显示。保留曲谱/音色/校准，上电等待时钟后仅自动演出一次。实际导出顶层无UART冷启动仿真通过，尚无该合并版整曲/满载/PnR/物理验收。必须按真实硬件填写workstation/microphone/stage约束，默认构建会拒绝缺失配置。
