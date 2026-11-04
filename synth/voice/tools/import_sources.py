"""Fetch pinned upstream pronunciation sources, preserving licenses and hashes."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('mozillazg/pinyin-data', '9193766130af24d2ac54230be979b2e98ac66223'),
    ('mozillazg/phrase-pinyin-data', 'cee0ed6e6e4898580cafd2bd5e3723e20b214aa0'),
    ('espeak-ng/espeak-ng', 'ba90c8e9f440ad544f674a790bb5f53878b6ffc5'),
]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Aurora-FPGA-voice-research'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()

def main():
    manifest = []
    for repo, commit in SOURCES:
        name = repo.split('/')[-1]
        base = ROOT / 'sources' / name
        files = {}
        omitted = []
        if name != 'espeak-ng':
            for path in ['LICENSE', 'README.md', 'pinyin.txt']:
                files[path] = fetch(f'https://raw.githubusercontent.com/{repo}/{commit}/{path}')
        else:
            archive = fetch(f'https://codeload.github.com/{repo}/tar.gz/{commit}')
            with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    path = member.name.split('/', 1)[1]
                    if path.startswith('phsource/') or path in ['COPYING', 'README.md', 'docs/phontab.md', 'docs/phonemes.md', 'docs/dictionary.md', 'src/libespeak-ng/wavegen.c']:
                        if path.lower().endswith(('.wav', '.ogg', '.mp3')):
                            omitted.append(path)
                        else:
                            files[path] = tar.extractfile(member).read()
        records = []
        for path, data in sorted(files.items()):
            dest = base / path
            if not dest.resolve().is_relative_to(base.resolve()):
                raise ValueError(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            records.append({'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest.append({'repository': f'https://github.com/{repo}', 'commit': commit,
                         'files': records, 'omitted_recording_files': sorted(omitted)})
        print(name, 'saved', len(records), 'files; omitted recordings', len(omitted), flush=True)
    (ROOT / 'sources.lock.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
