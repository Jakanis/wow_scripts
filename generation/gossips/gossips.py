from generation.npc.npc import load_npcs_from_db, NPC_MD
from generation.utils.utils import compare_directories


class Gossip:
    def __init__(self, npc_id, text: str, gossip_key: str = None, npc_name: str = None, expansion: str = None):
        self.npc_id = npc_id
        self.text = text
        self.gossip_key = gossip_key
        self.npc_name = npc_name
        self.expansion = expansion

    def __eq__(self, other):
        return self.npc_id == other.npc_id and self.text == other.text

    def __hash__(self):
        return hash((self.npc_id, self.text))


def __clean_newlines(value: str) -> str:
    return value.replace(r'\r\n', r'\n').replace(r'\n', '\n').replace('\r\n', '\n')


def load_missing_gossips() -> list[Gossip]:
    import pickle
    gossips = list()
    with open('input/missing_gossips.pkl', 'rb') as f:
        missing_gossips = pickle.load(f)
        for npc_id, npc_gossips in missing_gossips.items():
            for gossip_key, gossip_text in npc_gossips.items():
                gossip = Gossip(npc_id, __clean_newlines(gossip_text), gossip_key=gossip_key)
                gossips.append(gossip)
    return gossips


def populate_npcs(gossips: list[Gossip], npcs: dict[int, dict[str, NPC_MD]]):
    missing_npcs: set[str] = set()
    for gossip in gossips:
        if npcs.get(gossip.npc_id) is None:
            # print(f'Warning! NPC#{gossip.npc_id} not found in DB!')
            missing_npcs.add(gossip.npc_id)
            continue
        gossip.npc_name = (npcs[gossip.npc_id].get('classic') or npcs[gossip.npc_id].get('sod')).name
        gossip.expansion = (npcs[gossip.npc_id].get('classic') or npcs[gossip.npc_id].get('sod')).expansion + '?'

    if missing_npcs:
        print(f'Next NPCs were not found in DB: {sorted(missing_npcs)}')
    return gossips


def cleanup_gossips(gossips: list[Gossip]):
    existing_gossips = set()
    existing_common_texts = set()
    existing_texts: dict[str, int] = dict()

    filtered_gossips = list()
    for gossip in gossips:
        if gossip.text == '':
            continue
        if gossip.text in existing_common_texts:
            continue
        if gossip in existing_gossips:
            continue
        if gossip.text in existing_texts:
            print(f'Gossip text "{gossip.text}" already exist.')
        if gossip.npc_name == 'common':
            existing_common_texts.add(gossip.text)
        existing_gossips.add(gossip)
        if gossip.text in existing_texts:
            existing_texts[gossip.text] += 1
        else:
            existing_texts[gossip.text] = 0
        filtered_gossips.append(gossip)

    text_repeatance = list(sorted(existing_texts.items(), key=lambda item: item[1], reverse=True))

    return filtered_gossips
# filtered_gossips[67]
# filtered_gossips[85]
def save_to_db(gossips: list[Gossip], db_path: str):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute('DROP TABLE IF EXISTS gossips')
    conn.execute('''CREATE TABLE IF NOT EXISTS gossips(
                        npc_id INTEGER NOT NULL,
                        npc_name TEXT,
                        text TEXT,
                        gossip_key TEXT,
                        expansion TEXT
                    )''')
    conn.commit()
    with conn:
        for gossip in gossips:
            conn.execute('INSERT INTO gossips(npc_id, npc_name, text, gossip_key, expansion) VALUES(?, ?, ?, ?, ?)',
                        (gossip.npc_id, gossip.npc_name, gossip.text, gossip.gossip_key, gossip.expansion))

    conn.commit()

def load_from_db(db_path: str) -> list[Gossip]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    gossips: list[Gossip] = list()
    with (conn):
        cursor = conn.cursor()
        sql = f'SELECT * FROM gossips'
        res = cursor.execute(sql)
        chat_rows = res.fetchall()
        for row in chat_rows:
            npc_id = row[0]
            npc_name = row[1]
            text = row[2]
            gossip_key = row[3]
            expansion = row[4]
            gossip = Gossip(npc_id, __clean_newlines(text), npc_name=npc_name, gossip_key=gossip_key, expansion=expansion)
            gossips.append(gossip)
    return gossips


def __gossip_filename(gossip: Gossip) -> str:
    valid_chars = frozenset('-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return ''.join(c for c in gossip.npc_name if c in valid_chars) + '_' + str(gossip.npc_id)


def write_xml_gossip_file(path: str, gossips: list[Gossip]):
    with open(path, mode='w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        for gossip in gossips:
            f.write(f'  <string><![CDATA[{gossip.text}]]></string>\n')
        f.write('</resources>\n')


def generate_sources(gossips: list[Gossip]):
    import os
    from pathlib import Path
    import shutil

    print('Generating sources...')
    if os.path.exists('output/source_for_crowdin'):
        shutil.rmtree('output/source_for_crowdin')
    count = 0

    gossips_by_path: dict[str, list[Gossip]] = dict()

    for gossip in gossips:
        if gossip.expansion == 'classic':
            suffix = ''
        else:
            suffix = '_' + gossip.expansion

        if gossip.npc_id == 0:
            path = f'output/source_for_crowdin/gossip{suffix}/{gossip.npc_name}.xml'
        else:
            path = f'output/source_for_crowdin/gossip{suffix}/{gossip.npc_name.capitalize()[:1]}/{__gossip_filename(gossip)}.xml'

        gossips_by_path[path] = gossips_by_path.get(path, list())
        gossips_by_path[path].append(gossip)

    for path, gossips_on_path in gossips_by_path.items():
        Path(*Path(path).parts[:-1]).mkdir(parents=True, exist_ok=True)
        write_xml_gossip_file(path, gossips_on_path)

        count += 1
    print(f'Generated {count} gossips.')



if __name__ == '__main__':
    crowdin_gossips = load_from_db('crowdin_gossips.db')
    missing_gossips = load_missing_gossips()
    npcs = load_npcs_from_db('input/npcs.db')
    missing_gossips = populate_npcs(missing_gossips, npcs)

    combined_gossips = cleanup_gossips([*crowdin_gossips, *missing_gossips])

    # save_to_db(missing_gossips, 'gossips.db')
    save_to_db(combined_gossips, 'gossips.db')

    gossips = load_from_db('gossips.db')

    generate_sources(crowdin_gossips)

    diffs = compare_directories('input/source_from_crowdin', 'output/source_for_crowdin')

    print('')

# 14338 - nextlines
# 214070 and 214098 - names and same gossips with different npcs
# 11178 - too short and specific