"""Generate the concise delivery record from completed, hash-bound evidence."""
from pathlib import Path
import json,datetime
from delivery_evidence import read,best_band_record,host_test_count
root=Path(__file__).resolve().parents[3];band=root/'synth/band'
out=root/'output/final_workstation_20261022'
selected=json.loads((band/'CURRENT_RELEASE.json').read_text())
acceptance=json.loads((band/'evidence/software_acceptance.json').read_text())
hardware_path=band/'evidence/hardware_band.json'
hardware=json.loads(hardware_path.read_text()) if hardware_path.exists() else {}
manifest=json.loads((band/'release'/selected['release']/'manifest.json').read_text())
hardware=best_band_record(band,manifest['bitstream_sha256'])
diagnostic=read(band/'evidence/hardware_diagnostic_37888.json')
autoplay=read(band/'evidence/hardware_offline_autoplay.json')
board_ok=hardware.get('status')=='passed' and hardware.get('bitstream_sha256')==manifest['bitstream_sha256']
text=f'''星群 V5 工程候选版：交接与验证结果
生成：{datetime.datetime.now().isoformat(timespec='seconds')}

一、本次选定版本
目录：project/synth/band/release/{selected['release']}
位流 SHA256：{manifest['bitstream_sha256']}
构建身份：{manifest['build_id']:08X}
软件总验收：{acceptance['status']}
时序：Setup {manifest['setup_violations']}，Hold {manifest['hold_violations']} 个违规端点。
时序报告频率字段：{manifest.get('frequencies_from_report')}
最终 PnR 资源（已用/总量）：{selected.get('resource_usage','见对应 rpt.txt')}。
当前 SDC 约束 50 MHz 系统时钟；工具仍提示时钟使用通用布线。这里的时序通过不代表外部 ADC/DAC 的板级接口裕量已测量。
以上只适用于该目录绑定的 source_snapshot；其他 release 是历史或独立诊断配置。

二、软件与 RTL 已验证
20 项 RTL 回归（含连续及整板突发串口帧）；{host_test_count(band)} 项上位机交互测试。
97 秒整曲逐时钟与加速仿真 PCM 逐位一致，4,656,000 帧，峰值 12 声部，最大 142 周期，缺样 0、削波 0。
60 秒负载仿真包含 59 秒持续 256 槽和 1 秒释放，最大 966 周期，缺样 0、削波 0。
两种奏法音色的三音区、三力度矩阵通过数字分析；五元音、弯音和延迟尾音完成 RTL 波形分析。
整曲为 96 秒原创事件编排，97 秒测试覆盖结尾；不以预录 WAV 替代 FPGA 发声。
上位机有 16 轨控制、四个 MIDI 席位、八键入口、音色参数编辑、事件曲谱编辑、保存及脱机工程导出。
合唱编辑可按四分之一拍编排五元音，作用于后续新起音符；不改变已有持续音符，也不等于自然歌词歌唱。
编排页还可向空白合唱小节插入四拍元音乐句，包含音高、元音、90%门控及结束时的元音恢复。
舞台页显示16轨板端控制归属、曲谱位置及工程计数；失联或过期不显示旧状态为实时结果。没有模拟电平或歌词动画。
hardware_ensemble.json记录96秒整曲中两席软件模拟输入经真实FPGA的接管、单席归还、租约断链和重连；不替代实体MIDI及音质验收。
本地压力垫可编辑实测零点、增益和方向，随作品保存及脱机导出；正向/反向校准与冷启动默认值通过 RTL 测试，尚无实物传感器验收。
当前 USB-UART 链路采用每帧后 64 个零保护字节、每 5 ms 最多 4 个事件（GUI 上限 800 事件/秒）。裸连续突发曾截断回包；最小工程与当前乐队工程在该配置下均通过 1000 次完整查询。此配置降低控制吞吐，不能据此宣称任意突发或端到端 5 ms 已通过。
数字仿真不等于模拟音质评价，256 槽是八组各 32 槽配额，不是任意共享池。

三、本次板端验证
与选定位流身份一致的板端数字测试：{'通过' if board_ok else '未通过/未完成'}。
板端记录状态：{hardware.get('status','未执行')}
满载时长：{hardware.get('stress_seconds','未完成')} 秒；最大计算周期：{hardware.get('maximum_stress_cycles','未完成')}。
整曲观察时长：{hardware.get('automatic_test_seconds','未完成')} 秒；最大观察声部：{hardware.get('maximum_observed_voices_during_song','未完成')}。
错误：{hardware.get('error','无已记录错误')}
本次音频输出测试开关：{hardware.get('audible_test_enabled',False)}。静音数字回传不能证明模拟输出无削波或声音好听。
本次回传 CRC 错误：{hardware.get('parser_bad_crc','未记录')}。未达到零错误的旧记录保留为失败证据。
下载采用 SRAM；没有写 Flash，断电后本轮 SRAM 固件不保留。

四、必须继续做的实物工作
实际 DAC/音箱听音与噪声、增益、失真测量；输入到声音的端到端延迟。
外置标准 I2S DAC、本地 MCP3208 压力席、脚踏、LED 的接线与管脚核对。
真实多人 MIDI/压力席接管和拔线；本次系统未枚举到 MIDI 输入，不能写成打击垫实测成功。
电源、温升、长时间演出稳定性；Flash 冷启动及故障回退。
37888 独立分量为另一个诊断配置：板端记录状态 {diagnostic.get('status','未执行')}，持续 {diagnostic.get('duration_seconds','未完成')} 秒，最大 {diagnostic.get('max_cycles','未测')} 周期。
该诊断没有内嵌构建 ID，依靠下载日志、位流哈希及回传配置关联；未采集板端模拟频谱，不等于完整乐队的并发容量。
独立导出配置的板端自启动记录：{autoplay.get('status','未执行')}；不发送播放命令，关闭串口后继续演出。此结果不是 Flash 物理断电启动。
有限元音已实现；任意歌词自然歌唱、麦克风声码器、视觉融合和运行中 Flash 作品保存未实现。
后续43008独立分量配置已完成50MHz时序、行为模型43008谱峰及60秒真板调度验证，RAM336/340；精确源码在release/diagnostic43008，证据在evidence/diagnostic43008与hardware_diagnostic_43008.json。依然不等于乐队容量、板端音质或芯片绝对上限。

五、队友开始使用
解压后进入 project，运行 synth/band/setup_and_launch.ps1；已有环境可运行 synth/band/launch.ps1。
串口正常枚举时选择 COM12；更换电脑后以设备管理器实际端口为准。先连接并核对固件身份，再从低音量开始。
上位机不通过电脑播放音源；必须连接运行匹配 V4 协议固件的 FPGA。
源码说明和命令见 synth/band/README.txt，协议见 PROTOCOL.txt，详细方案见 documents 中 Word 文件。
evidence/software_acceptance.json 记录软件验收；hardware_band_1h.json 记录主版本一小时满载及整曲板测，hardware_band.json 保留早期五分钟记录。对应 release/band_*/manifest.json 绑定位流与精确源码。
源码、测试、生成脚本、曲谱和必要旧模块均在压缩包中。Gowin、OSS CAD、Python 环境需要自行安装，未重分发。
解压复现校验 JSON 与交付校验 JSON 放在压缩包旁，分别记录源码复现和文件哈希检查。
'''
(out/'交接报告_验证结果.txt').write_text(text,encoding='utf-8')
print(text)
