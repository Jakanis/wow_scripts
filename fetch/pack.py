"""
Archives what fetch.py downloaded since the previous pack, so it can be
dropped over the local caches.

    python fetch/pack.py                 # fetch/fetched_<date>_<time>.tar.gz

The archive holds the files in fetch/manifest.txt plus the metadata pickles
it names, with paths relative to the repository root. Extract it there:

    tar -xzf fetched_<date>_<time>.tar.gz -C D:/dev/wow_scripts

Once the archive is written, the manifest is kept as fetch/packed_<date>_<time>.txt
and the next fetch run starts a new one, so every archive holds only what is
new. To pack the same files again, rename that list back to manifest.txt.
"""

import datetime
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = pathlib.Path(__file__).with_name('manifest.txt')


def main() -> int:
    if not MANIFEST.exists():
        print('nothing fetched since the last pack: no manifest')
        return 1
    paths = sorted({line.strip() for line in MANIFEST.read_text(encoding='utf-8').splitlines() if line.strip()})
    stamp = f'{datetime.datetime.now():%Y%m%d_%H%M}'
    out = MANIFEST.with_name(f'fetched_{stamp}.tar.gz')
    missing = 0
    try:
        with tarfile.open(out, 'w:gz') as tar:
            for rel in paths:
                path = ROOT / rel
                if path.exists():
                    tar.add(path, arcname=rel)
                else:
                    missing += 1
    except BaseException:
        out.unlink(missing_ok=True)  # a half-written archive, e.g. when the disk fills up
        raise
    MANIFEST.rename(MANIFEST.with_name(f'packed_{stamp}.txt'))
    print(f'{out}: {len(paths) - missing} file(s)' + (f', {missing} named in the manifest no longer exist' if missing else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
