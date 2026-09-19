"""
Downloads Wowhead data for the generators without parsing it, so the slow,
rate-limited part can run on another machine.

    python fetch/fetch.py                              # every module, every expansion
    python fetch/fetch.py --module items spells        # some modules
    python fetch/fetch.py --expansion forever          # one expansion of each
    python fetch/fetch.py --module spells --render     # also the rendered spell pages

Ids listed in fetch/inventory.json (written by inventory.py on the machine
that holds the caches) count as present and are skipped. Every file this run
writes is appended to fetch/manifest.txt, which pack.py turns into an archive.

Per module this is the download half of retrieve_*_data():
  items    search metadata, an XML per item, an HTML page for readable items
  spells   search metadata, a raw page per spell, and with --render the
           Chromium-rendered page for spells that have none yet
  npc      search metadata, a page per NPC where RETRIEVE_QUOTES is on, and
           the forced ids everywhere
  quests   search metadata, a page per quest
  objects  search metadata, a page per object
"""

import argparse
import importlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import __main__  # noqa: E402

MODULES = ('items', 'spells', 'npc', 'quests', 'objects')
INVENTORY = pathlib.Path(__file__).with_name('inventory.json')
MANIFEST = pathlib.Path(__file__).with_name('manifest.txt')


def load_module(name):
    os.chdir(ROOT / 'generation' / name)
    module = importlib.import_module(f'generation.{name}.{name}')
    # the generators run as scripts, so their pickles name every class as
    # __main__.<Class>; match that or the local run cannot load what we write
    for attr, value in vars(module).items():
        if isinstance(value, type) and value.__module__ == module.__name__:
            value.__module__ = '__main__'
            setattr(__main__, attr, value)
    return module


class Run:
    def __init__(self, module: str, inventory: dict):
        self.module = module
        self.inventory = inventory
        self.written = 0
        self.skipped = 0

    def have(self, folder: str, id: int, ext: str) -> bool:
        if id in self.inventory.get(f'{self.module}/{folder}', ()):
            return True
        return os.path.exists(f'cache/{folder}/{id}.{ext}')

    def fetch(self, folder: str, id: int, ext: str, save) -> bool:
        if self.have(folder, id, ext):
            self.skipped += 1
            return False
        save()
        path = f'cache/{folder}/{id}.{ext}'
        if os.path.exists(path):
            with open(MANIFEST, 'a', encoding='utf-8') as f:
                f.write(f'generation/{self.module}/{path}\n')
            self.written += 1
        return True

    def note_metadata(self, folder: str):
        with open(MANIFEST, 'a', encoding='utf-8') as f:
            f.write(f'generation/{self.module}/cache/tmp/{folder}.pkl\n')


def fetch_items(m, run: Run, expansion: str, args):
    props = m.expansion_data[expansion]
    md = m.get_wowhead_items_metadata(expansion)
    run.note_metadata(props[m.METADATA_CACHE])
    ids = (set(md) - set(props[m.IGNORES])) | set(props[m.FORCE_DOWNLOAD])
    for id in sorted(ids):
        run.fetch(props[m.XML_CACHE], id, 'xml', lambda: m.save_xml_page(expansion, id))
    # readable items also have a page; the flag is a phrase in the XML
    for id in sorted(ids):
        xml = f'cache/{props[m.XML_CACHE]}/{id}.xml'
        if os.path.exists(xml) and 'Right Click to Read' in open(xml, encoding='utf-8').read():
            run.fetch(props[m.HTML_CACHE], id, 'html', lambda: m.save_html_page(expansion, id))


def fetch_spells(m, run: Run, expansion: str, args):
    props = m.expansion_data[expansion]
    md = m.get_wowhead_spell_metadata(expansion)
    run.note_metadata(props[m.METADATA_CACHE])
    ids = set(md) | set(props.get(m.FORCE_DOWNLOAD, []))
    for id in sorted(ids):
        run.fetch(props[m.HTML_CACHE] + '_raw', id, 'html', lambda: m.save_page_raw(expansion, id))
    if args.render:
        os.makedirs(f'cache/{props[m.HTML_CACHE]}_rendered', exist_ok=True)
        for id in sorted(ids):
            run.fetch(props[m.HTML_CACHE] + '_rendered', id, 'html', lambda: m.save_page_calc(expansion, id))


def fetch_npc(m, run: Run, expansion: str, args):
    props = m.expansion_data[expansion]
    md = m.get_wowhead_npc_metadata(expansion)  # applies IGNORES and adds FORCE_DOWNLOAD
    run.note_metadata(props[m.METADATA_CACHE])
    ids = set(md) if props[m.RETRIEVE_QUOTES] else set(props[m.FORCE_DOWNLOAD])
    for id in sorted(ids):
        run.fetch(props[m.HTML_CACHE], id, 'html', lambda: m.save_page(expansion, id))


def fetch_quests(m, run: Run, expansion: str, args):
    props = m.expansion_data[expansion]
    md = m.get_wowhead_quests_metadata(expansion)
    run.note_metadata(props[m.METADATA_CACHE])
    for id in sorted(md):
        run.fetch(props[m.HTML_CACHE], id, 'html', lambda: m.save_page(expansion, id))


def fetch_objects(m, run: Run, expansion: str, args):
    props = m.expansion_data[expansion]
    md = m.get_wowhead_object_metadata(expansion)
    run.note_metadata(props[m.METADATA_CACHE])
    ids = set(md) | set(props[m.FORCE_DOWNLOAD])
    for id in sorted(ids):
        run.fetch(props[m.HTML_CACHE], id, 'html', lambda: m.save_html_page(expansion, id))


FETCHERS = {
    'items': fetch_items,
    'spells': fetch_spells,
    'npc': fetch_npc,
    'quests': fetch_quests,
    'objects': fetch_objects,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--module', nargs='+', choices=MODULES, default=list(MODULES))
    ap.add_argument('--expansion', nargs='+', help='limit to these expansions (default: all in the module)')
    ap.add_argument('--render', action='store_true', help='spells: also fetch the Chromium-rendered pages')
    ap.add_argument('--inventory', type=pathlib.Path, default=INVENTORY)
    args = ap.parse_args()

    inventory = {}
    if args.inventory.exists():
        inventory = {k: set(v) for k, v in json.loads(args.inventory.read_text(encoding='utf-8')).items()}
        print(f'inventory: {sum(len(v) for v in inventory.values())} ids already held elsewhere')
    else:
        print('no inventory, every id counts as missing')

    for name in args.module:
        m = load_module(name)
        run = Run(name, inventory)
        expansions = args.expansion or list(m.expansion_data)
        for expansion in expansions:
            if expansion not in m.expansion_data:
                print(f'{name}: no {expansion} block, skipping')
                continue
            print(f'== {name} {expansion}')
            FETCHERS[name](m, run, expansion, args)
        print(f'{name}: {run.written} file(s) written, {run.skipped} already held')
    return 0


if __name__ == '__main__':
    sys.exit(main())
