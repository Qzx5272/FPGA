"""Package immutable diagnostic sources and evidence, bound to the V5.1 delivery."""
from pathlib import Path
import datetime,hashlib,json,zipfile
root=Path(__file__).resolve().parents[3];band=root/'synth/band'
out=root/'output/final_workstation_20261022'
base=out/'星群V5.1_完整源码与一小时验证工程.zip'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base_hash=sha(base)
assert json.loads(base.with_name(base.stem+'_源码复现校验.json').read_text(encoding='utf-8'))['archive_sha256']==base_hash
hw=band/'evidence/hardware_diagnostic_43008.json';h=json.loads(hw.read_text())
restore=band/'evidence/restored_band_after_diagnostic.json';rest=json.loads(restore.read_text())
assert h['status']=='passed' and rest['status']=='passed'
assert datetime.datetime.fromisoformat(rest['time'])>datetime.datetime.fromisoformat(h['finished']), 'Restoration evidence must postdate this diagnostic test'
release=band/'release/diagnostic43008';m=json.loads((release/'manifest.json').read_text())
assert m['bitstream_sha256']==h['bitstream_sha256']==sha(release/'diagnostic43008.fs')
for name,digest in m['sources'].items():assert sha(release/'source_snapshot'/name)==digest
ev=band/'evidence/diagnostic43008'
spectral=json.loads((ev/'behavioral_spectrum.json').read_text())
assert spectral['state']=='passed' and spectral['verified_peaks']==43008
assert 'checked=986835' in (ev/'vendor_primitive_equivalence.log').read_text()
report=f'''星群 V5.1：43008 独立分量验证补充
生成时间：{datetime.datetime.now().isoformat(timespec='seconds')}
基础完整工程包：{base.name}
基础包 SHA256：{base_hash}

本补充不替换默认乐队音源，不改变256音符槽的完整乐队容量。
独立诊断配置采用42条1024深度分量通道；每个分量保留独立相位、频率、包络、目标及变化速率。
将每通道正弦表从两个RAM变为一个1024x18双端口DPX9B，保留原插值输出及流水延迟。
物理资源：RAM336/340、DSP86/298、逻辑31781/138240、寄存器12807/139140。
50MHz布线后Setup/Hold违例0；报告Fmax50.173MHz。时序余量很小，这不是芯片绝对上限。

证据分为三层，不能互相替代：
1. 厂商DPX9B模型与原核对照986835个有效样本，逐位相同；覆盖区间边界、随机相位、有效信号间断和复位。
2. 等价双读行为模型运行135168个音频样本；独立频率及不同包络验证43008个FFT谱峰。
   最大相对幅度误差{spectral['max_relative_error']:.8f}；此频谱不是板端DAC录音。
3. 真板持续60秒43008活跃分量，最大1030周期，期限违例0，CRC错误{h['bad_crc']}。
   最后地址归零后活跃数43007，恢复后43008；停止通过。
   该诊断无嵌入构建ID，依靠下载日志、位流哈希和回传类型/容量关联。
位流SHA256：{h['bitstream_sha256']}

已恢复默认band_57c8f7b5b006并读回身份，停止状态0活跃声部，发送总音量0。未写Flash。
第一次恢复确认未通过停音回执或CRC检查；第二次确认通过。原助手脚本首次失败未保存原始回传，原因未定位，已保留失败说明并修复证据保存及恢复时间校验。
用户报告音频输出、MIDI、麦克风、压力输入等外设均未接；模拟音质、实际可闻谱峰、实物交互和物理冷启动未验收。

使用：将project目录合并到V5.1基础包。保留基础包的CURRENT_RELEASE.json及主RTL不变。
本包包含diagnostic43008完整冻结源码、位流、时序/资源报告、谱峰测试源码、原语等价测试和板测原始回传。
复现构建：运行tools/prepare_rom_trial.py <新目录> --primitive；在生成工程运行tools/build_diagnostic.py 6 10 42。
复现原语比较：用Icarus编译冻结hq_sine_quarter.v、本包tb_rom_equivalence.v、hq_sine_reference.v及厂商gw5a/prim_sim.v，
并将冻结源码和本包测试目录加入-I路径；运行vvp。厂商模型由已安装Gowin提供，不在包内重分发。
频谱复现：prepare_rom_trial.py <另一个新目录>（不加--primitive），再运行verilate_pool.py 6 10 42 diverse。
下载仅使用load_sram.ps1 -ReleaseDirectory synth/band/release/diagnostic43008 -BitstreamName diagnostic43008.fs。
运行hardware_diagnostic.py时传入本次新下载日志；测试后恢复CURRENT_RELEASE.json指定乐队，再运行verify_restored_board.py。
构建时需要安装Gowin、Python依赖、OSS CAD及C++工具链；不同工具/布线版本应重新验收时序和板端行为。
'''
report_path=out/'43008分量_验证补充.txt';report_path.write_text(report,encoding='utf-8')
files=list(release.rglob('*'))+list(ev.rglob('*'))
files += [hw,hw.with_suffix('.raw'),restore,restore.with_suffix('.raw')]
files += [band/'evidence/restoration_first_attempt_43008.json']
files += [band/'tools'/n for n in ('package_43008_addendum.py','prepare_rom_trial.py','hardware_diagnostic.py','load_sram.ps1','verify_restored_board.py')]
files += list(Path(h['program_log']).glob('*'))
restore_logs=[p.parent for p in (band/'evidence').glob('program_*/loaded_manifest.json') if json.loads(p.read_text()).get('bitstream_sha256')==rest['bitstream_sha256']]
files += list(max(restore_logs,key=lambda p:p.name).glob('*'))
entries={'project/'+p.relative_to(root).as_posix():p.read_bytes() for p in files if p.is_file()}
entries[report_path.name]=report_path.read_bytes()
manifest=dict(base_archive_sha256=base_hash,files={n:hashlib.sha256(v).hexdigest() for n,v in entries.items()})
entries['MANIFEST.json']=json.dumps(manifest,indent=2,ensure_ascii=False).encode('utf-8')
archive=out/'星群V5.1_43008分量源码与板测补充.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in entries.items():z.writestr(name,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for n,digest in manifest['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==digest
result=dict(status='passed',archive=str(archive),sha256=sha(archive),base_archive_sha256=base_hash,files=len(entries),all_files_verified=True)
(out/'43008补充包校验.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(result,indent=2,ensure_ascii=False))
