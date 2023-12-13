import json
import os

import requests
from bs4 import BeautifulSoup, CData

THREADS = 16
CLASSIC = 'classic'
SOD = 'sod'
TBC = 'tbc'
WRATH = 'wrath'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
XML_CACHE = 'html_cache'
ITEM_CACHE = 'item_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'

expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        XML_CACHE: 'wowhead_classic_item_xml',
        ITEM_CACHE: 'wowhead_classic_item_cache',
        METADATA_FILTERS: ('82:', '5:', '11500:'),
        IGNORES: []
    },
    SOD: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        XML_CACHE: 'wowhead_sod_item_xml',
        ITEM_CACHE: 'wowhead_sod_item_cache',
        METADATA_FILTERS: ('82:', '2:', '11500:'),
        IGNORES: []
    },
    TBC: {
        INDEX: 1,
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        XML_CACHE: 'wowhead_tbc_item_xml',
        ITEM_CACHE: 'wowhead_tbc_item_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: []
    },
    WRATH: {
        INDEX: 2,
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        XML_CACHE: 'wowhead_wrath_item_xml',
        ITEM_CACHE: 'wowhead_wrath_item_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: []
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


class ItemData:
    def __init__(self, id, expansion, name, effects=None, flavor=None, readable=None, random_enchantment=False):
        self.id = id
        self.name = name
        self.expansion = expansion
        self.effects = effects
        self.flavor = flavor
        self.readable = readable
        self.random_enchantment = random_enchantment
        self.name_ua = None


class ItemEffect:
    def __init__(self, effect_type, effect_id, effect_text, rune_spell_id=None):
        self.effect_type = effect_type
        self.effect_id = effect_id
        self.effect_text = effect_text
        self.rune_spell_id = rune_spell_id

    def __str__(self):
        res = f"{self.effect_type.replace('Chance on hit', 'Hit')}"
        res += f'#{self.effect_id}' if self.effect_id else ''
        res += f': {self.effect_text}'
        res += f'#{self.rune_spell_id}' if self.rune_spell_id else ''
        return res


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


def save_page(expansion, id):
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
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for quest #{id}')
    if (f"<error>Item not found!</error>" in r.text):
        return
    with open(xml_file_path, 'w', encoding="utf-8") as output_file:
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

    save_func = partial(save_page, expansion)
    # for id in ids:
    #     save_page(expansion, id)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_func, save_ids)


def parse_wowhead_item_page(expansion, id) -> ItemData:
    import re
    xml_path = f'cache/{expansion_data[expansion][XML_CACHE]}/{id}.xml'
    with open(xml_path, 'r', encoding="utf-8") as file:
        xml = file.read()
    soup = BeautifulSoup(xml, 'xml')

    item_name = soup.find('name').text

    tooltip = soup.find('htmlTooltip')
    tooltip_soup = BeautifulSoup(tooltip.text, 'xml')

    effects = list()
    effect_tags = tooltip_soup.find_all('span', {"class": "q2"})  # Just green text
    random_enchantment = False
    readable = False
    for effect_tag in effect_tags:
        if effect_tag.text == 'Random enchantment':
            random_enchantment = True
            continue
        if effect_tag.text == 'Right Click to Read':
            readable = True
            continue
        if effect_tag.text == 'Right Click to Open':
            continue
        full_effect_text = effect_tag.text
        effect_type = full_effect_text[:full_effect_text.find(':')]
        a_tag = effect_tag.find('a')
        if a_tag:
            internal_a_tag = a_tag.find('a')
            if internal_a_tag:
                # For runes
                if expansion != SOD:
                    print(f'Warning! Rune-like effect outside SOD for item #{id}!')
                effect_spell_id = re.findall(r'spell=(\d+)', a_tag.get('href'))[0]
                effect_text = internal_a_tag.text
                rune_spell_id = re.findall(r'spell=(\d+)', internal_a_tag.get('href'))[0]
                effects.append(ItemEffect(effect_type, effect_spell_id, effect_text, rune_spell_id))
                pass
            else:
                effect_text = a_tag.text
                effect_link = a_tag.get('href')
                if '/item=' in effect_link:  # recipes for green items
                    continue
                effect_spell_id = re.findall(r'/spell=(\d+)', effect_link)[0]
                effects.append(ItemEffect(effect_type, effect_spell_id, effect_text))
        else:
            effects.append(ItemEffect(effect_type, None, full_effect_text[full_effect_text.find(':')+2:]))


    flavor = None
    flavor_tags = tooltip_soup.find_all('span', {"class": "q"})
    for flavor_tag in flavor_tags:
        if flavor_tag.find('br') or flavor_tag.find('a'):
            # There is another span with same class. It contains item level, damage, durability, etc
            continue
        if flavor:
            print(f'Warning! Setting flavor text more than one time for item #{id}')
        flavor = flavor_tag.text

    item_class_id = soup.find('class').get('id')
    if readable and item_class_id == 12:
        print(f'Check readability of item#{id}')

    return ItemData(id, expansion, item_name, effects, flavor, readable, random_enchantment)


def parse_wowhead_pages(expansion, metadata: dict[int, ItemMD]) -> dict[int, ItemData]:
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
        # wowhead_items = {id: parse_wowhead_item_page(expansion, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_item_page, expansion)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_items = p.map(parse_func, metadata.keys())
        wowhead_items = {item.id: item for item in wowhead_items}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_items, f)

    # wowhead_item_data = merge_quests_and_metadata(wowhead_items, metadata)

    # return wowhead_quest_entities
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


def save_items_to_db(items: dict[int, ItemData]):
    import sqlite3
    print('Saving objects to DB')
    conn = sqlite3.connect('cache/items.db')
    conn.execute('DROP TABLE IF EXISTS items')
    conn.execute('''CREATE TABLE items (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        name_ua TEXT,
                        effects TEXT,
                        flavor TEXT,
                        random_enchantment BOOL,
                        readable BOOL
                )''')
    conn.commit()
    with (conn):
        for key, item in items.items():
            if ('OLD' in item.name or
                'DEP' in item.name or
                '[PH]' in item.name or
                '(old)' in item.name or
                '(old2)' in item.name or
                'QATest' in item.name or
                key in expansion_data[item.expansion][IGNORES]):
                    continue
            item_effects = '\n'.join(map(lambda x: str(x), item.effects)) if item.effects else None
            conn.execute('INSERT INTO items(id, expansion, name, name_ua, effects, flavor, random_enchantment, readable) VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                        (item.id, item.expansion, item.name, item.name_ua, item_effects, item.flavor, item.random_enchantment, item.readable))


def populate_cache_db_with_items_data():
    wowhead_metadata = get_wowhead_items_metadata(CLASSIC)
    wowhead_metadata_sod = get_wowhead_items_metadata(SOD)
    wowhead_metadata_tbc = get_wowhead_items_metadata(TBC)
    wowhead_metadata_wrath = get_wowhead_items_metadata(WRATH)

    save_xmls_from_wowhead(CLASSIC, set(wowhead_metadata.keys()))
    save_xmls_from_wowhead(SOD, set(wowhead_metadata_sod.keys()))
    save_xmls_from_wowhead(TBC, set(wowhead_metadata_tbc.keys()))
    save_xmls_from_wowhead(WRATH, set(wowhead_metadata_wrath.keys()))

    wowhead_items = parse_wowhead_pages(CLASSIC, wowhead_metadata)
    wowhead_items_sod = parse_wowhead_pages(SOD, wowhead_metadata_sod)
    wowhead_items_tbc = parse_wowhead_pages(TBC, wowhead_metadata_tbc)
    wowhead_items_wrath = parse_wowhead_pages(WRATH, wowhead_metadata_wrath)

    translations = load_item_lua_names('input/entries/item.lua')
    translations_sod = load_item_lua_names('input/entries/item_sod.lua')

    for key in wowhead_items.keys() & translations.keys():
        wowhead_items[key].name_ua = translations[key]

    for key in wowhead_items_sod.keys() & translations_sod.keys():
        wowhead_items_sod[key].name_ua = translations_sod[key]
    #
    # questie_item_ids = load_questie_item_lua_ids()
    #
    # for key in questie_item_ids:
    #     if not wowhead_items[key].name_ua:
    #         wowhead_items[key].name_ua = 'questie'


    # print('Merging with TBC')
    # classic_and_tbc_items = merge_expansions(wowhead_items, wowhead_items_tbc)
    # print('Merging with WotLK')
    # all_items = merge_expansions(classic_and_tbc_items, wowhead_items_wrath)

    save_items_to_db({**wowhead_items, **wowhead_items_sod})



if __name__ == '__main__':
    populate_cache_db_with_items_data()

    # item = parse_wowhead_item_page(SOD, 204795)
    # item = parse_wowhead_item_page(CLASSIC, 22691)
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