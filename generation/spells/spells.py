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
    def __init__(self, id, expansion, name, description=None, aura_name=None, aura_description=None, name_ua=None,
                 description_ua=None, aura_ua=None, description_ref: int = 0, aura_ref: int = 0,
                 spell_md: SpellMD = None, category=None, rank=None):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.description = description
        self.aura_name = aura_name
        self.aura_description = aura_description
        self.name_ua = name_ua
        self.description_ua = description_ua
        self.aura_ua = aura_ua
        self.description_ref = description_ref
        self.aura_ref = aura_ref
        self.spell_md = spell_md
        self.category = category
        self.rank = rank


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
    data_lines = soup.find('div', {'class': 'db-action-buttons'}).next_sibling.text.replace('&nbsp;', ' ').splitlines()

    tooltip = aura = None
    for line in data_lines:
        if line.startswith(f'g_spells[{id}].tooltip_enus = '):
            tooltip = line.replace(f'g_spells[{id}].tooltip_enus = "', '').replace('\\', '')[:-2]
        if line.startswith(f'g_spells[{id}].buff_enus = '):
            aura = line.replace(f'g_spells[{id}].buff_enus = "', '').replace('\\', '')[:-2]

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
        # for a_tag in description_text.find_all('a'):  # Optional thing
        #     a_tag.replace_with(a_tag.get('href'))
        description = description_text.text
        # if re.findall(r'\n\n+', description):
        #     print(f'Subbed \\n in spell#{id}')
        description = re.sub(r'\n\n+', '\n\n', description)

    aura_name = aura_description = None
    if aura:
        aura_soup = BeautifulSoup(aura, 'html.parser')
        aura_name = aura_soup.find('b', {'class': 'q'}).text
        aura_description = aura_soup.find_all('td')[-1]
        for span in aura_description.find_all('span', {'class': 'q'}):
            span.replace_with('\n')
        aura_description = aura_description.get_text(strip=True, separator='<SPLIT>').split('<SPLIT>')
        aura_description = '\n'.join(aura_description)

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


def save_spells_to_db(spells: dict[int, SpellData]):
    import sqlite3
    print('Saving spells to DB')
    conn = sqlite3.connect('cache/spells.db')
    conn.execute('DROP TABLE IF EXISTS spells')
    conn.execute('''CREATE TABLE spells (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        name_ua TEXT,
                        description TEXT,
                        description_ua TEXT,
                        aura TEXT,
                        aura_ua TEXT,
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
            conn.execute('INSERT INTO spells(id, expansion, name, name_ua, description, description_ua, aura, aura_ua, rank, cat, level, schools, class, skill, desc_ref, aura_ref) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (spell.id, spell.expansion, spell.name, spell.name_ua, spell.description, spell.description_ua, spell.aura_description, spell.aura_ua,
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
            if getattr(spell.spell_md, 'chrclass') != 256:
                continue
            f.write(f'{spell.id}\t{spell.name}\t\t"{spell.description}"\t\t{spell.aura_name}\t\t"{spell.aura_description}"\t\t{spell.description_ref}\t{spell.aura_ref}\n')



def retrieve_spell_data():
    wowhead_metadata = get_wowhead_items_metadata(CLASSIC)
    wowhead_metadata_sod = get_wowhead_items_metadata(SOD)
    wowhead_metadata_tbc = get_wowhead_items_metadata(TBC)
    wowhead_metadata_wrath = get_wowhead_items_metadata(WRATH)

    save_htmls_from_wowhead(CLASSIC, set(wowhead_metadata.keys()))
    save_htmls_from_wowhead(SOD, set(wowhead_metadata_sod.keys()))
    # save_xmls_from_wowhead(TBC, set(wowhead_metadata_tbc.keys()))
    # save_xmls_from_wowhead(WRATH, set(wowhead_metadata_wrath.keys()))

    wowhead_spells = parse_wowhead_pages(CLASSIC, wowhead_metadata)
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

    return wowhead_metadata_sod, wowhead_spells_sod


def convert_translations_to_lua(translations: list[SpellData], group: tuple[str, str]):
    path = f'output/entries/{group[0]}'
    catergory = f'_{group[1]}' if group[1] else ''
    translations = sorted(translations, key=lambda x: x.name)
    os.makedirs(path, exist_ok=True)
    with open(f'{path}/spell{catergory}.lua', 'w', encoding="utf-8") as output_file:
        previous_name = None
        for spell in translations:
            if spell.name != previous_name:
                output_file.write(f'\n-- {spell.name}\n')
            description_text = 'nil'
            rune_refs = []
            if spell.description_ua:
                if spell.description_ua.startswith('ref='):
                    ref = int(spell.description_ua.split('=')[-1])
                    output_file.write('[{}] = {{ ref={} }}, -- {}\n'.format(spell.id, ref, spell.name))
                    continue
                description_text = []
                for line in spell.description_ua.splitlines():
                    if 'spell#' in line:
                        rune_refs.append(line.split('#')[-1])
                    else:
                        description_text.append(line)
                description_text = '\n'.join(description_text).replace('"', '\\"').replace('\n', '\\n')
                description_text = f'"{description_text}"'
            aura_text = spell.aura_ua.replace('"', '\\"').replace('\n', '\\n') if spell.aura_ua else None
            aura_text = f'"{aura_text}"' if aura_text else 'nil'
            if rune_refs:  # We take only first rune_ref. Take whole list if we can handle templates
                rune_text = rune_refs[0] if len(rune_refs) == 1 else '{' + ', '.join(rune_refs) + '}'
                output_file.write('[{}] = {{ "{}", {}, {}, rune={} }}, -- {}\n'.format(spell.id, spell.name_ua, description_text, aura_text, rune_text, spell.name))
            else:
                output_file.write('[{}] = {{ "{}", {}, {} }}, -- {}\n'.format(spell.id, spell.name_ua, description_text, aura_text, spell.name))
            previous_name = spell.name


def convert_translations_to_entries(translations: dict[int, SpellData]):
    grouped_translations: dict[tuple[str, str], list[SpellData]] = dict()
    for translation in translations.values():
        if not (translation.expansion, translation.category) in grouped_translations:
            grouped_translations[(translation.expansion, translation.category)] = list()
        grouped_translations[(translation.expansion, translation.category)].append(translation)

    for group, translations in grouped_translations.items():
        convert_translations_to_lua(translations, group)


def __try_cast_str_to_int(value: str, default=None):
    try:
        return int(value)
    except ValueError:
        return default


def read_translations_tsv() -> dict[int, SpellData]:
    import csv
    all_translations: dict[int, SpellData] = dict()
    with open('input/translations.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            spell_id = __try_cast_str_to_int(row[0])
            if not spell_id:
                print(f'Skipping: {row}')
                continue
            name_en = row[1]
            name_ua = row[2]
            description_en = row[3] if row[3] != '' else None
            description_ua = row[4] if row[4] != '' else None
            aura_name_en = row[5] if row[5] != '' else None
            aura_name_ua = row[6] if row[6] != '' else None
            aura_description_en = row[7] if row[7] != '' else None
            aura_description_ua = row[8] if row[8] != '' else None  # if len(row) >= 8 else None
            desc_ref = __try_cast_str_to_int(row[9], 0)
            aura_ref = __try_cast_str_to_int(row[10], 0)
            expansion = row[11]
            category = row[12] if len(row) > 12 and row[12] != '' else None
            if aura_name_ua and aura_name_ua != name_ua:
                print(f'Warning! Translation spell and aura names not equal for spell#{spell_id}!')
            all_translations[spell_id] = SpellData(spell_id, expansion, name=name_en, description=description_en,
                                                   aura_name=aura_name_en, aura_description=aura_description_en,
                                                   name_ua=name_ua, description_ua=description_ua,
                                                   aura_ua=aura_description_ua, description_ref=desc_ref,
                                                   aura_ref=aura_ref, category=category)

    return all_translations

def read_classicua_translations(spells_root_path: str, spell_metadata: dict[int, SpellMD]):
    from slpp import slpp as lua
    file_contents = list()
    for foldername, subfolders, filenames in os.walk(spells_root_path):
        for filename in filenames:
            # Construct the full path to the file
            file_path = foldername + '\\' + filename

            # Read the contents of the file
            with open(file_path, 'r', encoding="utf-8") as file:
                file_content = file.read()
                file_contents.append((file_path, file_content))

    all_spells: dict[int, SpellData] = dict()

    for file_path, lua_file in file_contents:
        expansion, file_name = file_path.split('\\')[-2:]
        file_name_split = file_name[:file_name.find('.')].split('_')
        category = file_name_split[1] if len(file_name_split) > 1 else ''
        lua_table = lua_file[lua_file.find(' = {\n') + 2:lua_file.find('\n}\n') + 2]
        decoded_spells = lua.decode(lua_table)
        for spell_id, decoded_spell in decoded_spells.items():
            if spell_id in all_spells:
                print(f'Warning! Duplicate for spell#{spell_id}')
            if type(decoded_spell) == dict:
                name_ua = decoded_spell.get(0)
                description_ua = decoded_spell.get(1)
                aura_ua = decoded_spell.get(2)
                runes = decoded_spell.get('rune')
                if 'ref' in decoded_spell:
                    name_ua = name_ua or all_spells[decoded_spell.get('ref')].name_ua
                    description_ua = f"ref={decoded_spell.get('ref')}"
                if runes and type(runes) == int:
                    description_ua += f'\nspell#{runes}'
                if runes and type(runes) == list:
                    for rune in runes:
                        description_ua += f'\nspell#{rune}'
            else:
                name_ua = decoded_spell[0]
                description_ua = decoded_spell[1]
                aura_ua = decoded_spell[2] if len(decoded_spell) > 2 else None
            if description_ua:
                description_ua = description_ua.replace('\\n','\n')
            if aura_ua:
                aura_ua = aura_ua.replace('\\n','\n')
            spell = SpellData(spell_id, expansion, spell_metadata[spell_id].name, category=category, name_ua=name_ua,
                              description_ua=description_ua, aura_ua=aura_ua)
            all_spells[spell_id] = spell
    return all_spells

def __diff_fields(field1, field2):
    import difflib
    differ = difflib.Differ()
    lines1 = field1.splitlines() if field1 else []
    lines2 = field2.splitlines() if field2 else []
    diff = differ.compare(lines1, lines2)
    return '\n'.join(diff)

def apply_translations_to_data(spell_data: dict[int, SpellData], translations: dict[int, SpellData]):
    for key in spell_data.keys() & translations.keys():
        orig_spell = spell_data[key]
        translation = translations[key]
        if spell_data[key].name != translations[key].name:
            print(f'Warning! Original name for spell#{key} differs:\n{__diff_fields(spell_data[key].name, translations[key].name)}')
        if spell_data[key].description != translations[key].description:
            print(f'Warning! Original description for spell#{key} differs:\n{__diff_fields(spell_data[key].description, translations[key].description)}')
        if spell_data[key].aura_description != translations[key].aura_description:
            print(f'Warning! Original aura for spell#{key} differs:\n{__diff_fields(spell_data[key].aura_description, translations[key].aura_description)}')
        spell_data[key].name_ua = translations[key].name_ua
        spell_data[key].description_ua = translations[key].description_ua
        spell_data[key].aura_ua = translations[key].aura_ua
        spell_data[key].name_ua = translations[key].name_ua
        spell_data[key].category = translations[key].category


def __validate_template(spell_id: int, value: str, translation: str):
    import re
    translation = re.sub('\nspell#\d+', '', translation)
    # translation = re.sub(r'(\[.+?]|\(.+?)', '42', value)
    template_start = translation.find('#')
    if template_start == -1:
        if len(re.findall('{\d+}', translation)) != 0:
            print(f"Warning! Template not described for spell#{spell_id}")
        return
    if len(re.findall('{\d+}', translation[:template_start])) != len(re.findall('{\d+}', translation[template_start + 1:])):
        print(f"Warning! Count of templates doesn't match for spell#{spell_id}")
    templates = translation[template_start + 1:].split('#')
    for template in templates:
        template = template.replace('.', '\\.')
        pattern = re.sub(r'{\d+}', '(\\\\d+|\\\\d+\\.\\\\d+|\[.+?\]|\(.+?\))', template).replace('\\\\', '\\')
        matches = re.findall(pattern, value)
        if len(matches) != 1:
            print(f'Warning! Template failed for spell#{spell_id}')

def __validate_templates(spell: SpellData):
    if spell.name_ua:
        __validate_template(spell.id, spell.name, spell.name_ua)
    if spell.description_ua and not spell.description_ua.startswith('ref='):
        __validate_template(spell.id, spell.description, spell.description_ua)
    if spell.aura_ua:
        __validate_template(spell.id, spell.aura_description, spell.aura_ua)


def __validate_newlines(spell: SpellData):
    import re
    if spell.description_ua and not spell.description_ua.startswith('ref='):
        if f'spell#' in spell.description_ua:
            if len(re.findall("spell#", spell.description_ua)) > 1:
                print(f"Warning! Check spell#{spell.id} manually")
        else:
            if re.findall("\n\n", spell.description) != re.findall("\n\n", spell.description_ua):
                print(f"Warning! Newline count doesn't match for spell#{spell.id} description")
    if spell.aura_ua and spell.aura_description:
        if re.findall("\n\n", spell.aura_ua) != re.findall("\n\n", spell.aura_description):
            print(f"Warning! Newline count doesn't match for spell#{spell.id} aura")


def __validate_existence(spell: SpellData):
    if spell.name_ua or spell.description_ua or spell.aura_ua:
        if spell.name and not spell.name_ua:
            print(f"Warning! There's no translation for spell#{spell.id} name")
        if spell.description and not spell.description_ua:
            print(f"Warning! There's no translation for spell#{spell.id} description")
        if spell.aura_description and not spell.aura_ua and not spell.description_ua.startswith("ref="):
            print(f"Warning! There's no translation for spell#{spell.id} aura")

def validate_translations(spells: dict[int, SpellData]):
    for spell in spells.values():
        __validate_templates(spell)
        __validate_newlines(spell)
        __validate_existence(spell)
    # check templates
    ## warning - No templates for raw values
    # check references


def compare_tsv_and_classicua(tsv_translations, classicua_translations):
    for key in tsv_translations.keys() ^ classicua_translations.keys():
        print(f"Warning! Spell#{key} doesn't exist in one of translations")
    for key in tsv_translations.keys() & classicua_translations.keys():
        tsv_translation = tsv_translations[key]
        classicua_translation = classicua_translations[key]
        if tsv_translation.name_ua != classicua_translation.name_ua:
            print(f'Warning! Name translation differs for spell#{key}:\n{__diff_fields(tsv_translation.name_ua, classicua_translation.name_ua)}')
        if tsv_translation.description_ua != classicua_translation.description_ua:
            print(f'Warning! Description translation differs for spell#{key}:\n{__diff_fields(tsv_translation.description_ua, classicua_translation.description_ua)}')
        if tsv_translation.aura_ua != classicua_translation.aura_ua:
            print(f'Warning! Aura translation differs for spell#{key}:\n{__diff_fields(tsv_translation.aura_ua, classicua_translation.aura_ua)}')


if __name__ == '__main__':
    parsed_metadata, parsed_spells = retrieve_spell_data()
    # spell = parse_wowhead_spell_page(SOD, 425463)

    tsv_translations = read_translations_tsv()
    classicua_translations = read_classicua_translations('input\\entries', parsed_metadata)

    apply_translations_to_data(parsed_spells, tsv_translations)

    save_spells_to_db(parsed_spells)

    compare_tsv_and_classicua(tsv_translations, classicua_translations)
    validate_translations(parsed_spells)

    convert_translations_to_entries(tsv_translations)
