import json
import os
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup, CData

THREADS = os.cpu_count()
CLASSIC = 'classic'
SOD = 'sod'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
MOP = 'mop'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
SPELL_CACHE = 'item_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'
CALCULATE = 'calculate'
PARENT_EXPANSIONS = 'parent_expansions'

expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_spell_html',
        SPELL_CACHE: 'wowhead_classic_spell_cache',
        METADATA_FILTERS: ('21:', '5:', '11500:'),
        CALCULATE: True,
        PARENT_EXPANSIONS: [],
        IGNORES: []
    },
    SOD: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_spell_html',
        SPELL_CACHE: 'wowhead_sod_spell_cache',
        METADATA_FILTERS: ('21:', '2:', '11500:'),
        CALCULATE: True,
        PARENT_EXPANSIONS: [CLASSIC],
        IGNORES: [401488, 401489, 401495, # Cutty
                  435445, 436419, 436425, 436563, 437666, 441532, 441540, 444651, 444652, 444890, 444891, 446096, 446120, 446150, 446160, 447947, 449008, 449010, # DNT
                  424684, 425151, 427780, 427781, 429336, 429337, 429338, 429355, 435884, 436529, 436895, 440247, 440856, 442543, 444651, 444652, 444890, 444891, 446096, 446120, 446160, 446374, 446847, 427123, 429432, 429436, 434435, 434436, 434698, # S03
                  398608, 398609, 399699, 423434, 423435, 428996, 428998, 429953, 431996, 443758, 445461, 445462, 445463, 426192, 436508, 436513, 436514, 436515, 436538, #TEST
                  ]
    },
    TBC: {
        INDEX: 1,
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_spell_html',
        SPELL_CACHE: 'wowhead_tbc_spell_cache',
        METADATA_FILTERS: ('', '', ''),
        PARENT_EXPANSIONS: [CLASSIC],
        CALCULATE: True,
        IGNORES: []
    },
    WRATH: {
        INDEX: 2,
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_spell_html',
        SPELL_CACHE: 'wowhead_wrath_spell_cache',
        METADATA_FILTERS: ('', '', ''),
        PARENT_EXPANSIONS: [CLASSIC, TBC],
        CALCULATE: True,
        IGNORES: []
    },
    CATA: {
        INDEX: 3,
        WOWHEAD_URL: 'https://www.wowhead.com/cata',
        METADATA_CACHE: 'wowhead_cata_metadata_cache',
        HTML_CACHE: 'wowhead_cata_spell_html',
        SPELL_CACHE: 'wowhead_cata_spell_cache',
        METADATA_FILTERS: ('', '', ''),
        PARENT_EXPANSIONS: [CLASSIC, TBC, WRATH],
        CALCULATE: True,
        IGNORES: []
    },
    MOP: {
        INDEX: 4,
        WOWHEAD_URL: 'https://www.wowhead.com/mop-classic',
        METADATA_CACHE: 'wowhead_mop_metadata_cache',
        HTML_CACHE: 'wowhead_mop_spell_html',
        SPELL_CACHE: 'wowhead_mop_spell_cache',
        METADATA_FILTERS: ('', '', ''),
        PARENT_EXPANSIONS: [CLASSIC, TBC, WRATH, CATA],
        CALCULATE: True,
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
        32: 'deathknight',
        64: 'shaman',
        128: 'mage',
        256: 'warlock',
        512: 'monk',
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
    def __init__(self, id, expansion, name, description=None, aura=None, name_ua=None,
                 description_ua=None, aura_ua=None, spell_md: SpellMD = None, category=None, group: str = None, rank=None,
                 ref: int = None, name_ref: int = None, description_ref: int = None, aura_ref: int = None):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.description = description
        self.aura = aura
        self.name_ua = name_ua
        self.description_ua = description_ua
        self.aura_ua = aura_ua
        self.ref = ref
        self.name_ref = name_ref
        self.description_ref = description_ref
        self.aura_ref = aura_ref
        self.spell_md = spell_md
        self.category = category
        self.group = group
        self.rank = rank

    def is_translated(self) -> bool:
        if self.name_ua or self.description_ua or self.aura_ua or self.ref:
            return True
        return False

    def is_equal_ignoring_values_to(self, __other):
        from generation.utils.utils import are_texts_equal_ignoring_values
        return are_texts_equal_ignoring_values(self.description, __other.description) and are_texts_equal_ignoring_values(self.aura, __other.aura)
        pass


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
                     .replace('popularity:', '"popularity":')
                     .replace('frommerge:', '"frommerge":'))
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


def get_wowhead_spell_metadata(expansion) -> dict[int, SpellMD]:
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


def save_page_raw(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/spell={id}'
    xml_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}_raw/{id}.html'
    if os.path.exists(xml_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    r = requests.get(url)
    if not r.ok:
        # raise Exception(f'Wowhead({expansion}) returned {r.status_code} for spell #{id}')
        print(f'Error! Wowhead({expansion}) returned {r.status_code} for spell #{id}:{expansion}')
    else:
        with open(xml_file_path, 'w', encoding="utf-8") as output_file:
            output_file.write(r.text)


def save_page_calc(expansion, id):
    import time
    from requests_html import HTMLSession
    try:
        session = HTMLSession()
        url = expansion_data[expansion][WOWHEAD_URL] + f'/spell={id}/'
        xml_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}_rendered/{id}.html'
        if os.path.exists(xml_file_path):
            print(f'Warning! Trying to download existing HTML for #{id}')
            # return
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'}
        r = session.get(url, headers=headers)
        if not r.ok:
            # raise Exception(f'Wowhead({expansion}) returned {r.status_code} for spell #{id}')
            print(f'Error! Wowhead({expansion}) returned {r.status_code} for spell #{id}')
        r.html.render()
        result = r.html.html
        session.close()
        with open(xml_file_path, 'w', encoding="utf-8") as output_file:
            output_file.write(result)
    except Exception as e:
        print(f'Error! Got exception({e}) for spell #{id}:{expansion}. Retrying...')
        time.sleep(5)
        save_page_calc(expansion, id)


def save_pages_async(expansion, ids):
    from requests_html import AsyncHTMLSession
    asession = AsyncHTMLSession(workers=4)
    urls = list([expansion_data[expansion][WOWHEAD_URL] + f'/spell={id}' for id in ids])

    async def fetch(url):
        r = await asession.get(url)
        await r.html.arender()
        return r

    all_responses = asession.run(*[lambda url=url: fetch(url) for url in urls])

    for response in all_responses:
        spell_id = response.html.base_url[response.html.base_url.find('spell=')+6:-1]
        xml_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{spell_id}.html'
        with open(xml_file_path, 'w', encoding="utf-8") as output_file:
            output_file.write(response.html.html)


def save_htmls_from_wowhead(expansion, ids: set[int], render: bool, force: set[int] = None):
    from functools import partial
    import multiprocessing
    html_type = 'rendered' if render else 'raw'
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}_{html_type}'
    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids and not force:
        print(f'HTML({html_type}) cache for all Wowhead({expansion}) spells ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    if force:
        print(f'Force saving HTMLs({html_type}) for {len(force)} spells from Wowhead({expansion}): {force}.')
        save_ids = save_ids | force
    print(f'Saving HTMLs({html_type}) for {len(save_ids)} of {len(ids)} spells from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    save_page_func = save_page_calc if render else save_page_raw
    threads = THREADS // 2 if render else THREADS * 2
    # for id in save_ids:
    #     save_page_func(expansion, id)
    save_func = partial(save_page_func, expansion)
    with multiprocessing.Pool(threads) as p:
        p.map(save_func, save_ids)
    # save_pages_async(expansion, list(save_ids)[:100])


def parse_wowhead_spell_page(expansion, render, id) -> SpellData:
    import re
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}_{'rendered' if render else 'raw'}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()

    soup = BeautifulSoup(html, 'html.parser')
    name = soup.find('h1').text

    tooltip_div = soup.find('div', {'id': f'tt{id}'})
    if tooltip_div is None:
        print(f'Error! No tooltip div for {id}:{expansion}. Title: {name}')
        return None
    tooltip_div = tooltip_div.find('div', {'class': 'q'})
    if tooltip_div is None:
        tooltip_div = soup.find('div', {'id': f'tt{id}'}).parent.find('div', {'class': 'q'})

    description = None
    if tooltip_div:
        for hidden_span in tooltip_div.find_all('span', {'class': 'wh-tooltip-formula', 'style': 'display:none'}):
            # hidden_span.replace_with('')
            hidden_span.decompose()
        for br in tooltip_div.find_all('br'):
            br.replace_with('\n')
        # for a_tag in tooltip_div.find_all('a'):  # Optional thing
        #     a_tag.replace_with(a_tag.get('href'))

        description = tooltip_div.text
        description = re.sub(r'\n\n+', '\n\n', description).replace(u'\xa0', ' ')
        # description = re.sub(r' +', ' ', description)

    aura = None
    # aura_div = soup.find('div', {'id': f'btt{id}'})
    aura_div = soup.find('div', {'id': f'btt{id}'}).parent.find_all('td')
    aura_div = aura_div[-1] if aura_div else None
    if aura_div:
        for hidden_span in aura_div.find_all('span', {'class': 'wh-tooltip-formula', 'style': 'display:none'}):
            # hidden_span.replace_with('')
            hidden_span.decompose()
        # aura_div = aura_div.find_all('td')[-1]
        if aura_div.text.strip() != str(id):
            for yellow_text in aura_div.find_all('span', {'class': 'q'}):
                yellow_text.replace_with('\n')
            for br in aura_div.find_all('br'):
                br.replace_with('\n')
            aura = "\n".join(map(lambda line: line.strip(), aura_div.text.splitlines())).strip().replace(u'\xa0', ' ')
            # aura = re.sub(r' +', ' ', aura)

    return SpellData(id, expansion, name, description, aura)


def parse_wowhead_pages(expansion, metadata: dict[int, SpellMD], render: bool) -> dict[int, SpellData]:
    import pickle
    import multiprocessing
    from functools import partial
    spells_type = 'rendered' if render else 'raw'
    cache_path = f'cache/tmp/{expansion_data[expansion][SPELL_CACHE]}_{spells_type}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) spells')
        with open(cache_path, 'rb') as f:
            wowhead_spells = pickle.load(f)
    else:
        print(f'Parsing {spells_type} Wowhead({expansion}) spell pages')
        # wowhead_spells = {id: parse_wowhead_spell_page(expansion, render, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_spell_page, expansion, render)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_spells = p.map(parse_func, metadata.keys())
        wowhead_spells = {spell.id: spell for spell in wowhead_spells}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_spells, f)

    for spell_id in metadata.keys() & wowhead_spells.keys():
        wowhead_spells[spell_id].spell_md = metadata[spell_id]

    return wowhead_spells


def save_spells_to_db(spells: dict[int, dict[str, SpellData]]):
    import sqlite3
    print('Saving spells to DB')
    conn = sqlite3.connect('cache/spells.db')
    conn.execute('DROP TABLE IF EXISTS spells')
    conn.execute('''CREATE TABLE spells (
                        id INT NOT NULL,
                        expansion TEXT NOT NULL,
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
                        ref INT,
                        name_ref INT,
                        desc_ref INT,
                        aura_ref INT
                )''')
    conn.commit()
    with (conn):
        for key in spells.keys():
            for expansion, spell in spells[key].items():
                if ('[DNT]' in spell.name.upper() or
                        'DND' in spell.name or
                        '(DND)' in spell.name.upper() or
                        '(DNT)' in spell.name.upper() or
                        '[DNT]' in spell.name.upper() or
                        '(OLD)' in spell.name.upper() or
                        '(TEST)' in spell.name.upper() or
                        'TEST' in spell.name or
                        '(NYI)' in spell.name.upper() or
                        '(DNC)' in spell.name.upper() or
                        '(PT)' in spell.name.upper() or
                        '[PH]' in spell.name.upper() or
                        spell.name.startswith('QA') or
                        key in expansion_data[spell.expansion][IGNORES]):
                    continue
                md_skill = str(spell.spell_md.skill) if spell.spell_md.skill else None
                conn.execute(
                    'INSERT INTO spells(id, expansion, name, name_ua, description, description_ua, aura, aura_ua, rank, cat, level, schools, class, skill, ref, name_ref, desc_ref, aura_ref) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (spell.id, spell.expansion, spell.name, spell.name_ua, spell.description, spell.description_ua,
                     spell.aura, spell.aura_ua,
                     spell.spell_md.rank, spell.spell_md.cat, spell.spell_md.level, spell.spell_md.schools,
                     spell.spell_md.get_class(), md_skill,
                     spell.ref, spell.name_ref, spell.description_ref, spell.aura_ref))


def load_spells_from_db(db_path = 'cache/spells.db') -> dict[int, dict[str, SpellData]]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    spells: dict[int, dict[str, SpellData]] = dict()
    with (conn):
        cursor = conn.cursor()
        sql = f'SELECT * FROM spells'
        res = cursor.execute(sql)
        spell_rows = res.fetchall()
        for row in spell_rows:
            spell_id = row[0]
            expansion = row[1]
            name = row[2]
            name_ua = row[3]
            description = row[4]
            description_ua = row[5]
            aura = row[6]
            aura_ua = row[7]
            ref = row[14]
            spell = SpellData(spell_id, expansion, name, description, aura, name_ua=name_ua, description_ua=description_ua, aura_ua=aura_ua, ref=ref)
            spells[spell_id] = spells.get(spell_id, dict())
            spells[spell_id][expansion] = spell

    return spells

def is_spell_translated(spells: dict[str, SpellData]) -> list[str]:
    if not spells:
        return []
    translated_expansions = list()
    for expansion, spell in spells.items():
        if spell.name_ua or spell.description_ua or spell.aura_ua or spell.ref:
            translated_expansions.append(expansion)
    return translated_expansions


def populate_similarity(spells: dict[int, dict[str, SpellData]]):
    import re
    name_to_spells: dict[str, dict[str, int]] = dict()
    description_to_spells: dict[str, dict[str, int]] = dict()
    aura_to_spells: dict[str, dict[str, int]] = dict()
    for expansion in expansion_data.keys():
        for key in [key for key in sorted(spells.keys()) if expansion in spells[key].keys()]:
            spell = spells[key][expansion]
            description = re.sub(r'\d+(\.\d+)?', '{d}', spell.description) if spell.description else None
            aura = re.sub(r'\d+(\.\d+)?', '{d}', spell.aura) if spell.aura else None

            if spell.name in name_to_spells.keys():
                common_parent_expansions = name_to_spells[spell.name].keys() & set(expansion_data[expansion][PARENT_EXPANSIONS] + [expansion])
                if len(common_parent_expansions) == 1:
                    common_parent = next(iter(common_parent_expansions))
                    spell.name_ref = name_to_spells[spell.name][common_parent]
                elif len(common_parent_expansions) == 0:
                    if name_to_spells[spell.name].keys() != {'sod'}:
                        print(f"Warning. Suspicious name parent situation for {key}:{expansion}.")
                    name_to_spells[spell.name][expansion] = key
                else:
                    print(f"Warning! Strange name parent situation for {key}:{expansion}!")
            else:
                name_to_spells[spell.name] = {expansion: key}

            if description and description in description_to_spells.keys():
                common_parent_expansions = description_to_spells[description].keys() & set(expansion_data[expansion][PARENT_EXPANSIONS] + [expansion])
                if len(common_parent_expansions) == 1:
                    common_parent = next(iter(common_parent_expansions))
                    spell.description_ref = description_to_spells[description][common_parent]
                elif len(common_parent_expansions) == 0:
                    if description_to_spells[description].keys() != {'sod'}:
                        print(f"Warning. Suspicious description parent situation for {key}:{expansion}.")
                    description_to_spells[description][expansion] = key
                else:
                    print(f"Warning! Strange description parent situation for {key}:{expansion}!")
            else:
                description_to_spells[description] = {expansion: key}

            if aura and aura in aura_to_spells.keys():
                common_parent_expansions = aura_to_spells[aura].keys() & set(expansion_data[expansion][PARENT_EXPANSIONS] + [expansion])
                if len(common_parent_expansions) == 1:
                    common_parent = next(iter(common_parent_expansions))
                    spell.aura_ref = aura_to_spells[aura][common_parent]
                elif len(common_parent_expansions) == 0:
                    if aura_to_spells[aura].keys() != {'sod'}:
                        print(f"Warning. Suspicious aura parent situation for {key}:{expansion}.")
                    aura_to_spells[aura][expansion] = key
                else:
                    print(f"Warning! Strange aura parent situation for {key}:{expansion}!")
            else:
                aura_to_spells[aura] = {expansion: key}



def __to_tsv_val(value) -> str:
    if value:
        return '"' + str(value).replace('"', '""') + '"'
    else:
        return ''

def create_translation_sheet(spells: dict[int, dict[str, SpellData]], feedback_ids: list[int]):
    with (open(f'translate_this.tsv', mode='w', encoding='utf-8') as f):
        f.write('ID\tName(EN)\tName(UA)\tDescription(EN)\tDescription(UA)\tAura(EN)\tAura(UA)\tref\tname_ref\tdesc_ref\taura_ref\texpansion\tcategory\tgroup\n')
        count = 0
        for key in sorted(spells.keys()):
            # for expansion, spell in list(spells[key].items())[-1:]:
            for spell in sorted(set([list(spells[key].values())[0], list(spells[key].values())[-1]]), key=lambda x: expansion_data[x.expansion][INDEX]):
                if ('[DNT]' in spell.name.upper() or
                        'DND' in spell.name or
                        '(DND)' in spell.name.upper() or
                        '(DNT)' in spell.name.upper() or
                        '[DNT]' in spell.name.upper() or
                        '(OLD)' in spell.name.upper() or
                        '(TEST)' in spell.name.upper() or
                        'TEST' in spell.name or
                        '(NYI)' in spell.name.upper() or
                        '(DNC)' in spell.name.upper() or
                        '(PT)' in spell.name.upper() or
                        '[PH]' in spell.name.upper() or
                        spell.name.startswith('QA') or
                        key in expansion_data[spell.expansion][IGNORES]):
                    continue
                # if getattr(spell.spell_md, 'chrclass') in SpellMD._classes.keys() and spell.expansion == SOD and spell.name_ua is None and spell.description_ua is None and spell.aura_ua is None and spell.ref is None:

                ## Feedback translations:
                # feedback_ids = [468275, 1221337, 1225769, 1225771, 1225772, 1225906, 1225907, 1225960, 1225987, 1226007, 1226396, 1226800, 1226810, 1227369, 1229305, 1229308, 1229340, 1230942, 1230944, 1230980, 1231091, 1231254, 1231258, 1231267, 1231289, 1231330, 1231382, 1231402, 1231417, 1231547, 1231548, 1231550, 1231551, 1231553, 1231554, 1231578, 1231586, 1231604, 1231605, 1231612, 1231620, 1231624, 1231656, 1231681, 1231694, 1231698, 1231874, 1231904, 1232044, 1232057, 1232066, 1232103, 1232150, 1232153, 1232157, 1232158, 1232162, 1232167, 1232181, 1232312, 1232322, 1232477, 1232479, 1232896, 1232946, 1234033, 1234040, 1234085, 1234299, 1234326, 1234792, 1234805, 1235011, 1235320, 1235351, 1235681, 1237064]
                # if spell.expansion in [CLASSIC, SOD] and (spell.description is not None or spell.aura is not None) and spell.name_ua is None and spell.description_ua is None and spell.aura_ua is None and spell.ref is None and spell.spell_md.cat in (9, 11) and spell.id in feedback_ids: # Review manually. Skip recipes (for now, me may want to translate trainer interface)
                if spell.expansion in [CLASSIC, SOD] and spell.name_ua is None and spell.description_ua is None and spell.aura_ua is None and spell.ref is None and spell.spell_md.cat in (7, 5, 0, -2, -3, -4, -8, -11, -13, -25, -26) and spell.id in feedback_ids:
                # if spell.expansion in [CLASSIC, SOD] and spell.name_ua is None and spell.description_ua is None and spell.aura_ua is None and spell.ref is None and spell.id in feedback_ids: # Massive

                ## Autotranslation:
                # if spell.expansion in [CLASSIC, SOD] and spell.name_ua is None and spell.description_ua is None and spell.aura_ua is None and spell.ref is None and (
                #         (spell.spell_md.cat in (7,) and not spell.name.startswith('S03 -')) or
                #         (spell.spell_md.cat in (-5, -6)) or  # mount/pet journal. nice to have. Translate only if we can display translation. wrath+
                #         (spell.spell_md.cat in (0, -8, -26) and spell.aura is not None) or  # Enable when translating everything
                #         (spell.spell_md.cat in (-11,) and not spell.name.startswith('Language ')) or
                #         (spell.spell_md.cat in (-13,)) or  # Glyphs. Translate only when we can display translation. wrath+ (TODO)
                #         (spell.spell_md.cat in (5, -2, -3, -4))):

                ## For missing referenced spells
                # force_translate = (1220635, 1220642, 1220645, 1220650, 1220651, 1220653, 1220654, 1220655, 1220656, 1220657, 1220666, 1220668, 1220700, 1220702, 1220707, 1220708, 1220711, 28800, 1220738, 1220741, 1220756, 1220770, 1222974, 1222994, 1223010, 1220980, 1219019, 1219043, 1219083, 1223262, 1223341, 1223348, 1223349, 1223350, 1223351, 1223352, 1223353, 1223354, 1223355, 1223357, 1223367, 1223368, 1223370, 1223371, 1223372, 1223373, 1223374, 1223375, 1223376, 1223379, 1223380, 1223381, 1223382, 1223383, 1223384, 1223385, 1223386, 1223387, 1223455, 1219415, 1219500, 1219501, 1219503, 1219506, 1219507, 1219510, 1219511, 1219512, 1219513, 1219515, 1219519, 1219520, 1219521, 1219522, 1219539, 1219548, 1219552, 1219553, 1219557, 1219558, 1223689, 1223795, 1219740, 1219742, 1219743, 1219745, 1219747, 1219748, 1219749, 1219751, 1219752, 1219753, 1219754, 1219755, 1219756, 1219757, 1219758, 1219760, 1219762, 1219763, 1219764, 1219766, 1219767, 1219768, 1219769, 1219770, 1219771, 1219772, 1219773, 1219774, 1219775, 1219776, 1219777, 1219778, 1219779, 1219780, 1219781, 1219782, 1219783, 1219784, 1219785, 1219786, 1219787, 1219788, 1219789, 1219790, 1219791, 1219792, 1219793, 1219794, 1219795, 1219796, 1219797, 1219798, 1219799, 1219800, 1219801, 1219802, 1219803, 1219804, 1219805, 1219806, 1219807, 1219808, 1219809, 1219810, 1219811, 1219812, 1219813, 1219815, 1219816, 1219818, 1219819, 1219820, 1219821, 1219822, 1219823, 1219824, 1219825, 1219826, 1219827, 1219828, 1219829, 1219830, 1219831, 1219832, 1219833, 1219834, 1219835, 1219836, 1219837, 1219838, 1219839, 1219840, 1219841, 1219842, 1219843, 1219844, 1219845, 1219846, 1219847, 1219848, 1219849, 1219850, 1219851, 1219852, 1219853, 1219854, 1219855, 1219856, 1219857, 1219858, 1219859, 1219860, 1219861, 1219862, 1219863, 1219864, 1219865, 1219866, 1219867, 1219868, 1219869, 1219870, 1219871, 1219872, 1219873, 1219874, 1219875, 1219876, 1219877, 1219878, 1219879, 1219880, 1219881, 1219882, 1219883, 1219884, 1219885, 1219886, 1219887, 1219888, 1219889, 1219890, 1219891, 1219892, 1219893, 1219894, 1219895, 1219896, 1219897, 1219898, 1219899, 1219900, 1219901, 1219902, 1219903, 1219904, 1219905, 1219906, 1219907, 1219908, 1219909, 1219910, 1219911, 1219912, 1219913, 1219914, 1219915, 1219916, 1219917, 1219918, 1219919, 1219920, 1219921, 1219922, 1219923, 1219924, 1219925, 1219926, 1219927, 1219928, 1219929, 1219930, 1219931, 1219932, 1219933, 1219934, 1219935, 1219936, 1219937, 1219938, 1219939, 1219940, 1219941, 1219942, 1219943, 1219944, 1219945, 1219946, 1219947, 1219948, 1219949, 1219950, 1219951, 1219952, 1219953, 1219954, 28148, 1213971, 28282, 1222393, 1222394, 1218367, 1220418, 1220514, 1220521, 1214381, 1220533, 1220536, 1220538, 1220540, 1214407, 1214409, 1220560, 1220561, 1220563, 1220564, 1220565, 1220566, 1220567, 1220568)
                # if spell.expansion in [CLASSIC, SOD] and spell.name_ua is None and spell.description_ua is None and spell.aura_ua is None and spell.ref is None and spell.id in force_translate:

                # if True:
                    class_name = SpellMD._classes[getattr(spell.spell_md, 'chrclass')] if getattr(spell.spell_md, 'chrclass') in SpellMD._classes else ''
                    spell_description = spell.description
                    if spell_description and spell_description.startswith('+'):  # In case of '+123 Attack Power' etc
                        spell_description = "'" + spell_description
                    fields = [spell.id, spell.name, spell.name_ua, spell_description, spell.description_ua, spell.aura, spell.aura_ua, spell.ref, spell.name_ref, spell.description_ref, spell.aura_ref, spell.expansion, class_name, spell.group]
                    f.write(f'{'\t'.join(map(lambda x: __to_tsv_val(x), fields))}\n')
                    count += 1
        if count > 0:
            print(f"Added {count} spells for translation")

def merge_spell(id: int, old_spells: dict[str, SpellData], new_spell: SpellData) -> dict[str, SpellData]:
    import re
    if len(old_spells) > 1:
        last_old_spell_key = list(old_spells.keys())[-1]
        result = merge_spell(id, {last_old_spell_key: old_spells[last_old_spell_key]}, new_spell)
        del old_spells[last_old_spell_key]
        return {**old_spells, **result}
    if len(old_spells) == 1:
        old_spell = next(iter(old_spells.values()))

        if old_spell.name != new_spell.name or not old_spell.is_equal_ignoring_values_to(new_spell):
            return {**old_spells, **{new_spell.expansion: new_spell}}
        else:
            return old_spells
    else:
        print(f'Skip: Spell #{id} instance number unexpected')


def merge_expansions(old_expansion: dict[int, dict[str, SpellData]], new_expansion: dict[int, SpellData]) -> dict[int, dict[str, SpellData]]:
    result = dict()

    for id in old_expansion.keys() - new_expansion.keys():
        result[id] = old_expansion[id]

    for id in new_expansion.keys() - old_expansion.keys():
        result[id] = dict()
        result[id][new_expansion[id].expansion] = new_expansion[id]

    for id in old_expansion.keys() & new_expansion.keys():
        result[id] = merge_spell(id, old_expansion[id], new_expansion[id])
    return result


def compare_stored_raw_spells(expansion, fresh_spells: dict[int, SpellData]) -> set[int]:
    import pickle
    diffed_spells = set()
    print(f'Comparing raw spells for {expansion}')
    cache_path = f'cache/tmp/wowhead_{expansion}_spell_cache_raw_stored.pkl'
    if os.path.exists(cache_path):
        print(f'Loading stored raw Wowhead({expansion}) spells')
        with open(cache_path, 'rb') as f:
            stored_spells = pickle.load(f)
        absent_keys = stored_spells.keys() ^ fresh_spells.keys()
        if absent_keys:
            print(f'These keys absent in one of sets: {absent_keys}')
        for spell_id in stored_spells.keys() & fresh_spells.keys():
            if (stored_spells[spell_id].name != fresh_spells[spell_id].name or
                    stored_spells[spell_id].description != fresh_spells[spell_id].description or
                    stored_spells[spell_id].aura != fresh_spells[spell_id].aura):
                diffed_spells.add(spell_id)
    return diffed_spells


def store_raw_spells(expansion, fresh_spells: dict[int, SpellData]):
    import pickle
    cache_path = f'cache/tmp/wowhead_{expansion}_spell_cache_raw_stored.pkl'
    os.makedirs('cache/tmp', exist_ok=True)
    with open(cache_path, 'wb') as f:
        pickle.dump(fresh_spells, f)


def retrieve_spell_data() -> dict[int, dict[str, SpellData]]:
    all_spells = dict()
    for expansion, expansion_properties in expansion_data.items():
        wowhead_md = get_wowhead_spell_metadata(expansion)

        save_htmls_from_wowhead(expansion, set(wowhead_md.keys()), render=False)
        wowhead_spells_raw = parse_wowhead_pages(expansion, wowhead_md, render=False) # First, store raw spells (delete 'wowhead_<expansion>_spell_html.raw' to do that)

        changed_spells = compare_stored_raw_spells(expansion, wowhead_spells_raw) # Then, compare downloaded raw pages with stored in 'tmp/wowhead_<expansion>_spell_cache_raw_stored'
        save_htmls_from_wowhead(expansion, set(wowhead_md.keys()), render=True, force=changed_spells) # Download absent rendered pages and force-download changed pages from 'changed_spells'
        wowhead_spells_rendered = parse_wowhead_pages(expansion, wowhead_md, render=True)

        store_raw_spells(expansion, wowhead_spells_raw) # Store current raw pages as 'tmp/wowhead_<expansion>_spell_cache_raw_stored'

        print(f'Merging with {expansion}')
        all_spells = merge_expansions(all_spells, wowhead_spells_rendered)

    return all_spells


def __spell_guide_header() -> str:
    import textwrap
    # TODO: Expertise - TBD
    return textwrap.dedent("""\
        --[[
        
        ## Термінологія для опису заклять в spell*.lua та ефектів у item*.lua
        
        Balance spells                      -- закляття спеціалізації "Баланс"
        Affliction spells                   -- закляття спеціалізації "Химородь"
        Destruction spells                  -- закляття спеціалізації "Руйнація"
        
        X Physical damage                   -- X фізичної шкоди
        X Arcane damage                     -- X шкоди арканою
        X Fire damage                       -- X шкоди вогнем
        X Frost damage                      -- X шкоди кригою
        X Nature damage                     -- X шкоди природою
        X Shadow damage                     -- X шкоди тінню
        X Holy damage                       -- X шкоди святістю
        X weapon damage                     -- X шкоди зброєю
        initial damage                      -- первинна шкода
        main hand / off-hand                -- основна рука / неосновна рука
        parry chance                        -- імовірність парирування
        dodge chance                        -- імовірність ухилення
        hit chance                          -- імовірність завдання удару
        dual wield                          -- бій з двох рук
        
        all attributes                      -- всі характеристики
        Intelligence                        -- інтелект
        Strength                            -- сила
        Agility                             -- спритність
        Stamina                             -- витривалість
        Spirit                              -- дух
        Mastery                             -- майстерність
        Expertise                           -- вправність
        Frenzy effect                       -- ефект навіженості
        Disease effect                      -- ефект хвороби
        Poison effect                       -- ефект отрути
        Curse effect                        -- ефект прокляття
        spell / ability                     -- закляття / здібність (синоніми, залежить від контексту)
        cooldown                            -- відновлення
        instance                            -- ігровимір
        to purge                            -- очистити / вичистити / чистити
        to dispel                           -- розсіяти
        resistance                          -- опір (вогню, кризі, ...)
        harmful spell                       -- шкідливе закляття
        beneficial spell                    -- сприятливе закляття
        offensive spells                    -- бойові закляття
        defensive spells                    -- захисні закляття
        stealth detection                   -- здатність виявлення непомітності
        Target cannot stealth or turn invisible -- Ціль не може стати непомітною чи невидимою
        This effect stack up to X times     -- Ефект накопичується до {X} разів
        Causes a high amount of threat      -- Спричиняє високий рівень загрози
        Movement Impairing effects          -- ефекти обмеження руху
        Only usable outdoors                -- Можна використовувати лише просто неба
        Only usable out of combat           -- Можна використовувати лише поза боєм
        must channel to maintain the spell  -- потрібно підтримувати закляття
        yields experience or honor          -- приносить досвід або честь
        to silence the target               -- знемовити ціль
        fully resisted spell                -- повністю протидіяти закляттю
        life drained / mana drained         -- (обсяг) випитого життя / випитої мани / висушувати
        which serves as a mount             -- для верхової їзди / на якому можна їздити верхи (якщо опис дозволяє)
        happiness                           -- щасливість (показник у вихованців мисливців)
        mount                               -- транспорт (при можливості уникати прямого слова, якщо контекст дозволяє)
        pet                                 -- вихованець (у мисливців) / прислужник (у чорнокнижників)
        
        Dazed                               -- Запаморочення
        Asleep                              -- Сон
        Feared                              -- Налякано
        Rooted                              -- Приковано
        Frozen                              -- Заморожено
        Chilled                             -- Охолоджено
        Charmed                             -- Причаровано
        Stunned                             -- Приголомшено
        Taunted                             -- Спровоковано
        Enraged                             -- Розлючено
        Silenced                            -- Знемовлено
        Disarmed                            -- Роззброєно
        Enslaved                            -- Поневолено
        Horrified                           -- Нажахано
        Invisible                           -- Невидимість
        Stealthed                           -- Непомітність
        Disoriented                         -- Дезорієнтовано
        Immobilized / Immobile              -- Знерухомлено / Нерухомість
        Invulnerable                        -- Невразливість
        Incapacitated                       -- Недієздатність
        
        Fear and Horror effects                     -- ефекти страху та жаху
        Increases your Defense skill by X           -- Збільшує вашу навичку захисту на X
        Awards 1 combo point                        -- Збільшує довжину комбінації на X прийом
        Target must be facing you                   -- Ціль має бути повернута до вас
        Must be behind the target                   -- Необхідно бути позаду цілі
        Must be stealthed                           -- Необхідно бути непомітним
        Does not break stealth                      -- Не порушує непомітності
        More effective than XXXXX (Rank X)          -- Дієвіше за "XXXXX" (Ранг X)
        Requires a dagger in the main hand          -- Працює лише за наявності кинджалу в основній руці
        Any damage caused will revive the target    -- Будь-яка шкода знімає ефект з ураженої цілі
        Any damage caused will awaken the target    -- Будь-яка шкода пробудить ціль
        Any damage caused will remove the effect    -- Будь-яка шкода скасує ефект
        Stacks up to X times on a single target     -- Накопичується до X разів на одній цілі
        Turns off your attack when used             -- Припиняє вашу атаку при використанні
        Finishing move                              -- Завершальний рух
        each tick                                   -- на кожному такті
        1 charge                                    -- 1 заряд
        
        interrupts spellcasting and prevents any spell in that school from being cast for X sec
        -- перериває вимову закляття та унеможливлює вимову заклять тієї ж школи протягом X с
        
        chance to resist interruption caused by damage while casting
        -- імовірність уникнути затримки вимови заклять, спричиненої шкодою
        
        chance to resist interruption caused by damage while channeling
        -- імовірність уникнути переривання промовляння заклять, спричиненого шкодою
        
        Conjured items disappear if logged out for more than 15 minutes.
        -- Начакловані предмети зникнуть, якщо вийти з гри більше, ніж на 15 хвилин.
        
        Will not work if the target is in another instance or on another continent.
        -- Не працює, якщо ціль перебуває в іншому ігровимірі або на іншому континенті.
        
        Only one form of tracking can be active at a time.
        -- Одночасно можна вистежувати лише щось одне.
        
        ]]--
        
        local _, addonTable = ...
        addonTable.spell = {
        
        -- [id] = {
        --     [ref] = ID (optional),
        --     [1] = title (optional),
        --     [2] = description (optional),
        --     [3] = aura (optional),
        -- }
        
        """)


def __prepare_lua_str(value: str) -> str:
    return value.replace('"', r'\"').replace('\n', r'\n')


def __spell_to_lua_row(spell: SpellData):
    name_text = f'"{__prepare_lua_str(spell.name_ua)}"' if spell.name_ua else 'nil'

    description_text = 'nil'
    rune_refs = []
    if spell.description_ua:
        description_text = []
        for line in spell.description_ua.splitlines():
            if line.startswith('spell#'):
                rune_refs.append(line.split('#')[-1])
            else:
                description_text.append(line)
        description_text = __prepare_lua_str('\n'.join(description_text))
        description_text = f'"{description_text}"'

    aura_text = __prepare_lua_str(spell.aura_ua) if spell.aura_ua else None
    aura_text = f'"{aura_text}"' if aura_text else 'nil'

    rune_text = None
    if rune_refs:  # We take only first rune_ref. Take whole list if we can handle templates
        rune_text = rune_refs[0] if len(rune_refs) == 1 else '{' + ', '.join(rune_refs) + '}'

    translations = [name_text, description_text, aura_text]

    while True:
        if translations and translations[-1] == 'nil':
            translations = translations[:-1]
        else:
            break

    if rune_text:
        translations.append('rune={}'.format(rune_text))

    if spell.ref:
        translations.append('ref={}'.format(spell.ref))

    original_name = ""
    if spell.name_ua:
        translations.append('en="{}"'.format(__prepare_lua_str(spell.name)))
    else:
        original_name = f' -- {spell.name}'

    return '[{}] = {{ {} }},{}\n'.format(spell.id, ', '.join(translations), original_name)

def convert_translations_to_lua(translations: list[SpellData], category: tuple[str, str]):
    path = f'output/entries/{category[0]}'
    spells_class = f'_{category[1]}' if category[1] else ''
    translations = sorted(translations, key=lambda x: x.name) if spells_class != '' else sorted(translations, key=lambda x: x.id) # sort by spell name for spell{_some-class}, and by spell id for spell.lua
    os.makedirs(path, exist_ok=True)
    is_classic_spells_lua = category[0] == 'classic' and spells_class == ''
    with open(f'{path}/spell{spells_class}.lua', 'w', encoding="utf-8") as output_file:
        if is_classic_spells_lua:
            output_file.write(__spell_guide_header())
        else:
            output_file.write('local _, addonTable = ...\n\n'
                              + 'local {}spells = '.format(f'{category[1]}_' if category[1] else '')
                              + '{\n\n-- See /entries/classic/spell.lua for data format details.\n\n')

        previous_name = None
        for spell in filter(lambda x: x.group is None, translations):
            if spell.id == spell.ref: # Manually set to preserve translation from previous expansion
                continue
            if spells_class != '':  # Spell is in spell_{some_group}.lua
                if spell.name != previous_name:
                    output_file.write(f'-- {spell.name}\n')  # Group
            previous_name = spell.name
            output_file.write(__spell_to_lua_row(spell))

        groups: dict[str, list[SpellData]] = dict()
        grouped_spells = filter(lambda x: x.group is not None, translations)
        for spell in grouped_spells:
            if spell.id == spell.ref:  # Manually set to preserve translation from previous expansion
                continue
            groups[spell.group] = groups.get(spell.group, list())
            groups[spell.group].append(spell)

        for group in sorted(groups.keys()):
            output_file.write(f'\n-- {group}\n')
            for spell in sorted(groups[group], key=lambda x: x.name) if spells_class != '' else sorted(groups[group], key=lambda x: x.id):
                output_file.write(__spell_to_lua_row(spell))

        output_file.write('\n}\n')
        if not is_classic_spells_lua:
            output_file.write('\nfor k, v in pairs({}spells) do addonTable.spell[k] = v end\n'.format(f'{category[1]}_' if category[1] else ''))


def convert_translations_to_entries(translations: dict[int, dict[str, SpellData]]):
    grouped_translations: dict[tuple[str, str], list[SpellData]] = dict()
    for key in translations.keys():
        for translation in translations[key].values():
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


def read_translations_sheet() -> dict[int, dict[str, SpellData]]:
    import csv
    all_translations: dict[int, dict[str, SpellData]] = dict()
    with open('input/translations.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            spell_id = __try_cast_str_to_int(row[0])
            if not spell_id:
                print(f'Skipping: {row}')
                continue
            name_en = row[1] if row[1] != '' else None
            name_ua = row[2] if row[2] != '' else None
            description_en = row[3] if row[3] != '' else None
            description_ua = row[4] if row[4] != '' else None
            aura_en = row[5] if row[5] != '' else None
            aura_ua = row[6] if row[6] != '' else None  # if len(row) >= 8 else None
            ref = __try_cast_str_to_int(row[7], None)
            name_ref = __try_cast_str_to_int(row[8], None)
            desc_ref = __try_cast_str_to_int(row[9], None)
            aura_ref = __try_cast_str_to_int(row[10], None)
            expansion = row[11] if len(row) > 11 and row[11] != '' else None
            category = row[12] if len(row) > 12 and row[12] != '' else None
            group = row[13] if len(row) > 13 and row[13] != '' else None
            all_translations[spell_id] = all_translations.get(spell_id, dict())
            if expansion in all_translations[spell_id]:
                print(f'Warning! Duplicate for {spell_id}:{expansion}')
            all_translations[spell_id][expansion] = SpellData(spell_id, expansion, name=name_en,
                                                              description=description_en, aura=aura_en, name_ua=name_ua,
                                                              description_ua=description_ua, aura_ua=aura_ua, ref=ref,
                                                              name_ref=name_ref, description_ref=desc_ref,
                                                              aura_ref=aura_ref, category=category, group=group)

    return all_translations

def read_classicua_translations(spells_root_path: str, spell_data: dict[int, dict[str, SpellData]]):
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

    all_spells: dict[int, dict[str, SpellData]] = dict()

    for file_path, lua_file in file_contents:
        expansion, file_name = file_path.split('\\')[-2:]
        file_name_split = file_name[:file_name.find('.')].split('_')
        category = file_name_split[1] if len(file_name_split) > 1 else ''
        lua_table = lua_file[lua_file.find(' = {\n') + 2:lua_file.find('\n}\n') + 2]
        decoded_spells = lua.decode(lua_table)
        for spell_id, decoded_spell in decoded_spells.items():
            ref = None
            if spell_id in all_spells and expansion in all_spells[spell_id]:
                print(f'Warning! Duplicate for spell#{spell_id}:{expansion}')
            if type(decoded_spell) == dict:
                name_ua = decoded_spell.get(0)
                description_ua = decoded_spell.get(1)
                aura_ua = decoded_spell.get(2)
                runes = decoded_spell.get('rune')
                ref = decoded_spell.get('ref')
                if runes and type(runes) == int:
                    description_ua += f'\nspell#{runes}'
                if runes and type(runes) == list:
                    for rune in runes:
                        description_ua += f'\nspell#{rune}'
            else:
                name_ua = decoded_spell[0]
                description_ua = decoded_spell[1] if len(decoded_spell) > 1 else None
                aura_ua = decoded_spell[2] if len(decoded_spell) > 2 else None
            if description_ua:
                description_ua = description_ua.replace('\\n','\n')
            if aura_ua:
                aura_ua = aura_ua.replace('\\n', '\n')
            if spell_id in spell_data and expansion in spell_data[spell_id].keys():
                original_name = spell_data[spell_id][expansion].name
            else:
                print(f"Warning! Spell#{spell_id}:{expansion} doesn't exist on Wowhead!")
                original_name = 'UNKNOWN'
            spell = SpellData(spell_id, expansion, original_name, category=category, name_ua=name_ua,
                              description_ua=description_ua, aura_ua=aura_ua, ref=ref)
            all_spells[spell_id] = all_spells.get(spell_id, dict())
            all_spells[spell_id][expansion] = spell
    return all_spells

def __diff_fields(field1, field2):
    import difflib
    differ = difflib.Differ()
    lines1 = field1.splitlines() if field1 else []
    lines2 = field2.splitlines() if field2 else []
    diff = differ.compare(lines1, lines2)
    return '\n'.join(diff)

def apply_translations_to_data(spell_data: dict[int, dict[str, SpellData]], translations: dict[int, dict[str, SpellData]]):
    for key in sorted(spell_data.keys() & translations.keys()):
        for expansion in spell_data[key].keys() & translations[key].keys():
            orig_spell = spell_data[key][expansion]
            translation = translations[key][expansion]
            if orig_spell.name != translation.name:
                print(f'Warning! Original name for spell#{key}:{expansion} differs:\n{__diff_fields(translation.name, orig_spell.name)}')
            if translation.description and orig_spell.description != translation.description:
                print(f'Warning! Original description for spell#{key}:{expansion} differs:\n{__diff_fields(translation.description, orig_spell.description)}')
            if translation.aura and orig_spell.aura != translation.aura:
                print(f'Warning! Original aura for spell#{key}:{expansion} differs:\n{__diff_fields(translation.aura, orig_spell.aura)}')
            orig_spell.name_ua = translation.name_ua
            orig_spell.description_ua = translation.description_ua
            orig_spell.aura_ua = translation.aura_ua
            orig_spell.name_ua = translation.name_ua
            orig_spell.category = translation.category
            orig_spell.group = translation.group
            orig_spell.ref = translation.ref
            translation.spell_md = orig_spell.spell_md


def __validate_template(spell_id: int, expansion: str, value: str, translation: str):
    import re
    translation = re.sub(r'\nspell#\d+', '', translation)
    translation = re.sub(r'\[.+?#.+?]', '', translation, flags=re.DOTALL)
    template_start = translation.find('#')
    if template_start == -1:
        if len(re.findall(r'{\d+}', translation)) != 0:
            print(f"Warning!! Template not described for spell#{spell_id}:{expansion}")
        return
    translation_templates = re.findall(r'{\d+}', translation[:template_start])
    orig_templates = re.findall(r'{\d+}', translation[template_start + 1:])
    if set(translation_templates) != set(orig_templates):
        print(f"Warning! Templates numbers doesn't match for spell#{spell_id}:{expansion}")
    templates = translation[template_start + 1:].split('#')
    for template in templates:
        template = template.replace('.', '\\.').replace('(', r'\(').replace(')', r'\)').replace('+', r'\+')
        pattern = re.sub(r'{\d+}', r'(\\d+|\\d+\.\\d+|\.\\d+|\[.+?\]|\(.+?\))', template).replace('\\\\', '\\')
        matches = re.findall(pattern, value)
        if len(matches) != 1:
            print(f'Warning! Template failed for spell#{spell_id}:{expansion}')

def __validate_templates(spell: SpellData):
    if spell.name_ua:
        __validate_template(spell.id, spell.expansion, spell.name, spell.name_ua)
    if spell.description_ua and not spell.description_ua.startswith('ref='):
        __validate_template(spell.id, spell.expansion, spell.description, spell.description_ua)
    if spell.aura_ua:
        __validate_template(spell.id, spell.expansion, spell.aura, spell.aura_ua)


def __validate_newlines(spell: SpellData):
    import re
    if spell.description_ua and not spell.description_ua.startswith('ref='):
        if not f'spell#' in spell.description_ua:
            if re.findall("\n\n", spell.description) != re.findall("\n\n", spell.description_ua):
                print(f"Warning! Newline count doesn't match for spell#{spell.id}:{spell.expansion} description")
        # else:
        #     if len(re.findall("spell#", spell.description_ua)) > 1:
        #         print(f"Warning! Check spell#{spell.id} manually")
    if spell.aura_ua and spell.aura:
        if re.findall("\n\n", spell.aura_ua) != re.findall("\n\n", spell.aura):
            print(f"Warning! Newline count doesn't match for spell#{spell.id}:{spell.expansion} aura")

def __validate_translation_completion(spell: SpellData):
    if spell.name and not spell.name_ua:
        print(f"Warning!! There's no translation for spell#{spell.id}:{spell.expansion} name")
    if spell.description and not spell.description_ua:
        print(f"Warning!! There's no translation for spell#{spell.id}:{spell.expansion} description")
    if spell.aura and not spell.aura_ua:
        print(f"Warning!! There's no translation for spell#{spell.id}:{spell.expansion} aura")


def __validate_numbers(spell_id: int, value: str, translation: str):
    import re
    if set(re.findall(r'\d+', value)) != set(re.findall(r'\d+', translation)):
        print(f"Warning!! Numbers don't match for spell spell#{spell_id}")

def __validate_spell_numbers(spell: SpellData):
    if spell.description and spell.description_ua and not spell.description_ua.startswith('ref=') and not '#' in spell.description_ua:
        __validate_numbers(spell.id, spell.description, spell.description_ua)
    if spell.aura_ua and spell.aura and not '#' in spell.aura_ua:
        __validate_numbers(spell.id, spell.aura, spell.aura_ua)

def __validate_references(spells: dict[int, dict[str, SpellData]], spell: SpellData):
    if spell.ref == spell.id:
        return
    if spell.ref:
        if not spell.ref in spells.keys() or len(spells[spell.ref]) == 0:
            print(f'Warning! Non-existent ref#{spell.ref} for spell#{spell.id}')
        else:
            reffed_spells = spells[spell.ref]
            for expansion, ref_spell in reffed_spells.items():
                if ref_spell.ref:
                    print(f'Warning! Double ref in ref_spell#{ref_spell.id}:{ref_spell.expansion} from spell#{spell.id}:{spell.expansion}')
                if (ref_spell.name_ua or ref_spell.description_ua or ref_spell.aura_ua):
                    __validate_translation_completion(ref_spell)

def validate_translations(spells: dict[int, dict[str, SpellData]]):
    print("Validating...")
    for key in sorted(spells.keys()):
        for spell in spells[key].values():
            __validate_templates(spell)
            __validate_newlines(spell)
            if (spell.name_ua or spell.description_ua or spell.aura_ua) and not spell.ref:
                __validate_translation_completion(spell)
            __validate_spell_numbers(spell)
            # __validate_references(spells, spell)

    # check if spell was updated in next expansion but has no translation


def compare_tsv_and_classicua(tsv_translations, classicua_translations):
    for key in sorted(tsv_translations.keys() - classicua_translations.keys()):
        print(f"Warning! Spell#{key} doesn't exist in ClassicUA")
    for key in sorted(classicua_translations.keys() - tsv_translations.keys()):
        print(f"Warning! Spell#{key} doesn't exist in TSV")
    for key in sorted(tsv_translations.keys() & classicua_translations.keys()):
        for expansion in tsv_translations[key].keys() - classicua_translations[key].keys():
            spell = tsv_translations[key][expansion]
            if (not spell.id == spell.ref): # Intentional skipping by setting ref to id
                print(f"Warning! Spell#{key}:{expansion} doesn't exist in ClassicUA")
        for expansion in classicua_translations[key].keys() - tsv_translations[key].keys():
            print(f"Warning! Spell#{key}:{expansion} doesn't exist in data")
        for expansion in tsv_translations[key].keys() & classicua_translations[key].keys():
            tsv_translation = tsv_translations[key][expansion]
            classicua_translation = classicua_translations[key][expansion]
            if tsv_translation.name_ua != classicua_translation.name_ua:
                print(f'Warning! Name translation differs for spell#{key}:{expansion}:\n{__diff_fields(tsv_translation.name_ua, classicua_translation.name_ua)}')
            if tsv_translation.description_ua != classicua_translation.description_ua:
                print(f'Warning! Description translation differs for spell#{key}:{expansion}:\n{__diff_fields(tsv_translation.description_ua, classicua_translation.description_ua)}')
            if tsv_translation.aura_ua != classicua_translation.aura_ua:
                print(f'Warning! Aura translation differs for spell#{key}:{expansion}:\n{__diff_fields(tsv_translation.aura_ua, classicua_translation.aura_ua)}')


def check_feedback_spells(spells: dict[int, dict[str, SpellData]]) -> list[int]:
    import csv
    feedback = dict()
    with open('input/missing_spells.tsv', 'r', encoding='utf-8') as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            feedback[int(row[0])] = row[1]

    missed_spells = set()
    for feedback_id, feedback_name in feedback.items():
        if feedback_id not in spells:
            print(f'Warning! Feedback spell#{feedback_id} "{feedback_name}" does not exist in DB!')
            missed_spells.add(feedback_id)
        else:
            translated = False
            for spell in spells[feedback_id].values():
                if spell.name_ua or spell.ref:
                    translated = True
            if not translated:
                # print(f'Warning! Feedback spell#{feedback_id} "{feedback_name}" is not translated!')
                missed_spells.add(feedback_id)

    # print(f'Missed IDs from feedback({len(missed_spells)}): {sorted(missed_spells)}')

    return sorted(missed_spells)


def filter_latest_untranslated(spells: dict[int, dict[str, SpellData]]) -> dict[int, dict[str, SpellData]]:
    result = dict()
    for key in spells.keys():
        spell_by_expansion = spells[key]
        expansions = sorted(list(spell_by_expansion.keys()), key=lambda x: expansion_data[x][INDEX])
        if len(expansions) > 1:
            first_expansion_spell = spell_by_expansion[expansions[0]]
            last_expansion_spell = spell_by_expansion[expansions[-1]]
            if first_expansion_spell.is_translated() and not last_expansion_spell.is_translated():
                result[key] = dict()
                result[key][last_expansion_spell.expansion] = last_expansion_spell
    return result


if __name__ == '__main__':
    # save_pages_async(SOD, [427717])
    # save_page_calc(CLASSIC, 1459)
    # spell1 = parse_wowhead_spell_page(CLASSIC, 1459)
    # save_page_raw(CLASSIC, 1460)
    # spell2 = parse_wowhead_spell_page(CLASSIC, 1460)
    # save_page_calc(SOD, 427717)
    # spell3 = parse_wowhead_spell_page(SOD, 427717)
    # print(spell1)
    # print(spell2)
    # print(spell3)

    # load_spells_from_db()

    all_spells = retrieve_spell_data()
    populate_similarity(all_spells)

    tsv_translations = read_translations_sheet()
    classicua_translations = read_classicua_translations(r'input\entries', all_spells)

    # apply_translations_to_data(all_spells, classicua_translations)
    apply_translations_to_data(all_spells, tsv_translations)

    save_spells_to_db(all_spells)

    compare_tsv_and_classicua(tsv_translations, classicua_translations)
    validate_translations(all_spells)

    missing_spells = check_feedback_spells(all_spells)

    convert_translations_to_entries(tsv_translations)

    # needs_update = filter_latest_untranslated(all_spells)
    # create_translation_sheet(needs_update, missing_spells)
    create_translation_sheet(all_spells, missing_spells)
