import os

import requests
import multiprocessing

from bs4 import BeautifulSoup


THREADS = 16
WOWDB = 'WOWDB'
CLASSICDB = 'CLASSICDB'
EVOWOW = 'EVOWOW'
TWINHEAD = 'TWINSTAR'
WARCRAFTDB = 'WARCRAFTDB'
WOWHEAD = 'WOWHEAD'
URL = 'URL'
HTML_FOLDER = 'HTML_FOLDER'
ZONES_CACHE = 'ZONES_CACHE'

sources = {
    WOWDB: {
        URL: 'https://www.wowdb.com',
        HTML_FOLDER: 'cache/wowdb_zone_htmls',
        ZONES_CACHE: 'cache/tmp/wowdb_zone_cache.pkl'
    },
    CLASSICDB: {
        URL: 'https://classicdb.ch',
        HTML_FOLDER: 'cache/classicdb_zone_htmls',
        ZONES_CACHE: 'cache/tmp/classicdb_zone_cache.pkl'
    },
    EVOWOW: {  # Actually it's a private server, but it's at least limited with Wrath content
        URL: 'https://wotlk.evowow.com',
        HTML_FOLDER: 'cache/evowow_zone_htmls',
        ZONES_CACHE: 'cache/tmp/evowow_zone_cache.pkl'
    },
    TWINHEAD: {  # Actually it's a private server, but it's at least limited with Wrath content
        URL: 'https://cata-twinhead.twinstar.cz/',
        HTML_FOLDER: 'cache/twinhead_zone_htmls',
        ZONES_CACHE: 'cache/tmp/twinhead_zone_cache.pkl'
    },
    WARCRAFTDB: {  # Actually it's a private server, but it's at least limited with Wrath content
        URL: 'https://warcraftdb.com/cataclysm',
        HTML_FOLDER: 'cache/warcraftdb_zone_htmls',
        ZONES_CACHE: 'cache/tmp/warcraftdb_zone_cache.pkl'
    },
    WOWHEAD: {
        URL: 'https://www.wowhead.com/cata'
    }
}
IGNORES = [5, 30, 49, 81, 82, 83, 84, 471, 472, 473, 500, 877, 926, 1218, 1518, 2037, 2159, 2238, 2239, 2280, 2877,
           3428, 3695, 3817, 3941, 3948, 3995, 4072, 4076, 4096, 4471, 4602, 4621, 4688, 4774, 5311, 5894, 5895, 14284,
           14285, 14286, 14287]

CATEGORIES = {
    "Northrend": "Нортренд",
    "dungeon": "підземелля",
    "raid": "рейд",
    "battleground": "поле битви",
    "Eastern Kingdoms": "Східні Королівства",
    "Kalimdor": "Калімдор",
    "Outland": "Позамежжя",
    "arena": "арена",
}

class WowheadZone:
    def __init__(self, id, name, category=None, expansion=None, instance=None, territory=None):
        self.id = id
        self.name = name
        self.category = category
        self.expansion = expansion
        self.instance = instance
        self.territory = territory

    def __str__(self):
        return f'{self.id},"{self.name}"'

    def get_category(self) -> str:
        if self.category == 0:
            return 'Eastern Kingdoms'
        if self.category == 1:
            return 'Kalimdor'
        elif self.category == 2:
            return 'dungeon'
        elif self.category == 3:
            return 'raid'
        elif self.category == 6:
            return 'battleground'
        elif self.category == 8:
            return 'Outland'
        elif self.category == 9:
            return 'arena'
        elif self.category == 10:
            return 'Northrend'
        else:
            None

    def get_expansion(self) -> str:
        if self.expansion is None:
            return 'classic'
        elif self.expansion == 1:
            return 'tbc'
        elif self.expansion == 2:
            return 'wrath'
        elif self.expansion == 3:
            return 'cata'
        else:
            return 'unknown'


class Zone:
    def __init__(self, id, name, parent_zone=None, translation=None, expansion=None, category=None, source=None):
        self.id = id
        self.name = name
        self.parent_zone = parent_zone
        self.translation = translation
        self.expansion = expansion
        self.category = category
        self.source = source

    def __str__(self):
        res = ''
        res += f'#{self.id}'
        res += f':{self.expansion} ' if self.expansion else ' '
        res += f'{self.parent_zone}/' if self.parent_zone else ''
        res += self.name
        res += f' -> {self.translation}' if self.translation else ''
        return res


def save_wowdb_zone_page(id) -> str:
    if os.path.exists(f'{sources[WOWDB][HTML_FOLDER]}/{id}.html'):
        return
    url = sources[WOWDB][URL] + f'/zones/{id}'
    r = requests.get(url)
    with open(f'{sources[WOWDB][HTML_FOLDER]}/{id}.html', 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)

def save_wowdb_zones_htmls():
    ids = range(1, 10000)
    os.makedirs(sources[WOWDB][HTML_FOLDER], exist_ok=True)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_wowdb_zone_page, ids)

def save_classicdb_zone_page(id) -> str:
    if os.path.exists(f'{sources[CLASSICDB][HTML_FOLDER]}/{id}.html'):
        return
    url = sources[CLASSICDB][URL] + f'/?zone={id}'
    r = requests.get(url)
    with open(f'{sources[CLASSICDB][HTML_FOLDER]}/{id}.html', 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)

def save_classicdb_zones_htmls():
    ids = range(1, 10000)
    os.makedirs(sources[CLASSICDB][HTML_FOLDER], exist_ok=True)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_classicdb_zone_page, ids)


def save_evowow_zone_page(id) -> str:
    if os.path.exists(f'{sources[EVOWOW][HTML_FOLDER]}/{id}.html'):
        return
    url = sources[EVOWOW][URL] + f'/?zone={id}'
    r = requests.get(url)
    with open(f'{sources[EVOWOW][HTML_FOLDER]}/{id}.html', 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)

def save_evowow_zones_htmls():
    ids = range(1, 10000)
    os.makedirs(sources[EVOWOW][HTML_FOLDER], exist_ok=True)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_evowow_zone_page, ids)


def save_twinhead_zone_page(id) -> str:
    # if os.path.exists(f'{sources[TWINHEAD][HTML_FOLDER]}/{id}.html'):
    #     return
    url = sources[TWINHEAD][URL] + f'/?zone={id}'
    r = requests.get(url)
    if 'Sorry, you have been blocked' in r.text:
        print('CloudFlare')
    with open(f'{sources[TWINHEAD][HTML_FOLDER]}/{id}.html', 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)

def save_twinhead_zones_htmls():
    ids = range(1, 10000)
    os.makedirs(sources[TWINHEAD][HTML_FOLDER], exist_ok=True)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_twinhead_zone_page, ids)


def save_warcraftdb_zone_page(id) -> str:
    # if os.path.exists(f'{sources[TWINHEAD][HTML_FOLDER]}/{id}.html'):
    #     return
    url = sources[WARCRAFTDB][URL] + f'/zone/{id}'
    r = requests.get(url)
    if not r.ok:
        print(f'Not OK for {id}!')
        return
    with open(f'{sources[WARCRAFTDB][HTML_FOLDER]}/{id}.html', 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)

def save_warcraftdb_zones_htmls():
    ids = range(1, 10000)
    os.makedirs(sources[WARCRAFTDB][HTML_FOLDER], exist_ok=True)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_warcraftdb_zone_page, ids)
    # for id in ids:
    #     save_warcraftdb_zone_page(id)


def parse_wowdb_zone_page(file_name) -> (int, str):
    id = int(file_name.removesuffix(".html"))
    html_path = f'{sources[WOWDB][HTML_FOLDER]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html5lib')

    zone_name_tag = soup.find('h2', class_='header')
    if zone_name_tag:
        return (id, zone_name_tag.text)

    return None


def parse_wowdb_zone_pages() -> dict[int, str]:
    import pickle
    cache_path = sources[WOWDB][ZONES_CACHE]
    if os.path.exists(cache_path):
        print(f'Loading cached WOWDB zones')
        with open(cache_path, 'rb') as f:
            wowdb_zones = pickle.load(f)
    else:
        print(f'Parsing WOWDB zones')
        with multiprocessing.Pool(THREADS) as p:
            wowdb_zones = p.map(parse_wowdb_zone_page, os.listdir(sources[WOWDB][HTML_FOLDER]))

        # wowdb_zones = []
        # for file_name in os.listdir(sources[WOWDB][HTML_FOLDER])[:100]:
        #     wowdb_zones.append(parse_wowdb_zone_page(file_name))

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowdb_zones, f)

    return {zone[0]: zone[1:] for zone in wowdb_zones if zone}


def parse_classicdb_zone_page(file_name) -> (int, str):
    id = int(file_name.removesuffix(".html"))
    html_path = f'{sources[CLASSICDB][HTML_FOLDER]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html5lib')
    zone_name = soup.find_all('h1')[1].text

    if zone_name == '':
        return None

    for link in soup.find_all('a', href=True):
        if link['href'].startswith('?zone='):
            zone_parent = link.text
            return (id, zone_name, zone_parent)

    return (id, zone_name)


def parse_classicdb_zone_pages() -> dict[int, str]:
    import pickle
    cache_path = sources[CLASSICDB][ZONES_CACHE]
    if os.path.exists(cache_path):
        print(f'Loading cached CLASSICDB zones')
        with open(cache_path, 'rb') as f:
            classicdb_zones = pickle.load(f)
    else:
        print(f'Parsing CLASSICDB zones')
        with multiprocessing.Pool(THREADS) as p:
            classicdb_zones = p.map(parse_classicdb_zone_page, os.listdir(sources[CLASSICDB][HTML_FOLDER]))

        # classicdb_zones = []
        # for file_name in os.listdir(sources[CLASSICDB][HTML_FOLDER]):
        #     classicdb_zones.append(parse_classicdb_zone_page(file_name))

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(classicdb_zones, f)

    return {zone[0]: zone[1:] for zone in classicdb_zones if zone}


def parse_evowow_zone_page(file_name) -> (int, str):
    import re
    id = int(file_name.removesuffix(".html"))
    html_path = f'{sources[EVOWOW][HTML_FOLDER]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()

    if "This zone doesn't exist." in html:
        return None

    soup = BeautifulSoup(html, 'html5lib')
    zone_name = soup.find_all('h1')[1].text

    match = re.search(r'This zone is part of [zone=(\d+)]', html)
    if match:
        parent_zone_id = int(match.group(1))
        return (id, zone_name, parent_zone_id)

    return (id, zone_name)


def parse_evowow_zone_pages() -> dict[int, str]:
    import pickle
    cache_path = sources[EVOWOW][ZONES_CACHE]
    if os.path.exists(cache_path):
        print(f'Loading cached EVOWOW zones')
        with open(cache_path, 'rb') as f:
            evowow_zones = pickle.load(f)
    else:
        print(f'Parsing EVOWOW zones')
        with multiprocessing.Pool(THREADS) as p:
            evowow_zones = p.map(parse_evowow_zone_page, os.listdir(sources[EVOWOW][HTML_FOLDER]))

        # zones = []
        # for file_name in os.listdir(sources[EVOWOW][HTML_FOLDER]):
        #     evowow_zones.append(parse_evowow_zone_page(file_name))

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(evowow_zones, f)

    zones_dict = {zone[0]: zone[1:] for zone in evowow_zones if zone}

    for zone_id, zone in zones_dict.items():
        if len(zone) == 2:
            zones_dict[zone_id] = (zone[0], zones_dict[zone[1]][0])

    return zones_dict


def parse_twinhead_zone_page(file_name) -> (int, str):
    import re
    id = int(file_name.removesuffix(".html"))
    html_path = f'{sources[TWINHEAD][HTML_FOLDER]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()

    if "Zone does not exist" in html:
        return None

    soup = BeautifulSoup(html, 'html5lib')
    zone_name_divs = soup.find_all('h1')
    zone_name = zone_name_divs[0].text if zone_name_divs else None

    match = re.search(r'This is an area of zone [zone=(\d+)]', html)
    if match:
        parent_zone_id = int(match.group(1))
        return (id, zone_name, parent_zone_id)

    return (id, zone_name)


def parse_twinhead_zone_pages() -> dict[int, str]:
    import pickle
    cache_path = sources[TWINHEAD][ZONES_CACHE]
    if os.path.exists(cache_path):
        print(f'Loading cached TWINHEAD zones')
        with open(cache_path, 'rb') as f:
            twinhead_zones = pickle.load(f)
    else:
        print(f'Parsing TWINHEAD zones')
        # with multiprocessing.Pool(THREADS) as p:
        #     twinhead_zones = p.map(parse_twinhead_zone_page, os.listdir(sources[TWINHEAD][HTML_FOLDER]))

        twinhead_zones = []
        for file_name in os.listdir(sources[TWINHEAD][HTML_FOLDER]):
            twinhead_zones.append(parse_twinhead_zone_page(file_name))

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(twinhead_zones, f)

    zones_dict = {zone[0]: zone[1:] for zone in twinhead_zones if zone}

    for zone_id, zone in zones_dict.items():
        if len(zone) == 2:
            zones_dict[zone_id] = (zone[0], zones_dict[zone[1]][0])

    return zones_dict


def parse_warcraftdb_zone_page(file_name) -> (int, str):
    import json
    import re
    id = int(file_name.removesuffix(".html"))
    html_path = f'{sources[WARCRAFTDB][HTML_FOLDER]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()

    if "Zone does not exist" in html:
        return None

    soup = BeautifulSoup(html, 'html5lib')
    script_content = soup.find_all('script')[1].string
    json_data = script_content[16:]
    if not json_data:
        return None
    zone_json = json.loads(json_data)

    zone_name = zone_json['dataView']['title']
    content_xml = zone_json['dataView']['content']
    soup = BeautifulSoup(content_xml, 'lxml')
    zone_name2 = soup.find('tt-item-line', {'data-line-type': 'zone-name'}).text
    if zone_name != zone_name2:
        print(f"Different names for #{id}")
    parent_zone_div = soup.find('tt-item-line', {'data-line-type': 'zone-parent'})
    if parent_zone_div:
        parent_zone_name = parent_zone_div.text.replace('Location: ', '')
        return (id, zone_name, parent_zone_name)

    return (id, zone_name)


def parse_warcraftdb_zone_pages() -> dict[int, str]:
    import pickle
    cache_path = sources[WARCRAFTDB][ZONES_CACHE]
    if os.path.exists(cache_path):
        print(f'Loading cached WARCRAFTDB zones')
        with open(cache_path, 'rb') as f:
            warcraftdb_zones = pickle.load(f)
    else:
        print(f'Parsing TWINHEAD zones')
        # with multiprocessing.Pool(THREADS) as p:
        #     warcraftdb_zones = p.map(parse_warcraftdb_zone_page, os.listdir(sources[WARCRAFTDB][HTML_FOLDER]))

        warcraftdb_zones = []
        for file_name in os.listdir(sources[WARCRAFTDB][HTML_FOLDER]):
            warcraftdb_zones.append(parse_warcraftdb_zone_page(file_name))

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(warcraftdb_zones, f)

    zones_dict = {zone[0]: zone[1:] for zone in warcraftdb_zones if zone}

    for zone_id, zone in zones_dict.items():
        if len(zone) == 2:
            zones_dict[zone_id] = (zone[0], zone[1])

    return zones_dict


def save_temp_zones_to_cache_db(wowhead: dict[int, WowheadZone], wowdb: dict[int, str], classicdb: dict[int, str], evowow: dict[int, str], warcraftdb: dict[int, str]):
    import sqlite3
    print('Saving temp zones data to cache DB')
    conn = sqlite3.connect('cache/zones.db')
    conn.execute('DROP TABLE IF EXISTS zones_temp')
    conn.execute('''CREATE TABLE zones_temp (
                        id INTEGER NOT NULL,
                        wowhead_name TEXT,
                        wowdb_name TEXT,
                        classicdb_name TEXT,
                        classicdb_parent TEXT,
                        evowow_name TEXT,
                        evowow_parent TEXT,
                        warcraftdb_name TEXT,
                        warcraftdb_parent TEXT
                )''')

    conn.commit()
    with conn:
        for key in wowdb.keys() | classicdb.keys() | evowow.keys() | warcraftdb.keys() | wowhead.keys():
            wowhead_zone = wowhead.get(key)
            wowhead_name = None
            if wowhead_zone:
                wowhead_name = wowhead_zone.name
            wowdb_name = wowdb.get(key)
            if wowdb_name:
                wowdb_name = wowdb_name[0]

            classicdb_name = None
            classicdb_parent = None
            classicdb_zone = classicdb.get(key)
            if classicdb_zone:
                classicdb_name = classicdb_zone[0]
                if len(classicdb_zone) == 2:  # Has parent id - replacing with its name
                    classicdb_parent = classicdb_zone[1]

            evowow_name = None
            evowow_parent = None
            evowow_zone = evowow.get(key)
            if evowow_zone:
                evowow_name = evowow_zone[0]
                if len(evowow_zone) == 2:  # Has parent id - replacing with its name
                    evowow_parent = evowow_zone[1]

            warcraftdb_name = None
            warcraftdb_parent = None
            warcraftdb_zone = warcraftdb.get(key)
            if warcraftdb_zone:
                warcraftdb_name = warcraftdb_zone[0]
                if len(warcraftdb_zone) == 2:  # Has parent id - replacing with its name
                    warcraftdb_parent = warcraftdb_zone[1]

            conn.execute(f'''INSERT INTO zones_temp(id, wowhead_name, wowdb_name, classicdb_name, classicdb_parent, evowow_name, evowow_parent, warcraftdb_name, warcraftdb_parent)
                                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (key, wowhead_name, wowdb_name, classicdb_name, classicdb_parent, evowow_name, evowow_parent, warcraftdb_name, warcraftdb_parent))


def read_new_translations() -> dict[str, str]:
    import csv
    all_zones = dict()
    with open('new_translations.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            if (len(row) != 2):
                print(f'check {row}')
            zone_name = row[0]
            name_ua = row[1]
            all_zones[zone_name] = name_ua
    return all_zones


def get_wowhead_zones() -> dict[int, WowheadZone]:
    import json
    url = sources[WOWHEAD][URL] + '/zones'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    script_tag = soup.find('script', type='text/javascript', src=None)
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('new Listview(') + 13
        start = script_content.find('data: [', start) + 5
        end = script_content.rfind('});')
        json_data = script_content[start:end]
        return {md.get('id'): WowheadZone(md.get('id'), md.get('name'), md.get('category'), md.get('expansion'), md.get('instance'), md.get('territory')) for md in json.loads(json_data)}
    else:
        return None


def __cleanup_name(name: str) -> str:
    import re
    result = re.sub(r'\[.*?\]|\(.*?\)', '', name)  # Remove [UNUSED], (Arena) and (Outland)
    result = result.replace('UNUSED', '')
    return result.strip()

def merge_zones(wowhead: dict[int, WowheadZone], wowdb: dict[int, str], classicdb: dict[int, str], evowow: dict[int, str], warcraftdb: dict[int, str], translated: dict[str, str]) -> dict[str, Zone]:
    added_names = set()
    merged_zones = dict()

    for zone_id in wowhead.keys() | wowdb.keys() | classicdb.keys() | evowow.keys() | warcraftdb.keys():
        if zone_id in IGNORES:
            continue
        name_set = set()
        parent_set = set()
        wowhead_zone = wowhead.get(zone_id)
        if wowhead_zone:
            name_set.add(__cleanup_name(wowhead_zone.name))

        wowdb_zone = wowdb.get(zone_id)
        if wowdb_zone:
            name_set.add(__cleanup_name(wowdb_zone[0]))

        classicdb_zone = classicdb.get(zone_id)
        if classicdb_zone:
            name_set.add(__cleanup_name(classicdb_zone[0]))
            if len(classicdb_zone) == 2:  # Has parent id - replacing with its name
                parent_set.add(__cleanup_name(classicdb_zone[1]))

        evowow_zone = evowow.get(zone_id)
        if evowow_zone:
            name_set.add(__cleanup_name(evowow_zone[0]))
            if len(evowow_zone) == 2:  # Has parent id - replacing with its name
                parent_set.add(__cleanup_name(evowow_zone[1]))

        warcraftdb_zone = warcraftdb.get(zone_id)
        if warcraftdb_zone:
            name_set.add(__cleanup_name(warcraftdb_zone[0]))
            if len(warcraftdb_zone) == 2:  # Has parent id - replacing with its name
                parent_set.add(__cleanup_name(warcraftdb_zone[1]))

        if len(name_set) < 1:
            print(f'! No name for id #{zone_id}')
            continue

        if len(parent_set) > 1:
            print(f'! Parent name differs for id #{zone_id}: {str(parent_set)}')  # 0
            continue

        parent_name = None
        if len(parent_set) == 1:
            parent_name = next(iter(parent_set))

        for zone_name in name_set.copy():
            if 'UNUSED' in zone_name.upper() or '***' in zone_name:
                name_set.remove(zone_name)
                continue

            sources = []
            if wowhead_zone and zone_name == __cleanup_name(wowhead_zone.name):
                sources.append('wowhead')
            if wowdb_zone and zone_name == __cleanup_name(wowdb_zone[0]):
                sources.append('wowdb')
            if classicdb_zone and zone_name == __cleanup_name(classicdb_zone[0]):
                sources.append('classicdb')
            if evowow_zone and zone_name == __cleanup_name(evowow_zone[0]):
                sources.append('evowow')
            if warcraftdb_zone and zone_name == __cleanup_name(warcraftdb_zone[0]):
                sources.append('warcraftdb')

            translated_name = None
            if translated.get(zone_name):
                translated_name = translated.get(zone_name)
            elif translated.get('The ' + zone_name):
                translated_name = translated.get('The ' + zone_name)
            elif translated.get(zone_name.replace('The ', '')):
                translated_name = translated.get(zone_name.replace('The ', ''))

            merged_zones[zone_name] = Zone(zone_id, zone_name, parent_name,
                                           translated_name,
                                           wowhead[zone_id].get_expansion() if wowhead.get(zone_id) else None,
                                           wowhead[zone_id].get_category() if wowhead.get(zone_id) else None,
                                           ', '.join(sources))

        if len(name_set) > 1:
            print(f'? Name differs for id #{zone_id}: {name_set}')  # 48
            # continue

        # if zone_name in added_names:
        #     print(f'? Name {zone_name} duplicated for id #{zone_id}')  # 159
        #     # continue
        # added_names.add(zone_name)

    return merged_zones


def save_zones_to_db(zones: dict[str, Zone]):
    import sqlite3
    print('Saving zones to DB')
    conn = sqlite3.connect('cache/zones.db')
    conn.execute('DROP TABLE IF EXISTS zones')
    conn.execute('''CREATE TABLE zones (
                        id INT NOT NULL,
                        parent_zone TEXT,
                        name TEXT PRIMARY KEY,
                        translation TEXT,
                        expansion TEXT,
                        category TEXT,
                        source TEXT
                )''')
    conn.commit()

    with conn:
        for key, zone in zones.items():
            conn.execute('INSERT INTO zones(id, parent_zone, name, translation, expansion, category, source) VALUES(?, ?, ?, ?, ?, ?, ?)',
                        (zone.id, zone.parent_zone, zone.name, zone.translation, zone.expansion, zone.category, zone.source))


def read_zones_from_glossary() -> dict[str, str]:
    import csv
    all_zones = dict()
    with open('glossary.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            if row[0] == 'Term [uk]':
                continue
            if 'локація' in row[1]:
                translation = row[3]
                name = row[0]
                if name in all_zones:
                    print(f'Zone "{id}" duplicated')
                all_zones[name] = translation
    return all_zones


def generate_glossary_row(zone_key: str, zones: dict[str, Zone]) -> str:
    if not zones.get(zone_key):
        print(f'! No zone for {zone_key}')
        return zone_key
    zone = zones[zone_key]
    zone_description = 'локація'
    if zone.parent_zone:
        zone_description += f', {zones[zone.parent_zone].translation}'
    if zone.category:
        if zones.get(zone.category):
            zone_description += f', {zones[zone.category].translation}'
        if zone.category in CATEGORIES:
            zone_description += f', {CATEGORIES[zone.category]}'
        else:
            print(f'! No parent zone for {zone.name} ({zone.category})')
    zone_name = zone.name[4:] if zone.name.startswith('The ') else zone.name
    row = '"{}","{}","{}"'.format(
        zone.translation.replace('"', '""'),
        zone_name.replace('"', '""'),
        zone_description
    )
    return row


def save_translations_to_glossary(translated_zones: dict[str, str], glossary_zones: dict[str, str], merged_zones: dict[str, Zone]):
    glossary_import_lines = list()
    glossary_import_lines.append('"Term [uk]","Term [en]","Description [en]"')
    for zone_name in glossary_zones.keys() & translated_zones.keys():
        print(f'! Zone {zone_name} already exists.')
    for zone_name in translated_zones.keys() - glossary_zones.keys():
        glossary_import_lines.append(generate_glossary_row(zone_name, merged_zones))

    with open('new_zones_dictionary.csv', 'w', encoding="utf-8") as out_file:
        out_file.writelines('\n'.join(glossary_import_lines))


if __name__ == '__main__':
    # save_warcraftdb_zone_page(5502)
    # test_zone = parse_warcraftdb_zone_page('5502.html')

    # save_wowdb_zones_htmls()
    # save_classicdb_zones_htmls()
    # save_evowow_zones_htmls()
    # # save_twinhead_zones_htmls() # protected by CloudFlare
    # save_warcraftdb_zones_htmls()

    wowhead_zones = get_wowhead_zones()
    wowdb_zones = parse_wowdb_zone_pages()
    classicdb_zones = parse_classicdb_zone_pages()
    evowow_zones = parse_evowow_zone_pages()
    # twinhead_zones = parse_twinhead_zone_pages()
    warcraftdb_zones = parse_warcraftdb_zone_pages()
    translated_zones = read_new_translations()  # To generate glossary import rows for Crowdin
    glossary_zones = read_zones_from_glossary()  # To generate DB with up-to-date translations

    for key in (translated_zones.keys() & glossary_zones.keys()):
        print(f'Warning: clashing translations for {key}: "{translated_zones[key]}" and "{glossary_zones[key]}"')
    merged_translations = {**translated_zones, **glossary_zones}

    save_temp_zones_to_cache_db(wowhead_zones, wowdb_zones, classicdb_zones, evowow_zones, warcraftdb_zones)

    merged_zones = merge_zones(wowhead_zones, wowdb_zones, classicdb_zones, evowow_zones, warcraftdb_zones, merged_translations)
    save_zones_to_db(merged_zones)

    save_translations_to_glossary(translated_zones, glossary_zones, merged_zones)
