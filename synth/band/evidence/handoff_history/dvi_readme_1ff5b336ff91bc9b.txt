当前进度（2026-10-26 07:40）：
最新domains候选删除原始复位绕过同步释放寄存器的通路。wrapper当前dc2205f3；联调073747、整机综合6d54正在运行，小边界ca8253仅综合通过，尚无新版本时序结论。
此前clockreset整机1a8aa927cffc布局布线完成，但有23条建立/恢复、3条保持/移除违例；失败证据保留。e46eac9479a7通过仅适用于旧wrapper的小模块，不能套用到当前源码或整机。
以下为参数、来源与历史修复记录；具体结论始终按源码哈希匹配。

星群 DVI 视频输出候选（2026-10-26）
仅视频 TMDS，无 HDMI 音频、DDC/HPD 或实际显示器兼容性验收。
来源固定在 Sipeed TangMega-138KPro-example 提交 d3cebf1703f1bcd06dca8a53bf2b660c86a5ec16，见 SOURCE.json。编码器保留 Clifford Wolf ISC 版权许可；仅改模块名、去除未使用 include。仓库根许可证另存 LICENSE.Sipeed.txt。

当前时钟：板载 50 MHz，IDIV=1，FBDIV=1，MDIV=15+6/8，VCO=787.5 MHz；ODIV0=6+2/8 输出 126 MHz，专用 CLKDIV5 输出同源 25.2 MHz。PFD=50 MHz，满足布局布线工具要求的 19~81.25 MHz 范围。参数来自 UG306-1.0.7E 第4.3、5.1节；实际抖动、锁定与信号完整性仍待上板测量。
旧 IDIV=5 的配置 PFD=10 MHz，虽仿真/综合通过，但小模块 PnR e725f4701485 被 PA2078 拒绝，禁止将其当作可上板版本。

接口：gowin_dvi_output 集成 PLL/CLKDIV、编码器及串行器。上游须在 video_ready 为低时复位显示管线。RGB 为 R 高8位、G 中8位、B 低8位；通道0蓝色及同步、1绿色、2红色。串行器异步复位，等待4个像素周期清空编码流水。
当前时钟源码 9a463693：厂商模型两段各1000像素、5000串行上升沿通过；三通道复位前后共11150位逐位匹配独立编码参考。独立综合62e5031e460d通过。完整融合导出与时序需按各自源码哈希查验 evidence，不能沿用旧版本通过结论。

HDMI0 引脚模板取自同提交官方 Pro Dock 示例；其他音频、麦克风与演奏席约束未完成。探索性自动分配 IO 工程一律不得烧录。尚无物理屏幕验收。

复位路径修正：OSER10 RESET 不再直接由 pixel 域 ready 驱动，改为立即置位、serial 上升沿两级同步释放。负沿释放候选虽消除 removal，却产生到 PCLK 的 recovery 违例，已保留失败证据，未发布为通过版本。当前实现以最新 source-bound 时序报告为准。

当前复位实现7b4bfcad：两级 FCLK 负沿复位桥接，再用 FCLK 正沿寄存器释放 OSER。直接正沿同步候选09812e43347b仍有2条同步器CLEAR removal违例，未通过。新候选逐位模型通过，正在检验全部 recovery/removal 路径，不添加 false path 掩盖这些同步时钟路径。

当前小模块时序e46eac9479a7已通过：三时钟50/126/25.2MHz，Setup0、Hold0，包含recovery/removal；无false-path约束。仅固定时钟/复位/官方HDMI0引脚，其余IO自动分配，仍禁止烧录，不代表整机时序或实屏通过。
