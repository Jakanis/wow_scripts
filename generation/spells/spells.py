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
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for spell #{id}')
    with open(xml_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_page_calc(expansion, id):
    from requests_html import HTMLSession
    session = HTMLSession()
    url = expansion_data[expansion][WOWHEAD_URL] + f'/spell={id}'
    xml_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}_rendered/{id}.html'
    if os.path.exists(xml_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
    r = session.get(url, headers=headers)
    if not r.ok:
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for spell #{id}')
    r.html.render()
    result = r.html.html
    session.close()
    with open(xml_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(result)


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

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'HTML({html_type}) cache for all Wowhead({expansion}) spells ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    if force:
        print(f'Force saving HTMLs({html_type}) for {len(force)} spells from Wowhead({expansion}).')
        save_ids += force
    print(f'Saving HTMLs({html_type}) for {len(save_ids)} of {len(ids)} spells from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    save_page = save_page_calc if render else save_page_raw
    threads = THREADS // 2 if render else THREADS * 2
    # for id in ids:
    #     save_page(expansion, id)
    save_func = partial(save_page, expansion)
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
        # wowhead_spells = {id: parse_wowhead_spell_page(expansion, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_spell_page, expansion, render)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_spells = p.map(parse_func, metadata.keys())
        wowhead_spells = {item.id: item for item in wowhead_spells}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_spells, f)

    for spell_id, spell in wowhead_spells.items():
        spell.spell_md = metadata[spell_id]

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
                        '(OLD)' in spell.name.upper() or
                        '(TEST)' in spell.name.upper() or
                        '(NYI)' in spell.name.upper() or
                        '(DNC)' in spell.name.upper() or
                        '(PT)' in spell.name.upper() or
                        '[PH]' in spell.name.upper() or
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


def populate_similarity(spells: dict[int, dict[str, SpellData]]):
    import re
    name_to_id: dict[str, dict[str, int]] = dict()
    description_to_id: dict[str, dict[str, int]] = dict()
    aura_to_id: dict[str, dict[str, int]] = dict()
    for expansion in expansion_data.keys():
        for key in [key for key in sorted(spells.keys()) if expansion in spells[key].keys()]:
            spell = spells[key][expansion]
            description = re.sub(r'\d+(\.\d+)?', '{d}', spell.description) if spell.description else None
            aura = re.sub(r'\d+(\.\d+)?', '{d}', spell.aura) if spell.aura else None

            if spell.name in name_to_id.keys():
                common_parents = name_to_id[spell.name].keys() & set(expansion_data[expansion][PARENT_EXPANSIONS] + [expansion])
                if len(common_parents) == 1:
                    common_parent = next(iter(common_parents))
                    spell.name_ref = name_to_id[spell.name][common_parent]
                elif len(common_parents) == 0:
                    if name_to_id[spell.name].keys() != {'sod'}:
                        print(f"Warning. Suspicious name parent situation for {key}:{expansion}.")
                    name_to_id[spell.name][expansion] = key
                else:
                    print(f"Warning! Strange name parent situation for {key}:{expansion}!")
            else:
                name_to_id[spell.name] = {expansion: key}

            if description and description in description_to_id.keys():
                common_parents = description_to_id[description].keys() & set(expansion_data[expansion][PARENT_EXPANSIONS] + [expansion])
                if len(common_parents) == 1:
                    common_parent = next(iter(common_parents))
                    spell.description_ref = description_to_id[description][common_parent]
                elif len(common_parents) == 0:
                    if description_to_id[description].keys() != {'sod'}:
                        print(f"Warning. Suspicious description parent situation for {key}:{expansion}.")
                    description_to_id[description][expansion] = key
                else:
                    print(f"Warning! Strange description parent situation for {key}:{expansion}!")
            else:
                description_to_id[description] = {expansion: key}

            if aura and aura in aura_to_id.keys():
                common_parents = aura_to_id[aura].keys() & set(expansion_data[expansion][PARENT_EXPANSIONS] + [expansion])
                if len(common_parents) == 1:
                    common_parent = next(iter(common_parents))
                    spell.aura_ref = aura_to_id[aura][common_parent]
                elif len(common_parents) == 0:
                    if aura_to_id[aura].keys() != {'sod'}:
                        print(f"Warning. Suspicious aura parent situation for {key}:{expansion}.")
                    aura_to_id[aura][expansion] = key
                else:
                    print(f"Warning! Strange aura parent situation for {key}:{expansion}!")
            else:
                aura_to_id[aura] = {expansion: key}

def __to_tsv_val(value) -> str:
    if value:
        return '"' + str(value).replace('"', '""') + '"'
    else:
        return ''

def create_translation_sheet(spells: dict[int, dict[str, SpellData]]):
    with open(f'translate_this.tsv', mode='w', encoding='utf-8') as f:
        f.write('ID\tName(EN)\tName(UA)\tDescription(EN)\tDescription(UA)\tAura(EN)\tAura(UA)\tref\tname_ref\tdesc_ref\taura_ref\texpansion\tcategory\tgroup\n')
        for key in sorted(spells.keys()):
            for expansion, spell in spells[key].items():
                # if getattr(spell.spell_md, 'chrclass') == 1 and spell.expansion == SOD and spell.name_ua is None:
                if spell.expansion != SOD and (spell.name_ua or spell.ref):
                    fields = [spell.id, spell.name, spell.name_ua, spell.description, spell.description_ua, spell.aura,
                              spell.aura_ua, spell.ref, spell.name_ref, spell.description_ref, spell.aura_ref, spell.expansion, spell.category, spell.group]
                    f.write(f'{'\t'.join(map(lambda x: __to_tsv_val(x), fields))}\n')


def merge_spell(id: int, old_spells: dict[str, SpellData], new_spell: SpellData) -> dict[str, SpellData]:
    import re
    if len(old_spells) > 1:
        last_old_spell_key = list(old_spells.keys())[-1]
        result = merge_spell(id, {last_old_spell_key: old_spells[last_old_spell_key]}, new_spell)
        del old_spells[last_old_spell_key]
        return {**old_spells, **result}
    if len(old_spells) == 1:
        old_spell = next(iter(old_spells.values()))

        if (old_spell.name != new_spell.name
                or (old_spell.description and new_spell.description and re.sub(r'\d+(\.\d+)?', '{d}', old_spell.description) != re.sub(r'\d+(\.\d+)?', '{d}', new_spell.description))
                or (old_spell.aura and new_spell.aura and re.sub(r'\d+(\.\d+)?', '{d}', old_spell.aura) != re.sub(r'\d+(\.\d+)?', '{d}', new_spell.aura))):
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
        wowhead_spells_raw = parse_wowhead_pages(expansion, wowhead_md, render=False)

        changed_spells = compare_stored_raw_spells(expansion, wowhead_spells_raw)
        save_htmls_from_wowhead(expansion, set(wowhead_md.keys()), render=True, force=changed_spells)
        wowhead_spells_rendered = parse_wowhead_pages(expansion, wowhead_md, render=True)

        store_raw_spells(expansion, wowhead_spells_raw)

        print(f'Merging with {expansion}')
        all_spells = merge_expansions(all_spells, wowhead_spells_rendered)

    return all_spells


def __spell_guide_header() -> str:
    import textwrap
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
        parry chance                        -- імовірність парирувати
        dodge chance                        -- імовірність ухилитися
        hit chance                          -- імовірність поцілити
        dual wield                          -- бій з двох рук
        
        all attributes                      -- всі характеристики
        Intelligence                        -- інтелект
        Strength                            -- сила
        Agility                             -- спритність
        Stamina                             -- витривалість
        Frenzy effect                       -- ефект навіженості
        Disease effect                      -- ефект хвороби
        Poison effect                       -- ефект отрути
        Curse effect                        -- ефект прокляття
        spell / ability                     -- закляття / здібність (синоніми, залежить від контексту)
        cooldown                            -- поновлення
        instance                            -- ігровимір
        to purge                            -- очистити / вичистити / чистити
        to dispel                           -- розсіяти
        resistance                          -- опір (вогню, кризі, ...)
        harmful spell                       -- шкідливе закляття
        beneficial spell                    -- сприятливе закляття
        offensive spells                    -- атакуючі закляття
        defensive spells                    -- захисні закляття
        stealth detection                   -- здатність виявлення непомітності
        Target cannot stealth or turn invisible -- Ціль не може стати непомітною або невидимою
        This effect stack up to X times     -- Ефект накладається до {X} разів
        Causes a high amount of threat      -- Спричиняє високий рівень загрози
        Movement Impairing effects          -- ефекти перешкоди руху
        Only usable outdoors                -- Можна використовувати лише просто неба
        Only usable out of combat           -- Можна використовувати лише поза боєм
        must channel to maintain the spell  -- повинен підтримувати закляття
        yields experience or honor          -- приносить досвід або честь
        to silence the target               -- знемовити ціль
        fully resisted spell                -- повністю протидіяти закляттю
        life drained / mana drained         -- (обсяг) випитого життя / випитої мани / висушувати
        which serves as a mount             -- для верхової їзди / на якому можна їздити верхи (якщо опис дозволяє)
        happiness                           -- щасливість (показник у вихованців мисливців)
        mount                               -- транспорт (при можливості уникати прямого слова, якщо контекст дозволяє)
        pet                                 -- вихованець (у мисливців) / прислужник (у чорнокнижників)
        
        Dazed                               -- Запаморочений
        Asleep                              -- Сплячий
        Feared                              -- Наляканий
        Rooted                              -- Прикований
        Frozen                              -- Заморожений
        Chilled                             -- Охолоджений
        Charmed                             -- Причарований
        Stunned                             -- Приголомшений
        Taunted                             -- Підбурений
        Enraged                             -- Розлючений
        Silenced                            -- Знемовлений
        Disarmed                            -- Роззброєний
        Enslaved                            -- Поневолений
        Horrified                           -- Нажаханий
        Invisible                           -- Невидимий
        Stealthed                           -- Непомітний
        Disoriented                         -- Дезорієнтований
        Immobilized / Immobile              -- Знерухомлений / Нерухомий
        Invulnerable                        -- Невразливий
        Incapacitated                       -- Недієздатний
        
        Fear and Horror effects             -- ефекти страху та жаху
        Increases your Defense skill by X   -- Збільшує вашу захисну здібність на X
        Awards 1 combo point                -- Збільшує довжину комбінації на X прийом
        Target must be facing you           -- Ціль має бути повернута до вас
        Must be behind the target           -- Необхідно бути позаду цілі
        Must be stealthed                   -- Необхідно бути непомітним
        Does not break stealth              -- Не порушує непомітності
        More effective than XXXXX (Rank X)  -- Дієвіше за "XXXXX" (Ранг X)
        Requires a dagger in the main hand  -- Працює лише за наявності кинджалу в основній руці
        Any damage caused will revive the target -- Будь-яка шкода знімає ефект з ураженої цілі
        Any damage caused will awaken the target -- Будь-яка шкода пробудить ціль
        Any damage caused will remove the effect -- Будь-яка шкода скасує ефект
        Stacks up to X times on a single target -- Накладається до X разів на одній цілі
        Turns off your attack when used     -- Припиняє вашу атаку при використанні
        Finishing move                      -- Завершальний рух
        each tick                           -- на кожному такті
        1 charge                            -- 1 заряд
        
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


def __spell_to_lua_row(spell: SpellData):
    name_text = f'"{spell.name_ua.replace('"', '\\"')}"' if spell.name_ua else 'nil'

    description_text = 'nil'
    rune_refs = []
    if spell.description_ua:
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

    original_name = f'{spell.name} ({spell.spell_md.rank})' if spell.spell_md and spell.spell_md.rank else spell.name

    return '[{}] = {{ {} }}, -- {}\n'.format(spell.id, ', '.join(translations), original_name)

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
            if spells_class != '': # Spell is in spell_{some_group}.lua
                if spell.name != previous_name:
                    output_file.write(f'-- {spell.name}\n')  # Group
            previous_name = spell.name
            output_file.write(__spell_to_lua_row(spell))

        groups: dict[str, list[SpellData]] = dict()
        grouped_spells = filter(lambda x: x.group is not None, translations)
        for spell in grouped_spells:
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
            if spell_id in all_spells:
                print(f'Warning! Duplicate for spell#{spell_id}')
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
    for key in spell_data.keys() & translations.keys():
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


def __validate_template(spell_id: int, value: str, translation: str):
    import re
    translation = re.sub(r'\nspell#\d+', '', translation)
    # translation = re.sub(r'(\[.+?]|\(.+?)', '42', value)
    template_start = translation.find('#')
    if template_start == -1:
        if len(re.findall(r'{\d+}', translation)) != 0:
            print(f"Warning! Template not described for spell#{spell_id}")
        return
    if len(re.findall(r'{\d+}', translation[:template_start])) != len(re.findall(r'{\d+}', translation[template_start + 1:])):
        print(f"Warning! Count of templates doesn't match for spell#{spell_id}")
    templates = translation[template_start + 1:].split('#')
    for template in templates:
        template = template.replace('.', '\\.')
        pattern = re.sub(r'{\d+}', r'(\\d+|\\d+\.\\d+|\.\\d+|\[.+?\]|\(.+?\))', template).replace('\\\\', '\\')
        matches = re.findall(pattern, value)
        if len(matches) != 1:
            print(f'Warning! Template failed for spell#{spell_id}')

def __validate_templates(spell: SpellData):
    if spell.name_ua:
        __validate_template(spell.id, spell.name, spell.name_ua)
    if spell.description_ua and not spell.description_ua.startswith('ref='):
        __validate_template(spell.id, spell.description, spell.description_ua)
    if spell.aura_ua:
        __validate_template(spell.id, spell.aura, spell.aura_ua)


def __validate_newlines(spell: SpellData):
    import re
    if spell.description_ua and not spell.description_ua.startswith('ref='):
        if not f'spell#' in spell.description_ua:
            if re.findall("\n\n", spell.description) != re.findall("\n\n", spell.description_ua):
                print(f"Warning! Newline count doesn't match for spell#{spell.id} description")
        # else:
        #     if len(re.findall("spell#", spell.description_ua)) > 1:
        #         print(f"Warning! Check spell#{spell.id} manually")
    if spell.aura_ua and spell.aura:
        if re.findall("\n\n", spell.aura_ua) != re.findall("\n\n", spell.aura):
            print(f"Warning! Newline count doesn't match for spell#{spell.id} aura")


def __validate_existence(spell: SpellData):
    if (spell.name_ua or spell.description_ua or spell.aura_ua) and not spell.ref:
        if spell.name and not spell.name_ua:
            print(f"Warning! There's no translation for spell#{spell.id} name")
        if spell.description and not spell.description_ua:
            print(f"Warning! There's no translation for spell#{spell.id} description")
        if spell.aura and not spell.aura_ua:
            print(f"Warning! There's no translation for spell#{spell.id} aura")


def __validate_numbers(spell_id: int, value: str, translation: str):
    import re
    if set(re.findall(r'\d+', value)) != set(re.findall(r'\d+', translation)):
        print(f"Warning! Numbers don't match for spell spell#{spell_id}")

def __validate_spell_numbers(spell: SpellData):
    if spell.description and spell.description_ua and not spell.description_ua.startswith('ref=') and not '#' in spell.description_ua:
        __validate_numbers(spell.id, spell.description, spell.description_ua)
    if spell.aura_ua and spell.aura and not '#' in spell.aura_ua:
        __validate_numbers(spell.id, spell.aura, spell.aura_ua)

def validate_translations(spells: dict[int, dict[str, SpellData]]):
    for key in sorted(spells.keys()):
        for spell in spells[key].values():
            __validate_templates(spell)
            __validate_newlines(spell)
            __validate_existence(spell)
            __validate_spell_numbers(spell)
    # check templates
    ## warning - No templates for raw values
    # check references


def compare_tsv_and_classicua(tsv_translations, classicua_translations):
    for key in tsv_translations.keys() - classicua_translations.keys():
        print(f"Warning! Spell#{key} doesn't exist in ClassicUA")
    for key in classicua_translations.keys() - tsv_translations.keys():
        print(f"Warning! Spell#{key} doesn't exist in TSV")
    for key in tsv_translations.keys() & classicua_translations.keys():
        for expansion in tsv_translations[key].keys() ^ classicua_translations[key].keys():
            print(f"Warning! Spell#{key}:{expansion} doesn't exist in one of translations")
        for expansion in tsv_translations[key].keys() & classicua_translations[key].keys():
            tsv_translation = tsv_translations[key][expansion]
            classicua_translation = classicua_translations[key][expansion]
            if tsv_translation.name_ua != classicua_translation.name_ua:
                print(f'Warning! Name translation differs for spell#{key}:{expansion}:\n{__diff_fields(tsv_translation.name_ua, classicua_translation.name_ua)}')
            if tsv_translation.description_ua != classicua_translation.description_ua:
                print(f'Warning! Description translation differs for spell#{key}:{expansion}:\n{__diff_fields(tsv_translation.description_ua, classicua_translation.description_ua)}')
            if tsv_translation.aura_ua != classicua_translation.aura_ua:
                print(f'Warning! Aura translation differs for spell#{key}:{expansion}:\n{__diff_fields(tsv_translation.aura_ua, classicua_translation.aura_ua)}')


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

    all_spells = retrieve_spell_data()
    populate_similarity(all_spells)

    tsv_translations = read_translations_sheet()
    classicua_translations = read_classicua_translations(r'input\entries', all_spells)

    # apply_translations_to_data(all_spells, classicua_translations)
    apply_translations_to_data(all_spells, tsv_translations)

    save_spells_to_db(all_spells)

    compare_tsv_and_classicua(tsv_translations, classicua_translations)
    validate_translations(all_spells)

    convert_translations_to_entries(tsv_translations)

    create_translation_sheet(all_spells)


# Warning! Template failed for spell#974
# Warning! Numbers don't match for spell spell#400735
#! Warning! Numbers don't match for spell spell#407632
# Warning! Numbers don't match for spell spell#408255
#! Warning! Numbers don't match for spell spell#424799
#! Warning! Numbers don't match for spell spell#424800
# Warning! Newline count doesn't match for spell#424925 description
#! Warning! Numbers don't match for spell spell#425012
# Warning! Template failed for spell#436516
# Warning! Newline count doesn't match for spell#436516 description
# Warning! Template failed for spell#436517
# Warning! Numbers don't match for spell spell#443635