FPGA实际PCM的显示/分析数据入口（实验模块，尚未接入最终顶层）

pcm_snapshot直接接收发声路径pcm_valid/left/right。默认512个立体声16位采样，共16384bit快照；RAM是否映射为单块BSRAM须以综合结果为准。
没有audio_ready，不向音频路径施加背压。显示端持有快照期间丢弃新的可视化采样并累计visualization_skipped；该计数不是音频丢帧数。
完整窗口写入后，经两级toggle同步公布frame_available。显示端只能在有效窗口内请求读取，read_valid与读数在读时钟边沿后同时有效；release_frame优先并使窗口失效。
元数据和RAM一直保持到释放握手返回。两个时钟域共用复位；独立时钟域的单边复位尚不支持。实际集成需分别处理复位释放、同步寄存器和稳定数据总线的CDC时序约束。
frame_last_sample为32位PCM有效事件索引（从0计数，溢出回绕），不是视频时间；峰值使用17位以正确表示-32768的绝对值。

验证：python synth/band/tools/test_pcm_snapshot.py
仿真覆盖异步时钟、完整左右声道读取、-32768峰值、显示停顿37个输入采样但窗口保持、读/释放冲突、复位和部分窗口不对外公布。
512点生产深度仿真已通过；单模块综合报告294逻辑、306寄存器、1个SDPB、0锁存器，仅综合结果。synthesis_snapshot可独立运行gw_sh build.tcl复现。
band_stage_visual_top.sv由prepare_visual_stage.py生成，将快照接到融合乐队最终pcm_valid/left/right输出；不修改正在构建的原stage顶层。共享panic/rst清除快照。
集成仿真：python synth/band/tools/test_singer_uart.py --visual
已比对实际合成输出的全部512个立体声采样及峰值；暂停显示时钟40个音频帧，音频/DAC继续且无超期/欠载，释放与panic使旧快照失效。场景同时覆盖双席ADC、脚踏、UART歌手和麦克风断流恢复，约14.46ms。
仍需：视频时钟/显示输出、频谱硬件分析、新增快照版本的布局布线和实物显示。该模块本身不是完成的HDMI或FFT功能。

硬件FFT核（内核；PCM融合链路见下文）
fft_fixed.v为分时radix-2 DIT复数FFT：16位有符号输入，Q17旋转系数，每级除2，输出自然顺序X[k]/N。默认2048点，附16/512点系数及测试；旋转系数是数学常量，不是音频录音。
start必须在start_ready时发出；随后提交恰好N个input_valid&&input_ready样本。输出valid/data/bin在output_ready为0时保持；最后频点握手后done。复位撤销部分加载和旧结果。
每次变换clip_count统计发生饱和的蝶形，任意复数满量程输入须留矢量裕量。rejected_starts累计忙时启动请求；不覆盖正在计算的数据。
当前不包含窗函数。频谱显示接入时仍需Hann窗、幅度标定、数据缓存与刷新调度，不把矩形窗频谱直接当成最终显示。
验证命令：python synth/band/tools/test_fft_fixed.py 2048（也支持16、512）。
五组信号逐频点比对独立浮点参考：实数双音、复数单音/DC、随机复数、负满量程冲激、全零；第六组满量程方形复数轨迹验证饱和计数。16点用直接DFT，较大点数用递归浮点DFT。覆盖输入间隙、输出停顿、忙时重复启动和部分加载复位。
2048点五组正常幅度测试最大实/虚分量误差10LSB；复数单音峰值在第7频点，零输入输出精确零。不是任意输入精度或物理频谱测量的普遍保证。
2048点从最后输入到首个频点为101378仿真时钟周期，不含整帧收集和全部输出传送。未做该核的布局布线，不将名义50MHz换算值当实测速度。
独立Gowin综合：588逻辑、314寄存器、4个MULTALU27X18、6个RAM原语（4 SDPB+2 pROMX9）、0锁存器。初稿因多处数组读取推断了重复RAM，14个原语；显式单读写地址复用后降至6，三个长度共18组输出文件逐字节一致。仅模块综合对比，非整机全局优化结论。
复现综合：python synth/band/tools/build_fft_synthesis.py。首次源码与报告保留在fft_initial_snapshot及evidence/fft_fixed/synthesis/history。

PCM到加窗频谱链路（2026-10-25新增）
pcm_spectrum.v：最终PCM的左声道 -> 2048点冻结快照 -> 周期Hann窗（unsigned Q15，中央精确为1）-> 2048点FFT。右声道仍保留峰值统计，但当前频谱仅分析左声道，不能声称立体声合并频谱。
输出为加窗后X[k]/N的实虚分量。尚未补偿Hann相干增益，尚无dB SPL标定；不得把这些整数直接叫实测声压或每声部独立可闻证明。频率坐标k*实际采样率/2048。
每批谱携带冻结窗口的帧号、最后采样序号与左右峰值。下游ready为0时当前频点保持；下一窗口可先缓存，满后仅丢弃可视化采样，visualization_skipped会累计，不阻塞发声路径。
补测复现了停分析时钟期间复位未被同步FFT看到的问题；增加异步置位/两拍释放的复位保持，并屏蔽复位中的valid。证据stopped_clock_reset_failure.json保留原失败；当前2048点全部频点比对最大实虚分量误差约7LSB，覆盖异步时钟、停钟、输出停顿、帧身份和停钟复位恢复。
复现：python synth/band/tools/test_pcm_spectrum.py 2048；独立综合：python synth/band/tools/build_spectrum_synthesis.py。
band_stage_spectrum_top.sv由prepare_spectrum_stage.py生成，将分析器接在完整舞台顶层最终PCM输出后，共享总停音；联合测试python synth/band/tools/test_singer_uart.py --spectrum，会把实际2048点输出和每个频点与浮点参考比较。该分析版本尚未做整机布局布线，也没有实现实体视频输出。

整帧显示读取边界（V5.10封存后新增）
spectrum_snapshot.v接收顺序FFT频点，只有完整2048点及一致帧元数据才发布。显示域用read_enable/read_address同步读取，read_valid为返回有效；release_frame优先于同时读取，撤销当前帧。一个帧保持到释放，避免显示过程中上下半屏混用两帧。
帧号、最后PCM采样序号和左右峰值随发布握手跨域；异步复位撤销完整和不完整帧，显示时钟停止期间亦清除可用标志。排序错误或元数据变化丢弃不完整帧并累计rejected_bins，等待新的第0频点。
pcm_spectrum_buffered.v连接PCM快照、周期Hann/FFT和频谱快照，三个独立时钟分别为audio/analysis/display。显示变慢会背压FFT并增加可视化丢弃数，音频入口没有ready，不能因此停止发声。
验证：test_spectrum_snapshot.py检查两帧、所有频点、错误排序/混帧、读/释放冲突及停钟复位；test_buffered_spectrum.py检查实际分析器输出2048点逐点一致、停显示时钟、两帧身份、音频继续和复位恢复。
独立综合build_buffered_spectrum_synthesis.py：1028逻辑、947寄存器、14个RAM原语。这是完整分析/缓存子系统综合结果，不是融合乐队的增量资源或实物显示时序。当前尚未连到显示像素生成、HDMI或融合顶层的缓存接口。

缓存融合顶层band_stage_buffered_top.sv已生成：prepare_buffered_stage.py以当前stage源生成，最终PCM连接到完整分析/缓存链；display_clk、display_read/address/release为独立显示读取接口。test_singer_uart.py --buffered已完成约49.59ms整机联合仿真：实际2048点PCM经窗函数/FFT/冻结RAM读回，逐频点误差约6.55LSB，暂停显示40帧音频继续，释放及分析/显示同时停钟时总停音清除帧。无HDMI像素输出、该版本整机PnR或物理验收。

完整工作站组合：prepare_workstation.py生成band_workstation_top.sv，将当前本地席/脚踏/歌手/乐队、I2S队列及断钟保护、2048点加窗FFT与整帧缓存接成同一个顶层。test_singer_uart.py --workstation约51.54ms联合仿真通过：4660个实际I2S声道字一致，全部频点浮点参考比对通过，显示停钟40帧音频继续、音频断钟清场、恢复后显式播放、总停音通过。不是整曲/满载/该组合顶层PnR或物理验收；仍需接入脱机导出流程。

2026-10-26：32频带像素消费者 spectrum_bars.v（独立扩展）
读取spectrum_snapshot的同一display_clk域接口：read_enable/address发请求，read_valid携带返回，完整读取正频率bin1..1023后release_frame。忽略DC和负频率镜像；32段边界在band_end函数中，频率为bin*实际采样率/2048。幅度用饱和abs(real)+abs(imag)，高度为15*bit_length，属于粗略对数指示，不是精确幅值、dB或声压。
双份32x8位柱高缓冲，仅在调用者frame_start时整帧切换；未显示的帧保持到切换，不覆盖前台。640x480逻辑坐标中，柱图位于x=64..575、y=200..439，每柱16像素宽含2像素间隙。调用者提供像素坐标、视频帧边界及同域时钟。异步复位在显示时钟停顿时也清除旧画面。
它不产生视频同步、不编码HDMI、不声明物理显示已完成，也未并入已验收内部时序的006d0f90662f工作站。接入后必须重新做整机资源/时序/视频验收。
验证：tools/test_spectrum_bars.py，使用真实spectrum_snapshot及合成复数频点，对照独立Python频带高度，覆盖全部32频带、像素边界、停顿、静音帧、无撕裂、中途复位及停显示钟复位。尚不属于实际PCM到显示的整链验证。
综合：tools/build_spectrum_bars.py，75b15e98c291独立综合670逻辑、581FF、0RAM/0DSP/0锁存器；不是完整整机增量的物理资源或像素时序证明。
当前不含本扩展的serialregs工作站内部PnR006d0f90662f已通过四时钟Setup/Hold0，实际外设约束与物理验收仍缺。

PCM到像素的独立组合 pcm_spectrum_display.v（2026-10-26）
将真实pcm_spectrum_buffered与spectrum_bars连接，输入PCM，无音频ready；显示侧自动读取和释放频谱帧。输出RGB、画面有效、已显示帧数，以及可视化丢弃/FFT削波/拒绝计数。视频时钟、坐标、frame_start仍由调用者提供。
test_pcm_spectrum_display.py用测试方波PCM，真实Hann/FFT和跨域缓存产生频点，独立Python从2048个实际FFT结果计算32柱高度并与RTL读出对照。覆盖显示停钟导致分析背压而PCM继续、非静音/静音两画面原子切换、停钟复位及恢复无旧帧。
独立综合82e80361ff07：1665逻辑、1432FF、14个RAM原语、0锁存器。未做此组合的布局布线；综合器默认100MHz估算不是时序验收。本模块未接入乐队最终顶层，没有HDMI编码或实物显示验收。

逻辑RGB视频输出 pcm_video_640x480.v / video_timing_640x480.v
总时序800x525、有效640x480，负极性行同步x656..751、场同步y490..491；消隐区RGB强制0。在最后一个消隐像素发frame_boundary，下一拍进入(0,0)前完成画面缓冲切换。输入像素时钟25.2MHz时为60帧/秒；未生成PLL时钟、未实现HDMI/TMDS物理输出。
test_pcm_video.py从测试PCM经过实际Hann/FFT/缓存/柱图，检查整帧420000个时隙：有效307200、行同步低电平50400、场同步低电平1600、非背景柱图30870像素，以及全消隐黑色、第一有效像素换帧和停钟复位。仿真像素时钟25MHz（约59.524帧/秒），不宣称实测60Hz或硬件视频兼容。初版测试误要求复位释放后有效区仍全黑；已改为验证复位时黑色、释放后空背景，RTL未因此修改。
独立综合81d485d5f51a：1702逻辑、1452FF、14个RAM原语、0锁存器。完整乐队已有FFT缓存，后续接入只需频谱像素消费者和时序模块，不应重复实例化分析器。本扩展尚未合入工作站/PnR或外部显示。
