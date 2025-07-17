import os

import requests
from bs4 import BeautifulSoup

from generation.utils.utils import compare_directories, update_on_crowdin

THREADS = os.cpu_count() // 2
CLASSIC = 'classic'
SOD = 'sod'
SOD_PTR = 'sod_ptr'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
OBJECT_CACHE = 'object_cache'
IGNORES = 'ignores'
FORCE_DOWNLOAD = 'force_download'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'

expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_html',
        OBJECT_CACHE: 'wowhead_classic_object_cache',
        METADATA_FILTERS: ('6:', '5:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    SOD: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_html',
        OBJECT_CACHE: 'wowhead_sod_object_cache',
        METADATA_FILTERS: ('6:', '2:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    TBC: {
        INDEX: 1,
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_html',
        OBJECT_CACHE: 'wowhead_tbc_object_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    WRATH: {
        INDEX: 2,
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_html',
        OBJECT_CACHE: 'wowhead_wrath_object_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: []
    },
    CATA: {
        INDEX: 3,
        WOWHEAD_URL: 'https://www.wowhead.com/cata',
        METADATA_CACHE: 'wowhead_cata_metadata_cache',
        HTML_CACHE: 'wowhead_cata_html',
        OBJECT_CACHE: 'wowhead_cata_object_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [ ]
    }
}

class ObjectData:
    def __init__(self, id, expansion, name, type=None, text: list[str] = []):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.type = type
        self.text = text

    def get_type_str(self) -> str:
        if self.type is None:
            return 'Unknown'
        if self.type == -9:
            return 'interactive-objects'
        if self.type == -8:
            return 'treasures'
        if self.type == -7:
            return 'archaeology'
        if self.type == -6:
            return 'tools'
        if self.type == -5:
            return 'chests'
        if self.type == -4:
            return 'mineral-veins'
        if self.type == -3:
            return 'herbs'
        if self.type == -2:
            return 'quests'
        elif self.type == 3:
            return 'containers'
        elif self.type == 9:
            return 'books'
        elif self.type == 19:
            return 'mailboxes'
        elif self.type == 25:
            return 'fishing-pools'
        elif self.type == 45:
            return 'garrison-shipments'
        elif self.type == 50:
            return 'shared-containers'
        else:
            return f'Unknown({self.type})'


def __get_wowhead_search(expansion, start, end=None) -> list[ObjectData]:
    import json
    base_url = expansion_data[expansion][WOWHEAD_URL]
    metadata_filters = expansion_data[expansion][METADATA_FILTERS]
    if end:
        url = base_url + f"/objects?filter={metadata_filters[0]}15:15;{metadata_filters[1]}2:5;{metadata_filters[2]}{start}:{end}"
    else:
        url = base_url + f"/objects?filter={metadata_filters[0]}15;{metadata_filters[1]}2;{metadata_filters[2]}{start}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    pre_script_div = soup.find('div', id='lv-objects')
    if not pre_script_div:
        return []
    script_tag = pre_script_div.next_element
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('new Listview(') + 13
        start = script_content.find('"data":[', start) + 7
        end = script_content.rfind('}],"') + 2
        json_data = script_content[start:end]
        return list(map(lambda md: ObjectData(id=md.get('id'),
                                              expansion=expansion,
                                              name=md.get('name').strip(),
                                              type=md.get('type')),
                        json.loads(json_data)))
    else:
        return []


def __retrieve_objects_metadata_from_wowhead(expansion) -> dict[int, ObjectData]:
    objects_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            objects = __get_wowhead_search(expansion, start)
            print(f'Checking {start}+. Len: {len(objects)}')
            if len(objects) < 1000:
                objects_metadata.extend(objects)
                break
        objects = __get_wowhead_search(expansion, start, start + 1000)
        objects_metadata.extend(objects)
        i += 1
    return {md.id: md for md in objects_metadata}


def get_wowhead_object_metadata(expansion) -> dict[int, ObjectData]:
    import pickle
    cache_file_name = expansion_data[expansion][METADATA_CACHE]
    if os.path.exists(f'cache/tmp/{cache_file_name}.pkl'):
        print(f'Loading cached Wowhead({expansion}) metadata')
        with open(f'cache/tmp/{cache_file_name}.pkl', 'rb') as f:
            wowhead_metadata = pickle.load(f)
    else:
        print(f'Retrieving Wowhead({expansion}) metadata')
        wowhead_metadata = __retrieve_objects_metadata_from_wowhead(expansion)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/{cache_file_name}.pkl', 'wb') as f:
            pickle.dump(wowhead_metadata, f)
    return wowhead_metadata


def save_html_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/object={id}'
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


def save_htmls_from_wowhead(expansion, ids: set[int]):
    from functools import partial
    import multiprocessing
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}'

    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'HTML cache for all Wowhead({expansion}) objects ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    print(f'Saving HTMLs for {len(save_ids)} of {len(ids)} objects from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    # for id in save_ids:
    #     print("Saving XML for item #" + str(id))
    #     save_page(expansion, id)
    save_func = partial(save_html_page, expansion)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_func, save_ids)


def parse_wowhead_page(expansion, id) -> ObjectData:
    import json5
    import re
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()

    # soup = BeautifulSoup(html, 'html.parser')
    soup = BeautifulSoup(html, 'html5lib')
    name = soup.find('h1').text

    for item in html.split("\n"):
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

            return ObjectData(id=id, expansion=expansion, name=name, text=list(pages))

    return ObjectData(id=id, expansion=expansion, name=name)


def parse_wowhead_pages(expansion, metadata: dict[int, ObjectData]) -> dict[int, ObjectData]:
    import pickle
    import multiprocessing
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][OBJECT_CACHE]}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) spells')
        with open(cache_path, 'rb') as f:
            wowhead_objects = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) objects')
        # wowhead_objects = {id: parse_wowhead_page(expansion, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_page, expansion)
        with multiprocessing.Pool(THREADS) as p:
            wowhead_objects = p.map(parse_func, metadata.keys())
        wowhead_objects = {spell.id: spell for spell in wowhead_objects}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_objects, f)

    return wowhead_objects


def merge_object(id: int, old_objects: dict[str, ObjectData], new_object: ObjectData) -> dict[str, ObjectData]:
    if len(old_objects) > 1:
        last_old_object_key = list(old_objects.keys())[-1]
        result = merge_object(id, {last_old_object_key: old_objects[last_old_object_key]}, new_object)
        del old_objects[last_old_object_key]
        return {**old_objects, **result}
    if len(old_objects) == 1:
        old_object = next(iter(old_objects.values()))

        if old_object.name.lower() != new_object.name.lower():
            return {**old_objects, **{new_object.expansion: new_object}}

        if old_object.text != new_object.text:
            if old_object.text and new_object.text:
                print(f'Texts differ for object #{id}')
            return {**old_objects, **{new_object.expansion: new_object}}

        return old_objects
    else:
        print(f'Skip: Object #{id} instance number unexpected')


def merge_expansions(old_expansion: dict[int, dict[str, ObjectData]], new_expansion: dict[int, ObjectData]) -> dict[int, dict[str, ObjectData]]:
    result = dict()

    for id in old_expansion.keys() - new_expansion.keys():
        result[id] = old_expansion[id]

    for id in new_expansion.keys() - old_expansion.keys():
        result[id] = dict()
        result[id][new_expansion[id].expansion] = new_expansion[id]

    for id in sorted(old_expansion.keys() & new_expansion.keys()):
        result[id] = merge_object(id, old_expansion[id], new_expansion[id])
    return result


def fix_expansion_objects(expansion, objects: dict[int, ObjectData]):
    ## Known valid diffs
    # Texts differ for object #25329
    # Texts differ for object #177199

    if expansion == CLASSIC:
        objects[25330].text[0] = objects[25330].text[0].replace("By Blood and Honor We Serve. ", "By Blood and Honor We Serve.")
        objects[25331].text[0] = objects[25331].text[0].replace("most beloved of our kin. ", "most beloved of our kin.")
        objects[25332].text[0] = objects[25332].text[0].replace("drenched with the blood of heroes. ", "drenched with the blood of heroes.")
        objects[25333].text[0] = objects[25333].text[0].replace("Presumed deceased. ", "Presumed deceased.").replace("Wherever you are. ", "Wherever you are.")
        objects[175748].text[2] = objects[175748].text[2].replace("of the Azeroth", "of Azeroth").replace("to sew chaos", "to sow chaos")

    if expansion == TBC:
        objects[175748].text[2] = objects[175748].text[2].replace("of the Azeroth", "of Azeroth").replace("to sew chaos", "to sow chaos")

    if expansion == WRATH:
        objects[175748].text[2] = objects[175748].text[2].replace("of the Azeroth", "of Azeroth").replace("to sew chaos", "to sow chaos")
        objects[191663].text[3] = objects[191663].text[3].replace(" \n\n\n\n", "\n\n\n")

    if expansion in [CLASSIC, TBC, WRATH, CATA]:
        objects[179706].text[0] = objects[179706].text[0].replace(
            'with the ranks of each listed in descending order from highest to lowest. Long live the Alliance!',
            'with the ranks\nof each listed in descending order from highest to lowest.\nLong live the Alliance!')
        objects[179707].text[0] = objects[179707].text[0].replace(
            'As is fitting, the strongest are listed at the top, with the weaker listed below them.',
            'As is\nfitting, the strongest are listed at the top, with the weaker\nlisted below them.')


def merge_metadata(expansion, wowhead_objects, wowhead_md):

    absent_in_md = wowhead_objects.keys() - wowhead_md.keys()
    if absent_in_md:
        print(f'Warning! Wowhead({expansion}) objects {absent_in_md} not present in metadata.')

    absent_in_objects = wowhead_md.keys() - wowhead_objects.keys()
    if absent_in_objects:
        print(f'Warning! Wowhead({expansion}) metadata {absent_in_objects} not present in objects.')

    for id in sorted(wowhead_objects.keys() & wowhead_md.keys()):
        if wowhead_objects[id].name.lower() != wowhead_md[id].name.lower():
            print(f'Warning! Wowhead({expansion}) object #{id} name mismatch: '
                  f'"{wowhead_objects[id].name}" vs "{wowhead_md[id].name}"')
        wowhead_objects[id].type = wowhead_md[id].type


def fix_objects(all_objects):
    all_objects[175755][CLASSIC] = all_objects[175755][SOD]
    all_objects[175755][CLASSIC].expansion = CLASSIC
    del all_objects[175755][SOD]


def retrieve_object_data() -> dict[int, dict[str, ObjectData]]:
    all_objects = dict()
    for expansion, expansion_properties in expansion_data.items():
        wowhead_md = get_wowhead_object_metadata(expansion)
        save_htmls_from_wowhead(expansion, set(wowhead_md.keys()))
        wowhead_objects = parse_wowhead_pages(expansion, wowhead_md)
        merge_metadata(expansion, wowhead_objects, wowhead_md)
        print(f'Merging with {expansion}')
        fix_expansion_objects(expansion, wowhead_objects)
        all_objects = merge_expansions(all_objects, wowhead_objects)

    fix_objects(all_objects)

    return all_objects


def save_objects_to_db(objects: dict[int, dict[str, ObjectData]]):
    import sqlite3
    print('Saving objects to DB')
    conn = sqlite3.connect('cache/objects.db')
    conn.execute('DROP TABLE IF EXISTS objects')
    conn.execute('''CREATE TABLE objects (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        name_ua TEXT,
                        text_pages INT,
                        type TEXT
                )''')
    conn.commit()
    with (conn):
        for key in objects.keys():
            for expansion, object in objects[key].items():
                conn.execute('INSERT INTO objects(id, expansion, name, name_ua, text_pages, type) VALUES(?, ?, ?, ?, ?, ?)',
                            (object.id, object.expansion, object.name, None, len(object.text), object.get_type_str()))


def __object_filename(book_id, book_title):
    valid_chars = frozenset("-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return ''.join(c for c in book_title if c in valid_chars) + '_' + str(book_id)


def write_xml_object_file(path: str, object: ObjectData):
    with open(path, mode='w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        for page_no, page_text in enumerate(object.text, start=1):
            f.write(f'<string name="PAGE_{page_no}"><![CDATA[{page_text}]]></string>\n')
        f.write('</resources>\n')


def generate_crowdin_sources(readable_objects: dict[int, dict[str, ObjectData]]):
    import os
    import shutil
    from pathlib import Path

    print('Generating objects sources...')
    if os.path.exists('output/source_for_crowdin'):
        shutil.rmtree('output/source_for_crowdin')
    count = 0
    objects_by_path: dict[str, ObjectData] = dict()

    for item_id, items in readable_objects.items():
        for item in items.values():
            if not item.text:
                continue
            if item.expansion == 'classic':
                suffix = ''
            else:
                suffix = '_' + item.expansion

            object_filename = __object_filename(item.id, item.name)
            path = f'output/source_for_crowdin/objects{suffix}/{object_filename.capitalize()[:1]}/{object_filename}.xml'

            objects_by_path[path] = item

    for path, book in objects_by_path.items():
        Path(*Path(path).parts[:-1]).mkdir(parents=True, exist_ok=True)
        write_xml_object_file(path, book)
        count += 1

    print(f'Generated {count} book files.')



if __name__ == '__main__':
    all_objects = retrieve_object_data()

    save_objects_to_db(all_objects)

    generate_crowdin_sources(all_objects)
    diffs, removals, additions = compare_directories('input/source_from_crowdin', 'output/source_for_crowdin')
    update_on_crowdin(diffs, removals, additions)
