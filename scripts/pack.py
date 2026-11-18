#!/usr/bin/env python3
"""Build an offline, ready-to-run pack: the project, its built helpers and the
pinned Wine and DXVK archives, as a .tar.gz and as a self-installing .run file.
The CrealityScan installer is never included; users supply it from Creality.

    python3 scripts/pack.py [--out DIR]
"""
import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import NAMES as BUILD_NAMES  # noqa: E402
from common import LOCK, ROOT, digest  # noqa: E402
import fetch  # noqa: E402
import onboard  # noqa: E402


def project_files():
    """Tracked files plus new, non-ignored ones, read from the working tree."""
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z', '--cached', '--others',
                          '--exclude-standard'], capture_output=True, check=True).stdout
    names = sorted({n for n in out.decode().split('\0') if n})
    # A stray nested copy of the project is not part of it.
    return [n for n in names if not n.startswith('crealityscan-linux-compat/') and (ROOT/n).is_file()]


def built_helpers():
    """build/ files, refusing a stale or incomplete build."""
    manifest = json.loads((ROOT/'build/manifest.json').read_text())
    if sorted(manifest) != sorted(BUILD_NAMES):
        raise RuntimeError('build/manifest.json does not list every helper; run creality.py build')
    for name, h in manifest.items():
        if digest(ROOT/'build'/name) != h:
            raise RuntimeError(f'build/{name} does not match its manifest; rebuild')
    licenses = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'build/licenses').glob('*') if p.is_file())
    if not licenses:
        raise RuntimeError('build/licenses is empty; third-party notices must ship with the helpers')
    return [f'build/{n}' for n in BUILD_NAMES] + ['build/manifest.json'] + licenses


def runtime_archives(cache):
    """The pinned runner and DXVK archives, downloaded (and checked) if needed."""
    out = []
    for url, h in ((LOCK['runner_archive_url'], LOCK['runner_archive_sha256']),
                   (LOCK['dxvk_archive_url'], LOCK['dxvk_archive_sha256'])):
        path = fetch.download(url, h, cache)
        if digest(path) != h:
            raise RuntimeError(f'{path} does not match its pin')
        out.append(path)
    return out


def add(t, top, arcname, path):
    info = t.gettarinfo(str(path), f'{top}/{arcname}')
    info.uid = info.gid = 0; info.uname = info.gname = ''
    info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
    with open(path, 'rb') as f:
        t.addfile(info, f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT/'dist')
    ap.add_argument('--cache', type=Path, default=onboard.data_home()/'crealityscan-linux/runtime/downloads',
                    help='where pinned Wine/DXVK archives are kept or downloaded')
    args = ap.parse_args()
    version = LOCK['crealityscan_tested'][0]['version']
    top = f'crealityscan-linux-{version}'
    files = [(n, ROOT/n) for n in project_files() + built_helpers()]
    files += [(f'downloads/{p.name}', p) for p in runtime_archives(args.cache)]

    sums = ''.join(f'{digest(p)}  {n}\n' for n, p in files)
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out/f'{top}-pack.tar.gz'
    tmp = target.with_suffix('.partial')
    with tarfile.open(tmp, 'w:gz') as t:
        for name, path in files:
            add(t, top, name, path)
        info = tarfile.TarInfo(f'{top}/SHA256SUMS'); info.size = len(sums.encode()); info.mode = 0o644
        t.addfile(info, io.BytesIO(sums.encode()))
    tmp.replace(target)
    payload = target.read_bytes()
    h = hashlib.sha256(payload).hexdigest()
    header = (ROOT/'scripts/run-header.sh').read_text()
    line = header.count('\n') + 1
    header = header.replace('@PAYLOAD_LINE@', str(line)).replace('@PAYLOAD_SHA256@', h)
    if header.count('\n') + 1 != line: raise RuntimeError('run header line count changed')
    run = args.out/f'{top}.run'
    tmp = run.with_suffix('.partial')
    tmp.write_bytes(header.encode() + payload); tmp.chmod(0o755); tmp.replace(run)
    sums = []
    for f in (target, run):
        fh = hashlib.sha256(f.read_bytes()).hexdigest(); sums.append(f'{fh}  {f.name}\n')
        print(f'{f} ({f.stat().st_size / 1e6:.0f} MB) SHA-256: {fh}')
    (args.out/'SHA256SUMS').write_text(''.join(sums))
    for old in args.out.glob('*.tar.gz.sha256'): old.unlink()


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        print('Pack failed:', e, file=sys.stderr); sys.exit(1)
