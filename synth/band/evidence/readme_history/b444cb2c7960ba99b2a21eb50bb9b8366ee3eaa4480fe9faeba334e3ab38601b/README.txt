最新实物进展（2026-10-26 13:03；最终验收未完成）
当前演出候选：pt8211_dvi_620164a544d2，CURRENT_RELEASE.json已选择，SRAM已验证；Flash已编程校验并通过JTAG重新加载自主演出，旧band_57c8f7b5b006保留回退。
板载PT8211＋DVI固定管脚布局布线986a1：Setup/Hold均0，15物理管脚、11约束核对通过；50MHz核心Fmax50.031MHz，时钟普通布线警告保留，不能宣称大时序余量。
物理资源：68322逻辑、37133寄存器、47405 CLS、245 RAM、168 DSP。
实板静音验证：60秒连续256槽，最坏966周期；96秒整曲自然结束至4608000采样点；遥测CRC0。
实板＋上位机合成双席：接管/冲突/分别归还/断连回收/重加入通过，完整整曲完成；842份歌手/DAC状态中丢事件、DAC丢样和欠载均0。
以上不证明模拟音质、真实MIDI手感、实际屏幕显示、麦克风/ADC/脚踏、Flash冷启动或长期热稳定。板端已发送总停音和主音量0。
完整外设扩展源码保留，但当前固定管脚封装将未接的麦克风/ADC/脚踏固定空闲，不能当已实现实物输入使用。
当前PT8211短满载联合仿真已通过：2510帧保持256槽，3002串行立体声帧匹配PCM，DVI每通道12000位匹配参考。旧98秒PCM渲染/60秒仿真成绩只适用于原serialregs版本。

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
  43,008 独立分量是单独诊断配置；已完成 RTL 频谱、布局布线及 60 秒板端调度验证。
  该成绩不是乐队声部容量，也不是板端模拟频谱或可闻性证明，见 hardware_diagnostic_43008.json。
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

作品编辑器现可打开“导出脱机工程”菜单，选择“融合演奏席·板载音频”；先将第16轨设为电子歌手。该入口导出完整融合源码并保留当前演奏参数，不构建、不烧录。缺少实际外设约束仍不能构建。

音频舞台反馈（V5.8后新增）
舞台实时状态窗口 -> 音频输入·波形/频谱/李萨如 -> 选择电脑音频输入 -> 开始监测。
默认不采集；停止、关闭监测窗口或关闭演奏台都会结束输入。Ctrl+Space或窗口内总停音直接调用FPGA总停音。
只保留短时内存窗口，不保存、不回放、不参与合成；超过0.5秒无新样本即清除旧图。
监测FPGA的模拟输出需要实际线路输入/声卡接线，选择其他麦克风不会自动代表FPGA。立体声显示前两个声道；单声道复制波形并注明无立体声相位信息。频谱为1024点Hann FFT，不是高分辨率分量性能验收。
已验证分块PCM、1500Hz谱峰及幅度、四种PCM格式、非有限浮点数、容量限制、过期、关闭与总停音；尚未实测真实设备采集/延迟/校准。
Qt接口依据：https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QAudioSource.html

合并工作站导出（2026-10-26）：编辑器选择电子歌手角色后，可在“导出脱机工程”菜单选择“外置I2S音频与频谱读取”，或运行tools/export_workstation.py <作品.json> <空目录>。此配置使用外部24.576MHz时钟和I2S DAC，包含断钟清场及冻结频谱RAM读取接口；不是现成HDMI显示。保留曲谱/音色/校准，上电等待时钟后仅自动演出一次。实际导出顶层无UART冷启动仿真通过，当前serialregs快照已通过98秒整曲、60秒256槽满载和内部PnR；这些结论只绑定对应导出与源码，物理验收仍未完成。必须按真实硬件填写workstation/microphone/stage约束，默认构建会拒绝缺失配置。

实际接口与当前控制映射请读 HARDWARE_INTERFACE.txt。它描述RTL协议，不是已确定的外设引脚表或焊接电气图。

2026-10-26 12:46 长时验证补充
本版一小时256槽静音实板测试及随后完整96秒曲谱/停音通过；最坏966周期。99451个原始回传帧CRC复核0错误，3540个歌手/DAC健康帧丢事件/丢样/欠载均0。94131份256槽状态覆盖3600.0秒，最大观测间隔0.094秒。
证据：hardware_pt8211_dvi_1h_20261026.json、同名.raw/.driver.txt及_metrics.json。状态轮询不是逐音频采样捕获，不证明每个声部可闻、模拟质量、真实输入、实屏、温度或冷启动。测试结束确认停止/声部0，清理发送总停音和主音量0。
复现：hardware_check.py --release synth/band/release/pt8211_dvi_620164a544d2 --seconds 97 --stress-seconds 3600 --require-singer-health --output 新的证据路径.json。正式听音前从低音量恢复。
本次证据及自主演出验证产生于V5.21之后，下一归档统一纳入，不改写旧归档。

Flash入口：tools/load_flash.py 默认离线预检，--execute 写入 CURRENT_RELEASE.json 指定的已核验版本并要求厂商明确校验成功。写入替换当前启动程序，无旧Flash读出备份。真实断电重启与UART身份验证仍须分别记录。

多人MIDI映射（2026-10-26）：每个演奏席独立学习八垫；先选择席位、连接该席MIDI，再点学习并按八个不同垫。学习不会覆盖其他席位。新曲谱保存 seat_pad_mappings，旧曲谱只有 pad_mapping 时使用共享默认映射。载入新曲谱会释放旧触点；本地映射文件原子写入，写入失败会显示本次有效但未保存。此项为上位机实现，不代表物理打击垫或离线FPGA直接解析USB MIDI已验收。

V5.25 MIDI连接修正：同一输入不能同时绑定两个席位；换设备打开失败时保留旧连接；重连/拔出后旧代次回调被丢弃；设备枚举失败或关闭只回收对应席位的触点、延音和控制归属。FPGA串口断开时仍检查MIDI设备断线。名称重复设备暂拒绝绑定，需在驱动侧区分名称。47项上位机测试通过，包含模拟设备异常；非真实USB热插拔验收。板端固件未改变。

共享乐队导出（2026-10-26）：编辑器将第16轨设为电子歌手后，在“导出脱机工程”选择“共享乐队 · 板载音频与显示 · 开发候选”。host/offline_shared.py导出共享256槽及中央参数表，保存各轨表情、弯音、元音、包络预设和独立歌手音量。不会写入板卡；改变作品后必须重新构建、审核实际引脚与时序并做板端回归。当前通过导出预设/reset/release-slew RTL检查及48项上位机测试；新导出的完整PT8211/DVI仿真另行记录，不沿用已发布位流的结论。V5.29归档早于此入口新增，尚不包含这一改动。

共享命令行导出：项目Python运行 synth/band/tools/export_shared.py <作品.json> <空目录>；默认上电自动演出，--manual-start改为等待播放。作品需singer-v1格式；导出不下载、不改Flash，需独立构建验收。
