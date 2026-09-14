import json
import os
import re

from bs4 import BeautifulSoup

from generation.utils.glossary import Glossary, GlossaryTerm, NPC_TAG, glossary_path
from generation.utils.utils import (ValidationError, classicua_root, copy_classicua_entries,
                                    download_crowdin_glossary, download_csv_from_google_sheet,
                                    run_classicua_generator, update_glossary_on_crowdin, wowhead_get)

SCRAPE_THREADS = 1
PARSE_THREADS = os.cpu_count()
CLASSIC = 'classic'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
MISTS = 'mists'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
NPC_CACHE = 'npc_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'
SOD = 'sod'
FORCE_DOWNLOAD = 'force_download'
RETRIEVE_QUOTES = 'retrieve_quotes'
FORCE_LOAD_NAME = 'FORCE LOAD'  # placeholder until the real name is read off the NPC page

expansion_data = {
    CLASSIC: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_npc_html',
        NPC_CACHE: 'wowhead_classic_npc_cache',
        METADATA_FILTERS: ('13:', '5:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: True
    },
    SOD: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_npc_html',
        NPC_CACHE: 'wowhead_sod_npc_cache',
        METADATA_FILTERS: ('13:', '2:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: [207795, 209889, 212157, 222231, 222240, 223739, 242756],
        RETRIEVE_QUOTES: True
    },
    TBC: {
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_npc_html',
        NPC_CACHE: 'wowhead_tbc_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: True
    },
    WRATH: {
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_npc_html',
        NPC_CACHE: 'wowhead_wrath_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: True
    },
    CATA: {
        WOWHEAD_URL: 'https://www.wowhead.com/cata',
        METADATA_CACHE: 'wowhead_cata_metadata_cache',
        HTML_CACHE: 'wowhead_cata_npc_html',
        NPC_CACHE: 'wowhead_cata_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: False
    },
    MISTS: {
        WOWHEAD_URL: 'https://www.wowhead.com/mop-classic',
        METADATA_CACHE: 'wowhead_mists_metadata_cache',
        HTML_CACHE: 'wowhead_mists_npc_html',
        NPC_CACHE: 'wowhead_mists_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: False
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
    def __init__(self, id, expansion, name: str = None, quotes: list[str] = [], tag: str = None, name_ua: str = None):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.tag = tag
        self.name_ua = name_ua
        self.quotes = quotes


class PendingNpc:
    def __init__(self, id: str, expansion: str, name_en: str, tag_en: str, name_uk: str, tag_uk: str,
                 race: str, sex: str, note: str):
        self.id = id
        self.expansion = expansion
        self.name_en = name_en
        self.tag_en = tag_en
        self.name_uk = name_uk
        self.tag_uk = tag_uk
        self.race = race
        self.sex = sex
        self.note = note

    def __repr__(self) -> str:
        return f'@pending_npc #{self.id}:{self.expansion} {self.name_en} -> {self.name_uk}'

def __get_wowhead_npc_search(expansion, start, end=None) -> list[NPC_MD]:
    base_url = expansion_data[expansion][WOWHEAD_URL]
    metadata_filters = expansion_data[expansion][METADATA_FILTERS]
    if end:
        url = base_url + f"/npcs?filter={metadata_filters[0]}37:37;{metadata_filters[1]}2:5;{metadata_filters[2]}{start}:{end}"
    else:
        url = base_url + f"/npcs?filter={metadata_filters[0]}37;{metadata_filters[1]}2;{metadata_filters[2]}{start}"
    r = wowhead_get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    pre_script_div = soup.find('div', id='lv-npcs')
    if not pre_script_div:
        # An empty result set still renders the NPC listview scaffolding. If even that is missing - we got an error page.
        if 'Listview/Templates/npc.js' not in r.text:
            raise Exception(f'Wowhead({expansion}) returned an unexpected page for {url}')
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

    for ignore_id in expansion_data[expansion][IGNORES]:
        if ignore_id in wowhead_metadata:
            del wowhead_metadata[ignore_id]

    # Wowhead's search no longer lists retired content (SoD in particular), so those NPCs are pinned by ID.
    # The real name/tag is filled in from their page later, by apply_page_data_to_metadata().
    for force_id in expansion_data[expansion][FORCE_DOWNLOAD]:
        if force_id not in wowhead_metadata:
            wowhead_metadata[force_id] = NPC_MD(force_id, FORCE_LOAD_NAME, expansion=expansion)
        else:
            print(f"Warning! NPC #{force_id}:{expansion} forced to load, but already exists in Wowhead metadata")

    wowhead_npcs = dict()
    for key, value in wowhead_metadata.items():
        wowhead_npcs[key] = dict()
        wowhead_npcs[key][expansion] = value

    return wowhead_npcs

def load_npc_lua(path: str) -> dict[int, NPC_Short]:
    from slpp import slpp as lua
    npcs = dict()
    if not os.path.exists(path):  # an expansion with no NPC translations yet
        print(f'Warning! No entries at {path}, treating as untranslated')
        return npcs
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
                        '<old>' in npc.name or
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
    r = wowhead_get(url)
    if not r.ok:  # no such zone in the classic client
        return None

    # Every real zone page renders at least one listview, with or without NPCs. Without one we got an
    # error/interstitial page instead, and returning None would silently drop that zone's NPCs.
    if 'new Listview(' not in r.text:
        raise Exception(f'Wowhead returned an unexpected page for zone {zone_id}')

    start = r.text.find("template: 'npc'")
    if start == -1:  # No NPCs on page
        return None
    start = r.text.find('data: [', start)
    end = r.text.find('});', start)
    if start == -1 or end == -1:
        raise Exception(f'Could not read the NPC listview of zone {zone_id}')
    json_data = r.text[start + len('data: '):end]
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
        with multiprocessing.Pool(SCRAPE_THREADS) as p:
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


def apply_page_data_to_metadata(expansion, metadata: dict[int, dict[str, NPC_MD]], page_data: dict[int, NPC_Data]):
    unavailable = []
    for id, npcs in metadata.items():
        npc_md = npcs[expansion]
        page_npc = page_data.get(id)
        if not page_npc:
            if npc_md.name == FORCE_LOAD_NAME:
                unavailable.append(id)
            continue
        if npc_md.name == FORCE_LOAD_NAME:
            npc_md.name = page_npc.name
            npc_md.tag = page_npc.tag
            continue
        if npc_md.name != page_npc.name:
            print(f'Warning! NPC#{id}:{expansion} name differs between search and page: '
                  f'"{npc_md.name}" <> "{page_npc.name}"')
        if npc_md.tag != page_npc.tag:
            print(f'Warning! NPC#{id}:{expansion} tag differs between search and page: '
                  f'"{npc_md.tag}" <> "{page_npc.tag}"')
    if unavailable:
        print(f'Warning! Wowhead({expansion}) has no page for force-loaded NPCs: {sorted(unavailable)}')


def retrieve_forced_npc_pages(expansion, force_ids: list[int]) -> dict[int, NPC_Data]:
    # For expansions we don't pull quotes for, only the force-loaded pages are fetched - their name/tag
    # exists nowhere else, and the full page set would be a multi-hour download.
    save_htmls_from_wowhead(expansion, set(force_ids))
    html_cache = f'cache/{expansion_data[expansion][HTML_CACHE]}'
    return {id: parse_wowhead_npc_page(expansion, id) for id in force_ids
            if os.path.exists(f'{html_cache}/{id}.html')}


def retrieve_npc_data() -> tuple[dict[int, dict[str, NPC_MD]], dict[str, dict[int, NPC_Data]]]:
    all_npcs = dict()
    npc_quotes = dict()

    for expansion, expansion_properties in expansion_data.items():
        wowhead_md = get_wowhead_npc_metadata(expansion)

        if expansion_properties[RETRIEVE_QUOTES]:
            save_htmls_from_wowhead(expansion, set(wowhead_md.keys()))
            npc_quotes[expansion] = parse_wowhead_pages(expansion, wowhead_md)
            apply_page_data_to_metadata(expansion, wowhead_md, npc_quotes[expansion])
        elif expansion_properties[FORCE_DOWNLOAD]:
            forced_pages = retrieve_forced_npc_pages(expansion, expansion_properties[FORCE_DOWNLOAD])
            apply_page_data_to_metadata(expansion, wowhead_md, forced_pages)

        print(f'Merging with {expansion}')
        all_npcs = merge_expansions(all_npcs, wowhead_md)

    fix_npc_data(all_npcs)

    return all_npcs, npc_quotes


def read_classicua_translations(entries_root_path: str) -> dict[str, dict[int, NPC_Short]]:
    return {expansion: load_npc_lua(f'{entries_root_path}/{expansion}/npc.lua')
            for expansion in expansion_data.keys()}


def apply_translations_to_data(all_npcs: dict[int, dict[str, NPC_MD]], translations: dict[str, dict[int, NPC_Short]]):
    for key in all_npcs.keys():
        for expansion in all_npcs[key].keys():
            if key in translations[expansion]:
                all_npcs[key][expansion].name_ua = translations[expansion][key].name
                all_npcs[key][expansion].tag_ua = translations[expansion][key].tag


def populate_npc_locations(all_npcs: dict[int, dict[str, NPC_MD]]):
    # Just for handier translation
    from generation.zones import zones
    wowhead_zones = zones.get_wowhead_zones()
    npc_ids_to_zone_ids = get_wowhead_zones_npc_ids(wowhead_zones.keys())

    # The search metadata already carries a per-expansion location, and the zone pages are scraped from
    # the classic client only - so the two complement each other rather than replace one another.
    for key in all_npcs.keys():
        for expansion in all_npcs[key].keys():
            npc_md = all_npcs[key][expansion]
            zone_ids = set(npc_md.location or []) | set(npc_ids_to_zone_ids.get(key, []))
            npc_md.location = sorted(zone_ids)


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
    with open(f'input/translations.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            npc_id = __try_cast_str_to_int(row[0])
            if not npc_id:
                print(f'Skipping: {row}')
                continue
            name_en = row[2]
            tag_en = row[3][1:-1] if row[3] != '' else None
            name_ua = row[4]
            tag_ua = row[5][1:-1] if row[5] != '' else None
            expansion = row[1]
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
        if feedback_id in all_npcs:
            translated = False
            for npc in all_npcs[feedback_id].values():
                if npc.name_ua:
                    translated = True
            if not translated:
                # print(f'Warning! Feedback NPC#{feedback_id} "{feedback_name}" is not translated!')
                missed_npcs.add(feedback_id)
        else:
            # print(f'Warning? Feedback NPC#{feedback_id} "{feedback_name}" does not exist in DB!')
            # missed_npcs.add(feedback_id)
            continue

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


def build_name_pretranslation_map(npcs: dict[int, dict[str, NPC_MD]]) -> dict[str, str]:
    name_translations = dict()
    for key in npcs.keys():
        for expansion, npc in sorted(npcs[key].items()):
            if npc.name_ua:
                if npc.name in name_translations and name_translations[npc.name] != npc.name_ua:
                    print(f'Warning! Name translation for {npc.name} differs: {name_translations[npc.name]} <> {npc.name_ua}')
                else:
                    name_translations[npc.name] = npc.name_ua
    return name_translations


def create_translation_sheet(npcs: dict[int, dict[str, NPC_MD]], missed_npcs: set[int] = None):
    name_pretranslation_map = build_name_pretranslation_map(npcs)
    with (open(f'translate_this.tsv', mode='w', encoding='utf-8') as f):
        f.write('ID\tName(EN)\tDescription(EN)\tName(UA)\tDescription(UA)\tраса\tстать\tNote\texpansion\n')
        count = 0
        for key in sorted(npcs.keys()):
            for expansion, npc in npcs[key].items():
                if (npc.name_ua is None and (npc.react != [None, None] or npc.location != [] or key in missed_npcs or npc.name in name_pretranslation_map.keys()) and npc.expansion in [CLASSIC, SOD, TBC]):
                    npc_name_ua = npc.name_ua if npc.name_ua else ''
                    if npc_name_ua == '' and npc.name in name_pretranslation_map.keys():
                        npc_name_ua = name_pretranslation_map[npc.name] + ' ???'
                # if npc.name_ua is None and npc.expansion in [CLASSIC, SOD]:
                # if npc.expansion in [CLASSIC, SOD] and npc.id in [14465, 14466, 229001, 232335, 202387, 202390, 222231, 202392, 202391, 14751, 222240, 205733, 230695, 7863, 8376, 212157, 11200, 213450, 229452, 222293, 7383, 232921, 2671, 2673, 2674, 228596, 11637, 7543, 7545, 223739]:
                    f.write(f'{npc.id}\t"{npc.name}"\t"{f"<{npc.tag}>" if npc.tag else ""}"\t{npc_name_ua}\t\t\t\t\t{npc.expansion}\n')
                    count += 1
        if count > 0:
            print(f"Added {count} NPCs for translation")


def save_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/npc={id}'
    html_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    if os.path.exists(html_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    r = wowhead_get(url)
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

    # for id in save_ids:
    #     print(f"Saving NPC #{id}")
    #     save_page(expansion, id)
    save_func = partial(save_page, expansion)
    with multiprocessing.Pool(SCRAPE_THREADS) as p:
        p.map(save_func, save_ids)


def __parse_npc_name_and_tag(html: str, heading: str) -> tuple[str, str]:
    page_info_name = re.search(r'g_pageInfo = \{[^}]*?name: "((?:[^"\\]|\\.)*)"', html)
    if page_info_name:
        npc_name = json.loads(f'"{page_info_name.group(1)}"')  # a JS string literal: \" and \/ occur
        if heading.startswith(npc_name):
            npc_tag = heading[len(npc_name):].strip()
            if npc_tag.startswith('<') and npc_tag.endswith('>'):
                return npc_name, npc_tag[1:-1]
            return npc_name, npc_tag or None
    print(f'Warning! No usable g_pageInfo name, splitting the heading instead: "{heading}"')
    npc_name, _, npc_tag = heading.partition(' <')
    return npc_name, (npc_tag[:-1] if npc_tag.endswith('>') else npc_tag) or None


def parse_wowhead_npc_page(expansion, id) -> NPC_Data:
    # print(f"Parsing #{id}")
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html5lib')

    npc_name, npc_tag = __parse_npc_name_and_tag(html, soup.find('h1').text)
    npc_quotes_header = soup.find('h2', {'class': 'heading-size-3'}, string=re.compile('Quotes'))

    npc_quotes = list()
    if npc_quotes_header:
        npc_quotes_list = npc_quotes_header.find_next('ul').find_all('li')
        for list_element in npc_quotes_list:
            npc_quote = list_element.text[list_element.text.find(':') + 2:]
            # npc_quote = npc_quote.replace('  ', ' ')
            npc_quotes.append(npc_quote)

    return NPC_Data(id, expansion, name=npc_name, quotes=npc_quotes, tag=npc_tag)


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
        with multiprocessing.Pool(PARSE_THREADS) as p:
            wowhead_npcs = p.map(parse_func, metadata.keys())
        wowhead_npcs = {npc.id: npc for npc in wowhead_npcs}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_npcs, f)

    # wowhead_item_data = merge_quests_and_metadata(wowhead_items, metadata)

    # return wowhead_quest_entities
    return wowhead_npcs


def save_npc_quotes(npc_quotes: dict[str, dict[int, NPC_Data]]):
    import pickle
    os.makedirs('output', exist_ok=True)
    with open('output/all_npcs.pkl', 'wb') as f:
        pickle.dump(npc_quotes, f)
    print(f'Stored quotes for {", ".join(npc_quotes.keys())}')


def read_pending_npcs(path: str) -> list[PendingNpc]:
    import csv
    with open(path, 'r', encoding='utf-8') as input_file:
        rows = list(csv.reader(input_file))
    columns = {name: i for i, name in enumerate(rows[0])}

    def value(row, name):
        index = columns[name]
        return row[index].strip() if len(row) > index else ''

    result = []
    for row in rows[1:]:
        if not row or not value(row, 'Id'):
            continue
        result.append(PendingNpc(value(row, 'Id'), value(row, 'expansion'), value(row, 'Name(EN)'),
                                 value(row, 'Tag (EN)'), value(row, 'Name(UA)'), value(row, 'Tag (UA)'),
                                 value(row, 'раса'), value(row, 'стать'), value(row, 'Note')))
    return result


def group_pending_npcs(pending: list[PendingNpc]) -> dict[str, list[PendingNpc]]:
    # A Note holding another NPC's id folds that row into the same glossary term - a character's other
    # incarnations, minions and parts don't deserve terms of their own. The head is the row it points at.
    groups = dict()
    for npc in pending:
        groups.setdefault(npc.note or npc.id, []).append(npc)
    for key, members in groups.items():
        members.sort(key=lambda npc: (npc.id != key, npc.id))
    return groups


def __as_tag(text: str) -> str:
    # Tags are comma separated in the glossary definition, and a literal comma is escaped as '_'
    return text.strip().strip('<>').strip().replace(',', '_')


def __is_untranslated(text: str) -> bool:
    # Same test ClassicUA runs over generated entries: no Ukrainian characters means nobody translated it
    return bool(text) and text == text.encode(encoding='utf-8').decode('ascii', errors='ignore')


def __resolve_pending_tag(npc: PendingNpc, glossary: Glossary,
                          translations: dict[str, set[str]]) -> tuple[str, list[ValidationError]]:
    # An English tag is a reference to another glossary term, so one translation is shared by every NPC
    # using it (and picks the right gender). A Ukrainian tag is a literal that has to be repeated, which
    # is perfectly fine for a one-off description - only report it when there is something to gain.
    issues = []
    tag_en = __as_tag(npc.tag_en)
    tag_uk = __as_tag(npc.tag_uk)

    if tag_en and glossary.resolve(tag_en) is not None:
        return tag_en, issues

    if tag_en and not tag_uk:
        issues.append(ValidationError(npc.id, npc.expansion, 'npc', 'Error', 'tag',
                                      f'No glossary term resolves tag "{tag_en}" and there is no Ukrainian '
                                      f'fallback, so it would reach the addon untranslated. Add a term for '
                                      f'it, or fill Tag (UA).'))
        return tag_en, issues

    if not tag_uk:
        return '', issues

    if __is_untranslated(tag_uk):
        issues.append(ValidationError(npc.id, npc.expansion, 'npc', 'Error', 'tag',
                                      f'Tag (UA) "{tag_uk}" has no Ukrainian characters - it looks like the '
                                      f'English tag was copied over instead of translated.'))
        return tag_uk, issues

    candidates = translations.get(tag_uk)
    if candidates:
        suggestion = f'<{sorted(candidates)[0]}>' if len(candidates) == 1 else \
            'one of ' + ', '.join(f'<{c}>' for c in sorted(candidates))
        issues.append(ValidationError(npc.id, npc.expansion, 'npc', 'Warning', 'tag',
                                      f'Ukrainian tag "{tag_uk}" is already the translation of an existing '
                                      f'term - write {suggestion} instead to share it.'))
    return tag_uk, issues


def __id_tag(npc: PendingNpc, reference_name_uk: str, tag: str) -> str:
    # #ID[:EXPANSION][ NAME][ <DESC>] - the name is only spelled out when it differs from the term's own
    result = f'#{npc.id}' + (f':{npc.expansion}' if npc.expansion and npc.expansion != CLASSIC else '')
    if npc.name_uk and npc.name_uk != reference_name_uk:
        result += f' {__as_tag(npc.name_uk)}'
    if tag:
        result += f' <{tag}>'
    return result


def __append_ids_to_term(existing: GlossaryTerm, members: list[PendingNpc],
                         member_tags: dict[str, str]) -> tuple[str, str]:
    # Only the missing ids are appended - the rest of the term is hand-curated, so it is left alone
    known_ids = set(existing.npc_ids())
    added = [__id_tag(npc, existing.translation(), member_tags[npc.id]) for npc in members
             if (int(npc.id), npc.expansion or CLASSIC) not in known_ids]
    return (existing.text_en, ', '.join(existing.tags + added)) if added else None


def __build_glossary_term(key: str, members: list[PendingNpc], glossary: Glossary,
                          translations: dict[str, set[str]], terms_by_en: dict,
                          id_owners: dict) -> tuple[tuple, tuple, list[ValidationError]]:
    # Returns (new_term, description_update, issues). A group whose NPCs belong to a term that already
    # exists becomes an update to that term rather than a new one.
    issues = []
    head = members[0]
    existing = None

    if head.id != key:
        owners = sorted({owner for (npc_id, _), names in id_owners.items() if str(npc_id) == key
                         for owner in names})
        if not owners:
            issues.append(ValidationError(key, head.expansion, 'npc', 'Error', 'note',
                                          f'{len(members)} NPCs point at #{key}, which is neither in this '
                                          f'sheet nor in the glossary: {", ".join(n.id for n in members)}.'))
            return None, None, issues
        existing = terms_by_en[owners[0].lower()][0]
        issues.append(ValidationError(key, head.expansion, 'npc', 'Warning', 'note',
                                      f'{len(members)} NPCs point at #{key}, so they are appended to the '
                                      f'existing term "{existing.text_en}" instead of starting a new one: '
                                      f'{", ".join(n.id for n in members)}.'))
    elif head.name_en.lower() in terms_by_en:
        existing = terms_by_en[head.name_en.lower()][0]
        issues.append(ValidationError(head.id, head.expansion, 'npc', 'Warning', 'name_en',
                                      f'Term "{head.name_en}" already exists in the glossary '
                                      f'(-> {existing.text_uk}), so the ids are appended to it instead of '
                                      f'adding a new term: {", ".join(n.id for n in members)}.'))

    for npc in members:
        if __is_untranslated(npc.name_uk):
            issues.append(ValidationError(npc.id, npc.expansion, 'npc', 'Error', 'name_uk',
                                          f'Name(UA) "{npc.name_uk}" has no Ukrainian characters - it looks '
                                          f'like the English name was copied over instead of translated.'))
            return None, None, issues

    if not existing and not head.name_uk:
        issues.append(ValidationError(head.id, head.expansion, 'npc', 'Error', 'name_uk',
                                      f'"{head.name_en}" heads a group of {len(members)} but has no '
                                      f'Ukrainian name, so no term can be created for it.'))
        return None, None, issues

    member_tags = dict()
    for npc in members:
        tag, tag_issues = __resolve_pending_tag(npc, glossary, translations)
        issues.extend(tag_issues)
        member_tags[npc.id] = tag

    if existing:
        return None, __append_ids_to_term(existing, members, member_tags), issues

    tags = [NPC_TAG]
    if head.sex:
        tags.append(__as_tag(head.sex))
    if head.race:
        tags.append(__as_tag(head.race))

    # Most of the glossary keeps a shared description at term level and only repeats it per id when the
    # NPCs differ, so follow that.
    shared_tag = member_tags[head.id] if len(set(member_tags.values())) == 1 else ''
    if shared_tag:
        tags.append(f'<{shared_tag}>')

    tags.extend(__id_tag(npc, head.name_uk, '' if shared_tag else member_tags[npc.id]) for npc in members)

    return (head.name_en, head.name_uk, ', '.join(tags)), None, issues


MIN_REPEATS_FOR_OWN_TERM = 3  # how often a tag must repeat before it deserves a glossary term of its own
def __validate_repeated_tags(groups: dict[str, list[PendingNpc]], glossary: Glossary,
                             translations: dict[str, set[str]]) -> list[ValidationError]:
    import collections
    # A Ukrainian tag written out many times over is a term waiting to be created
    orphans = collections.Counter()
    for members in groups.values():
        for npc in members:
            tag_uk = __as_tag(npc.tag_uk)
            tag_en = __as_tag(npc.tag_en)
            if tag_uk and tag_uk not in translations and glossary.resolve(tag_en or tag_uk) is None:
                orphans[(tag_en, tag_uk)] += 1

    issues = []
    for (tag_en, tag_uk), count in orphans.most_common():
        if count >= MIN_REPEATS_FOR_OWN_TERM:
            issues.append(ValidationError(0, '', 'npc', 'Warning', 'tag',
                                          f'Tag "{tag_uk}" is written out {count} times and no term '
                                          f'resolves it' + (f' (English: "{tag_en}")' if tag_en else '') +
                                          '. Consider adding a glossary term so it is translated once.'))
    return issues


def __report_pending_issues(issues: list[ValidationError]):
    for severity in ('Error', 'Warning'):
        of_severity = [i for i in issues if i.severity == severity]
        if not of_severity:
            continue
        print('-' * 100)
        for issue in of_severity:
            print(issue)
    errors = len([i for i in issues if i.severity == 'Error'])
    warnings = len(issues) - errors
    print('-' * 100)
    print(f'Pending NPCs validation: {errors} error(s), {warnings} warning(s)')


def __write_new_glossary_terms(new_terms: list[tuple], path: str = 'output/new_npcs_glossary.csv'):
    import csv
    # The tags go in Description [en] - that is what ClassicUA reads the NPC ids and traits out of.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as output_file:
        writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
        writer.writerow(['Term [en]', 'Term [uk]', 'Description [en]'])
        for text_en, text_uk, description in new_terms:
            writer.writerow([text_en, text_uk, description])
    print(f'Wrote {len(new_terms)} new glossary terms to {path}')


def process_pending_npcs(glossary: Glossary):
    # Pending NPCs sheet -> new Crowdin glossary terms, plus everything that needs a manual fix first.
    # Replaces the old combine_npcs.py flow.
    pending = read_pending_npcs('input/pending_npcs.csv')
    groups = group_pending_npcs(pending)
    print(f'Read {len(pending)} pending NPCs in {len(groups)} group(s)')

    translations = glossary.terms_by_translation()
    terms_by_en = glossary.terms_by_en()
    id_owners = glossary.npc_id_owners()

    issues = []
    new_terms = []
    description_updates = []
    for key in sorted(groups, key=lambda k: int(k) if k.isdigit() else 0):
        term, update, term_issues = __build_glossary_term(key, groups[key], glossary, translations,
                                                          terms_by_en, id_owners)
        issues.extend(term_issues)
        if term:
            new_terms.append(term)
        if update:
            description_updates.append(update)

    issues.extend(__validate_repeated_tags(groups, glossary, translations))

    __report_pending_issues(issues)
    __write_new_glossary_terms(new_terms)
    return new_terms, description_updates


def __bracketed(text: str) -> str:
    # The sheet keeps descriptions in angle brackets; the sources hand them over either way
    text = (text or '').strip().strip('<>').strip()
    return f'<{text}>' if text else ''


def __glossary_terms_by_npc_id(glossary: Glossary) -> dict[tuple[int, str], GlossaryTerm]:
    result = dict()
    for term in glossary.npcs():
        for npc_id in term.npc_ids():
            result[npc_id] = term
    return result


SEX_TAGS = ('чол', 'жін')
def __term_traits(term: GlossaryTerm) -> tuple[str, str]:
    # Race and sex have their own columns in the sheet, but in the glossary they are ordinary tags
    sex = next((tag for tag in term.tags if tag in SEX_TAGS), '')
    race = next((tag for tag in term.tags if tag != NPC_TAG and tag not in SEX_TAGS
                 and not tag.startswith('#') and not tag.startswith('<')), '')
    return race, sex


def create_missing_entries_sheet(all_npcs: dict[int, dict[str, NPC_MD]], glossary: Glossary,
                                 entries_dir: str = 'input/entries', path: str = 'output/missing_entries.tsv'):
    import csv
    translations = read_classicua_translations(entries_dir)
    sheet = load_merged_translations()
    terms_by_id = __glossary_terms_by_npc_id(glossary)

    rows = []
    missing_from_wowhead = []
    for expansion in expansion_data:
        for npc_id in sorted(translations.get(expansion, {})):
            if expansion in sheet.get(npc_id, {}):
                continue
            entry = translations[expansion][npc_id]
            # npcs.db collapses an NPC into the expansion it first appeared in, so fall back to any of them
            wowhead_npcs = all_npcs.get(npc_id) or {}
            wowhead = wowhead_npcs.get(expansion) or next(iter(wowhead_npcs.values()), None)
            if not wowhead:
                missing_from_wowhead.append(f'{npc_id}:{expansion}')
            term = terms_by_id.get((npc_id, expansion))
            race, sex = __term_traits(term) if term else ('', '')
            rows.append([npc_id, expansion,
                         wowhead.name if wowhead else '',
                         __bracketed(wowhead.tag) if wowhead else '',
                         entry.name or '',
                         __bracketed(entry.tag),
                         race, sex, 'ClassicUA import'])

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as output_file:
        writer = csv.writer(output_file, delimiter='\t')
        writer.writerow(['Id', 'expansion', 'Name(EN)', 'Description (EN)', 'Name(UA)',
                         'Description (UA)', 'раса', 'стать', 'Note'])
        writer.writerows(rows)

    in_sheet = sum(len(expansions) for expansions in sheet.values())
    generated = sum(len(entries) for entries in translations.values())
    print(f'NPCs sheet has {in_sheet} row(s), ClassicUA generates {generated} entry(ies)')
    print(f'Wrote {len(rows)} missing entry(ies) to {path}')
    if missing_from_wowhead:
        print(f'Warning! {len(missing_from_wowhead)} of them are not in npcs.db, so they have no English '
              f'original: {", ".join(missing_from_wowhead[:10])}'
              + (' ...' if len(missing_from_wowhead) > 10 else ''))


def generate_entries_with_classicua(glossary: Glossary, entries_dir: str = 'input/entries') -> Glossary:
    # ClassicUA owns NPC entry generation - it turns the Crowdin glossary into entries/<expansion>/npc.lua
    # the same way it does for quests, chats and gossips - so run its generator instead of repeating the
    # rules here, then take the result as our input. Returns the glossary it generated from, which is a
    # newer one than the caller passed in.
    if not classicua_root():
        print(f'CLASSICUA_ROOT is not set, keeping the existing {entries_dir}')
        return glossary

    # This runs straight after the glossary was updated on Crowdin, so the local copy is a version behind
    # by definition - regenerating from it would quietly undo the terms we just added.
    download_crowdin_glossary(glossary_path())
    run_classicua_generator('gen_npc_lua.py', glossary=glossary_path())
    print(f'Copying generated entries into {entries_dir}')
    copy_classicua_entries('npc.lua', expansion_data.keys(), entries_dir)
    return Glossary.load()


if __name__ == '__main__':
    download_csv_from_google_sheet('NPCs')

    all_npcs_md, npc_quotes = retrieve_npc_data()

    populate_npc_locations(all_npcs_md)

    classicua_translations = read_classicua_translations('input/entries')
    apply_translations_to_data(all_npcs_md, classicua_translations)

    save_npcs_to_db(all_npcs_md)  # Generate cache/npcs.db
    save_npc_quotes(npc_quotes)  # Generate output/all_npcs.pkl

    check_existing_translations(all_npcs_md)  # Check if original data changes since previous translation and difference between ClassicUA and translation sheet
    # update_questie_translation(all_npcs)  # Update translations for Questie

    missed_npcs = check_feedback_npcs(all_npcs_md)

    # create_translation_sheet(all_npcs_md)
    create_translation_sheet(all_npcs_md, missed_npcs)

    # Pending NPCs -> new Crowdin glossary terms (replaces combine_npcs.py)
    download_csv_from_google_sheet('Pending NPCs', 'input/pending_npcs.csv')
    glossary = Glossary.load()
    new_terms, description_updates = process_pending_npcs(glossary)
    update_glossary_on_crowdin(new_terms, description_updates)

    # Regenerate ClassicUA's npc.lua from the updated glossary and take it as our input
    # glossary = generate_entries_with_classicua(glossary)

    # Entries that exist in ClassicUA but were never recorded on the NPCs sheet
    # create_missing_entries_sheet(all_npcs_md, glossary)

