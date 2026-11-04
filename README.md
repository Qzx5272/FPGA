# 星群 STARCLUSTER FPGA 演奏台

基于 Tang Mega 138K Pro 的 FPGA 音频合成与交互演奏工程，包含 Verilog 固件、Python 桌面上位机、硬件约束、测试及发布固件。

## 项目入口

- [演奏台说明](synth/band/README.txt)
- [基础合成器说明](synth/README.md)
- [当前发布版本](synth/band/CURRENT_RELEASE.json)
- [硬件接口](synth/band/HARDWARE_INTERFACE.txt)
- [验收标准与已知边界](synth/band/FINAL_ACCEPTANCE_STANDARD_20261028.md)
- [第三方声明](synth/band/THIRD_PARTY_NOTICES.txt)

## 目录

- `synth/band/`：演奏台固件、上位机、硬件资料、实验模块与验证记录。
- `synth/rtl/`、`synth/host/`：基础合成器逻辑与桌面控制程序。
- `synth/voice/`：中文人声相关资料与实现。
- `assets/`：项目参考资源。
- 根目录 `.cmd`：Windows 启动及 FPGA 下载入口。

使用前按对应说明安装依赖、准备 Gowin 工具，并检查板卡型号、实际串口与引脚连接。部分启动脚本使用本机 `.venv` 和默认串口，迁移到其他电脑时需按实际环境配置。

仓库保留现有实现及验证状态，不表示所有实验模块已完成实物验收。具体边界以各模块说明和验收记录为准。

## 版本控制范围

源码、项目资源、发布固件和验证说明纳入版本控制。`tmp/`、`output/` 中的临时工作文件与生成交付包、工具缓存、构建中间文件、本机配置和超大原始耐久测试遥测不上传；本地文件仍保留。
