# 首版验证记录

验证日期：2026-10-11。范围为当前 Pro 板和 Windows 上位机，不代表全部比赛要求已验收。

## 后续 Flash 固化

用户要求断电保留后，已将相同位流写入板载启动 Flash（ID 0xEF4018，起始地址 0）。首次 2.5 MHz 操作校验失败；降低通信频率至 0.5 MHz 重试后，Programmer 明确返回 `Program and Verify Flash successfully`，耗时 134.6 秒。失败记录保留在 `test-output/flash_program_attempt1_failed.log`，成功记录在 `test-output/flash_program.log`。

随后通过 Reprogram 命令从 Flash 重新加载（没有再次写 SRAM），等待配置完成后，COM12 实板检查再次通过：状态回传、1/8 声部、松键释放、断线静音均正常。物理断电重启尚未由用户操作，但 Flash 写入/读回校验及从 Flash 加载均已实测。

烧录脚本现在检查日志中的明确成功标识，不仅检查退出码；该 Programmer 曾在校验失败时返回退出码 0。

## 已通过

| 项目 | 证据 |
|---|---|
| Gowin V1.9.12.03 综合、布局布线、位流生成 | `build.log`、`impl/pnr/aurora_synth.rpt.txt` |
| 50 MHz 内部时序 | Setup/Hold TNS 均为 0，报告 Fmax 74.913 MHz |
| 资源 | 9597 个逻辑资源（7%）、1952 FF（2%）、25/298 DSP（9%） |
| 实际 SRAM 加载 | Programmer 成功完成，目标 ID 0x0001081B；未写 Flash |
| COM12 实板回传 | 校验通过、单声部和八声部、松键释放、500 ms 看门狗；`test-output/hardware.json` |
| 数字音频数据 | 短音测试 FPGA 回报非零峰值，测试结束后清除声部 |
| UART 仿真 | 256 种字节逐一回环，8N1 接收正确 |
| 控制协议仿真 | 完整状态更新、错误校验拒收、包头同步、全部停止、断线静音 |
| 音频串行仿真 | PT8211 和标准 I2S 分别用独立接收逻辑逐字核验，左右测试字不同；10 ms 中约 480 帧 |
| 合成器仿真 | 单声部、八声部、释放静音、拨弦自然衰减、全部停止 |
| 声音数值分析 | A4 FFT 峰值 440.0 Hz；八音基频全部存在；测试绝对峰值 5339，未到 16 位削波阈值 |
| 上位机 | 协议测试 2 项、控件综合交互测试 1 项；实际连接截图 `test-output/ui-connected.png` |

`test-output/rtl_demo.wav` 来自 RTL 仿真样本，不是用于 FPGA 播放的预录音。所有测试源代码均在 `tests/`，可复现。

## 已知边界

- 模拟输出是否从用户音箱正常发出，需要用户听音或外部录音采集确认；数字峰值回传不能代替模拟链路验收。
- 板载 PT8211 为右对齐协议；标准 I2S 模块通过仿真，但未接实体 I2S DAC。
- 电脑键盘/旋钮替代本阶段实体交互，尚未实现最终 FSR 压力传感器及其他模拟控件采集。
- 没有测量端到端音频延迟、THD+N、SNR 或左右声道串扰，不宣称这些指标达标。
- 采样时钟采用 50 MHz 分数分频，平均为 48 kHz，边沿有 20 ns 量化抖动。
- PnR 提示 P16 时钟输入路径使用通用布线（PR1014）；内部时序已通过，但板外音频接口尚无示波器测量，不能将内部 Fmax 等同于完整接口时序验收。
- 首版为 8 声部 × 3 个加法分量，不是 32 声部/32 分量扩展要求；尚未实现混响、延迟或合唱效果器。
- 旋钮时间为目标参数，包络采用整数步长，存在时间量化误差，释放时间由当前包络高度影响。

## 本机环境变更

- 项目内 `.venv` 安装桌面 GUI 和串口依赖。
- IDE `bin/gwlicense.ini` 改为用户提供的许可证路径；原配置备份在 `tmp/gwlicense.ini.original`，未更改许可证内容。
- 自动审批拦截过仿真器安装程序执行，后续使用项目 tmp 内的便携 OSS CAD Suite 完成仿真，无需系统安装仿真器。
- 原有指南、附件和其他项目文件保留。
# 人声原型增量验证（2026-10-11）

- 新增单声部 32 谐波实时合成通路，7 个谱参数配置和 1 个噪声配置；未采用录音播放。不是完整 eSpeak 移植，不支持任意歌词。
- UART、控制、串行音频、原乐器和人声共 5 组 RTL 仿真通过。人声实际仿真输出 59,600 点，峰值 2126，释放末段为零，元音频谱不同；不能据此推断可懂度。
- 上位机 4 项测试通过，包括人声序列、停止和返回乐器模式。Windows 实际渲染截图已检查，新增区域无裁切。
- Gowin 构建：逻辑 11,172/138,240，FF 2,677，BSRAM 14/340，DSP 33/298；50 MHz 约束下 Fmax 68.204 MHz，内部 Setup/Hold TNS 均为 0。原有 PR1014 时钟布线警告仍在。
- SRAM 上板后，COM12 验证全部 8 种人声配置有非零峰值、单声部状态正确、释放静音、看门狗停音；原 1/8 声部回归通过。数据见 `test-output/voice_hardware.json`。
- 新位流 SHA-256：`D9B7D04C0E3DE7E6D0BEBFB68BF514CAAAD50B463545B73B1015730266CFAA23`。
- 旧位流保留为 `release/aurora_instrument_backup.fs`，SHA-256 与之前已验证版本一致。
- 新位流已用 0.5 MHz 写入 Flash，明确返回 `Program and Verify Flash successfully`，随后 Reprogram 从 Flash 重载，再次通过全部 8 个配置的串口人声检查。未进行人工断电重启；发音清晰度待用户试听。

# “你好”第二版增量验证（2026-10-11）

- 新增 `hello_engine.v`，128 帧动态参数、64 路分时谐波、连续音高、带限气流；FPGA 内部时序驱动普通与慢速短句，无 PCM 数据。
- RTL 定向仿真验证：有限输出、无削波、句尾静音、保持触发不循环、慢速计时、panic 停止。仿真峰值 10,897；“你”稳定段 RMS 3436.67，“好”稳定段 RMS 3277.47，间隔 RMS 0。采样输出见 `test-output/hello_rtl.wav`。这些指标不证明歌词可懂度。
- 上位机 4 项测试通过；修复关闭窗口/测试清理时未显式移除事件过滤器、清理定时器的问题，重测无退出异常。Windows 界面截图已检查。
- 内部时序：50 MHz 约束，Fmax 62.857 MHz，Setup/Hold TNS 都为 0；逻辑 12,481，FF 3,092，BSRAM 24/340，DSP 40/298。PR1014 时钟布线警告仍在。
- SRAM 板上验证普通/慢速时长、有效输出、自动结束、不循环、panic 和 watchdog 均通过；原 1/8 声部静音回归通过。见 `test-output/hello_hardware.json`。
- 位流 SHA-256：`08193DEF4E2D79E99974B8CDE8BF5FDFABF12668684E822DC4E547A61D8A464F`。第一版人声备份为 `release/aurora_voice_v1_backup.fs`。
- Flash 写入返回明确的 Program and Verify Flash successfully；Reprogram 从 Flash 重载后再次通过普通/慢速、结束/停止与 watchdog 检查。未人工断电测试，可懂度等待用户试听。

