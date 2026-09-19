"""
Lists the ids every cache folder already holds, so a fetch run on another
machine can skip them without carrying the files themselves.

    python fetch/inventory.py            # writes fetch/inventory.json

Upload the file next to the code on the fetch machine; fetch.py reads it.
"""

import datetime
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = ('items', 'spells', 'npc', 'quests', 'objects')
OUT = pathlib.Path(__file__).with_name('inventory.json')


def day(timestamp: float) -> str:
    return datetime.date.fromtimestamp(timestamp).isoformat()


def main() -> int:
    inventory = {}
    rows = []
    for module in MODULES:
        cache = ROOT / 'generation' / module / 'cache'
        if not cache.is_dir():
            continue
        for folder in sorted(os.listdir(cache)):
            if not folder.startswith('wowhead_'):
                continue
            ids, oldest, newest = [], None, None
            with os.scandir(cache / folder) as entries:
                for entry in entries:
                    stem = entry.name.split('.')[0]
                    if not stem.isdigit():
                        continue
                    ids.append(int(stem))
                    written = entry.stat().st_mtime
                    oldest = written if oldest is None or written < oldest else oldest
                    newest = written if newest is None or written > newest else newest
            inventory[f'{module}/{folder}'] = sorted(ids)
            rows.append((newest or 0, f'{module}/{folder}', len(ids), oldest, newest))
        # the search result each folder was filled from
        for name in sorted(os.listdir(cache / 'tmp')) if (cache / 'tmp').is_dir() else []:
            if name.endswith('_metadata_cache.pkl'):
                written = (cache / 'tmp' / name).stat().st_mtime
                rows.append((written, f'{module}/tmp/{name}', 0, written, written))

    print(f'{"cache":<50} {"files":>7} {"oldest":>11} {"newest":>11}')
    for _, name, count, oldest, newest in sorted(rows):
        print(f'{name:<50} {count or "":>7} {day(oldest) if oldest else "":>11} {day(newest) if newest else "":>11}')
    OUT.write_text(json.dumps(inventory), encoding='utf-8')
    print(f'wrote {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
