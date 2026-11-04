# 中文发音词库与合成参考资料

本目录包含离线读音查询、上游音素参考资料及第一版人声参数移植。新增元音和“你好”试唱原型，详见 [移植说明](PORT.md)。**尚未实现任意歌词唱歌，也没有完整中文人声参数库**。

## 已整理的来源

| 上游项目 | 本地内容 | 用途与许可 |
|---|---|---|
| [pinyin-data](https://github.com/mozillazg/pinyin-data) | `sources/pinyin-data/pinyin.txt`、README、LICENSE | 单字与候选读音；上游项目声明 MIT，README 保留了其数据来源说明 |
| [phrase-pinyin-data](https://github.com/mozillazg/phrase-pinyin-data) | `sources/phrase-pinyin-data/pinyin.txt`、README、LICENSE | 词组读音；上游项目声明 MIT；本次未导入另行汇编的 large_pinyin.txt 和 cc_cedict.txt |
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng) | `sources/espeak-ng/phsource/`、文档、COPYING | 普通话及共享音素、共振峰/包络参考数据；GPL-3.0-or-later，独立保留原文与许可证 |

所有下载固定到提交版本，详见 `sources.lock.json`，每个文件有 SHA-256。这些是上游数据快照，不代表本项目原创，也不代表它们已完成 FPGA 适配。直接复用、改编和分发时须保留并遵守相应许可，不能将 eSpeak 派生资料自动视为 MIT。各上游 README 中列出的原始数据来源也一并保留。

eSpeak 的共享音素存在跨语言引用，因此保留整个 phsource 的非音频文件用于研究。下载时排除了 203 个带音频扩展名的文件；测试还检查了保留文件中没有 RIFF/WAVE 音频。这不是完整可运行的 eSpeak 安装包。**不应直接运行其全部发音路径作为参赛方案**：普通话文件中 15 个定义直接调用 WAV/AddWav，间接调用还需要继续审核。音素定义数量也包含声调标记，不能当作可发声种类计数。

## 生成结果

- `generated/lexicon.sqlite3`：44,435 个汉字，47,111 个词组，读音用 JSON 保存，保留候选项。
- `generated/syllables.json`：1,559 个带调拼写条目，保留带调形式、无调拼写及声调编号；这不是 1,559 个独立音素。
- `generated/mandarin_phoneme_reference.json`：68 个普通话定义的原文、行号、直接资源引用及采样标记。
- `generated/validation.json`：来源校验和统计结果。
- `examples/pronunciation.json`：短句离线查询示例。

## 使用与复现

在项目根目录运行（仅 Python 标准库，不需要额外安装）：

```powershell
python synth/voice/tools/lexicon.py "你好，重庆银行音乐" --output synth/voice/examples/pronunciation.json
python synth/voice/tools/build_lexicon.py
python synth/voice/tools/test_lexicon.py
```

需要重新下载同一版本时运行 `python synth/voice/tools/import_sources.py`，再运行构建脚本。构建前会校验所有导入文件的哈希。

查询使用最长词组匹配，单字回退时保留全部读音，用 `needs_review` 标记歧义。标点标为停顿，未知字符明确标记，不静默丢弃。这是基础规则查询，不保证复杂分词、所有多音字都正确；词组命中也不等于语境必然正确。歌词应人工复核。没有额外实施变调、儿化或歌唱咬字规则；音高应来自乐谱，不能直接把普通话声调曲线当成歌唱旋律。

## 还需要完成的声音参数工作

当前词库解决“字怎么读”，eSpeak 原始资料提供“如何发音”的研究起点，两者尚未自动贯通。后续需要：

1. 选定短句，确认拼音，建立拼音到发音单元的映射，处理 j/q/x 后 ü、舌尖元音及复韵母等特殊情况。
2. 从参考格式解析共振峰随时间的变化，结合我们自己的声源/滤波结构转换为频率、带宽、增益与过渡参数；不能把原始二进制文件直接当滤波系数。
3. 对引用录音的辅音，设计 FPGA 噪声源、爆破激励和滤波器，替换采样依赖。
4. 联合乐谱安排声母、韵母时长；用软件参考模型试听，验证参数与定点量化，再实现 HDL。

数据库主要留在电脑端。FPGA 后续只需保存选定的合成参数表，并接收音素、音高和时长等控制信息，不需要装入整个汉字词典。
