"""
Archives what fetch.py downloaded, so it can be dropped over the local caches.

    python fetch/pack.py                 # fetch/fetched_<date>.tar.gz

The archive holds the files in fetch/manifest.txt plus the metadata pickles
it names, with paths relative to the repository root. Extract it there:

    tar -xzf fetched_<date>.tar.gz -C D:/dev/wow_scripts
"""

import datetime
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = pathlib.Path(__file__).with_name('manifest.txt')


def main() -> int:
    if not MANIFEST.exists():
        print('nothing fetched: no manifest')
        return 1
    paths = sorted({line.strip() for line in MANIFEST.read_text(encoding='utf-8').splitlines() if line.strip()})
    out = MANIFEST.with_name(f'fetched_{datetime.date.today():%Y%m%d}.tar.gz')
    missing = 0
    with tarfile.open(out, 'w:gz') as tar:
        for rel in paths:
            path = ROOT / rel
            if path.exists():
                tar.add(path, arcname=rel)
            else:
                missing += 1
    print(f'{out}: {len(paths) - missing} file(s)' + (f', {missing} named in the manifest no longer exist' if missing else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
