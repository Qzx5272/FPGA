# 星群 Android 原生应用 0.1.0

当前开发版已更新为 **0.2.0**，新增独立串口 FPGA 演奏页。接口、测试范围和候选固件说明见 [PHONE_UART_0.2.md](PHONE_UART_0.2.md)；下面保留0.1首轮实测记录。

Android 8+，包名 `cn.starcluster.controller`。原生 Java + Android BLE GATT，无 WebView、网页服务器或第三方运行时；安装后蓝牙控制无需电脑或 USB 转发。

## 交付与已验证结果

- APK：项目根 `output/android/Starcluster-0.1.0.apk`，开发签名，不是应用商店发布版本。
- 2026-10-31 已安装至用户 vivo X200 Pro。用户确认连接 C3 成功，改色成功，敲击后记录数增加。
- C3 v5：原有 MIDI 接收保留；配置事务先核对 Pocket_004 型号，再写入并回读。
- 单键 MIDI 编号编辑：预设、Bank、键号选择；先读 26 字节记录，只改音符字节，再回读完整记录核对其它字段。只接受 mode0 音符垫。
- Windows BLE 实物测试保持预设4 / Bank2 / 键5 的音符24不变，验证写入与完整记录回读；此测试不等于所有16物理键映射已验证。
- Android 构建、APK v2/v3签名校验通过。测试证据位于 `../../evidence/android_app_20261031/`。

## 功能

1. 设备：主动扫描、选择 C3、请求附近设备权限、状态显示、固定示范垫 RGB 配置与回读反馈。
2. 键位：16键手机方案持久化、单键音符下发、方案 JSON 导出。方案属于本地16键模板；选择预设/Bank不会自动读取设备映射，不能把模板值当成设备当前值。
3. 曲谱：示例、系统文件选择器导入、HTTPS在线下载、结构/范围校验、本地保存、导出。当前不向FPGA上传。
4. 记录：独立BLE通知逐条接收打击垫MIDI事件、序号缺失检查、结束保存、JSON导出。后台切换停止记录；断链/序号缺失/记录结束仍有按住音符会标记不完整。连接前已按下的音符状态无法回溯。不是 WAV 音频录音。

在线曲谱格式（最大1MB，最多20000音符，按at_ms排序，BPM20–300）：

```json
{"format":"starcluster-score-1","title":"练习","bpm":120,"events":[{"at_ms":0,"duration_ms":400,"note":60,"velocity":90}]}
```

HTTPS下载不自动跟随重定向，使用文件最终地址。暂无预置线上曲谱服务器。实际手机联网下载、文件导入导出、后台和20次重连仍需专项实测。

## 与高云题目二的关系

已核对官方网页：https://www.gowinsemi.com.cn/university/match2026 （2026-10-31）。题目二拓展4列出蓝牙App联动、在线曲谱下载、键位自定义、演奏录音回传；音频核心仍须由FPGA HDL实时生成。

| 项目 | 当前证据 | 仍需完成 |
|---|---|---|
| 蓝牙App联动 | 原生App连接、改色及事件计数经真实手机确认 | 多次重连、并发与长稳 |
| 键位自定义 | 软件实现；单键同值写入及26字节回读实测 | 16键/Bank实物映射和掉电保存 |
| 在线曲谱下载 | HTTPS客户端、校验、本地保存已实现并编译 | 手机网络实测、曲谱服务、C3至FPGA传输和校验 |
| 演奏录音回传 | 当前仅演奏事件回传与保存 | FPGA音频采集/存储、传输及真实音频文件验证 |
| 脱机LED曲目指引 | 本App不作为完成证据 | 板端曲谱调度与LED同步 |
| 纯HDL/I2S/多维输入/复音/延迟 | 由FPGA整机单独验收 | App成功不能替代整机验收 |

## 构建

无Gradle依赖，使用官方Android SDK平台35、build-tools35和JDK21：

```powershell
python synth/band/bridges/android/build.py --jdk D:/CUBEMX/jre --sdk tmp/android-sdk
```

流程：aapt2资源编译/链接 → javac → d8 → zipalign → apksigner → APK签名验证。
SDK归档来源Google官方repository，下载时按官方XML给出的SHA1校验。开发签名密钥在build目录，保留可持续覆盖安装；不得作为正式发布密钥使用。

## C3 v5 接口

服务 `4fafc201-1fb5-459e-8fcc-c5c9c331914b`，命令c202，状态c203，MIDI事件c204。
8字节命令：`53 01 ID KIND A B C CHECKSUM`，末字节是前7字节和的按位反。
- KIND1：ABC=RGB，固定示范垫预设零基3/槽20。
- KIND2：ABC=预设0–3、槽0–111、音符0–127。槽=Bank零基编号×16+键零基编号。
- 状态保持v4的20字节格式；仅结果2代表设备回读通过，GATT写入成功不等于设备已修改。
- MIDI通知13字节：`4D 01 sequenceLE32 c3MillisLE32 status data1 data2`。序号对应C3累计decoded计数；不是200ms采样状态推导的事件。

当前为本地开发原型，BLE服务尚未加入配对认证，固定示范垫改色和键位编辑接口仅用于受控联调环境。
