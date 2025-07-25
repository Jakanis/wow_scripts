import os

from generation.npc.npc import load_npcs_from_db, NPC_MD
from generation.utils.utils import compare_directories, update_on_crowdin, get_text_code, get_text_hash


class Gossip:
    def __init__(self, npc_id, text: str, gossip_type = None, gossip_key: str = None, npc_name: str = None, expansion: str = None):
        self.npc_id = npc_id
        self.text = text
        self.gossip_type = gossip_type
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

    feedbacks_folder = 'input/feedbacks'
    for feedback_file in os.listdir(feedbacks_folder):
        feedback_file_path = os.path.join(feedbacks_folder, feedback_file)
        if os.path.isfile(feedback_file_path) and feedback_file.endswith('.pkl'):
            with open(feedback_file_path, 'rb') as f:
                missing_gossips = pickle.load(f)
                for npc_id, npc_gossips in missing_gossips.items():
                    for gossip_key, gossip_object in npc_gossips.items():
                        gossip_text = None
                        if type(gossip_object) == str:
                            gossip_text = gossip_object
                        elif type(gossip_object) == dict:
                            gossip_text = gossip_object[0]
                        else:
                            print(f"Warning! Unknown gossip_object type: {type(gossip_object)}")
                            continue
                        gossip = Gossip(npc_id, __clean_newlines(gossip_text).strip(), gossip_key=gossip_key)
                        if not gossip in gossips:
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


def is_value_regex_in_set(gossip: Gossip, collection: set[str], result: list[Gossip] = None):
    import re
    if collection is None:
        return False
    if gossip.text in collection:
        return True
    for key in collection:
        re_template = r'.+?'
        if "<" in key:
            key_pattern = '^' + re.sub('<.+?>', re_template, re.escape(key)) + '$'
            if key_pattern != r'^.+?$' and re.match(key_pattern, gossip.text):
                return True
        if "<" in gossip.text:
            chat_pattern = '^' + re.sub('<.+?>', re_template, re.escape(gossip.text)) + '$'
            if re.match(chat_pattern, key):
                collection.remove(key)
                if result and gossip in result:
                    result.remove(gossip)
                collection.add(key)
                return False

    return False


def cleanup_gossips(gossips: list[Gossip]):
    existing_gossips = set()
    existing_common_texts = set()
    existing_texts: dict[str, int] = dict()
    existing_texts_by_npc: dict[str, set[str]] = dict()

    filtered_gossips = list()
    for gossip in gossips:
        if gossip.text == '':
            continue
        if gossip.text in existing_common_texts:
            continue
        if gossip in existing_gossips:
            continue
        if is_value_regex_in_set(gossip, existing_common_texts):
            continue
        if gossip.npc_id in existing_texts_by_npc and is_value_regex_in_set(gossip, existing_texts_by_npc[gossip.npc_id], filtered_gossips):
            continue
        if gossip.npc_name == 'common':
            existing_common_texts.add(gossip.text)
        existing_texts[gossip.text] = existing_texts.get(gossip.text, 0) + 1
        existing_gossips.add(gossip)
        existing_texts_by_npc[gossip.npc_id] = existing_texts_by_npc.get(gossip.npc_id, set())
        existing_texts_by_npc[gossip.npc_id].add(gossip.text)
        filtered_gossips.append(gossip)

    text_repeatance = list(sorted(filter(lambda x: x[1] > 1, existing_texts.items()), key=lambda item: item[1], reverse=True))

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
                        gossip_type TEXT,
                        gossip_key TEXT,
                        expansion TEXT
                    )''')
    conn.commit()
    with conn:
        for gossip in gossips:
            conn.execute('INSERT INTO gossips(npc_id, npc_name, text, gossip_type, gossip_key, expansion) VALUES(?, ?, ?, ?, ?, ?)',
                        (gossip.npc_id, gossip.npc_name, gossip.text, gossip.gossip_type, gossip.gossip_key, gossip.expansion))

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
            # gossip_type = row[4]
            gossip_type = ''
            expansion = row[4]
            gossip = Gossip(npc_id, __clean_newlines(text), npc_name=npc_name, gossip_type=gossip_type, gossip_key=gossip_key, expansion=expansion)
            gossips.append(gossip)
    return gossips


def __gossip_filename(gossip: Gossip) -> str:
    valid_chars = frozenset('-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return ''.join(c for c in gossip.npc_name if c in valid_chars) + '_' + str(gossip.npc_id)


def __get_text_code(text):
    # [!] Any changes made to this func must be kept in sync with ClassicUA impl
    import re
    get_text_code_replace_seq = (
        '<race>',
        'human',
        'dwarf',
        'night elf',
        'gnome',
        'orc',
        'troll',
        'undead',
        'tauren',
        'draenei',
        'blood elf',
        'worgen',
        'goblin',

        # player classes (keep in sync with entries/class.lua)
        '<class>',
        'warrior',
        'paladin',
        'hunter',
        'rogue',
        'priest',
        'shaman',
        'mage',
        'warlock',
        'druid',
        'death knight',

        # player name
        '<name>',
    )
    # text = 'Do not turn your back on the Light, warrior, it may be the one thing that saves you some day.'
    # text = 'Hello, Death Knight. Every hunter of our tribe worships shamanistic duty.'
    # text = 'I was wondering when I'd see you again, <name>.'
    # text = 'Hail, <class>!'
    # print('TEXT1', text)

    result = [ '_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_' ]
    result_len = len(result)
    text = text.lower()
    # print('TEXT2', text)

    for p in get_text_code_replace_seq:
        text = text.replace(p, '')
    # print('TEXT3', text)

    result_fill_idx = 0
    for word in re.findall(r'(\w+)', text):
        if len(word) > 0:
            if result_fill_idx >= result_len:
                break

            for i in range(len(word)):
                result[result_fill_idx] = word[i]
                # print(result_fill_idx, ''.join(result))
                result_fill_idx += 1
                if result_fill_idx >= result_len:
                    break

    result_idx = 0
    result_rewind = 0
    for word in re.findall(r'(\w+)', text):
        if len(word) > 0:
            result[result_idx] = word[0]
            # print(result_idx, ''.join(result))
            result_idx += 1
            if result_idx >= result_len:
                result_rewind = result_rewind + 1 if result_rewind < result_len - 1 else result_len - 4
                result_idx = result_rewind

    # print('CODE', ''.join(result))
    return ''.join(result)


def write_xml_gossip_file(path: str, gossips: list[Gossip]):
    with open(path, mode='w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        for gossip in gossips:
            string_comment = get_text_code(gossip.text)[0]
            string_name = string_comment
            if not '.' in string_name:
                string_name = str(get_text_hash(gossip.text))
            f.write(f'  <string name="{string_name}" comment="{string_comment}"><![CDATA[{gossip.text}]]></string>\n')
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
            path = f'output/source_for_crowdin/gossip{suffix}/{__gossip_filename(gossip).capitalize()[:1]}/{__gossip_filename(gossip)}.xml'

        gossips_by_path[path] = gossips_by_path.get(path, list())
        gossips_by_path[path].append(gossip)

    for path, gossips_on_path in gossips_by_path.items():
        Path(*Path(path).parts[:-1]).mkdir(parents=True, exist_ok=True)
        write_xml_gossip_file(path, gossips_on_path)

        count += 1
    print(f'Generated {count} gossip files.')


def group_gossips_by_npcs(gossips: list[Gossip]) -> dict[(str, int), list[Gossip]]:
    npcs_to_gossips: dict[(str, int), list[Gossip]] = dict()
    for gossip in gossips:
        npc_key = (gossip.npc_name, gossip.npc_id)
        npcs_to_gossips[npc_key] = npcs_to_gossips.get(npc_key, list())
        npcs_to_gossips[npc_key].append(gossip)
    return npcs_to_gossips

def verify_duplicates(gossips: list[Gossip]):
    gossips_by_npcs = group_gossips_by_npcs(gossips)
    common_chat_texts = map(lambda x: x.text, gossips_by_npcs.get(('common', 0)))
    for npc_key, gossips in gossips_by_npcs.items():
        npc_texts = set()
        for gossip in gossips:
            if gossip.text in npc_texts:
                print(f'Warning! Gossip duplicated for NPC "{npc_key}": {gossip.text}')
            npc_texts.add(gossip.text)

            if npc_key != ('common', 0) and gossip.text in common_chat_texts:
                print(f'Warning! Gossip text already exist in common for NPC "{npc_key}": {gossip.text}')


if __name__ == '__main__':
    crowdin_gossips = load_from_db('crowdin_gossips.db')
    missing_gossips = load_missing_gossips()
    npcs = load_npcs_from_db('input/npcs.db')
    missing_gossips = populate_npcs(missing_gossips, npcs)

    combined_gossips = cleanup_gossips([*crowdin_gossips, *missing_gossips])

    save_to_db([*crowdin_gossips, *missing_gossips], 'raw_gossips.db')
    # save_to_db(missing_gossips, 'gossips.db')
    save_to_db(combined_gossips, 'gossips.db')

    # gossips = load_from_db('gossips.db')

    verify_duplicates(crowdin_gossips)
    generate_sources(crowdin_gossips)

    diffs, removals, additions = compare_directories('input/source_from_crowdin', 'output/source_for_crowdin')
    update_on_crowdin(diffs, removals, additions)

# 14338 - nextlines
# 214070 and 214098 - names and same gossips with different npcs
# 11178 - too short and specific