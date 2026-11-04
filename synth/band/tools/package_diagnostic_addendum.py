"""Append independently verified board evidence without altering the base ZIP."""
from pathlib import Path
import hashlib,json,zipfile,datetime
root=Path(__file__).resolve().parents[3];band=root/'synth/band'
out=root/'output/final_workstation_20261022'
hardware=band/'evidence/hardware_diagnostic_37888.json'
result=json.loads(hardware.read_text())
restored=band/'evidence/restored_band_after_diagnostic.json'
restoration=json.loads(restored.read_text())
assert result['status']=='passed' and restoration['status']=='passed'
base=out/'星群V5_完整源码与验证工程.zip'
base_hash=hashlib.sha256(base.read_bytes()).hexdigest()
assert base_hash==json.loads((out/'交付校验.json').read_text(encoding='utf-8'))['sha256']
program=Path(result['program_log'])
restore_logs=[]
for p in (band/'evidence').glob('program_*/loaded_manifest.json'):
    m=json.loads(p.read_text())
    if m.get('bitstream_sha256')==restoration['bitstream_sha256']:restore_logs.append(p.parent)
restore_log=max(restore_logs,key=lambda p:p.name)
text=f'''星群 V5 板端性能验证补充（{datetime.datetime.now().isoformat(timespec='seconds')}）

本补充更新原交接报告中“37888 分量尚未上板”的状态，不改变完整乐队的容量和验证范围。
基础完整交付包 SHA256：{base_hash}

独立诊断固件：diagnostic37888
位流 SHA256：{result['bitstream_sha256']}
板端持续运行 {result['duration_seconds']} 秒，活跃分量 37888，最大计算周期 {result['max_cycles']}。
持续负载段期限违例 0，回传 CRC 错误 {result['bad_crc']}。
由板端样本计数与电脑单调时钟估算采样进度 {result['observed_sample_rate_hz']:.2f} Hz；这不是精密时钟测量。
单独将最后一个地址的包络归零后，活跃数降为 37887；恢复后回到 37888；停止命令通过。

证据边界：诊断固件没有内嵌构建 ID，依据下载日志、位流哈希、诊断回传类型及容量关联。
这是单独配置，不是整支乐队同时拥有 37888 声部，也不是板子的绝对极限。
本次没有采集模拟输出或板端音频频谱，不证明每个分量在实际 DAC 输出中均可闻。
诊断固件播放时启用低幅监听输出；该过程不是静音音质测试。
此前的独立频率、包络和有效谱峰证据仍属于 RTL 仿真层。

测试后已重新下载 band_57c8f7b5b006，读回构建身份 0x57C8F7B5、容量 256。
确认停止状态、活跃声部 0，已发送总音量 0；未写 Flash。
真实音质、端到端延迟、多人实体演奏、外设接线、长时温升和 Flash 冷启动仍待完成。

文件包含新增验收脚本、支持指定 .fs 文件名的 SRAM 下载脚本、原始回传、下载日志及恢复确认。
将 project 下文件合并到基础包的 project 目录即可。基础包内旧报告请与本补充一起阅读。
复现：先用 load_sram.ps1 -ReleaseDirectory synth/band/release/diagnostic37888 -BitstreamName diagnostic37888.fs 下载，
再运行 hardware_diagnostic.py --release synth/band/release/diagnostic37888 --program-log <本次下载日志目录> --seconds 60。
完成后务必下载 CURRENT_RELEASE.json 指向的乐队固件，并运行 verify_restored_board.py。
'''
report=out/'37888分量_板端验证补充.txt';report.write_text(text,encoding='utf-8')
files=[hardware,hardware.with_suffix('.raw'),restored,restored.with_suffix('.raw')]
files += [band/'tools'/n for n in ('hardware_diagnostic.py','verify_restored_board.py','load_sram.ps1','package_diagnostic_addendum.py')]
files += list(program.glob('*.txt'))+list(program.glob('*.json'))+list(restore_log.glob('*.txt'))+list(restore_log.glob('*.json'))
entries={('project/'+p.relative_to(root).as_posix()):p.read_bytes() for p in files}
entries['37888分量_板端验证补充.txt']=report.read_bytes()
manifest=dict(base_archive_sha256=base_hash,files={n:hashlib.sha256(b).hexdigest() for n,b in entries.items()})
entries['MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
archive=out/'星群V5_37888分量板端验证补充.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in entries.items():z.writestr(n,b)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for n,digest in manifest['files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==digest
record=dict(status='passed',archive=str(archive),bytes=archive.stat().st_size,
    sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),base_archive_sha256=base_hash,
    files=len(entries),every_file_verified=True)
(out/'37888补充包校验.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
