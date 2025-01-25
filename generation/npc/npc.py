import json
import os

import requests
from bs4 import BeautifulSoup

THREADS = 16
CLASSIC = 'classic'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
NPC_CACHE = 'npc_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'
SOD = 'sod'
FORCE_DOWNLOAD = 'force_download'

expansion_data = {
    CLASSIC: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_npc_html',
        NPC_CACHE: 'wowhead_classic_npc_cache',
        METADATA_FILTERS: ('13:', '5:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    SOD: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_npc_html',
        NPC_CACHE: 'wowhead_sod_npc_cache',
        METADATA_FILTERS: ('13:', '2:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: [207795, 212157, 222231, 222240, 223739]
    },
    TBC: {
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_npc_html',
        NPC_CACHE: 'wowhead_tbc_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    WRATH: {
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_npc_html',
        NPC_CACHE: 'wowhead_wrath_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    CATA: {
        WOWHEAD_URL: 'https://www.wowhead.com/cata',
        METADATA_CACHE: 'wowhead_cata_metadata_cache',
        HTML_CACHE: 'wowhead_cata_npc_html',
        NPC_CACHE: 'wowhead_cata_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    }
}


# Metadata from Wowhead
class NPC_MD:
    # def __init__(self, id: int, name: str, tag: str = None, type: int = None, boss: int = None,
    #              classification: int = None, displayName: str = None, displayNames: list[str] = None,
    #              location: list[int] = None, names: list[str] = None, react: list[int] = None, expansion: str = None):
    def __init__(self, id, name, tag=None, name_ua=None, tag_ua=None, type=None, boss=None, classification=None, location=None, names=None, react=None, expansion=None):
        self.id = id
        self.name = name
        self.tag = tag
        self.name_ua = name_ua
        self.tag_ua = tag_ua
        self.type = type
        self.boss = boss
        self.classification = classification
        self.location = location
        self.names = names
        self.react = react
        self.expansion = expansion
        def get_classification(self):
            if self.classification == 0:
                return 'normal'
            elif self.classification == 1:
                return 'elite'
            elif self.classification == 2:
                return 'rare elite'
            elif self.classification == 3:
                return 'boss'
            elif self.classification == 4:
                return 'rare'

    def __str__(self):
        res = f'#{self.id}:'
        res += f' "{self.name}"'
        res += f' <{self.tag}>' if self.tag else ''
        return res

    def __eq__(self, __value):
        return self.name == __value.name and self.name_ua == __value.name_ua and self.name_ua == __value.name_ua


class NPC_Short:
    def __init__(self, id, name, tag=None):
        self.id = id
        self.name = name
        self.tag = tag


class NPC_Data:
    def __init__(self, id, expansion, name: str = None, quotes: list[str] = [], name_ua: str = None):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.name_ua = name_ua
        self.quotes = quotes


def __get_wowhead_npc_search(expansion, start, end=None) -> list[NPC_MD]:
    base_url = expansion_data[expansion][WOWHEAD_URL]
    metadata_filters = expansion_data[expansion][METADATA_FILTERS]
    if end:
        url = base_url + f"/npcs?filter={metadata_filters[0]}37:37;{metadata_filters[1]}2:5;{metadata_filters[2]}{start}:{end}"
    else:
        url = base_url + f"/npcs?filter={metadata_filters[0]}37;{metadata_filters[1]}2;{metadata_filters[2]}{start}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    pre_script_div = soup.find('div', id='lv-npcs')
    if not pre_script_div:
        return []
    script_tag = pre_script_div.next_element
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('new Listview(') + 13
        start = script_content.find('"data":[', start) + 7
        end = script_content.rfind('}],"') + 2
        json_data = script_content[start:end]
        return list(map(lambda md: NPC_MD(md.get('id'), md.get('name'), md.get('tag'), None, None, md.get('type'), md.get('boss'),
                                          md.get('classification'), md.get('location'), md.get('names'), md.get('react'), expansion), json.loads(json_data)))
    else:
        return []


def __retrieve_npc_metadata_from_wowhead(expansion) -> dict[int, NPC_MD]:
    all_npcs_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            npcs = __get_wowhead_npc_search(expansion, start)
            if len(npcs) < 1000:
                all_npcs_metadata.extend(npcs)
                break
        npcs = __get_wowhead_npc_search(expansion, start, start + 1000)
        all_npcs_metadata.extend(npcs)
        i += 1
    return {md.id: md for md in all_npcs_metadata}



def get_wowhead_npc_metadata(expansion) -> dict[int, dict[str, NPC_MD]]:
    import pickle
    cache_file_name = expansion_data[expansion][METADATA_CACHE]
    if os.path.exists(f'cache/tmp/{cache_file_name}.pkl'):
        print(f'Loading cached Wowhead({expansion}) metadata')
        with open(f'cache/tmp/{cache_file_name}.pkl', 'rb') as f:
            wowhead_metadata = pickle.load(f)
    else:
        print(f'Retrieving Wowhead({expansion}) metadata')
        wowhead_metadata = __retrieve_npc_metadata_from_wowhead(expansion)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/{cache_file_name}.pkl', 'wb') as f:
            pickle.dump(wowhead_metadata, f)

    for force_id in expansion_data[expansion][FORCE_DOWNLOAD]:
        wowhead_metadata[force_id] = NPC_MD(force_id, "FORCE LOAD", expansion=expansion)

    wowhead_npcs = dict()
    for key, value in wowhead_metadata.items():
        wowhead_npcs[key] = dict()
        wowhead_npcs[key][expansion] = value

    return wowhead_npcs

def load_npc_lua(path: str) -> dict[int, NPC_Short]:
    from slpp import slpp as lua
    npcs = dict()
    with open(path, 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        start = lua_file.find("npc = {") + 5
        decoded_npcs = lua.decode(lua_file[start:])
        for npc_id, decoded_npc in decoded_npcs.items():
            npc_name_ua = decoded_npc[0]
            if type(decoded_npc) == dict:
                npc_tag_ua = decoded_npc.get(1)
            else:
                npc_tag_ua = decoded_npc[1] if len(decoded_npc) > 1 else None
            npcs[npc_id] = NPC_Short(npc_id, npc_name_ua, npc_tag_ua)
    return npcs

def load_questie_npcs() -> dict[int, NPC_Short]:
    from slpp import slpp as lua
    npcs = dict()
    with open('input/questie_npc.lua', 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        decoded_npcs = lua.decode(lua_file)
        for npc_id, decoded_npc in decoded_npcs.items():
            npc_name = decoded_npc[0]
            npc_tag = None
            if len(decoded_npc) == 2:
                npc_tag = decoded_npc[1]
            npcs[npc_id] = NPC_Short(npc_id, npc_name, npc_tag)
    return npcs

# def apply_translations(wowhead_metadata: dict[int, NPC_MD]):

def save_npcs_to_db(all_npcs: dict[int, dict[str, NPC_MD]]):
    import sqlite3
    print('Saving NPCs to DB')
    conn = sqlite3.connect('cache/npcs.db')
    conn.execute('DROP TABLE IF EXISTS npcs')
    conn.execute('''CREATE TABLE npcs (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        tag TEXT,
                        name_ua TEXT,
                        tag_ua TEXT,
                        type TEXT,
                        boss TEXT,
                        classification TEXT,
                        location TEXT,
                        names TEXT,
                        react TEXT
                )''')
    conn.commit()
    with conn:
        for key, npcs in all_npcs.items():
            for expansion, npc in npcs.items():
                if ('TEST' in npc.name or
                        '[PH]' in npc.name or
                        'DND' in npc.name or
                        'DNT' in npc.name or
                        'UNUSED' in npc.name or
                        '<TXT>' in npc.name or
                        key in expansion_data[npc.expansion][IGNORES]):
                    continue
                npc_tag = f'<{npc.tag}>' if npc.tag else None
                npc_location = ', '.join(map(lambda x: f"'{x}'", npc.location)) if npc.location else None
                conn.execute('INSERT INTO npcs(id, expansion, name, tag, name_ua, tag_ua, type, boss, classification, location, names, react) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (npc.id, expansion, npc.name, npc_tag, npc.__dict__.get('name_ua'), npc.__dict__.get('tag_ua'), npc.type, npc.boss, npc.classification, npc_location, str(npc.names), str(npc.react)))


def load_npcs_from_db(db_path = 'cache/npcs.db') -> dict[int, dict[str, NPC_MD]]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    npcs: dict[int, dict[str, NPC_MD]] = dict()
    with (conn):
        cursor = conn.cursor()
        sql = f'SELECT * FROM npcs'
        res = cursor.execute(sql)
        npc_rows = res.fetchall()
        for row in npc_rows:
            npc_id = row[0]
            expansion = row[1]
            name = row[2]
            tag = row[3]
            name_ua = row[4]
            tag_ua = row[5]
            type = row[6]
            boss = row[7]
            classification = row[8]
            location = row[9]
            names = row[10]
            react = row[11]
            npc = NPC_MD(npc_id, name, expansion=expansion, tag=tag, name_ua=name_ua, tag_ua=tag_ua, type=type, boss=boss,
                         classification=classification, location=location, names=names, react=react)
            npcs[npc_id] = npcs.get(npc_id, dict())
            npcs[npc_id][expansion] = npc

    return npcs

def get_zone_page(zone_id):
    import json
    url = f'https://www.wowhead.com/classic/zone={zone_id}'
    r = requests.get(url)
    start = r.text.find("template: 'npc'")
    if start == -1: # No NPCs on page
        return None
    start = r.text.find('data: [', start) + 5
    end = r.text.find('});', start)
    json_data = r.text[start:end]
    return (zone_id, json.loads(json_data))


def get_wowhead_zones_npc_ids(zone_ids) -> dict[int, list[int]]:
    import multiprocessing
    import pickle
    if os.path.exists(f'cache/tmp/npc_ids_to_zone_ids_cache.pkl'):
        print(f'Loading cached npc_ids_to_zone_ids')
        with open(f'cache/tmp/npc_ids_to_zone_ids_cache.pkl', 'rb') as f:
            npc_ids_to_zone_ids = pickle.load(f)
    else:
        print(f'Retrieving npc_ids_to_zone_ids data')
        npc_ids_to_zone_ids = dict()
        with multiprocessing.Pool(16) as p:
            npcs_by_zone = filter(lambda x: x is not None, p.map(get_zone_page, zone_ids))
        for zone_id, npcs in sorted(npcs_by_zone):
            for npc in npcs:
                if not npc['id'] in npc_ids_to_zone_ids:
                    npc_ids_to_zone_ids[npc['id']] = list()
                npc_ids_to_zone_ids[npc['id']].append(zone_id)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/npc_ids_to_zone_ids_cache.pkl', 'wb') as f:
            pickle.dump(npc_ids_to_zone_ids, f)
    return npc_ids_to_zone_ids


def merge_npc(id: int, old_npcs: dict[str, NPC_MD], new_npcs: dict[str, NPC_MD]) -> dict[str, NPC_MD]:
    if len(old_npcs) > 1 and len(new_npcs) == 1:
        # print(f'Merging more than one instance from previous expansion for NPC #{id}')
        last_old_npc_key = list(old_npcs.keys())[-1]
        result = merge_npc(id, {last_old_npc_key: old_npcs[last_old_npc_key]}, new_npcs)
        del old_npcs[last_old_npc_key]
        return {**old_npcs, **result}
    if len(old_npcs) == 1 and len(new_npcs) == 1:
        old_npc = next(iter(old_npcs.values()))
        new_npc = next(iter(new_npcs.values()))

        if old_npc.name != new_npc.name or old_npc.tag != new_npc.tag:
            return {**old_npcs, **new_npcs}
        else:
            return old_npcs
    else:
        print('-' * 100)
        print(f'Skip: NPC #{id} instance number unexpected')


def merge_expansions(old_expansion: dict[int, dict[str, NPC_MD]], new_expansion: dict[int, dict[str, NPC_MD]]) -> dict[int, dict[str, NPC_MD]]:
    result = dict()

    for id in old_expansion.keys() - new_expansion.keys():
        result[id] = old_expansion[id]

    for id in new_expansion.keys() - old_expansion.keys():
        result[id] = new_expansion[id]

    for id in old_expansion.keys() & new_expansion.keys():
        result[id] = merge_npc(id, old_expansion[id], new_expansion[id])
    return result


def fix_npc_data(all_npcs: dict[int, dict[str, NPC_MD]]):
    all_npcs[185336][CLASSIC] = all_npcs[185336][SOD]
    del all_npcs[185336][SOD]
    all_npcs[207795][SOD].name = "Galvanic Icon"
    all_npcs[212157][SOD].name = "Decoy Totem"
    all_npcs[222231][SOD].name = "Serpent Totem"
    all_npcs[222240][SOD].name = "Serpent Totem"
    all_npcs[223739][SOD].name = "Atal'ai Totem"


def populate_cache_db_with_npc_data() -> dict[int, dict[str, NPC_MD]]:
    wowhead_metadata_classic = get_wowhead_npc_metadata(CLASSIC)
    wowhead_metadata_sod = get_wowhead_npc_metadata(SOD)
    wowhead_metadata_tbc = get_wowhead_npc_metadata(TBC)
    wowhead_metadata_wrath = get_wowhead_npc_metadata(WRATH)
    wowhead_metadata_cata = get_wowhead_npc_metadata(CATA)

    print('Merging with TBC')
    classic_and_tbc_npcs = merge_expansions({**wowhead_metadata_classic, **wowhead_metadata_sod}, wowhead_metadata_tbc)
    print('Merging with WotLK')
    classic_tbc_wrath_npcs = merge_expansions(classic_and_tbc_npcs, wowhead_metadata_wrath)
    print('Merging with Cata')
    all_npcs = merge_expansions(classic_tbc_wrath_npcs, wowhead_metadata_cata)

    fix_npc_data(all_npcs)

    translations = dict()
    translations[CLASSIC] = load_npc_lua('input/entries/classic/npc.lua')
    translations[SOD] = load_npc_lua('input/entries/sod/npc.lua')
    translations[TBC] = load_npc_lua('input/entries/tbc/npc.lua')
    translations[WRATH] = load_npc_lua('input/entries/wrath/npc.lua')
    translations[CATA] = load_npc_lua('input/entries/cata/npc.lua')

    for key in all_npcs.keys():
        for expansion in all_npcs[key].keys():
            if key in translations[expansion]:
                all_npcs[key][expansion].name_ua = translations[expansion][key].name
                all_npcs[key][expansion].tag_ua = translations[expansion][key].tag

    # Just for handier translation
    import zones
    wowhead_zones = zones.get_wowhead_zones()
    npc_ids_to_zone_ids = get_wowhead_zones_npc_ids(wowhead_zones.keys())

    for key in all_npcs.keys():
        for expansion in all_npcs[key].keys():
            if key in npc_ids_to_zone_ids:
                all_npcs[key][expansion].location = npc_ids_to_zone_ids[key]

    save_npcs_to_db(all_npcs)

    return all_npcs


def update_questie_translation(all_npcs: dict[int, dict[str, NPC_MD]]):
    pass
    # questie_npcs = load_questie_npcs()
    #
    # for key in wowhead_metadata.keys() & questie_npcs.keys():
    #     wowhead_metadata[key].names = 'questie'
    #
    #
    # with open(f'lookupNpcs.lua', 'w', encoding="utf-8") as output_file:
    #     for key in wowhead_metadata.keys() & questie_npcs.keys():
    #         if not hasattr(wowhead_metadata[key], 'name_ua'):
    #             continue
    #         wowhead_metadata[key].names = 'questie'
    #         questie_name = wowhead_metadata[key].name_ua[0].upper() + wowhead_metadata[key].name_ua[1:]
    #         questie_name = '{"' + questie_name.replace('"', '\\"') + '"'
    #         questie_tag = wowhead_metadata[key].tag_ua[0].upper() + wowhead_metadata[key].tag_ua[1:] if wowhead_metadata[key].tag_ua else None
    #         questie_tag = '"' + questie_tag.replace('"', '\\"') + '"}' if questie_tag else 'nil}'
    #         output_file.write(f'[{key}] = {questie_name},{questie_tag},\n')


def __try_cast_str_to_int(value: str, default=None):
    try:
        return int(value)
    except ValueError:
        return default

def load_merged_translations() -> dict[int, dict[str, NPC_MD]]:
    import csv
    merged_translations = dict()
    with open(f'input/translations.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in reader:
            npc_id = __try_cast_str_to_int(row[0])
            if not npc_id:
                print(f'Skipping: {row}')
                continue
            name_en = row[1]
            tag_en = row[2][1:-1] if row[2] != '' else None
            name_ua = row[3]
            tag_ua = row[4][1:-1] if row[4] != '' else None
            expansion = row[8]
            npc = NPC_MD(npc_id, name_en, name_ua=name_ua, tag=tag_en, tag_ua=tag_ua, expansion=expansion)
            if npc_id not in merged_translations:
                merged_translations[npc_id] = {expansion: npc}
            else:
                if expansion in merged_translations[npc_id]:
                    existing_npc = merged_translations[npc_id][expansion]
                    if existing_npc != npc:
                        print(f'Warning! NPC#{npc_id}:{expansion} duplicated and differs')
                    if existing_npc == npc:
                        print(f'Warning! NPC#{npc_id}:{expansion} duplicated')
                merged_translations[npc_id][expansion] = npc
    return merged_translations


def check_feedback_npcs(all_npcs: dict[int, dict[str, NPC_MD]]) -> set[int]:
    import csv
    feedback = dict()
    with open('input/missing_npcs.tsv', 'r', encoding='utf-8') as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            feedback[int(row[0])] = row[1]

    missed_npcs = set()
    for feedback_id, feedback_name in feedback.items():
        if feedback_id not in all_npcs:
            print(f'Warning! Feedback NPC#{feedback_id} "{feedback_name}" does not exist in DB!')
            missed_npcs.add(feedback_id)
        else:
            translated = False
            for npc in all_npcs[feedback_id].values():
                if npc.name_ua:
                    translated = True
            if not translated:
                print(f'Warning! Feedback NPC#{feedback_id} "{feedback_name}" is not translated!')
                missed_npcs.add(feedback_id)

    print(f'Missed IDs({len(missed_npcs)}): {sorted(missed_npcs)}')
    return missed_npcs


def compare_npc(tsv_npc: NPC_MD, lua_npc: NPC_MD):
    if tsv_npc.name != lua_npc.name:
        print(f'Warning! NPC#{tsv_npc.id}:{tsv_npc.expansion} name differs:\n{tsv_npc.name}<->{lua_npc.name}')
    if tsv_npc.tag != lua_npc.tag:
        print(f'Warning! NPC#{tsv_npc.id}:{tsv_npc.expansion} tag differs:\n{tsv_npc.tag}<->{lua_npc.tag}')
    if tsv_npc.name_ua != lua_npc.name_ua:
        print(f'Warning! NPC#{tsv_npc.id}:{tsv_npc.expansion} translation differs:\n{tsv_npc.name_ua}<->{lua_npc.name_ua}')



def check_existing_translations(all_npcs: dict[int, dict[str, NPC_MD]]):
    merged_translations = load_merged_translations()
    for key in merged_translations.keys() - all_npcs.keys():
        print(f'NPC#{key} does not exist in ClassicUA')

    for key in merged_translations.keys() & all_npcs.keys():
        for expansion in merged_translations[key].keys() - all_npcs[key].keys():
            print(f'NPC#{key}:{expansion} does not exist in ClassicUA')

        for expansion in merged_translations[key].keys() & all_npcs[key].keys():
            compare_npc(merged_translations[key][expansion], all_npcs[key][expansion])


def create_translation_sheet(npcs: dict[int, dict[str, NPC_MD]], missed_npcs: set[int] = None):
    with (open(f'translate_this.tsv', mode='w', encoding='utf-8') as f):
        f.write('ID\tName(EN)\tDescription(EN)\tName(UA)\tDescription(UA)\tраса\tстать\tNote\texpansion\n')
        count = 0
        for key in sorted(npcs.keys()):
            for expansion, npc in npcs[key].items():
                if (npc.name_ua is None and (npc.react != [None, None] or npc.location != [] or key in missed_npcs) and npc.expansion in [CLASSIC, SOD]):
                # if npc.name_ua is None and npc.expansion in [CLASSIC, SOD]:
                # if npc.expansion in [CLASSIC, SOD] and npc.id in [14465, 14466, 229001, 232335, 202387, 202390, 222231, 202392, 202391, 14751, 222240, 205733, 230695, 7863, 8376, 212157, 11200, 213450, 229452, 222293, 7383, 232921, 2671, 2673, 2674, 228596, 11637, 7543, 7545, 223739]:
                    f.write(f'{npc.id}\t"{npc.name}"\t"{f"<{npc.tag}>" if npc.tag else ""}"\t\t\t\t\t\t{npc.expansion}\n')
                    count += 1
        if count > 0:
            print(f"Added {count} NPCs for translation")


def save_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/npc={id}'
    html_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    if os.path.exists(html_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    r = requests.get(url)
    if not r.ok:
        # You download over 90000 pages in one hour - you'll fail
        # You do it async - you fail
        # Have a tea break (or change IP, lol)
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for NPC #{id}')
    if (f"<error>Item not found!</error>" in r.text):
        return
    with open(html_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_htmls_from_wowhead(expansion, ids: set[int]):
    from functools import partial
    import multiprocessing
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}'

    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'HTML cache for all Wowhead({expansion}) NPCs ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    print(f'Saving HTMLs for {len(save_ids)} of {len(ids)} NPCs from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    for id in save_ids:
        print(f"Saving NPC #{id}")
        save_page(expansion, id)
    # save_func = partial(save_page, expansion)
    # with multiprocessing.Pool(THREADS) as p:
    #     p.map(save_func, save_ids)


def parse_wowhead_npc_page(expansion, id) -> NPC_Data:
    import re
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html5lib')

    npc_name = soup.find('h1').text
    npc_name = npc_name[:npc_name.find(' <')] if ' <' in npc_name else npc_name
    npc_quotes_header = soup.find('h2', {'class': 'heading-size-3'}, string=re.compile('Quotes'))

    npc_quotes = list()
    if npc_quotes_header:
        npc_quotes_list = npc_quotes_header.find_next('ul').find_all('li')
        for list_element in npc_quotes_list:
            npc_quote = list_element.text[list_element.text.find(':') + 2:]
            npc_quotes.append(npc_quote)

    return NPC_Data(id, expansion, name=npc_name, quotes=npc_quotes)


def parse_wowhead_pages(expansion, metadata: dict[int, dict[str, NPC_MD]]) -> dict[int, NPC_Data]:
    import pickle
    import multiprocessing
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][NPC_CACHE]}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) NPCs')
        with open(cache_path, 'rb') as f:
            wowhead_npcs = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) NPC pages')
        # wowhead_npcs = {id: parse_wowhead_npc_page(expansion, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_npc_page, expansion)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_npcs = p.map(parse_func, metadata.keys())
        wowhead_npcs = {npc.id: npc for npc in wowhead_npcs}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_npcs, f)

    # wowhead_item_data = merge_quests_and_metadata(wowhead_items, metadata)

    # return wowhead_quest_entities
    return wowhead_npcs


def store_npc_quotes(npc_metadata: dict[int, dict[str, NPC_MD]]):
    import pickle
    wowhead_md = dict()
    wowhead_npcs = dict()
    all_npcs = dict()
    # download_npc_pages(npc_metadata)
    # wowhead_metadata_classic = get_wowhead_npc_metadata(CLASSIC)
    # wowhead_metadata_sod = get_wowhead_npc_metadata(SOD)

    for expansion in list(expansion_data.keys())[:2]:
        wowhead_md[expansion] = get_wowhead_npc_metadata(expansion)
        save_htmls_from_wowhead(expansion, set(wowhead_md[expansion].keys()))
        wowhead_npcs[expansion] = parse_wowhead_pages(expansion, wowhead_md[expansion])
        # print(f'Merging with {expansion}')
        # all_items = merge_expansions(all_npcs, wowhead_npcs[expansion])

    with open('output/all_npcs.pkl', 'wb') as f:
        pickle.dump(wowhead_npcs, f)
    print('Done')

if __name__ == '__main__':
    all_npcs_md = populate_cache_db_with_npc_data()  # Generate cache/npcs.db

    check_existing_translations(all_npcs_md)  # Check if original data changes since previous translation and difference between ClassicUA and translation sheet
    # update_questie_translation(all_npcs)  # Update translations for Questie

    missed_npcs = check_feedback_npcs(all_npcs_md)

    # create_translation_sheet(all_npcs_md)
    create_translation_sheet(all_npcs_md, missed_npcs)

    store_npc_quotes(all_npcs_md)

