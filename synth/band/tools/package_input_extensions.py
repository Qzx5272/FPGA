"""Supplement V5.2 with isolated, separately graded candidates and full sources."""
from pathlib import Path
import json,hashlib,zipfile,datetime
root=Path(__file__).resolve().parents[3];b=root/'synth/band';out=root/'output/final_workstation_20261022'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=out/'星群V5.2_整曲协作与元音乐句完整工程.zip'
base_record=json.loads(base.with_name(base.stem+'_源码复现校验.json').read_text(encoding='utf-8'))
assert base_record['status']=='passed' and base_record['archive_sha256']==sha(base)
release=b/'release/band_09ebdeb5e533';m=json.loads((release/'manifest.json').read_text())
hardware=json.loads((b/'evidence/hardware_band_single_ram.json').read_text())
restore=json.loads((b/'evidence/restored_band_after_diagnostic.json').read_text())
assert hardware['status']==restore['status']=='passed'
assert hardware['bitstream_sha256']==m['bitstream_sha256']==sha(release/'starcluster_band.fs')
assert datetime.datetime.fromisoformat(restore['time'])>datetime.datetime.fromisoformat(hardware['completed'])
for n,digest in m['snapshot_sha256'].items():assert sha(release/'source_snapshot'/n)==digest
assert json.loads((b/'evidence/audio_input/result.json').read_text())['status']=='passed'
assert json.loads((b/'evidence/vocoder_biquad/result.json').read_text())['status']=='passed'
files=[p for p in release.rglob('*') if p.is_file()]
for folder in ('experimental/audio_input','experimental/vocoder','evidence/audio_input','evidence/vocoder_biquad','evidence/band_single_ram_sine'):
    files += [p for p in (b/folder).rglob('*') if p.is_file() and p.suffix not in ('.vvp','.pyc')]
files += [b/'evidence'/n for n in ('hardware_band_single_ram.json','hardware_band_single_ram.raw','restored_band_after_diagnostic.json','restored_band_after_diagnostic.raw')]
files += [b/'tools'/n for n in ('test_audio_input.py','build_audio_input.py','test_vocoder_biquad.py','test_frozen_board.py','package_input_extensions.py','prepare_rom_trial.py')]
for program in ('program_20261024_230455','program_20261024_231427'):
    files += [p for p in (b/'evidence'/program).glob('*') if p.is_file()]
text='''星群V5.2补充：单RAM乐队候选与音频输入基础
将project合并到V5.2完整工程。默认CURRENT_RELEASE.json、正式rtl及旧位流不改变。
1. band_09ebdeb5e533：单RAM正弦核完整乐队候选，203/340RAM（原211），112DSP，29882逻辑。
50MHz Setup/Hold0，Fmax50.071MHz。厂商原语模型板顶层回归通过；真板300秒256音符+97秒整曲通过，最大966周期，CRC/期限/削波/拒绝0。
这是资源优化，声部容量仍256；没有宣称更高音质或稳定性上限。默认仍保留具有3600秒负载证据的57c8版本。
本次恢复身份57c8、0活跃音符、停止及主音量0已确认；未写Flash。
2. experimental/audio_input：新编写I2S24接收器与反向CDC。500组接收、100组跨域顺序、复位、帧错误与拥塞测试通过；Gowin仅综合通过。
尚无外设管脚、外部BCK时序/CDC物理验收、真实麦克风、输入时钟丢失检测或正式音源集成。
3. experimental/vocoder：VOXOS MIT模块参考来源与许可证保留。ported仅修正双二阶核第二级末项系数以及复位初始化。
独立定点参考的256组输入通过，原始模块在不同两级系数的第一个测试向量失败。不能由此推断原项目的所有实际系数都会触发该问题。
filterbank/mixer/constants/coeffs仍为未修改参考文件，仓库常量为16带；不能照搬报告的24带宣称实现容量。
完整声码器的滤波稳定性、溢出/削波、带宽、包络、混音、输入握手、资源与板级音质尚未验证。
来源：https://github.com/Li357/voxos ，固定commit见PROVENANCE.json；许可证见upstream/LICENSE。
输入时序依据：https://www.nxp.com/docs/en/user-manual/UM11732.pdf
复现：python synth/band/tools/test_audio_input.py；python synth/band/tools/test_vocoder_biquad.py。
候选ROM构建：prepare_rom_trial.py <新目录> --primitive，再在导出工程执行build_band.py；仿真须使用Gowin gw5a/prim_sim.v。
硬件检查仍用load_sram.ps1与hardware_check.py，明确传入候选release；测试后恢复CURRENT_RELEASE.json所指默认固件。
该补充不代表最终整机完成；未验证外设、模拟音质、真实多模态演出与物理冷启动均保持未完成。
'''
entries={'project/'+p.relative_to(root).as_posix():p.read_bytes() for p in files}
entries['补充说明.txt']=text.encode('utf-8')
manifest=dict(base_sha256=sha(base),files={n:hashlib.sha256(v).hexdigest() for n,v in entries.items()})
entries['MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
archive=out/'星群V5.2_单RAM音源与音频输入源码补充.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for n,data in entries.items():z.writestr(n,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for n,digest in manifest['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==digest
result=dict(status='passed',archive=str(archive),sha256=sha(archive),files=len(entries),base_sha256=sha(base),every_file_verified=True)
(out/'单RAM与输入补充校验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
