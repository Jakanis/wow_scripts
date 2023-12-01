import json
import os
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup, CData

THREADS = 16
CLASSIC = 'classic'
SOD = 'sod'
TBC = 'tbc'
WRATH = 'wrath'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
SPELL_CACHE = 'item_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'

expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_spell_html',
        SPELL_CACHE: 'wowhead_classic_spell_cache',
        METADATA_FILTERS: ('21:', '5:', '11500:'),
        IGNORES: []
    },
    SOD: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_spell_html',
        SPELL_CACHE: 'wowhead_sod_spell_cache',
        METADATA_FILTERS: ('21:', '2:', '11500:'),
        IGNORES: []
    },
    TBC: {
        INDEX: 1,
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_spell_html',
        SPELL_CACHE: 'wowhead_tbc_spell_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: []
    },
    WRATH: {
        INDEX: 2,
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_spell_html',
        SPELL_CACHE: 'wowhead_wrath_spell_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: []
    }
}


# Metadata from Wowhead
class SpellMD:
    _classes = {
        1: 'warrior',
        2: 'paladin',
        4: 'hunter',
        8: 'rogue',
        16: 'priest',
        64: 'shaman',
        128: 'mage',
        256: 'warlock',
        1024: 'druid',
    }
    def __init__(self, id, name, expansion=None, cat=None, level=None, schools=None, rank=None, chrclass=None, reqclass=None, skill=None):
        self.id = id
        self.name = name
        self.expansion = expansion
        self.cat = cat
        self.level = level
        self.schools = schools
        self.rank = rank
        self.chrclass = chrclass
        self.reqclass = reqclass
        self.skill = skill

    def get_class(self):
        if not self.chrclass and not self.reqclass:
            return None
        if self.chrclass == self.reqclass:
            return self._classes.get(self.chrclass) if self.chrclass in self._classes else 'unknown'
        return 'ERROR'


class SpellData:
    spell_md: SpellMD
    description_ref: int
    aura_ref: int

    def __init__(self, id, expansion, name, description=None, aura_name=None, aura_description=None):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.description = description
        self.aura_name = aura_name
        self.aura_description = aura_description
        self.spell_md = None
        self.description_ref = 0
        self.aura_ref = 0


class SpellTranslation:
    def __init__(self, id, name, name_ua, description_ua=None, aura_ua=None):
        self.id = id
        self.name = name
        self.name_ua = name_ua
        self.description_ua = description_ua
        self.aura_ua = aura_ua


def __get_wowhead_spell_search(expansion, start, end=None) -> list[SpellMD]:
    base_url = expansion_data[expansion][WOWHEAD_URL]
    metadata_filters = expansion_data[expansion][METADATA_FILTERS]
    if end:
        url = base_url + f"/spells?filter={metadata_filters[0]}14:14;{metadata_filters[1]}2:5;{metadata_filters[2]}{start}:{end}"
    else:
        url = base_url + f"/spells?filter={metadata_filters[0]}14;{metadata_filters[1]}2;{metadata_filters[2]}{start}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    script_tag = soup.find('script', src=None, type="text/javascript")
    if not script_tag:
        return []
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('listviewspells = [') + 16
        end = script_content.find('}];') + 2
        json_data = (script_content[start:end]
                     .replace('quality:', '"quality":')
                     .replace('popularity:', '"popularity":'))
        return list(map(lambda md: SpellMD(md.get('id'), md.get('name'), expansion, md.get('cat'), md.get('level'), md.get('schools'), md.get('rank'), md.get('chrclass'), md.get('reqclass'), md.get('skill')), json.loads(json_data)))
    else:
        return []


def __retrieve_spells_metadata_from_wowhead(expansion) -> dict[int, SpellMD]:
    all_spells_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            items = __get_wowhead_spell_search(expansion, start)
            print(f'Checking {start}+. Len: {len(items)}')
            if len(items) < 1000:
                all_spells_metadata.extend(items)
                break
        items = __get_wowhead_spell_search(expansion, start, start + 1000)
        all_spells_metadata.extend(items)
        i += 1
    return {md.id: md for md in all_spells_metadata}


def get_wowhead_items_metadata(expansion) -> dict[int, SpellMD]:
    import pickle
    cache_file_name = expansion_data[expansion][METADATA_CACHE]
    if os.path.exists(f'cache/tmp/{cache_file_name}.pkl'):
        print(f'Loading cached Wowhead({expansion}) metadata')
        with open(f'cache/tmp/{cache_file_name}.pkl', 'rb') as f:
            wowhead_metadata = pickle.load(f)
    else:
        print(f'Retrieving Wowhead({expansion}) metadata')
        wowhead_metadata = __retrieve_spells_metadata_from_wowhead(expansion)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/{cache_file_name}.pkl', 'wb') as f:
            pickle.dump(wowhead_metadata, f)
    return wowhead_metadata


def save_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/spell={id}'
    xml_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    if os.path.exists(xml_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    r = requests.get(url)
    if not r.ok:
        # You download over 90000 pages in one hour - you'll fail
        # You do it async - you fail
        # Have a tea break (or change IP, lol)
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for spell #{id}')
    if (f"Spell #{id} doesn't exist." in r.text):
        return
    with open(xml_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_htmls_from_wowhead(expansion, ids: set[int]):
    from functools import partial
    import multiprocessing
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}'

    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'HTML cache for all Wowhead({expansion}) spells ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    print(f'Saving HTMLs for {len(save_ids)} of {len(ids)} spells from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    save_func = partial(save_page, expansion)
    # for id in ids:
    #     save_page(expansion, id)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_func, save_ids)


def parse_wowhead_spell_page(expansion, id) -> SpellData:
    import re
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html.parser')
    data_lines = soup.find('div', {'class': 'db-action-buttons'}).next_sibling.text.splitlines()

    tooltip = buff = None
    for line in data_lines:
        if line.startswith(f'g_spells[{id}].tooltip_enus = '):
            tooltip = line.replace(f'g_spells[{id}].tooltip_enus = "', '').replace('\\', '')[:-2]
        if line.startswith(f'g_spells[{id}].buff_enus = '):
            buff = line.replace(f'g_spells[{id}].buff_enus = "', '').replace('\\', '')[:-2]

    if not tooltip:
        print(f'Error parsing spell #{id}')
        return None

    tooltip_soup = BeautifulSoup(tooltip, 'html.parser')
    name = soup.find('h1').text
    description_tables = tooltip_soup.find_all('table')
    description_text = description_tables[-1].find('div', {'class': 'q'}) if len(description_tables) > 1 else None
    description = None
    if description_text:
        for br in description_text.find_all('br'):
            br.replace_with('\n')
        description = description_text.text
        description = re.sub('\n+', '\n', description)

    aura_name = aura_description = None
    if buff:
        aura_soup = BeautifulSoup(buff, 'html.parser')
        aura_name = aura_soup.find('b', {'class': 'q'}).text
        aura_description = aura_soup.find_all('td')[-1].get_text(strip=True, separator='<SPLIT>').split('<SPLIT>')[0]

    return SpellData(id, expansion, name, description, aura_name, aura_description)


def parse_wowhead_pages(expansion, metadata: dict[int, SpellMD]) -> dict[int, SpellData]:
    import pickle
    import multiprocessing
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][SPELL_CACHE]}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) spells')
        with open(cache_path, 'rb') as f:
            wowhead_spells = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) spell pages')
        # wowhead_spells = {id: parse_wowhead_spell_page(expansion, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_spell_page, expansion)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_spells = p.map(parse_func, metadata.keys())
        wowhead_spells = {item.id: item for item in wowhead_spells}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_spells, f)

    for spell_id, spell in wowhead_spells.items():
        spell.spell_md = metadata[spell_id]

    return wowhead_spells

def load_object_lua() -> dict[str, str]:
    from slpp import slpp as lua
    translations = dict()
    with open('input/object.lua', 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        decoded_objects = lua.decode(lua_file)
        for object_name, object_translation in decoded_objects.items():
            if object_name.lower() in translations:
                print('Warning! Duplicated object in ClassicUA.')
            translations[object_name.lower()] = object_translation
    return translations


def load_item_lua_names() -> dict[int, str]:
    from slpp import slpp as lua
    items = dict()
    with open('input/item.lua', 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        decoded_items = lua.decode(lua_file)
        for item_id, decoded_item in decoded_items.items():
            if type(decoded_item) == list or 0 in decoded_item:
                item_name_ua = decoded_item[0]
            else:
                item_name_ua = decoded_items[decoded_item['ref']][0]
            items[item_id] = item_name_ua
    return items


def load_questie_item_lua_ids() -> set[int]:
    from slpp import slpp as lua
    item_ids = set()
    with open('input/lookupItems.lua', 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        decoded_items = lua.decode(lua_file)
        for item_id, decoded_item in decoded_items.items():
            item_ids.add(item_id)
    return item_ids


def save_spells_to_db(spells: dict[int, SpellData]):
    import sqlite3
    print('Saving spells to DB')
    conn = sqlite3.connect('cache/spells.db')
    conn.execute('DROP TABLE IF EXISTS spells')
    conn.execute('''CREATE TABLE spells (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        description TEXT,
                        aura_name TEXT,
                        aura_description TEXT,
                        rank TEXT,
                        cat INT,
                        level INT,
                        schools INT,
                        class INT,
                        skill TEXT,
                        desc_ref INT,
                        aura_ref INT
                )''')
    conn.commit()
    with (conn):
        for key, spell in spells.items():
            if ('[DNT]' in spell.name or
                'DND' in spell.name or
                key in expansion_data[spell.expansion][IGNORES]):
                    continue
            md_skill = str(spell.spell_md.skill) if spell.spell_md.skill else None
            conn.execute('INSERT INTO spells(id, expansion, name, description, aura_name, aura_description, rank, cat, level, schools, class, skill, desc_ref, aura_ref) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (spell.id, spell.expansion, spell.name, spell.description, spell.aura_name, spell.aura_description, 
                         spell.spell_md.rank, spell.spell_md.cat, spell.spell_md.level, spell.spell_md.schools, spell.spell_md.get_class(), md_skill,
                         spell.description_ref, spell.aura_ref))


def populate_similarity(spells: dict[int, SpellData]):
    import re
    description_to_id: dict[str, int] = dict()
    aura_description_to_id: dict[str, int] = dict()

    for key, spell in sorted(spells.items()):
        description = spell.name + ':' + re.sub(r'\d+', '{d}', spell.description) if spell.description else None
        aura_description = spell.name + ':' + re.sub(r'\d+', '{d}', spell.aura_description) if spell.aura_description else None
        if description and description in description_to_id.keys():
            spell.description_ref = description_to_id[description]
        else:
            description_to_id[description] = key

        if aura_description and aura_description in aura_description_to_id.keys():
            spell.aura_ref = aura_description_to_id[aura_description]
        else:
            aura_description_to_id[aura_description] = key


def create_translation_sheet(spells: dict[int, SpellData]):
    with open(f'translate_this.tsv', mode='w', encoding='utf-8') as f:
        f.write('ID\tName(EN)\tName(UA)\tDescription(EN)\tDescription(UA)\tAura(EN)\tAura(UA)\tAura description(EN)\tAura description(UA)\tdesc_ref\taura_ref\n')
        for key, spell in sorted(spells.items()):
            if getattr(spell.spell_md, 'chrclass') != 8:
                continue
            f.write(f'{spell.id}\t{spell.name}\t\t"{spell.description}"\t\t{spell.aura_name}\t\t"{spell.aura_description}"\t\t{spell.description_ref}\t{spell.aura_ref}\n')



def populate_cache_db_with_spells_data():
    wowhead_metadata = get_wowhead_items_metadata(CLASSIC)
    wowhead_metadata_sod = get_wowhead_items_metadata(SOD)
    wowhead_metadata_tbc = get_wowhead_items_metadata(TBC)
    wowhead_metadata_wrath = get_wowhead_items_metadata(WRATH)

    # save_htmls_from_wowhead(CLASSIC, set(wowhead_metadata.keys()))
    save_htmls_from_wowhead(SOD, set(wowhead_metadata_sod.keys()))
    # save_xmls_from_wowhead(TBC, set(wowhead_metadata_tbc.keys()))
    # save_xmls_from_wowhead(WRATH, set(wowhead_metadata_wrath.keys()))

    # wowhead_spells = parse_wowhead_pages(CLASSIC, wowhead_metadata)
    wowhead_spells_sod = parse_wowhead_pages(SOD, wowhead_metadata_sod)
    # wowhead_items_tbc = parse_wowhead_pages(TBC, wowhead_metadata_tbc)
    # wowhead_items_wrath = parse_wowhead_pages(WRATH, wowhead_metadata_wrath)

    # translations = load_item_lua_names()
    #
    # for key in wowhead_items.keys() & translations.keys():
    #     wowhead_items[key].name_ua = translations[key]
    #
    # questie_item_ids = load_questie_item_lua_ids()
    #
    # for key in questie_item_ids:
    #     if not wowhead_items[key].name_ua:
    #         wowhead_items[key].name_ua = 'questie'

    populate_similarity(wowhead_spells_sod)

    create_translation_sheet(wowhead_spells_sod)
    # print('Merging with TBC')
    # classic_and_tbc_items = merge_expansions(wowhead_items, wowhead_items_tbc)
    # print('Merging with WotLK')
    # all_items = merge_expansions(classic_and_tbc_items, wowhead_items_wrath)

    save_spells_to_db(wowhead_spells_sod)

def convert_translations_to_lua():
    import csv
    all_translations: list[SpellTranslation] = list()
    with open('input/translations.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            spell_id = row[0]
            name_en = row[1]
            name_ua = row[2]
            description_ua = row[4]
            aura_ua = row[8] if len(row) >= 8 else None
            all_translations.append(SpellTranslation(spell_id, name_en, name_ua, description_ua, aura_ua))

    all_translations = sorted(all_translations, key=lambda x: x.name)

    with open('spell.lua', 'w', encoding="utf-8") as output_file:
        previous_name = None
        for spell in all_translations:
            if spell.name != previous_name:
                output_file.write(f'\n-- {spell.name}\n')
            description_text = spell.description_ua.replace('"', '\\"').replace('\n', '\\n') if spell.description_ua else None
            description_text = f'"{description_text}"' if description_text else 'nil'
            aura_text = spell.aura_ua.replace('"', '\\"').replace('\n', '\\n') if spell.aura_ua else None
            aura_text = f'"{aura_text}"' if aura_text else 'nil'
            output_file.write('[{}] = {{ "{}", {}, {} }}, -- {}\n'.format(spell.id, spell.name_ua, description_text, aura_text, spell.name))
            previous_name = spell.name


if __name__ == '__main__':
    populate_cache_db_with_spells_data()

    convert_translations_to_lua()

    # item = parse_wowhead_spell_page(SOD, 403476)
    # item = parse_wowhead_spell_page(CLASSIC, 364001)
    # print('l')
    # wowhead_metadata = get_wowhead_items_metadata(CLASSIC)
    # object_translations = load_object_lua()
    #
    # for object in wowhead_metadata.values():
    #     if 'TEST' in object.name.upper().split(' ') or object.id in expansion_data[object.expansion][IGNORES]:
    #         continue
    #     if object.name.lower() in object_translations:
    #         object.name_ua = object_translations[object.name.lower()]
    #     else:
    #         print(f"Translation for {object} doesn't exist")

    # questie_objects = load_questie_objects_ids()
    #
    # missing_questie_objects = {
    #     175287: 'жаровня',
    #     175298: 'жаровня'
    # }
    # for key in wowhead_metadata.keys() & questie_objects:
    #     wowhead_metadata[key].names = 'questie'
    #
    # with open(f'lookupObjects.lua', 'w', encoding="utf-8") as output_file:
    #     for key in sorted(questie_objects):
    #         translation = None
    #         if key in wowhead_metadata:
    #             translation = wowhead_metadata[key].name_ua
    #         else:
    #             translation = missing_questie_objects[key]
    #         if translation is None:
    #             print(f'Missing translation for {key}')
    #             continue
    #         translation = translation.replace('"', '\\"')
    #         output_file.write(f'[{key}] = "{translation}",\n')


    # save_objects_to_db(wowhead_metadata)