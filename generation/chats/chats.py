from generation.npc.npc import load_npcs_from_db, NPC_MD
from generation.utils.utils import compare_directories


class Chat:
    def __init__(self, npc_name: str, text: str, chat_key: str = None, npc_id: str = None, expansion: str = None):
        self.npc_name = npc_name
        self.text = text
        self.chat_key = chat_key
        self.npc_id = npc_id
        self.expansion = expansion

    def __eq__(self, other):
        return self.npc_name == other.npc_name and self.text == other.text

    def __hash__(self):
        return hash((self.npc_name, self.text))


def load_missing_chats() -> list[Chat]:
    import pickle
    chats = list()
    with open('input/missing_chats.pkl', 'rb') as f:
        missing_chats = pickle.load(f)
        for npc_name, npc_chats in missing_chats.items():
            for chat_key, chat_text in npc_chats.items():
                chat = Chat(npc_name, chat_text, chat_key=chat_key)
                chats.append(chat)

    return chats


def populate_npcs(chats: list[Chat], npcs: dict[int, dict[str, NPC_MD]]):
    npc_by_name: [str, NPC_MD] = dict()
    for npc_id in sorted(npcs.keys()):
        for npc_expansion, npc in npcs[npc_id].items():
            if npc.name not in npc_by_name:
                npc_by_name[npc.name] = npc

    missing_npcs: set[str] = set()
    missing_npc_translations: set[int] = set()
    for chat in chats:
        if npc_by_name.get(chat.npc_name) is None:
            # print(f'Warning! NPC "{chat.npc_name}" not found in DB!')
            missing_npcs.add(chat.npc_name)
            continue
        chat.npc_id = npc_by_name[chat.npc_name].id
        if npc_by_name[chat.npc_name].name_ua is None:
            missing_npc_translations.add(chat.npc_id)
            # print(f'Warning! NPC#{chat.npc_id} have no translation!')

    if missing_npcs:
        print(f'Next NPCs were not found in DB: {sorted(missing_npcs)}')
    if missing_npc_translations:
        print(f'Next NPCs should have translation: {sorted(missing_npc_translations)}')
    return chats


def save_to_db(chats: list[Chat], db_path: str):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute('DROP TABLE IF EXISTS chats')
    conn.execute('''CREATE TABLE IF NOT EXISTS chats(
                        npc_name TEXT NOT NULL,
                        npc_id INTEGER,
                        text TEXT,
                        chat_key TEXT,
                        expansion TEXT
                    )''')
    conn.commit()
    with conn:
        for chat in chats:
            conn.execute('INSERT INTO chats(npc_name, npc_id, text, chat_key, expansion) VALUES(?, ?, ?, ?, ?)',
                        (chat.npc_name, chat.npc_id, chat.text, chat.chat_key, chat.expansion))

    conn.commit()

def load_from_db(db_path: str) -> list[Chat]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    chats: list[Chat] = list()
    with (conn):
        cursor = conn.cursor()
        sql = f'SELECT * FROM chats'
        res = cursor.execute(sql)
        chat_rows = res.fetchall()
        for row in chat_rows:
            npc_name = row[0]
            npc_id = row[1]
            text = row[2]
            chat_key = row[3]
            expansion = row[4]
            chat = Chat(npc_name, text, npc_id=npc_id, chat_key=chat_key, expansion=expansion)
            chats.append(chat)
    return chats


def __chat_filename(chat: Chat) -> str:
    valid_chars = frozenset('-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return ''.join(c for c in chat.npc_name if c in valid_chars) + '_' + str(chat.npc_id)


def write_xml_quest_file(path: str, chats: list[Chat]):
    with open(path, mode='w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        for chat in chats:
            f.write(f'  <string><![CDATA[{chat.text}]]></string>\n')
        f.write('</resources>\n')


def generate_sources(chats: list[Chat]):
    import os
    from pathlib import Path
    import shutil

    print('Generating sources...')
    if os.path.exists('output/source_for_crowdin'):
        shutil.rmtree('output/source_for_crowdin')
    count = 0

    chats_by_path: dict[str, list[Chat]] = dict()

    for chat in chats:
        if chat.expansion == 'classic':
            suffix = ''
        else:
            suffix = '_' + chat.expansion

        if chat.npc_id == 0:
            path = f'output/source_for_crowdin/chats{suffix}/{chat.npc_name}.xml'
        else:
            path = f'output/source_for_crowdin/chats{suffix}/{chat.npc_name.capitalize()[:1]}/{__chat_filename(chat)}.xml'

        chats_by_path[path] = chats_by_path.get(path, list())
        chats_by_path[path].append(chat)

    for path, chats_on_path in chats_by_path.items():
        Path(*Path(path).parts[:-1]).mkdir(parents=True, exist_ok=True)
        write_xml_quest_file(path, chats_on_path)

        count += 1
    print(f'Generated {count} chats.')


def cleanup_chats(chats: list[Chat]):
    existing_chats = set()
    existing_common_texts = set()
    existing_texts: dict[str, int] = dict()

    filtered_chats = list()
    for chat in chats:
        if chat.text == '':
            continue
        if chat.text in existing_common_texts:
            continue
        if chat in existing_chats:
            continue
        if chat.text in existing_texts:
            print(f'Chat text "{chat.text}" already exist.')
        if chat.npc_name == 'common':
            existing_common_texts.add(chat.text)
        existing_chats.add(chat)
        if chat.text in existing_texts:
            existing_texts[chat.text] += 1
        else:
            existing_texts[chat.text] = 0
        filtered_chats.append(chat)

    text_repeatance = list(sorted(existing_texts.items(), key=lambda item: item[1], reverse=True))

    return filtered_chats


def filter_imp_texts(chats: list[Chat]):
    starting_text = "Alright I'm going! Stop yelling!"

    imp_names = set()
    for chat in chats:
        if chat.text == starting_text:
            imp_names.add(chat.npc_name)

    imp_texts = set()
    for chat in chats:
        if chat.text == '':
            continue
        if chat.npc_name in imp_names:
            imp_texts.add(chat.text)

    imp_names_2 = set()
    for chat in chats:
        if chat.text in imp_texts:
            imp_names_2.add(chat.npc_name)

    imp_texts_2 = set()
    for chat in chats:
        if chat.text == '':
            continue
        if chat.npc_name in imp_names_2:
            imp_texts_2.add(chat.text)

    print(f'imp_names({len(imp_names)}): {imp_names}')
    print(f'imp_texts({len(imp_texts)}): {imp_texts}')
    print(f'imp_names_2({len(imp_names_2)}): {imp_names_2}')
    print(f'imp_texts_2({len(imp_texts_2)}): {imp_texts_2}')

    return imp_texts_2


if __name__ == '__main__':
    crowdin_chats = load_from_db('crowdin_chats.db')
    missing_chats = load_missing_chats()
    npcs = load_npcs_from_db('input/npcs.db')
    missing_chats = populate_npcs(missing_chats, npcs)

    combined_chats = cleanup_chats([*crowdin_chats, *missing_chats])

    save_to_db(missing_chats, 'raw_chats.db')
    save_to_db(combined_chats, 'chats.db')

    chats = load_from_db('chats.db')

    generate_sources(crowdin_chats)

    # imp_texts = filter_imp_texts(missing_chats) # Temp

    diffs = compare_directories('input/source_from_crowdin', 'output/source_for_crowdin')

    print('')