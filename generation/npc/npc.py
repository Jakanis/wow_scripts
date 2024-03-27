import json
import os

import requests
from bs4 import BeautifulSoup

CLASSIC = 'classic'
TBC = 'tbc'
WRATH = 'wrath'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
NPC_CACHE = 'npc_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'
SOD = 'sod'

expansion_data = {
    CLASSIC: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_npc_html',
        NPC_CACHE: 'wowhead_classic_npc_cache',
        METADATA_FILTERS: ('13:', '5:', '11500:'),
        IGNORES: []
    },
    SOD: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_npc_html',
        NPC_CACHE: 'wowhead_sod_npc_cache',
        METADATA_FILTERS: ('13:', '2:', '11500:'),
        IGNORES: []
    },
    TBC: {
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_npc_html',
        NPC_CACHE: 'wowhead_tbc_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: []
    },
    WRATH: {
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_npc_html',
        NPC_CACHE: 'wowhead_wrath_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: []
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


class NPC_Short:
    def __init__(self, id, name, tag=None):
        self.id = id
        self.name = name
        self.tag = tag


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
        decoded_npcs = lua.decode(lua_file)
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
                        'UNUSED' in npc.name or
                        '<TXT>' in npc.name or
                        key in expansion_data[npc.expansion][IGNORES]):
                    continue
                npc_tag = f'<{npc.tag}>' if npc.tag else None
                npc_location = ', '.join(map(lambda x: f"'{x}'", npc.location)) if npc.location else None
                conn.execute('INSERT INTO npcs(id, expansion, name, tag, name_ua, tag_ua, type, boss, classification, location, names, react) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (npc.id, expansion, npc.name, npc_tag, npc.__dict__.get('name_ua'), npc.__dict__.get('tag_ua'), npc.type, npc.boss, npc.classification, npc_location, str(npc.names), str(npc.react)))




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



if __name__ == '__main__':
    wowhead_metadata = dict()
    wowhead_metadata_classic = get_wowhead_npc_metadata(CLASSIC)
    wowhead_metadata_sod = get_wowhead_npc_metadata(SOD)
    wowhead_metadata_tbc = get_wowhead_npc_metadata(TBC)
    wowhead_metadata_wrath = get_wowhead_npc_metadata(WRATH)

    print('Merging with TBC')
    classic_and_tbc_npcs = merge_expansions({**wowhead_metadata_classic, **wowhead_metadata_sod}, wowhead_metadata_tbc)
    print('Merging with WotLK')
    all_npcs = merge_expansions(classic_and_tbc_npcs, wowhead_metadata_wrath)

    translations = dict()
    translations[CLASSIC] = load_npc_lua('input/entries/classic/npc.lua')
    translations[SOD] = load_npc_lua('input/entries/sod/npc.lua')
    translations[TBC] = load_npc_lua('input/entries/tbc/npc.lua')
    translations[WRATH] = load_npc_lua('input/entries/wrath/npc.lua')

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

    # questie_npcs = load_questie_npcs()
    #
    # for key in wowhead_metadata.keys() & questie_npcs.keys():
    #     wowhead_metadata[key].names = 'questie'


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

