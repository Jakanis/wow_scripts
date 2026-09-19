"""
Lists the ids every cache folder already holds, so a fetch run on another
machine can skip them without carrying the files themselves.

    python fetch/inventory.py            # writes fetch/inventory.json

Upload the file next to the code on the fetch machine; fetch.py reads it.
"""

import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = ('items', 'spells', 'npc', 'quests', 'objects')
OUT = pathlib.Path(__file__).with_name('inventory.json')


def main() -> int:
    inventory = {}
    for module in MODULES:
        cache = ROOT / 'generation' / module / 'cache'
        if not cache.is_dir():
            continue
        for folder in sorted(os.listdir(cache)):
            if not folder.startswith('wowhead_'):
                continue
            ids = sorted(int(name.split('.')[0]) for name in os.listdir(cache / folder)
                         if name.split('.')[0].isdigit())
            inventory[f'{module}/{folder}'] = ids
            print(f'{module}/{folder}: {len(ids)}')
    OUT.write_text(json.dumps(inventory), encoding='utf-8')
    print(f'wrote {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
