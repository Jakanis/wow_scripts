import json
import os

import requests
from bs4 import BeautifulSoup, CData
from generation.spells.spells import SpellData, load_spells_from_db, is_spell_translated
from generation.utils.utils import compare_directories, update_on_crowdin

THREADS = 16
CLASSIC = 'classic'
SOD = 'sod'
SOD_PTR = 'sod_ptr'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
XML_CACHE = 'xml_cache'
HTML_CACHE = 'html_cache'
ITEM_CACHE = 'item_cache'
BOOK_CACHE = 'book_cache'
IGNORES = 'ignores'
FORCE_DOWNLOAD = 'force_download'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'

expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        XML_CACHE: 'wowhead_classic_item_xml',
        HTML_CACHE: 'wowhead_classic_item_html',
        ITEM_CACHE: 'wowhead_classic_item_cache',
        BOOK_CACHE: 'wowhead_classic_book_cache',
        METADATA_FILTERS: ('82:', '5:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: [13503, 16785, 17782]
    },
    SOD: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        XML_CACHE: 'wowhead_sod_item_xml',
        HTML_CACHE: 'wowhead_sod_item_html',
        ITEM_CACHE: 'wowhead_sod_item_cache',
        BOOK_CACHE: 'wowhead_sod_book_cache',
        METADATA_FILTERS: ('82:', '2:', '11500:'),
        # METADATA_FILTERS: ('82:82:', '2:4:', '11500:11506:'),
        IGNORES: [759, 9232, 202256, 202316, 215235, 215394, 215405, 215406, 215410, 215412, 215450, 231752, 235583, 239061],
        FORCE_DOWNLOAD: []
    },
    # SOD_PTR: {
    #     INDEX: 0,
    #     WOWHEAD_URL: 'https://www.wowhead.com/classic-ptr',
    #     METADATA_CACHE: 'wowhead_sod_ptr_metadata_cache',
    #     XML_CACHE: 'wowhead_sod_ptr_item_xml',
    #     ITEM_CACHE: 'wowhead_sod_ptr_item_cache',
    #     METADATA_FILTERS: ('82:', '1:', '11506:'),
    #     IGNORES: [759, 9232, 202256, 202316, 215235, 215394, 215405, 215406, 215410, 215412, 215450, 231752, 235583, 239061],
    #     FORCE_DOWNLOAD: []
    # },
    TBC: {
        INDEX: 1,
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        XML_CACHE: 'wowhead_tbc_item_xml',
        HTML_CACHE: 'wowhead_tbc_item_html',
        ITEM_CACHE: 'wowhead_tbc_item_cache',
        BOOK_CACHE: 'wowhead_tbc_book_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [16785, ]
    },
    WRATH: {
        INDEX: 2,
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        XML_CACHE: 'wowhead_wrath_item_xml',
        HTML_CACHE: 'wowhead_wrath_item_html',
        ITEM_CACHE: 'wowhead_wrath_item_cache',
        BOOK_CACHE: 'wowhead_wrath_book_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [16785, ]
    },
    CATA: {
        INDEX: 3,
        WOWHEAD_URL: 'https://www.wowhead.com/cata',
        METADATA_CACHE: 'wowhead_cata_metadata_cache',
        XML_CACHE: 'wowhead_cata_item_xml',
        HTML_CACHE: 'wowhead_cata_item_html',
        ITEM_CACHE: 'wowhead_cata_item_cache',
        BOOK_CACHE: 'wowhead_cata_book_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [16785, ]
    }
}


# Metadata from Wowhead
class ItemMD:
    def __init__(self, id, name, expansion=None, classs=None, firstseenpatch=None):
        self.id = id
        self.name = name
        self.expansion = expansion
        self.classs = classs
        self.firstseenpatch = firstseenpatch


EFFECT_TYPES = ('Desc', 'Equip', 'Hit', 'Use', 'Flavor', 'Item', 'Rune', 'Ref')

class ItemEffect:
    def __init__(self, effect_type, effect_id, effect_text, rune_spell_id=None):
        self.effect_type = effect_type
        self.effect_id = effect_id
        self.effect_text = effect_text
        self.rune_spell_id = rune_spell_id

    def get_type(self):
        return 'Hit' if self.effect_type == 'Chance on hit' else self.effect_type

    def __str__(self):
        res = f"{self.effect_type.replace('Chance on hit', 'Hit')}" if self.effect_type else ''
        res += f'#{self.effect_id}' if self.effect_id else ''
        if self.effect_type == 'Item':
            return res
        res += f': {self.effect_text}' if self.effect_text else ''
        res += f':#{self.rune_spell_id}' if self.rune_spell_id else ''
        return res

    def short_str(self):
        res = f"{self.effect_type.replace('Chance on hit', 'Hit')}" if self.effect_type else ''
        if self.effect_type == 'Item':
            return res + f'#{self.effect_id}'
        if self.effect_type == 'Rune':
            return res + f'#{self.effect_id}'
        res += f'#{self.effect_id}' if self.effect_text is None and self.effect_id else ''
        res += f': {self.effect_text}' if self.effect_text else ''
        res += f':#{self.rune_spell_id}' if self.rune_spell_id else ''
        return res

    def spell_ref_str(self):
        res = f"{self.effect_type.replace('Chance on hit', 'Hit')}" if self.effect_type else ''
        # if self.effect_type == 'Item' or self.effect_type == 'Rune':
        #     return 'ERROR'
        res += f'#{self.effect_id}'
        return res


class ItemData:
    def __init__(self, id, expansion, name: str = None, effects: list[ItemEffect] = [], readable=None, random_enchantment=False, name_ua=None, effects_ua: list[ItemEffect]=None, ref=None, raw_effects=None, readable_pages: list[str] = None):
        self.id = id
        self.name = name
        self.expansion = expansion
        self.effects = effects
        self.readable = readable
        self.random_enchantment = random_enchantment
        self.name_ua = name_ua
        self.effects_ua = effects_ua
        self.ref = ref
        self.raw_effects = raw_effects
        self.readable_pages = readable_pages

    def is_translated(self) -> bool:
        if self.name_ua or self.effects_ua:
            return True
        return False


class ReadableItem:
    def __init__(self, id, expansion, name: str = None, pages: list[str] = []):
        self.id = id
        self.name = name
        self.expansion = expansion
        self.pages = pages


def __get_wowhead_item_search(expansion, start, end=None) -> list[ItemMD]:
    base_url = expansion_data[expansion][WOWHEAD_URL]
    metadata_filters = expansion_data[expansion][METADATA_FILTERS]
    if end:
        url = base_url + f"/items?filter={metadata_filters[0]}151:151;{metadata_filters[1]}2:5;{metadata_filters[2]}{start}:{end}"
    else:
        url = base_url + f"/items?filter={metadata_filters[0]}151;{metadata_filters[1]}2;{metadata_filters[2]}{start}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    script_tag = soup.find('script', src=None, type="text/javascript")
    if not script_tag:
        return []
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('listviewitems = [') + 16
        end = script_content.find('}];') + 2
        json_data = (script_content[start:end]
                     .replace('firstseenpatch', '"firstseenpatch"')
                     .replace('frommerge', '"frommerge"')
                     .replace('popularity', '"popularity"')
                     .replace('contentPhase', '"contentPhase"'))
        return list(map(lambda md: ItemMD(md.get('id'), md.get('name'), expansion, md.get('classs'), md.get('firstseenpatch')), json.loads(json_data)))
    else:
        return []


def __retrieve_items_metadata_from_wowhead(expansion) -> dict[int, ItemMD]:
    all_items_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            items = __get_wowhead_item_search(expansion, start)
            print(f'Checking {start}+. Len: {len(items)}')
            if len(items) < 1000:
                all_items_metadata.extend(items)
                break
        items = __get_wowhead_item_search(expansion, start, start + 1000)
        all_items_metadata.extend(items)
        i += 1
    return {md.id: md for md in all_items_metadata}


def get_wowhead_items_metadata(expansion) -> dict[int, ItemMD]:
    import pickle
    cache_file_name = expansion_data[expansion][METADATA_CACHE]
    if os.path.exists(f'cache/tmp/{cache_file_name}.pkl'):
        print(f'Loading cached Wowhead({expansion}) metadata')
        with open(f'cache/tmp/{cache_file_name}.pkl', 'rb') as f:
            wowhead_metadata = pickle.load(f)
    else:
        print(f'Retrieving Wowhead({expansion}) metadata')
        wowhead_metadata = __retrieve_items_metadata_from_wowhead(expansion)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/{cache_file_name}.pkl', 'wb') as f:
            pickle.dump(wowhead_metadata, f)
    return wowhead_metadata


def save_xml_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/item={id}?xml'
    xml_file_path = f'cache/{expansion_data[expansion][XML_CACHE]}/{id}.xml'
    if os.path.exists(xml_file_path):
        print(f'Warning! Trying to download existing XML for #{id}')
        return
    r = requests.get(url)
    if not r.ok:
        # You download over 90000 pages in one hour - you'll fail
        # You do it async - you fail
        # Have a tea break (or change IP, lol)
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for item #{id}')
    if (f"<error>Item not found!</error>" in r.text):
        return
    with open(xml_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_html_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/item={id}'
    html_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    if os.path.exists(html_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    r = requests.get(url)
    if not r.ok:
        # You download over 90000 pages in one hour - you'll fail
        # You do it async - you fail
        # Have a tea break (or change IP, lol)
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for item #{id}')
    with open(html_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_xmls_from_wowhead(expansion, ids: set[int]):
    from functools import partial
    import multiprocessing
    cache_dir = f'cache/{expansion_data[expansion][XML_CACHE]}'

    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'XML cache for all Wowhead({expansion}) items ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    print(f'Saving XMLs for {len(save_ids)} of {len(ids)} items from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    # for id in save_ids:
    #     print("Saving XML for item #" + str(id))
    #     save_page(expansion, id)
    save_func = partial(save_xml_page, expansion)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_func, save_ids)


def save_htmls_from_wowhead(expansion, ids: set[int]):
    from functools import partial
    import multiprocessing
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}'

    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'HTML cache for all Wowhead({expansion}) items ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    print(f'Saving HTMLs for {len(save_ids)} of {len(ids)} items from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    # for id in save_ids:
    #     print("Saving XML for item #" + str(id))
    #     save_page(expansion, id)
    save_func = partial(save_html_page, expansion)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_func, save_ids)


def parse_wowhead_item_xml_page(expansion, id) -> ItemData:
    import re
    xml_path = f'cache/{expansion_data[expansion][XML_CACHE]}/{id}.xml'
    with open(xml_path, 'r', encoding="utf-8") as file:
        xml = file.read()
    soup = BeautifulSoup(xml, 'xml')

    item_name = soup.find('name').text

    tooltip = soup.find('htmlTooltip')
    tooltip_soup = BeautifulSoup(tooltip.text, 'xml')

    flavor = None
    flavor_tags = tooltip_soup.find_all('span', {"class": "q"})
    for flavor_tag in flavor_tags:
        if flavor_tag.find('br') or flavor_tag.find('a'):
            # There is another span with same class. It contains item level, damage, durability, etc
            continue
        if flavor:
            print(f'Warning! Setting flavor text more than one time for item #{id}')
        flavor = flavor_tag.text

    effects = list()
    effect_tags = tooltip_soup.find_all('span')
    random_enchantment = True if "Random enchantment" in tooltip.text else False
    readable = True if "Right Click to Read" in tooltip.text else False
    for effect_tag in effect_tags:
        if effect_tag.text == 'Random enchantment':
            random_enchantment = True
            continue
        if effect_tag.text == 'Right Click to Read':
            readable = True
            continue
        if effect_tag.text == 'Right Click to Open':
            continue
        for br in effect_tag.find_all('br'):
            br.replace_with('\n')
        full_effect_text = effect_tag.text
        effect_type = full_effect_text[:full_effect_text.find(': ')] if full_effect_text.startswith(('Use: ', 'Chance on hit: ', 'Equip: ')) else None
        a_tag = effect_tag.find('a')
        if a_tag:
            internal_a_tag = a_tag.find('a')
            if internal_a_tag:
                effect_spell_id = re.findall(r'spell=(\d+)', a_tag.get('href'))[0]
                effect_text = internal_a_tag.text
                rune_spell_id = re.findall(r'spell=(\d+)', internal_a_tag.get('href'))[0]
                # For runes
                double_refered_items = [(20130, CLASSIC), (191280, CLASSIC)]  # Some items have double reference in effects. Don't want to spend time on that, so there's a hack
                if expansion == SOD:
                    effects.append(ItemEffect('Rune', effect_spell_id, None, rune_spell_id))
                elif (id, expansion) in double_refered_items:
                    effects.append(ItemEffect(effect_type, rune_spell_id, a_tag.text))
                else:
                    print(f'Warning! Unexpected double reference effect for item #{id}:{expansion}!')
            else:
                effect_text = a_tag.text
                effect_text = effect_text[:effect_text.find('. (Proc') + 1] if '. (Proc' in effect_text else effect_text # Remove (Proc chance: x%) text
                effect_link = a_tag.get('href')
                if '/item-set=' in effect_link:  # to prevent fetching next item links
                    break
                if '/item=' in effect_link:  # recipes
                    item_ids = re.findall(r'/item=(\d+)', effect_link)
                    if item_ids:
                        effects.append(ItemEffect('Item', item_ids[0], effect_text))
                        flavor = None
                    break
                effect_spell_ids = re.findall(r'/spell=(\d+)', effect_link)
                if effect_spell_ids and effect_type:
                    effects.append(ItemEffect(effect_type, effect_spell_ids[0], effect_text))
        elif effect_type:
            effects.append(ItemEffect(effect_type, None, full_effect_text[full_effect_text.find(':')+2:]))
        # if effect_type is None:
        #     print(f'Warning! Empty effect type for item#{id}:{expansion}')

    item_class_id = soup.find('class').get('id')
    if readable and item_class_id == 12:
        print(f'Check readability of item#{id}')

    if flavor:
        effects.append(ItemEffect('Flavor', None, flavor))

    return ItemData(id, expansion, item_name, effects, readable, random_enchantment)


def parse_wowhead_item_html_page(expansion, id) -> ReadableItem|None:
    import json5
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    content = None
    with open(html_path, 'r', encoding="utf-8") as file:
        content = file.read()

    soup = BeautifulSoup(content, 'html.parser')
    item_name = soup.find('h1').text

    for item in content.split("\n"):
        if f"new Book(" in item:
            start = item.find('new Book({') + 9
            end = item.find('})', start) + 1
            json_raw = item[start:end]
            json_data = json5.loads(json_raw).get('pages')
            pages = []
            page_no = 1
            for page in json_data:
                page_soup = BeautifulSoup(page, 'html5lib')
                for element in page_soup.find_all('br'):
                    # if br.previous_sibling and br.previous_sibling.name == 'p':
                    #     br.replace_with('\n\n')
                    # else:
                    element.replace_with('\n')
                for element in page_soup.find_all('p'):
                    if element.next_sibling:
                        element.replace_with(element.text + '\n')
                for element in page_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    element.replace_with(element.text + '\n')
                page_content = page_soup.text.replace(' ', '')
                if page_content.strip():
                    pages.append(page_content)
                    page_no += 1

            return ReadableItem(id, expansion, item_name, list(pages))

    return ReadableItem(id, expansion, item_name, [])


def parse_wowhead_xml_pages(expansion: str, item_ids: set[int]) -> dict[int, ItemData]:
    import pickle
    import multiprocessing
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][ITEM_CACHE]}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) items')
        with open(cache_path, 'rb') as f:
            wowhead_items = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) item pages')
        # wowhead_items = {id: parse_wowhead_item_xml_page(expansion, id) for id in item_ids}
        parse_func = partial(parse_wowhead_item_xml_page, expansion)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_items = p.map(parse_func, item_ids)
        wowhead_items = {item.id: item for item in wowhead_items}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_items, f)

    # wowhead_item_data = merge_quests_and_metadata(wowhead_items, metadata)

    # return wowhead_quest_entities
    return wowhead_items


def parse_wowhead_html_pages(expansion: str, items_ids: set[int]) -> dict[int, ReadableItem]:
    import pickle
    import multiprocessing
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][BOOK_CACHE]}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) readable items')
        with open(cache_path, 'rb') as f:
            wowhead_items = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) readable items')
        # wowhead_items = {id: parse_wowhead_item_html_page(expansion, id) for id in items_ids}
        parse_func = partial(parse_wowhead_item_html_page, expansion)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_items = p.map(parse_func, items_ids)
        wowhead_items = {item.id: item for item in wowhead_items if item is not None}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_items, f)

    return wowhead_items


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


def load_item_lua_names(path) -> dict[int, str]:
    from slpp import slpp as lua
    items = dict()
    with open(path, 'r', encoding='utf-8') as input_file:
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


def save_items_to_db(items: dict[int, dict[str, ItemData]]):
    import sqlite3
    print('Saving items to DB')
    conn = sqlite3.connect('cache/items.db')
    conn.execute('DROP TABLE IF EXISTS items')
    conn.execute('''CREATE TABLE items (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        name_ua TEXT,
                        effects TEXT,
                        effects_ua TEXT,
                        random_enchantment BOOL,
                        readable BOOL,
                        raw_effects TEXT
                )''')
    conn.commit()
    with (conn):
        for key in items.keys():
            for expansion, item in items[key].items():
                if ('OLD' in item.name or
                    'DEP' in item.name or
                    '[PH]' in item.name or
                    '(old)' in item.name or
                    '(old2)' in item.name or
                    'QATest' in item.name or
                    'DEBUG' in item.name or
                    '(DND)' in item.name or
                    'QAEnchant' in item.name or
                    'TEST' in item.name or
                    'UNUSED' in item.name or
                    item.name.startswith('Monster - ') or
                    key in expansion_data[item.expansion][IGNORES]):
                        continue
                item_effects = '\n'.join(map(lambda x: str(x), item.effects)) if item.effects else None
                item_effects_ua = '\n'.join(map(lambda x: str(x), item.effects_ua)) if item.effects_ua else None
                if item_effects_ua is None and item.ref:
                    item_effects_ua = f"ref={item.ref}"
                conn.execute('INSERT INTO items(id, expansion, name, name_ua, effects, effects_ua, random_enchantment, readable, raw_effects) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (item.id, item.expansion, item.name, item.name_ua, item_effects, item_effects_ua, item.random_enchantment, item.readable, item.raw_effects))


def __merge_item_effects(old_item: ItemData, new_item: ItemData):
    from collections import defaultdict
    from functools import cmp_to_key
    old_item.raw_effects = '\n'.join(map(lambda x: str(x), sorted(old_item.effects, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type()))))) if old_item.raw_effects is None else old_item.raw_effects
    new_item.raw_effects = '\n'.join(map(lambda x: str(x), sorted(new_item.effects, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type()))))) if new_item.raw_effects is None else new_item.raw_effects
    if len(old_item.effects) != len(new_item.effects):
        return

    old_item_effects_by_type = defaultdict(list)
    new_item_effects_by_type = defaultdict(list)
    for effect in old_item.effects:
        old_item_effects_by_type[effect.get_type()].append(effect)
    for effect in new_item.effects:
        new_item_effects_by_type[effect.get_type()].append(effect)

    for effect_type in old_item_effects_by_type.keys() & new_item_effects_by_type.keys():
        old_effects_group = old_item_effects_by_type[effect_type]
        new_effects_group = new_item_effects_by_type[effect_type]
        if len(old_effects_group) != len(new_effects_group):
            continue
        for i in range(len(old_effects_group)):
            old_effect = old_effects_group[i]
            new_effect = new_effects_group[i]
            if old_effect.effect_id and new_effect.effect_id and old_effect.effect_id == new_effect.effect_id and old_effect.effect_text != new_effect.effect_text:
                old_effect.effect_text = None
                new_effect.effect_text = None
            if old_effect.effect_id != new_effect.effect_id and old_effect.effect_text == new_effect.effect_text:
                old_effect.effect_id = None
                new_effect.effect_id = None
    old_item.effects = sorted(old_item.effects, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type())))
    new_item.effects = sorted(new_item.effects, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type())))


def merge_item(id: int, old_items: dict[str, ItemData], new_item: ItemData) -> dict[str, ItemData]:
    import re
    if len(old_items) > 1:
        last_old_item_key = list(old_items.keys())[-1]
        result = merge_item(id, {last_old_item_key: old_items[last_old_item_key]}, new_item)
        del old_items[last_old_item_key]
        return {**old_items, **result}
    if len(old_items) == 1:
        old_item = next(iter(old_items.values()))

        # all effects' full_strs are equal - return old_items
        # else - merge_item_effects:
        # sort effects
        # for each effect:
        #   if both GOT same spell id - delete text for both
        #   if both GOT same text - delete spell id for both
        #   ignore rune_spell_id?
        # if full_strs equal - return only one item
        # if full_strs diffed - return both items
        # test data: item#833classic/wrath (different order), item#728(classic/tbc) (same text, different spell), item#159/862/867/868/875/943 (same spell, different text)
        #
        # if name differs - merge their effects and return both

        __merge_item_effects(old_item, new_item)
        if old_item.name.lower() != new_item.name.lower():
            return {**old_items, **{new_item.expansion: new_item}}
        elif '\n'.join([str(effect) for effect in old_item.effects]) != '\n'.join([str(effect) for effect in new_item.effects]):
            return {**old_items, **{new_item.expansion: new_item}}
        else:
            return old_items

        # if old_item.name != new_item.name or '\n'.join([str(effect) for effect in old_item.effects]) != '\n'.join([str(effect) for effect in new_item.effects]):
        #     return {**old_items, **{new_item.expansion: new_item}}
        # else:
        #     return old_items
    else:
        print(f'Skip: Item #{id} instance number unexpected')


def merge_expansions(old_expansion: dict[int, dict[str, ItemData]], new_expansion: dict[int, ItemData]) -> dict[int, dict[str, ItemData]]:
    result = dict()

    for id in old_expansion.keys() - new_expansion.keys():
        result[id] = old_expansion[id]

    for id in new_expansion.keys() - old_expansion.keys():
        result[id] = dict()
        result[id][new_expansion[id].expansion] = new_expansion[id]

    for id in old_expansion.keys() & new_expansion.keys():
        result[id] = merge_item(id, old_expansion[id], new_expansion[id])
    return result


def merge_readable_item(id: int, old_items: dict[str, ReadableItem], new_item: ReadableItem) -> dict[str, ReadableItem]:
    if len(old_items) > 1:
        last_old_item_key = list(old_items.keys())[-1]
        result = merge_readable_item(id, {last_old_item_key: old_items[last_old_item_key]}, new_item)
        del old_items[last_old_item_key]
        return {**old_items, **result}
    if len(old_items) == 1:
        old_item = next(iter(old_items.values()))

        if len(old_item.pages) != len(new_item.pages):
            print(f'Warning! Readable item #{id} changed between {old_item.expansion} and {new_item.expansion}!')
            return {**old_items, **{new_item.expansion: new_item}}

        for i in range(len(old_item.pages)):
            old_page = old_item.pages[i]
            new_page = new_item.pages[i]
            if old_page != new_page:
                print(f'Warning! Readable item #{id} changed between {old_item.expansion} and {new_item.expansion} at page #{i+1}!')
                return {**old_items, **{new_item.expansion: new_item}}

        return old_items
    else:
        print(f'Skip: Readable item #{id} instance number unexpected')


def merge_readable_items(old_expansion: dict[int, dict[str, ReadableItem]], new_expansion: dict[int, ReadableItem]) -> dict[int, dict[str, ReadableItem]]:
    result = dict()

    for item_id in sorted(new_expansion.keys()):
        item = new_expansion[item_id]
        if not item.pages or len(item.pages) == 0:
            # print(f'Warning! Readable item #{item_id}:{item.expansion} has no pages!')
            del new_expansion[item_id]

    for item_id in old_expansion.keys() - new_expansion.keys():
        result[item_id] = old_expansion[item_id]

    for item_id in new_expansion.keys() - old_expansion.keys():
        new_item = new_expansion.get(item_id)
        if new_item and len(new_item.pages) > 0:
            result[item_id] = dict()
            result[item_id][new_expansion[item_id].expansion] = new_expansion[item_id]
        # else:
        #     print(f'Warning! No readable item data for #{item_id} in new expansion!')

    for item_id in sorted(old_expansion.keys() & new_expansion.keys()):
        result[item_id] = merge_readable_item(item_id, old_expansion[item_id], new_expansion[item_id])
    return result


def populate_book_text(item_data: dict[int, ItemData], readable_items: dict[int, ReadableItem]):
    for item_id, item in item_data.items():
        if item.readable and item_id in readable_items:
            readable_item = readable_items[item_id]
            if readable_item and readable_item.pages:
                item.readable_pages = readable_item.pages
            else:
                print(f'Warning! Item #{item_id} has no readable pages!')
        else:
            item.readable_pages = None


def fix_readables(expansion, items):
    ## Known valid diffs:
    # Readable item #20545 changed between classic and wrath at page #1
    # Readable item #745 changed between classic and cata
    # Readable item #2223 changed between classic and cata
    # Warning! Readable item #4834 changed between classic and cata # TODO: Check ingame
    # Readable item #4992 changed between classic and cata at page #1
    # Readable item #5505 changed between classic and cata at page #6
    # Readable item #9553 changed between classic and cata at page #1
    # Readable item #9577 changed between classic and cata at page #1
    # Readable item #9580 changed between classic and cata at page #1
    # Readable item #10839 changed between classic and cata at page #2
    # Readable item #16263 changed between classic and cata at page #1
    # Readable item #16307 changed between classic and cata at page #1
    # Readable item #16310 changed between classic and cata at page #1

    if expansion == CLASSIC:
        items[2007].pages[1] = items[2007].pages[1].replace("I'lalia", "I'lalai")
        items[2154].pages[2] = items[2154].pages[2].replace("cemetary near Raven's Hill", "cemetery near Raven Hill")
        items[2154].pages[3] = items[2154].pages[3].replace("cemetary", "cemetery")
        items[2154].pages[4] = items[2154].pages[4].replace("cemetary", "cemetery")
        items[2154].pages[6] = items[2154].pages[6].replace("cemetary", "cemetery")
        items[2154].pages[6] = items[2154].pages[6].replace("the chests of", "the chest of")
        items[2154].pages[7] = items[2154].pages[7].replace("cemetary", "cemetery")
        items[2748].pages[0] = items[2748].pages[0].replace("Lashtail Raptor's stalking", 'Lashtail Raptors stalking')
        items[2758].pages[0] = items[2758].pages[0].replace("their sites on the", 'their sights on the')
        items[2758].pages[7] = items[2758].pages[7].replace("Lashtail Raptor's stalking", 'Lashtail Raptors stalking')
        items[2885].pages[0] = items[2885].pages[0].replace("Captain Melrose", 'Captain Melrache')
        items[2885].pages[1] = items[2885].pages[1].replace("Captain Melrose", 'Captain Melrache')
        items[3657].pages[2] = items[3657].pages[2].replace('next deliver of', 'next delivery of')
        items[3657].pages[2] = items[3657].pages[2].replace('Azureload', 'Azurelode')
        items[3657].pages[3] = items[3657].pages[3].replace('Azureload', 'Azurelode')
        items[5088].pages[0] = items[5088].pages[0].replace('autmoatically', 'automatically')
        items[5594].pages[0] = items[5594].pages[0].replace("the Bloodfeather's have", 'the Bloodfeathers have')
        items[5594].pages[0] = items[5594].pages[0].replace("can have her head", 'can have their heads') # meh. pronouns? rly?
        items[5897].pages[0] = items[5897].pages[0].replace("disappounted", 'disappointed')
        items[9559].pages[0] = items[9559].pages[0].replace("we posses no magical", 'we possess no magical')
        items[9580].pages[0] = items[9580].pages[0].replace("hopefuly", 'hopefully')
        items[12438].pages[0] = items[12438].pages[0].replace("guage", 'gauge')
        items[13202].pages[8] = items[13202].pages[8].replace("Davil Lightforge", 'Davil Lightfire')
        items[15998].pages[0] = items[15998].pages[0].replace("bounty this land was", 'bounty for which this land was')
        items[16310].pages[0] = items[16310].pages[0].replace("the list students", 'the list of students')
        items[16310].pages[0] = items[16310].pages[0].replace("Honarary", 'Honorary')
        items[18664].pages[0] = items[18664].pages[0].replace('with the ranks of each listed in descending order from highest to lowest. Long live the Alliance!', 'with the ranks\nof each listed in descending order from highest to lowest.\nLong live the Alliance!')
        items[18675].pages[0] = items[18675].pages[0].replace('As is fitting, the strongest are listed at the top, with the weaker listed below them.', 'As is\nfitting, the strongest are listed at the top, with the weaker\nlisted below them.')
        items[20676].pages[0] = items[20676].pages[0].replace("The sing praise", 'They sing praise')

    if expansion == TBC:
        items[2007].pages[1] = items[2007].pages[1].replace("I'lalia", "I'lalai")
        items[2154].pages[2] = items[2154].pages[2].replace("cemetary near Raven's Hill", "cemetery near Raven Hill")
        items[2154].pages[3] = items[2154].pages[3].replace("cemetary", "cemetery")
        items[2154].pages[4] = items[2154].pages[4].replace("cemetary", "cemetery")
        items[2154].pages[6] = items[2154].pages[6].replace("cemetary", "cemetery")
        items[2154].pages[6] = items[2154].pages[6].replace("the chests of", "the chest of")
        items[2154].pages[7] = items[2154].pages[7].replace("cemetary", "cemetery")
        items[2885].pages[0] = items[2885].pages[0].replace("Captain Melrose", 'Captain Melrache')
        items[2885].pages[1] = items[2885].pages[1].replace("Captain Melrose", 'Captain Melrache')
        items[3657].pages[2] = items[3657].pages[2].replace('Azureload', 'Azurelode')
        items[3657].pages[3] = items[3657].pages[3].replace('Azureload', 'Azurelode')
        items[9559].pages[0] = items[9559].pages[0].replace("we posses no magical", 'we possess no magical')
        items[11737].pages[0] = items[11737].pages[0].replace('Master Kariel Winthalus', 'Master Telmius Dreamseeker')
        items[13202].pages[8] = items[13202].pages[8].replace("Davil Lightforge", 'Davil Lightfire')
        items[18664].pages[0] = items[18664].pages[0].replace('with the ranks of each listed in descending order from highest to lowest. Long live the Alliance!', 'with the ranks\nof each listed in descending order from highest to lowest.\nLong live the Alliance!')
        items[18675].pages[0] = items[18675].pages[0].replace('As is fitting, the strongest are listed at the top, with the weaker listed below them.', 'As is\nfitting, the strongest are listed at the top, with the weaker\nlisted below them.')
        items[32888].pages[0] = items[32888].pages[0].replace("to convice his", 'to convince his')
        items[20676].pages[0] = items[20676].pages[0].replace("The sing praise", 'They sing praise')
        items[23798].pages[0] = items[23798].pages[0].replace("their whips or goring", 'their whips, or goring')
        items[24237].pages[1] = items[24237].pages[1].replace("consciousness The torture", 'consciousness. The torture')

    if expansion == WRATH:
        items[2154].pages[2] = items[2154].pages[2].replace("cemetary near Raven's Hill", "cemetery near Raven Hill")
        items[2154].pages[3] = items[2154].pages[3].replace("cemetary", "cemetery")
        items[2154].pages[4] = items[2154].pages[4].replace("cemetary", "cemetery")
        items[2154].pages[6] = items[2154].pages[6].replace("cemetary", "cemetery")
        items[2154].pages[6] = items[2154].pages[6].replace("the chests of", "the chest of")
        items[2154].pages[7] = items[2154].pages[7].replace("cemetary", "cemetery")
        items[9559].pages[0] = items[9559].pages[0].replace("we posses no magical", 'we possess no magical')
        items[18664].pages[0] = items[18664].pages[0].replace('with the ranks of each listed in descending order from highest to lowest. Long live the Alliance!', 'with the ranks\nof each listed in descending order from highest to lowest.\nLong live the Alliance!')
        items[18675].pages[0] = items[18675].pages[0].replace('As is fitting, the strongest are listed at the top, with the weaker listed below them.', 'As is\nfitting, the strongest are listed at the top, with the weaker\nlisted below them.')
        items[20676].pages[0] = items[20676].pages[0].replace("The sing praise", 'They sing praise')
        items[23798].pages[0] = items[23798].pages[0].replace("their whips or goring", 'their whips, or goring')
        items[24237].pages[1] = items[24237].pages[1].replace("consciousness The torture", 'consciousness. The torture')

    if expansion == CATA:
        items[18664].pages[0] = items[18664].pages[0].replace('with the ranks of each listed in descending order from highest to lowest. Long live the Alliance!', 'with the ranks\nof each listed in descending order from highest to lowest.\nLong live the Alliance!')
        items[18675].pages[0] = items[18675].pages[0].replace('As is fitting, the strongest are listed at the top, with the weaker listed below them.', 'As is\nfitting, the strongest are listed at the top, with the weaker\nlisted below them.')


def retrieve_item_data() -> tuple[dict[int, dict[str, ItemData]], dict[str, dict[int, ReadableItem]]]:
    wowhead_md = dict()
    wowhead_items = dict()
    readable_items = dict()
    all_items = dict()
    all_readable_items = dict()

    for expansion, expansion_properties in expansion_data.items():
        wowhead_md[expansion] = get_wowhead_items_metadata(expansion)
        for ignore_id in expansion_properties[IGNORES]:
            del wowhead_md[expansion][ignore_id]
        for force_id in expansion_properties[FORCE_DOWNLOAD]:
            wowhead_md[expansion][force_id] = ItemMD(force_id, "FORCE LOAD", expansion)
        save_xmls_from_wowhead(expansion, set(wowhead_md[expansion].keys()))
        wowhead_items[expansion] = parse_wowhead_xml_pages(expansion, set(wowhead_md[expansion].keys()))
        readable_items_ids = {item_id for item_id, item in wowhead_items[expansion].items() if item.readable} # filter readable items
        save_htmls_from_wowhead(expansion, readable_items_ids)
        readable_items[expansion] = parse_wowhead_html_pages(expansion, readable_items_ids)
        fix_readables(expansion, readable_items[expansion])
        # populate_book_text(wowhead_items[expansion], readable_items[expansion])
        print(f'Merging with {expansion}')
        all_items = merge_expansions(all_items, wowhead_items[expansion])
        all_readable_items = merge_readable_items(all_readable_items, readable_items[expansion])

    # translations = load_item_lua_names('input/entries/item.lua')
    # translations_sod = load_item_lua_names('input/entries/item_sod.lua')
    #
    # for key in wowhead_items.keys() & translations.keys():
    #     wowhead_items[key].name_ua = translations[key]
    #
    # for key in wowhead_items_sod.keys() & translations_sod.keys():
    #     wowhead_items_sod[key].name_ua = translations_sod[key]
    #
    # questie_item_ids = load_questie_item_lua_ids()
    #
    # for key in questie_item_ids:
    #     if not wowhead_items[key].name_ua:
    #         wowhead_items[key].name_ua = 'questie'

    return all_items, all_readable_items


def __try_cast_str_to_int(value: str, default=None):
    try:
        return int(value)
    except ValueError:
        return default


def str_effect_to_effect(str_effect_row) -> ItemEffect:
    if not str_effect_row:
        print("Warning! Empty effect row!")
        return None
    if str_effect_row.startswith('Item#'):
        return ItemEffect('Item', str_effect_row[5:], None)
    effect_type_link, effect_text = str_effect_row.split(":", 1) if ":" in str_effect_row else (str_effect_row, None)
    effect_text = effect_text[1:] if effect_text else None
    effect_type, effect_spell_id = effect_type_link.split("#", 1) if '#' in effect_type_link else (effect_type_link, None)
    effect_spell_id = effect_spell_id and int(effect_spell_id)
    if str_effect_row.startswith('Rune#'):
        return ItemEffect('Rune', effect_spell_id, None, int(effect_text))
    return ItemEffect(effect_type, effect_spell_id, effect_text)


def str_effects_to_effects(str_effects: str, ignore_desc=False) -> list[ItemEffect]:
    import re
    if not str_effects:
        return []
    effects = list()
    for effect_row in re.split(r'\n(?=(?:Desc|Equip|Hit|Use|Flavor):|(?:Equip|Hit|Use|Rune|Ref|Item)#\d+)', str_effects):
        if effect_row.startswith(EFFECT_TYPES):
            effect = str_effect_to_effect(effect_row)
            if ignore_desc and effect.get_type() == "Desc":
                continue
            if effect:
                effects.append(effect)
    return effects


def read_translations_sheet() -> dict[int, dict[str, ItemData]]:
    import csv
    all_translations: dict[int, dict[str, ItemData]] = dict()
    with open('input/translations.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            item_id = __try_cast_str_to_int(row[0])
            if not item_id:
                print(f'Skipping: {row}')
                continue
            name_en = row[1] if row[1] else None
            name_ua = row[2] if row[2] else None
            effects = str_effects_to_effects(row[3], ignore_desc=True) if row[3] else []
            ref = None
            effects_ua = str_effects_to_effects(row[4]) if row[4] else []
            if effects_ua and effects_ua[0].effect_type == 'Ref':
                ref = effects_ua[0].effect_id
            expansion = row[6]
            all_translations[item_id] = all_translations.get(item_id, dict())
            if expansion in all_translations[item_id].keys():
                print(f'Warning! Duplicate for item#{item_id}:{expansion}')
            all_translations[item_id][expansion] = ItemData(item_id, expansion, name=name_en, name_ua=name_ua,
                                                            effects=effects, effects_ua=effects_ua, ref=ref)

    return all_translations


def lua_effect_to_effect(field: str, lua_effects) -> list[ItemEffect]:
    if lua_effects is None:
        return []
    elif type(lua_effects) == str:
        return [ItemEffect(field.capitalize(), None, lua_effects.replace(r'\n', '\n'))]
    elif type(lua_effects) == int:
        field_name = 'Item' if field == 'recipe_result_item' else field.capitalize()
        return [ItemEffect(field_name, lua_effects, None)]
    elif type(lua_effects) == list:
        effects = list()
        for lua_effect in lua_effects:
            effects.extend(lua_effect_to_effect(field, lua_effect))
        return effects


def decoded_lua_item_to_effects_list(decoded_item) -> list[ItemEffect]:
    effects = list()
    fields = ['desc', 'equip', 'hit', 'use', 'flavor', 'recipe_result_item', 'ref']
    for field in fields:
        effects.extend(lua_effect_to_effect(field, decoded_item.get(field)))
    return effects

def read_classicua_translations(items_root_path: str, item_data: dict[int, dict[str, ItemData]]):
    from slpp import slpp as lua
    file_contents = list()
    for foldername, subfolders, filenames in os.walk(items_root_path):
        for filename in filenames:
            # Construct the full path to the file
            file_path = foldername + '\\' + filename

            # Read the contents of the file
            with open(file_path, 'r', encoding="utf-8") as file:
                file_content = file.read()
                file_contents.append((file_path, file_content))

    all_items: dict[int, dict[str, ItemData]] = dict()

    for file_path, lua_file in file_contents:
        expansion, file_name = file_path.split('\\')[-2:]
        lua_table = lua_file[lua_file.find(' = {\n') + 2:lua_file.find('\n}\n') + 2]
        decoded_items = lua.decode(lua_table)
        for item_id, decoded_item in decoded_items.items():
            if item_id in all_items and expansion in all_items[item_id]:
                print(f'Warning! Duplicate for item#{item_id}:{expansion}')
            if type(decoded_item) == list:
                item = ItemData(id=id,
                                expansion=expansion,
                                name_ua=decoded_item[0],
                                effects_ua=[])
            else:
                effects = decoded_lua_item_to_effects_list(decoded_item)
                item = ItemData(id=id,
                                expansion=expansion,
                                name_ua=decoded_item.get(0),
                                effects_ua=effects)

            all_items[item_id] = all_items.get(item_id, dict())
            all_items[item_id][expansion] = item
    return all_items


def build_name_pretranslation_map(items: dict[int, dict[str, ItemData]]) -> dict[str, str]:
    name_translations = dict()
    for key in items.keys():
        for expansion, item in sorted(items[key].items()):
            if item.name_ua:
                if item.name in name_translations and name_translations[item.name] != item.name_ua:
                    print(f'Warning! Name translation for {item.name} differs: {name_translations[item.name]} <> {item.name_ua}')
                else:
                    name_translations[item.name] = item.name_ua
    return name_translations

def create_translation_sheet(items: dict[int, dict[str, ItemData]], spells: dict[int, dict[str, SpellData]]):
    name_pretranslation_map = build_name_pretranslation_map(items)
    with open(f'output/translate_this.tsv', mode='w', encoding='utf-8') as f:
        f.write('ID\tName(EN)\tName(UA)\tDescription(EN)\tDescription(UA)\tNote\texpansion\n')
        count = 0
        missing_spell_ids = set()
        for key in sorted(items.keys()):
            for expansion, item in sorted(items[key].items()):
                if ('OLD' in item.name or
                        'DEP' in item.name or
                        '[PH]' in item.name or
                        '(old)' in item.name or
                        '(old2)' in item.name or
                        'QATest' in item.name or
                        'DEBUG' in item.name or
                        '(DND)' in item.name or
                        'QAEnchant' in item.name or
                        'TEST' in item.name or
                        'UNUSED' in item.name or
                        item.name.startswith('Monster - ') or
                        item.id in expansion_data[item.expansion][IGNORES]):
                    continue

                # if item.expansion == 'sod' and not item.is_translated():
                if item.expansion in (SOD, SOD_PTR) and not item.is_translated():
                # if not item.is_translated():
                    item_name_ua = item.name_ua if item.name_ua else ''
                    if item_name_ua == '' and item.name in name_pretranslation_map.keys():
                        item_name_ua = name_pretranslation_map[item.name] + ' ???'
                    effects_ua_text = list()
                    # pretranslation = False
                    for original_effect in item.effects:
                        effect_id = int(original_effect.effect_id) if original_effect.effect_id and not original_effect.effect_type == "Item" else None
                        if effect_id and is_spell_translated(spells.get(effect_id)):
                            effects_ua_text.append(original_effect.spell_ref_str())
                            # pretranslation = True
                        else:
                            effect_text_ua = original_effect.effect_type
                            if original_effect.effect_id:
                                effect_text_ua = effect_text_ua + "#" + original_effect.effect_id
                            if original_effect.effect_text and not original_effect.effect_type == "Item":
                                effect_text_ua = effect_text_ua + ": TRANSLATE"
                            effects_ua_text.append(effect_text_ua)

                    effects_text = '\n'.join(map(lambda x: str(x), item.effects)).replace('"', '""') if item.effects else ''
                    # effects_ua_text = '\n'.join(map(lambda x: str(x), item.effects_ua)).replace('"', '""') if item.effects_ua else ''
                    effects_ua_text = '\n'.join(effects_ua_text).replace('"', '""') #if pretranslation else ''
                    f.write(f'{item.id}\t{item.name}\t{item_name_ua}\t"{effects_text}"\t"{effects_ua_text}"\t\t{item.expansion}\n')
                    count += 1
        if count > 0:
            print(f"Added {count} items for translation")
        if len(missing_spell_ids) > 0:
            print(f'Consider translating next {len(missing_spell_ids)} spells: {missing_spell_ids}')


def __effects_eq(effects1: list[ItemEffect], effects2: list[ItemEffect]) -> bool:
    if len(effects1) != len(effects2):
        return False
    for i in range(len(effects1)):
        if effects1[i].short_str() != effects2[i].short_str():
            return False
    return True


def apply_translations_to_data(item_data: dict[int, dict[str, ItemData]], translations: dict[int, dict[str, ItemData]]):
    for key in sorted(item_data.keys() & translations.keys()):
        for expansion in item_data[key].keys() & translations[key].keys():
            orig_item = item_data[key][expansion]
            translation = translations[key][expansion]
            if orig_item.name != translation.name:
                print(f'Warning! Original name differs for item#{key}:{expansion}:\n{__diff_fields(orig_item.name, translation.name)}')
            if not __effects_eq(orig_item.effects, translation.effects):
                orig_effects = '\n'.join(map(lambda x: x.short_str(), orig_item.effects)) if orig_item.effects else None
                translation_effects = '\n'.join(map(lambda x: x.short_str(), translation.effects)) if translation.effects else None
                print(f'Warning! Original effect differs for item#{key}:{expansion}:\n{__diff_fields(orig_effects, translation_effects)}')
            orig_item.name_ua = translation.name_ua
            orig_item.effects_ua = translation.effects_ua
            orig_item.ref = translation.ref


def __diff_fields(field1, field2):
    import difflib
    differ = difflib.Differ()
    lines1 = field1.splitlines() if field1 else []
    lines2 = field2.splitlines() if field2 else []
    diff = differ.compare(lines1, lines2)
    return '\n'.join(diff)

def compare_tsv_and_classicua(tsv_translations: dict[int, dict[str, ItemData]], classicua_translations):
    from functools import cmp_to_key
    for key in tsv_translations.keys() - classicua_translations.keys():
        print(f"Warning! Item#{key} doesn't exist in ClassicUA")
    for key in classicua_translations.keys() - tsv_translations.keys():
        print(f"Warning! Item#{key} doesn't exist in sheet")
    for key in tsv_translations.keys() & classicua_translations.keys():
        for expansion in tsv_translations[key].keys() - classicua_translations[key].keys():
            if tsv_translations[key][expansion].ref != key:
                print(f"Warning! Item#{key}:{expansion} doesn't exist in ClassicUA")
        for expansion in classicua_translations[key].keys() - tsv_translations[key].keys():
            print(f"Warning! Item#{key}:{expansion} doesn't exist in sheet")
        for expansion in tsv_translations[key].keys() & classicua_translations[key].keys():
            tsv_translation = tsv_translations[key][expansion]
            classicua_translation = classicua_translations[key][expansion]

            tsv_effects = '\n'.join(map(lambda x: x.short_str(), sorted(tsv_translation.effects_ua, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type()))))) if tsv_translation.effects_ua else None
            classicua_effects = '\n'.join(map(lambda x: x.short_str(), sorted(classicua_translation.effects_ua, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type()))))) if classicua_translation.effects_ua else None
            if tsv_translation.name_ua != classicua_translation.name_ua:
                print(f'Warning! Name translation differs for item#{key}:{expansion}:\n{__diff_fields(classicua_translation.name_ua, tsv_translation.name_ua)}')
            if tsv_effects != classicua_effects:
                print(f'Warning! Effects translation differs for item#{key}:{expansion}:\n{__diff_fields(classicua_effects, tsv_effects)}')


def __prepare_lua_str(value: str) -> str:
    return value.replace('"', r'\"').replace('\n', r'\n')

def __build_value(value: ItemEffect) -> str:
    effect_value = value.effect_text or value.effect_id
    if type(effect_value) == int:
        return f"{effect_value}"
    if type(effect_value) == str:
        return f'"{__prepare_lua_str(effect_value)}"'


def __build_values(values: list[ItemEffect]) -> str:
    if len(values) == 1:
        return __build_value(values[0])
    else:
        return '{ ' + ', '.join(map(lambda x: __build_value(x), values)) + ' }'


def convert_translations_to_lua(translations: list[ItemData], expansion: str):
    import textwrap
    path = f'output/entries/{expansion}'
    os.makedirs(path, exist_ok=True)
    with open(f'{path}/item.lua', 'w', encoding="utf-8") as output_file:
        output_file.write(textwrap.dedent("""\
        local _, addonTable = ...
        local items = {
        
        """))
        if expansion == CLASSIC:
            output_file.write(textwrap.dedent("""\
            -- [id] = {
            --     [ref]    = ID (optional),
            --     [1]      = title (optional),
            --     [desc]   = description (optional),
            --     [equip]  = text or number (spell id) for "Equip: ..." (green color) (optional)
            --     [hit]    = text or number (spell id) for "Chance on hit: ..." (green color) (optional)
            --     [use]    = text or number (spell id) for "Use: ..." (green color) (optional)
            --                supports code "{домівка}" for Hearthstone bind location
            --     [recipe_result_item] = number (item id) to show the item after the spell-recipe (optional)
            --     [flavor] = quoted text (golden color) (optional)
            --     --------
            --     note: value can be string or table (multiple strings)
            -- }
                        
            """))
        else:
            output_file.write(textwrap.dedent("""\
            -- See /entries/classic/item.lua for data format details.
                        
            """))
        for item in translations:
            if not item.name_ua and not item.effects_ua:
                continue
            desc = None
            equips = list(filter(lambda x: x.get_type() == "Equip", item.effects_ua))
            hits = list(filter(lambda x: x.get_type() == "Hit", item.effects_ua))
            uses = list(filter(lambda x: x.get_type() == "Use", item.effects_ua))
            flavor = None
            item_result = None
            ref = None
            for effect in item.effects_ua:
                if effect.get_type() == "Desc":
                    if desc is not None:
                        print(f"Warning! Double desc for item#{item.id}:{item.expansion}")
                    desc = __prepare_lua_str(effect.effect_text)
                # if effect.effect_type == "Equip":
                #     equips.append(effect.effect_text and __prepare_lua_str(effect.effect_text) or effect.effect_id)
                # if effect.effect_type == "Hit":
                #     hits.append(effect.effect_text and __prepare_lua_str(effect.effect_text) or effect.effect_id)
                # if effect.effect_type == "Use":
                #     uses.append(effect.effect_text and __prepare_lua_str(effect.effect_text) or effect.effect_id)
                if effect.get_type() == "Flavor":
                    if flavor is not None:
                        print(f"Warning! Double flavor for item#{item.id}:{item.expansion}")
                    flavor = __prepare_lua_str(effect.effect_text)
                if effect.get_type() == "Item":
                    if item_result is not None:
                        print(f"Warning! Double item_result for item#{item.id}:{item.expansion}")
                    item_result = effect.effect_id
                if effect.get_type() == "Ref":
                    if ref is not None:
                        print(f"Warning! Double ref for item#{item.id}:{item.expansion}")
                    ref = effect.effect_id

            if item.id == ref:  # Manually set to preserve translation from previous expansion
                continue

            translation_strs = list()
            if item.name_ua:
                translation_strs.append(f'"{__prepare_lua_str(item.name_ua)}"')
            if desc:
                translation_strs.append(f'desc="{desc}"')
            if equips:
                translation_strs.append(f'equip={__build_values(equips)}')
            if hits:
                translation_strs.append(f'hit={__build_values(hits)}')
            if uses:
                translation_strs.append(f'use={__build_values(uses)}')
            if flavor:
                translation_strs.append(f'flavor="{flavor}"')
            if item_result:
                translation_strs.append(f'recipe_result_item={item_result}')
            if ref:
                translation_strs.append(f'ref={ref}')

            translation_strs.append(f'en="{__prepare_lua_str(item.name)}"')
            translation_str = ", ".join(translation_strs)

            output_file.write('[{}] = {{ {} }},\n'.format(item.id, translation_str))

        output_file.write(textwrap.dedent("""\
        }

        if addonTable.item then
            for k, v in pairs(items) do addonTable.item[k] = v end
        else
            addonTable.item = items
        end
        """))


def convert_translations_to_entries(all_translations: dict[int, dict[str, ItemData]]):
    grouped_translations: dict[str, list[ItemData]] = dict()
    for key in sorted(all_translations.keys()):
        for expansion, translation in all_translations[key].items():
            if not (expansion) in grouped_translations:
                grouped_translations[expansion] = list()
            grouped_translations[expansion].append(translation)

    for expansion, translations_group in grouped_translations.items():
        convert_translations_to_lua(translations_group, expansion)


def __validate_template(orig_effect: ItemEffect, ua_effect: ItemEffect):
    pass


def __validate_item(item: ItemData):
    import re
    from functools import cmp_to_key
    if (not item.effects or not item.effects_ua
            or item.effects_ua[0].get_type() == 'Ref'
            or item.effects[0].get_type() == 'Rune'):
        return
    orig_effects = list(filter(lambda x: x.get_type() in ['Use', 'Equip', 'Hit', 'Flavor'], sorted(item.effects, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type())))))
    ua_effects = list(filter(lambda x: x.get_type() in ['Use', 'Equip', 'Hit', 'Flavor'], sorted(item.effects_ua, key=cmp_to_key(lambda x, y: EFFECT_TYPES.index(x.get_type()) - EFFECT_TYPES.index(y.get_type())))))
    if len(orig_effects) != len(ua_effects):
        print(f"Warning! Effects count doesn't match for item#{item.id}:{item.expansion}")
    # TODO: return validations
    # else:
    #     for i in range(len(orig_effects)):
    #         ua_effect = ua_effects[i]
    #         orig_effect = orig_effects[i]
    #
    #         if (ua_effect.get_type() != orig_effect.get_type()
    #                 and item.id not in [203992, 206384, 216738, 216740, 216744, 216745, 216746, 216747, 216748, 216764, 216767, 216768, 216769, 216770, 216771, 221978, 223163]):
    #             print(f'Warning! Effect type differs for item#{item.id}:{item.expansion}[{i}]')
    #         if ua_effect.effect_text:
    #             if '#' in ua_effect.effect_text:
    #                 __validate_template(orig_effect, ua_effect)
    #             else:
    #                 if (set(re.findall(r'\d+', orig_effect.effect_text)) != set(re.findall(r'\d+', ua_effect.effect_text))
    #                         and item.id not in [744, 10725, 11808, 11819, 12794, 19883, 203784, 203785, 203786, 203787, 204688, 204689, 204690, 207106, 207107, 207108, 207109, 208035, 208036, 208037, 208038, 208213, 208215, 208218, 208219, 208601, 208602, 208603, 208604, 213701, 213709, 215461, 221307]):
    #                     print(f"Warning! Numbers don't match for item#{item.id}:{item.expansion}[{i}]")



def validate_translations(items: dict[int, dict[str, ItemData]]):
    for key in sorted(items.keys()):
        for item in items[key].values():
            __validate_item(item)
    # check templates
    ## warning - No templates for raw values
    # check references
    # check if item was updated in next expansion but has no translation



def validate_spell_references(items: dict[int, dict[str, ItemData]], spells: dict[int, dict[str, SpellData]]):
    used_spell_references = set()
    for key in sorted(items.keys()):
        for item in items[key].values():
            if item.effects_ua:
                for item_effect in item.effects_ua:
                    if item_effect.effect_type not in ['Item', 'Ref'] and item_effect.effect_id:
                        used_spell_references.add(item_effect.effect_id)

    translated_spell_ids = set()
    for key in sorted(spells.keys()):
        for spell in spells[key].values():
            if spell.name_ua or spell.description_ua or spell.aura_ua or spell.ref:
                translated_spell_ids.add(spell.id)

    # print(f'Used spell references ({len(translated_spell_ids & used_spell_references)}): {sorted(translated_spell_ids & used_spell_references)}')
    print(f'Missing spell references ({len(used_spell_references - translated_spell_ids)}): {sorted(used_spell_references - translated_spell_ids)}')


def check_feedback_items(all_items: dict[int, dict[str, ItemData]]):
    import csv
    feedback = dict()
    with open('input/missing_items.tsv', 'r', encoding='utf-8') as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            feedback[int(row[0])] = row[1]

    missed_items = list()
    for feedback_id, feedback_name in feedback.items():
        if feedback_id not in all_items:
            print(f'Warning! Feedback Item#{feedback_id} "{feedback_name}" does not exist in DB!')
            missed_items.append(feedback_id)
        else:
            translated = False
            for item in all_items[feedback_id].values():
                if item.name_ua:
                    translated = True
            if not translated:
                print(f'Warning! Feedback Item#{feedback_id} "{feedback_name}" is not translated!')
                missed_items.append(feedback_id)

    print(f'Missed IDs: {sorted(missed_items)}')

def filter_latest_untranslated(items: dict[int, dict[str, ItemData]]) -> dict[int, dict[str, ItemData]]:
    result = dict()
    for key in items.keys():
        item_by_expansion = items[key]
        expansions = sorted(list(item_by_expansion.keys()), key=lambda x: expansion_data[x][INDEX])
        if len(expansions) > 1:
            first_expansion_item = item_by_expansion[expansions[0]]
            last_expansion_item = item_by_expansion[expansions[-1]]
            if first_expansion_item.is_translated() and not last_expansion_item.is_translated():
                result[key] = dict()
                result[key][last_expansion_item.expansion] = last_expansion_item
    return result


def __book_filename(book_id, book_title):
    valid_chars = frozenset("-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return ''.join(c for c in book_title if c in valid_chars) + '_' + str(book_id)


def write_xml_book_file(path: str, book: ReadableItem):
    with open(path, mode='w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        for page_no, page_text in enumerate(book.pages, start=1):
            f.write(f'<string name="PAGE_{page_no}"><![CDATA[{page_text}]]></string>\n')
        f.write('</resources>\n')


def generate_book_sources(readable_items: dict[str, dict[int, ReadableItem]]):
    import os
    import shutil
    from pathlib import Path

    print('Generating book sources...')
    if os.path.exists('output/source_for_crowdin'):
        shutil.rmtree('output/source_for_crowdin')
    count = 0
    books_by_path: dict[str, ReadableItem] = dict()

    for expansion, items in readable_items.items():
        for item in items.values():
            if item.expansion == 'classic':
                suffix = ''
            else:
                suffix = '_' + item.expansion

            book_filename = __book_filename(item.id, item.name)
            path = f'output/source_for_crowdin/books{suffix}/{book_filename.capitalize()[:1]}/{book_filename}.xml'

            books_by_path[path] = item

    for path, book in books_by_path.items():
        Path(*Path(path).parts[:-1]).mkdir(parents=True, exist_ok=True)
        write_xml_book_file(path, book)
        count += 1

    print(f'Generated {count} book files.')


if __name__ == '__main__':
    # parse_wowhead_item_page(CLASSIC, 9328)
    # parse_wowhead_item_xml_page(CLASSIC, 18664)
##id in [18664, 20405, 18675, 16785, 17781]

    parsed_items, readable_items = retrieve_item_data()

    tsv_translations = read_translations_sheet()
    classicua_translations = read_classicua_translations(r'input\entries', parsed_items)
    compare_tsv_and_classicua(tsv_translations, classicua_translations)

    # apply_translations_to_data(parsed_items, classicua_translations)
    apply_translations_to_data(parsed_items, tsv_translations)

    save_items_to_db(parsed_items)

    validate_translations(parsed_items)

    check_feedback_items(parsed_items)

    spells = load_spells_from_db('../spells/cache/spells.db')
    # print(len(spells))
    validate_spell_references(parsed_items, spells)

    # needs_update = filter_latest_untranslated(parsed_items)
    # create_translation_sheet(needs_update, spells)
    create_translation_sheet(parsed_items, spells)

    convert_translations_to_entries(tsv_translations)

    generate_book_sources(readable_items)
    diffs, removals, additions = compare_directories('input/source_from_crowdin', 'output/source_for_crowdin')
    update_on_crowdin(diffs, removals, additions)