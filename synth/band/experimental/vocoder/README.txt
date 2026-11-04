星群：16 频带声码器开发模块（非最终上板版本）

用途
麦克风/调制信号通过16个带通滤波器，绝对值整流后由100Hz四阶低通提取包络；
同样的16个带通滤波器处理合成载波，逐带相乘后累加、缩放并饱和到24位。
声码器不是任意歌词歌唱。未接麦克风，尚不能宣称歌声清晰度或现场演出通过。

文件和来源
upstream/：VOXOS原始文件与MIT许可证，commit见PROVENANCE.json。
ported/double_biquad.sv：修复第二节b2系数及复位，并显式复用乘法器。
ported/filterbank.sv：16频带状态、输入ready、确定性复位、绝对值溢出保护。
ported/coeffs.mem：原16带通保持；包络行换为可复现生成的Q20低通。
ported/vocoder_mixer.sv：星群新写；乘法寄存、68位累加、饱和、削波计数。
ported/vocoder_core.sv：完整独立声码器内核，忙时拒绝并计数。
ported/vocoder_i2s_frontend.sv：I2S输入、FIFO、内核与时钟丢失静音。
默认左声道为麦克风调制输入，载波由core_clk域的合成器提供。
STEREO_TEST_CARRIER只用于数值测试，使用右声道作为载波；正式接入应为0。
未绑定任何新物理引脚，未修改现有乐队release，未生成可烧录的正式整机版本。

已验证
1. 双二阶节256个独立定点向量；原版在变异对照中失败，修正版通过。
2. 16频带4096样本逐位匹配独立Python状态模型；忙时干扰和处理中复位通过。
3. 完整内核4096样本逐位匹配；优化版输出123时钟，滤波部分90时钟。
4. 混音256组边界向量，含正负满幅、饱和、负包络钳位、输入锁存和复位。
5. I2S→异步FIFO→声码器128样本匹配；停止BCK、超时清零、恢复、panic通过。
6. 有限序列定点模型：4096样本激励后48000样本静音，无回绕/输出削波；
   最后960样本输出峰值2LSB、内部状态峰值6120。存在定点残留，不等于严格零。
7. 高云综合：优化前43809逻辑、9340寄存器、123 MULT27X36；
   优化后23361逻辑、12562寄存器、30 MULT27X36。均为综合，不是物理DSP块计数。
8. 独立内核PnR：50MHz Setup/Hold均0，Fmax56.251MHz，逻辑19898、寄存器10972、DSP52/298。
   证据为evidence/vocoder_core/pnr.json；只约束独立模块内部50MHz，不包括I2S前端。
   PnR工程其他IO自动分配且无外部延迟约束，其位流绝不可下载到真实板卡。

数值问题与边界
上游生成脚本写出16带通+高通，却遗漏下一行低通；滤波器将高通当作包络低通。
修正后Q20低通DC增益1，100Hz增益约0.705921，所有量化极点模小于1。
公式依据：https://www.w3.org/TR/audio-eq-cookbook/ 。
逐项乘法右移、32位回绕仍是滤波器算术契约；有限测试不是所有输入的稳定性证明。
I2S固定24位数据、32位槽、双声道。输入采样率应为48kHz。
输入丢失默认5000000个core_clk周期后复位滤波状态并产生零输出通知；
在50MHz下为100ms。错误计数的_bck后缀表示仍在输入时钟域，不能直接跨域读。
缺失输入导致内核复位，因此内核计数清零；前端尚无跨故障持久累计遥测。

精简复现（仓库根目录；需Python和原工程的OSS CAD工具）
python synth/band/tools/generate_vocoder_coeffs.py
python synth/band/tools/test_vocoder_filterbank.py
python synth/band/tools/test_vocoder_core.py
python synth/band/tools/test_vocoder_mixer.py
python synth/band/tools/test_vocoder_input.py
算术核改变时加跑test_vocoder_biquad.py；系数/位宽改变时加跑audit_vocoder_tail.py。
没有相关修改不重复运行。build_vocoder.py用于新的不可变综合，pnr_vocoder.py建立独立时序工程（当前工具仍会重新综合）。

下一步接入要求
1. 指定乐队载波角色与音源，添加独立声码器混音轨、控制和遥测。
2. 并行处理而非串接到966周期乐队渲染之后：后者加123周期会超过48kHz预算。
3. 明确ADC/DAC时钟来源及采样率关系；异步FIFO仅负责跨域，不是采样率转换器。
4. 整机重新PnR，整曲/满载/停音/接管关键回归，再做真实麦克风与听音验收。

2026-10-25 后续接入模块（晚于V5.3压缩包，尚未打包）
band_vocoder_insert.sv将同一帧乐队PCM和声码器输出配对，125周期完成。
每1041周期接收一帧，512帧逐位测试通过；正常音量按每帧1级渐变，panic立即清零。
对外须预算额外一个音频帧延迟，不能将延迟声码器与未延迟乐队PCM混合。
它目前没有接入正式顶层，也没有定义载波角色；不能据此宣称整机集成完成。
证据：evidence/band_vocoder_insert/result.json。

电子歌手角色接入进展（晚于V5.3）
- vocoder_carrier.sv：64谐波带限载波，复用插值正弦核；每音频样本73周期，
  4096样本对独立傅里叶参考最大误差18个24位LSB。单音优先，不冒称复音歌手。
- singer_note_control.v：复用32槽身份分配器，最后按下音符优先，释放后退回仍按住的音符。
  过期epoch/serial不会关闭新音符，断连释放、panic和part分离已验证。
- singer_role.sv：已授权事件→载波→声码器→同帧乐队混音，完整链每帧199周期，512帧验证通过。
- integration/band_singer_core.sv：由prepare_singer_integration.py从主band_core生成的实验分支。
  内部part15（上位机第16轨）专用于电子歌手，part7（第8轨）仍为合唱；
  歌手事件只经既有所有权授权派发，广播断连在双方ready时原子提交，避免重复消费。
  已验证真实核心控制流程及256帧合成麦克风音频；这不是外部麦克风实测。
- 对外音频相对原版额外预算一帧延迟；render_cycles仍记录原乐队渲染阶段，
  singer_dropped记录新增链路丢帧，不能把两者解释为零附加延迟。
- 当前singer_mix是核心接口，尚未接入正式上位机参数/身份功能声明。
  主工程与V5.3压缩包没有改成这份实验分支。完整系统还需整机时序、整曲和满载验证。
复现：先test_vocoder_carrier.py生成并校验carrier.hex，后test_singer_role.py；
实际授权集成运行prepare_singer_integration.py与test_singer_integration.py。

调度修正（取代上面的串行接入时序描述）
不能依赖乐队PCM总是相隔1041周期：满载转空载会使完成相位提前。
已保留serial_singer_role.sv作为失败对照：147周期间隔时丢1帧。
当前singer_role在sample_tick并行合成载波，分别锁存载波/乐队PCM后汇合，
不再等乐队PCM到达才开始载波计算。同一转换测试通过，旧实现仍按预期失败。
效果器清零期间禁止不完整帧进入歌手链；真实核心启动与256帧回归通过。
并行接口仍是变延迟的valid数据流。最终DAC必须使用带帧队列的接口；
不能把left_out/right_out直接当作无valid的固定相位寄存器而忽略中间帧。
已过综合的是修正前串行快照：56055逻辑、30677FF、155个综合RAM原语；
不是修正后的时序，也不是物理RAM/DSP占用。新的256声部＋歌手测试正在执行。

2026-10-25 continuation: full 256bandvoices+singer transition test PASSED (1024loaded+16releaseframes,maxbandcycles966,peakPCM16=2515,no drops/deadlines). This is a short RTL check, not stability evidence.
The new four-frame PT8211 queue passed ten decoded stereo frames, empty-latch concurrent enqueue, overflow, drain and panic. Experimental band_singer_board_engine connects this queue and preserves the baseline UART/ownership flow; its microphone is core-clock PCM24, NOT a physical ADC pin. singer_mix remains an integration input, no new host control is claimed. Identity feature bit31 marks experiment. Wrapper elaboration passed; UART regression and updated core synthesis are in progress. No new bitstream has been programmed.

Output jitter correction: default START_FRAMES=2 prefill before DAC starts. A single-frame prefill inserts silence when completion latency alternates200/1090clocks; mutation evidence records that failure. Default passes12decoded stereo frames with no silence, drops or underruns. Edge/overflow/panic test deliberately usesSTART_FRAMES=1 to exercise empty-latch concurrent enqueue. Updated experimental board engine passed the original UART take/note/release/play/stop/panic/identity fixture with2frame prefill; its mic/gain are zero in that fixture. Dedicated singer numerical and full-load tests remain separate.

UART singer-specific verification: tools/test_singer_uart.py encodes actual host Event packets and runs the real UART receiver, ownership, singer and queued DAC. Source2 take, same-note retrigger, stale release and source3 unauthorized release, exact release, panic and identity passed with nonzero synthetic-mic PCM/DAC output (peakPCM16=79). This is not microphone quality evidence.
Fullengine internal50MHz timing exploration is running from immutable D:/StarclusterBuilds/singer_board_timing_134793007c6c. Only clk has a fixed known pin and clock constraint; other I/O is auto-placed, so NEVER PROGRAM its output even if timing passes.
Remaining interface work includes physical microphone ADC/CDC/watchdog integration, singer-specific host controls and explicit singer-active telemetry; current active_voices still counts the original band banks.

Singer expression integration: current generated core routes accepted parameter0/part15 controls to singer_expression. Existing host expression slider can send these when its seat is assigned to UI track16. Owner/epoch authorization remains in the production control pipeline; conductor source1 overrides it. Values above127 clamp,127 preserves prior gain,0 requests mute through existing per-frame gain slew. A registered expression product avoids a two-multiplier combinational chain. Part15 controls no longer reach the choir bank. test_singer_expression.py passed owner/stale/unauthorized/conductor/clamp/isolation; updated test_singer_integration.py passed256audioframes.
The still-running134793007c6c timing snapshot predates expression; do not apply its eventual result to this changed core. Host track naming and singer-active telemetry still need explicit firmware capability integration.

Microphone transport continuation: experimental/audio_input/microphone_capture.v drains complete left-channel PCM through the existing Gray FIFO and snapshots latest PCM on the band tick. Test covers two signed frames, skipped/repeated accounting, physically stopped simulatedBCK, watchdog-zero/async transport flush, fresh recovery and panic. This is not ASRC: real independent sample clocks require rate conversion or a shared clock; counters expose mismatch.
New band_microphone_top wires this transport to the experimental engine, with stale input gating singer_mix tozero (existing bounded per-frame gain slew, at most127sample steps plus pipeline under nominal running audio). It does NOT reset vocoder filter history. Fullband continues structurally. Top and engine elaboration passed; top behavioral, PnR, external clock/pin and analog tests remain. Only transport behavior has been tested so far.

Full microphone top behavior now PASSED via test_singer_uart.py --microphone: actual UART packets plus independent I2S/CDC input, band/singer/queued DAC, owner/retrigger/stale releases. Stopping microphoneBCK for170audioframes requests singer-only zero gain while ownership stays held and score/PCM continue; BCK restart recovers fresh frames and gain. Panic checks bothPCMchannels and sequencer stop. This is short digital simulation, not physical/ASRC quality.
A timeout/snapshot same-edge bug was reproduced in microphone_capture and fixed so timeout clearing wins. The focused test verifies no old PCM can reappear before the first fresh snapshot; pre-fix source/failure retained under evidence/microphone_capture. Complete top test rerun passed after fix.
Current expression-enabled core also passed the256bandvoices+singer1024loaded+16releaseframe regression (966maxbandcycles,peak2515,zero drops/deadlines).

AfterV5.5, experimental engine now advertises featurebit5 and responds to query19 with0xA2 singer gate/note/drop/staleoff/DAC counters. test_singer_uart.py --telemetry passed actual serial TX/RX/CRC decode. Host polls only advertised support, uses current-seat source, yields to uploads/backlog, expires state after2.5seconds and hides it after capability loss/disconnect. Gate is held-note state, never loudness. Track16 is named electronic singer only for supported firmware; band voice counts are explicitly labeled excluding the singer.20host tests passed, followed by a targeted capability/CRC/expiry check after the final immediate-hide adjustment. Pending772817 timing snapshot predates this telemetry addition.

Host usability verification: current singer capability disables unsupported pitch-bend, vowel preset and ADSR widgets and filters corresponding MIDI parameter writes; note/velocity/expression remain enabled. Other roles restore controls. Stage now shows singer telemetry separately from band counters.21host interaction tests pass. tools/preview_singer_host.py replays captured CRC-valid RTL identity/singer packets into realQt and saves desktop/stage previews;1180x780 has no horizontal overflow. Previews explicitly say no hardware connected. These changes follow the immutableV5.5 archive.

Autonomous singer verification: tools/test_singer_score.py builds a score2 fixture with the host upload encoder and drives actual upload-port CRC/atomic storage, sequencer, ownership and singer.2automatic notes/off, natural end, human takeover surviving old automatic release/end, next-performance real bar return to machine, and panic all passed (peak71, synthetic mic). This short320sample score is not a90s/full-concert test, and upload-port testing is separate from UART tests.
Expression-enabled frozen772817125c91 fullengine internal50MHzPnR passed0Setup/Hold,Fmax50.002MHz,RAM223,DSP194,FF32375. Timing margin is extremely small.232autoI/O ports and absent externalinterface constraints mean NEVER PROGRAM. Physical microphone top and later telemetry changes are not included. Exact source snapshot is retained. No vendor job remains running.

2026-10-26 combined PnR2d5bfcfe40c6 failed518setup/21hold. Registered32bit multiplier operands in double_biquad split state mux from product.256independent vectors,4096x16filterbank and4096completecore outputs remain bitexact. Core latency now153cycles (previous123); later integration/timing evidence required. Existing immutable long renders do NOT cover this latency change.
