import json
import os

import requests
from bs4 import BeautifulSoup

CLASSIC = 'classic'
SOD = 'sod'
TBC = 'tbc'
WRATH = 'wrath'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'

expansion_data = {
    CLASSIC: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        METADATA_FILTERS: ('6:', '5:', '11500:'),
        IGNORES: [252, 323, 1682, 2890, 3219, 3221, 3657, 13044, 18973, 20959, 20999, 27801, 28025, 35253, 35254, 35592, 37100, 65407, 73361, 73362, 123308, 133737, 138496, 175755, 175789, 176225, 176366, 176368, 176548, 177224, 177884, 177927, 179474, 179475, 179476, 179477, 179669, 179670, 179671, 180252, 180385, 180401, 180618, 180668, 180786, 180851, 180855, 180856, 180857, 180858, 180860, 180861, 180862, 180863, 180864, 180865, 181852, 181853, 181886, 375774,
                  180510, 180512, 180516, # TBC
                  123468, 123469 # Wrath?
                  ]
    },
    SOD: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        METADATA_FILTERS: ('6:', '2:', '11500:'),
        IGNORES: []
    },
    TBC: {
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        IGNORES: []
    },
    WRATH: {
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        IGNORES: []
    }
}


# Metadata from Wowhead
class ObjectMD:
    def __init__(self, id, name, name_ua=None, type=None, location=None, expansion=None):
        self.id = id
        self.name = name
        self.name_ua = name_ua
        self.type = type
        self.location = location
        self.expansion = expansion

    def __str__(self):
        res = f'#{self.id}:'
        res += f' "{self.name}"'
        return res

    def get_type(self):
        types = {
            9: 'book',#
            -5: 'chests',#
            3: 'containers',#
            -3: 'herbs',#
            -9: 'interactive-objects',#
            19: 'mailboxes',#
            -4: 'mineral-veins',#
            -2: 'quests',#
            -6: 'tools',#
            -8: 'treasures',
            # Not in Wowhead:
            25: 'fish',#
            22: 'skills',#
            50: 'chests'#
        }
        return types.get(self.type)


def __get_wowhead_object_search(expansion, start, end=None) -> list[ObjectMD]:
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
        return list(map(lambda md: ObjectMD(md.get('id'), md.get('name'), None, md.get('type'), md.get('location'), expansion), json.loads(json_data)))
    else:
        return []


def __retrieve_objects_metadata_from_wowhead(expansion) -> dict[int, ObjectMD]:
    all_objects_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            objects = __get_wowhead_object_search(expansion, start)
            if len(objects) < 1000:
                all_objects_metadata.extend(objects)
                break
        objects = __get_wowhead_object_search(expansion, start, start + 1000)
        all_objects_metadata.extend(objects)
        i += 1
    return {md.id: md for md in all_objects_metadata}



def get_wowhead_objects_metadata(expansion) -> dict[int, ObjectMD]:
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


def load_questie_objects_ids() -> set[int]:
    from slpp import slpp as lua
    objects = set()
    with open('input/lookupObjects.lua', 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        decoded_objects = lua.decode(lua_file)
        for object_id, decoded_object in decoded_objects.items():
            objects.add(object_id)
    return objects


def save_objects_to_db(objects: dict[int, ObjectMD]):
    import sqlite3
    print('Saving objects to DB')
    conn = sqlite3.connect('cache/objects.db')
    conn.execute('DROP TABLE IF EXISTS objects')
    conn.execute('''CREATE TABLE objects (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        name_ua TEXT,
                        type TEXT,
                        location TEXT
                )''')
    conn.commit()
    with conn:
        for key, object in objects.items():
            if 'TEST' in object.name.upper().split(' ') or key in expansion_data[object.expansion][IGNORES]:
                continue
            object_location = ', '.join(map(lambda x: f"'{x}'", object.location)) if object.location else None
            conn.execute('INSERT INTO objects(id, expansion, name, name_ua, type, location) VALUES(?, ?, ?, ?, ?, ?)',
                        (object.id, object.expansion, object.name, object.__dict__.get('name_ua'), object.get_type() or object.type, object_location))


if __name__ == '__main__':
    wowhead_metadata_classic = get_wowhead_objects_metadata(CLASSIC)
    wowhead_metadata_sod = get_wowhead_objects_metadata(SOD)
    object_translations = load_object_lua()

    wowhead_metadata = {**wowhead_metadata_classic, **wowhead_metadata_sod}

    for object in wowhead_metadata.values():
        if 'TEST' in object.name.upper().split(' ') or object.id in expansion_data[object.expansion][IGNORES]:
            continue
        if object.name.lower() in object_translations:
            object.name_ua = object_translations[object.name.lower()]
        else:
            print(f"Translation for {object} doesn't exist")

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


    save_objects_to_db(wowhead_metadata)