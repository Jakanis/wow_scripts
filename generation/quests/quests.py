import json
import os
import time

import requests
import multiprocessing
from bs4 import BeautifulSoup
import sqlite3
import difflib

THREADS = 32
# WOWHEAD_URL = 'https://www.wowhead.com/classic'
# WOWHEAD_URL_TBC = 'https://www.wowhead.com/tbc'
# WOWHEAD_URL_WRATH = 'https://www.wowhead.com/wotlk'

CLASSIC = 'classic'
TBC = 'tbc'
WRATH = 'wrath'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
QUESTS_CACHE = 'quests_cache'
IGNORES = 'ignores'
INDEX = 'index'

expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_quests_html',
        QUESTS_CACHE: 'wowhead_classic_quest_cache',
        IGNORES: [
            1, 785, 912, 999, 1005, 1006, 1099, 1174, 1272, 1500, 5383, 6843, 7522, 7561, 7797, 7906, 7961, 7962, 8226, 8259, 8289, 8296, 8478, 8489, 8618, 8896, 9065,  # Not used in all expansions
            # 8617, 8618, 8530, 8531 # '<faction_name> needs singed corestones' quests actually not used.
            236,  # Wintergrasp (lich o_O)
            8325, 8326, 8327, 8328, 8329, 8334, 8335, 8338, 8344, 8347, 8350, 8463, 8468, 8472, 8473, 8474, 8475, 8476, 8477, 8479, 8480, 8482, 8483, 8486, 8487, 8488, 8490, 8491, 8547, 8563, 8564, 8884, 8885, 8886, 8887, 8888, 8889, 8890, 8891, 8892, 8894, 8895, 9249, # TBC
        ]
    },
    TBC: {
        INDEX: 1,
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_quests_html',
        QUESTS_CACHE: 'wowhead_tbc_quest_cache',
        IGNORES: [
            1, 785, 912, 999, 1005, 1006, 1099, 1174, 1272, 1500, 5383, 6843, 7522, 7561, 7797, 7906, 7961, 7962, 8226, 8259, 8289, 8296, 8478, 8489, 8618, 8896, 9065,  # Not used in all expansions
            # 236,  # Still Wintergrasp. Doesn't exist for TBC
            9511, 9880, 9881, 10375, 10376, 10377, 10378, 10379, 10383, 10386, 10387, 10638, 10779, 10844, 10999, 11027, 11334, 11345, 11551, 11976, 24508, 24509, 65221, 65222, 65223, 65224, # Appeared in TBC, not used
            11196,  # Used in Cata
        ]
    },
    WRATH: {
        INDEX: 2,
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_quests_html',
        QUESTS_CACHE: 'wowhead_wrath_quest_cache',
        IGNORES: [
            1, 785, 912, 999, 1005, 1006, 1099, 1174, 1272, 1500, 5383, 6843, 7522, 7561, 7797, 7906, 7961, 7962, 8226, 8259, 8289, 8296, 8478, 8489, 8618, 8896, 9065,  # Not used in all expansions
            9511, 9880, 9881, 10375, 10376, 10377, 10378, 10379, 10383, 10386, 10387, 10638, 10779, 10844, 10999, 11027, 11334, 11345, 11551, 11976, 24508, 24509, 65221, 65222, 65223, 65224,  # Appeared in TBC, not used
            11179, 13997, 11402, 11461, 11578, 11579, 11939, 11987, 11992, 12162, 12163, 12426, 12586, 13299, 13317, 25306, 12233, 12493, 12586, 12825, 12834, 12835, 12837, 12881, 12890, 12911, 13977, # Appeared in Wrath, not used
            60860, 70685,  # Rewards for... ergh... TCG? Doesn't exist for other expansions and Wowhead has no text
            25055, 25092,  # TODO: Looks like pre-Cata. Check later
            11196,  # Used in Cata
        ]
    }
}

class Quest:
    def __init__(self, id, name, objective=None, description=None, progress=None, completion=None):
        self.id = id
        self.name = name
        self.objective = objective
        self.description = description
        self.progress = progress
        self.completion = completion

    def __str__(self):
        return f'{self.id}, "{self.name}"'

    def __eq__(self, other):
        if not isinstance(other, Quest):
            return False

        return (self.id == other.id and self.name == other.name and self.objective == other.objective and self.description == other.description
                and self.progress == other.progress and self.completion == other.completion)

    def diff(self, other):
        diffs = []
        if self.id != other.id:
             diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
             diffs.append(f'NAME: {self.name} <> {other.name}')
        if self.objective != other.objective:
             diffs.append(f'OBJECTIVE:\n{self.objective}\n<>\n{other.objective}')
        if self.description != other.description:
             diffs.append(f'DESCRIPTION:\n{self.description}\n<>\n{other.description}')
        if self.progress != other.progress:
             diffs.append(f'PROGRESS:\n{self.progress}\n<>\n{other.progress}')
        if self.completion != other.completion:
             diffs.append(f'COMPLETION:\n{self.completion}\n<>\n{other.completion}')
        return '\n'.join(diffs) if len(diffs) else None

    def diff_dels(self, other):
        diffs = []
        if self.id != other.id:
             diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
             diffs.append(f'NAME: {self.name} <> {other.name}')
        if self.objective is None and self.objective != other.objective:
             diffs.append(f'OBJECTIVE:\n{self.objective}\n<>\n{other.objective}')
        if self.description is None and self.description != other.description:
             diffs.append(f'DESCRIPTION:\n{self.description}\n<>\n{other.description}')
        if self.progress is None and self.progress != other.progress:
             diffs.append(f'PROGRESS:\n{self.progress}\n<>\n{other.progress}')
        if self.completion is None and self.completion != other.completion:
             diffs.append(f'COMPLETION:\n{self.completion}\n<>\n{other.completion}')
        return diffs

    def diff_updates(self, other):
        diffs = []
        if self.id != other.id:
             diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
             diffs.append(f'NAME: {self.name} <> {other.name}')
        if self.objective is not None and other.objective is not None and self.objective != other.objective:
             diffs.append(f'OBJECTIVE:\n{self.objective}\n<>\n{other.objective}')
        if self.description is not None and other.description is not None and self.description != other.description:
             diffs.append(f'DESCRIPTION:\n{self.description}\n<>\n{other.description}')
        if self.progress is not None and other.progress is not None and self.progress != other.progress:
             diffs.append(f'PROGRESS:\n{self.progress}\n<>\n{other.progress}')
        if self.completion is not None and other.completion is not None and self.completion != other.completion:
             diffs.append(f'COMPLETION:\n{self.completion}\n<>\n{other.completion}')
        return diffs


class QuestEntity:
    def __init__(self, id, name, objective=None, description=None, progress=None, completion=None, cat=None, side=None, type=None, lvl=None, rlvl=None, expansion=None):
        self.id = id
        self.name = name
        self.objective = objective
        self.description = description
        self.progress = progress
        self.completion = completion
        self.cat = cat
        self.side = side
        self.type = type
        self.lvl = lvl
        self.rlvl = rlvl
        self.expansion = expansion

    def __str__(self):
        return f'#{self.id}:{self.expansion}, "{self.name}"'

    def __eq__(self, other):
        if not isinstance(other, QuestEntity):
            return False

        return (self.id == other.id and self.name == other.name and self.objective == other.objective and self.description == other.description
                and self.progress == other.progress and self.completion == other.completion and self.cat == other.cat and self.side == other.side
                and self.type == other.type and self.lvl == other.lvl and self.rlvl == other.rlvl)

    def is_empty(self):
        if self.objective is None and self.description is None and self.progress is None and self.completion is None:
            return True
        else:
            return False

    def get_side(self):
        if self.side == 'none':
            return 'both'
        else:
            return self.side

    @staticmethod
    def __diff_fields(field1, field2):
        differ = difflib.Differ()
        lines1 = field1.splitlines() if field1 else []
        lines2 = field2.splitlines() if field2 else []
        diff = differ.compare(lines1, lines2)
        return '\n'.join(diff)

    def diff(self, other):
        differ = difflib.Differ()
        diffs = []
        if self.id != other.id:
            diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
            diffs.append(f'NAME: {self.name} <> {other.name}')
        if self.objective != other.objective:
            diff = QuestEntity.__diff_fields(self.objective, other.objective)
            diffs.append(f"OBJECTIVE:\n{diff}")
        if self.description != other.description:
            diff = QuestEntity.__diff_fields(self.description, other.description)
            diffs.append(f"DESCRIPTION:\n{diff}")
        if self.progress != other.progress:
            diff = QuestEntity.__diff_fields(self.progress, other.progress)
            diffs.append(f"PROGRESS:\n{diff}")
        if self.completion != other.completion:
            diff = QuestEntity.__diff_fields(self.completion, other.completion)
            diffs.append(f"COMPLETION:\n{diff}")
        if self.cat != other.cat:
            diffs.append(f'cat: {self.cat} <> {other.cat}')
        if self.side != other.side:
            diffs.append(f'side: {self.side} <> {other.side}')
        if self.type != other.type:
            diffs.append(f'type: {self.type} <> {other.type}')
        if self.lvl != other.lvl:
            diffs.append(f'lvl: {self.lvl} <> {other.lvl}')
        if self.rlvl != other.rlvl:
            diffs.append(f'rlvl: {self.rlvl} <> {other.rlvl}')
        return diffs

    def diff_deletes(self, other):
        diffs = []
        if self.id != other.id:
            diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
            diffs.append(f'NAME: {self.name} <> {other.name}')
        if self.objective is None and self.objective != other.objective:
            diffs.append(f'OBJECTIVE:\n{self.objective}\n<>\n{other.objective}')
        if self.description is None and self.description != other.description:
            diffs.append(f'DESCRIPTION:\n{self.description}\n<>\n{other.description}')
        if self.progress is None and self.progress != other.progress:
            diffs.append(f'PROGRESS:\n{self.progress}\n<>\n{other.progress}')
        if self.completion is None and self.completion != other.completion:
            diffs.append(f'COMPLETION:\n{self.completion}\n<>\n{other.completion}')
        return diffs

    def diff_updates(self, other):
        diffs = []
        if self.id != other.id:
            diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
            diffs.append(f'NAME: {self.name} <> {other.name}')
        if self.objective is not None and other.objective is not None and self.objective != other.objective:
            diff = QuestEntity.__diff_fields(self.objective, other.objective)
            diffs.append(f"OBJECTIVE:\n{diff}")
        if self.description is not None and other.description is not None and self.description != other.description:
            diff = QuestEntity.__diff_fields(self.description, other.description)
            diffs.append(f"DESCRIPTION:\n{diff}")
        if self.progress is not None and other.progress is not None and self.progress != other.progress:
            diff = QuestEntity.__diff_fields(self.progress, other.progress)
            diffs.append(f"PROGRESS:\n{diff}")
        if self.completion is not None and other.completion is not None and self.completion != other.completion:
            diff = QuestEntity.__diff_fields(self.completion, other.completion)
            diffs.append(f"COMPLETION:\n{diff}")
        return diffs

    def accept_text_additions(self, other):
        if self.objective is None and self.objective != other.objective:
             self.objective = other.objective
        if self.description is None and self.description != other.description:
             self.description = other.description
        if self.progress is None and self.progress != other.progress:
             self.progress = other.progress
        if self.completion is None and self.completion != other.completion:
             self.completion = other.completion
        return self

    def merge_metadata(self, other):
        # if self.cat != other.cat:
        #      pass # todo

        if 'both' in [self.side, other.side]:
             self.side = other.side = 'both'
        if self.side == 'none':
             self.side = other.side
        if other.side == 'none':
             other.side = self.side
        if self.side != other.side:
             self.side = other.side = 'both'

        self.type = other.type

        if other.lvl == -1:
            other.lvl = self.lvl
        else:
            self.lvl = other.lvl

        if other.rlvl == -1:
            other.rlvl = self.rlvl
        else:
            self.rlvl = other.rlvl


# Metadata from Wowhead
class QuestMD:
    def __init__(self, id, name, category=None, subcategory=None, side=None, type=None, lvl=None, rlvl=None, expansion=None):
        self.id = id
        self.name = name
        self.category = category
        self.subcategory = subcategory
        self.side = side
        self.type = type
        self.lvl = lvl
        self.rlvl = rlvl
        self.expansion = expansion

    def __str__(self):
        return f'{self.id},"{self.name}"'

    def get_side(self) -> str:
        if self.side == 1:
            return 'alliance'
        elif self.side == 2:
            return 'horde'
        elif self.side == 3:
            return 'both'
        else:
            return 'none'

    def get_type(self) -> str:
        if self.type == 0:
            return 'normal'
        elif self.type == 1:
            return 'elite'
        elif self.type == 41:
            return 'pvp'
        elif self.type == 62:
            return 'raid'
        elif self.type == 81:
            return 'dungeon'
        else:
            return 'normal'


# Metadata from DB
class QuestMD_DB:
    def __init__(self, id, name, cat=None, side=None, type=None, lvl=None, rlvl=None, expansion=None):
        self.id = id
        self.name = name
        self.cat = cat
        self.side = side
        self.type = type
        self.lvl = lvl
        self.rlvl = rlvl
        self.expansion = expansion


    def __eq__(self, other):
        if not isinstance(other, QuestMD_DB):
            return False

        return (self.id == other.id and self.name == other.name and self.cat == other.cat and self.side == other.side
                and self.type == other.type and self.lvl == other.lvl and self.rlvl == other.rlvl)

    def diff(self, other):
        diffs = []
        if self.id != other.id:
             diffs.append(f'id: {self.id} <> {other.id}')
        if self.name != other.name:
             diffs.append(f'name: {self.name} <> {other.name}')
        if self.cat != other.cat:
             diffs.append(f'cat: {self.cat} <> {other.cat}')
        if self.side != other.side:
             diffs.append(f'side: {self.side} <> {other.side}')
        if self.type != other.type:
             diffs.append(f'type: {self.type} <> {other.type}')
        if self.lvl != other.lvl:
             diffs.append(f'lvl: {self.lvl} <> {other.lvl}')
        if self.rlvl != other.rlvl:
             diffs.append(f'rlvl: {self.rlvl} <> {other.rlvl}')
        return '\n'.join(diffs)


def __get_wowhead_quests_search(expansion, start, end=None) -> list[QuestMD]:
    base_url = expansion_data[expansion][WOWHEAD_URL]
    if end:
        url = base_url + f"/quests?filter=30:30;5:2;{end}:{start}"
    else:
        url = base_url + f"/quests?filter=30;2;{start}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    script_tag = soup.find('script', type='text/javascript', src=None)
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('new Listview(') + 13
        start = script_content.find('data:[', start) + 5
        end = script_content.rfind('});')
        json_data = script_content[start:end]
        return list(map(lambda md: QuestMD(md.get('id'), md.get('name'), md.get('category2'), md.get('category'), md.get('side'), md.get('type'), md.get('level'), md.get('reqlevel'), expansion), json.loads(json_data)))
    else:
        return []

def get_wowhead_categories(expansion) -> dict[int, dict[int, str]]:
    url = expansion_data[expansion][WOWHEAD_URL] + f"/quests?filter=30;3;1"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    script_tags = soup.find_all('script', type=None, src=None)
    script_tag = next(filter(lambda script: 'Filter.init({' in script.text, script_tags))
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('"categories":[{') + 13
        end = script_content.find('}],')+2
        categories_data = json.loads(script_content[start:end])
    else:
        raise Exception("Can't retrieve categories.")

    categories = dict()
    for category_data in categories_data:
        category_id = int(category_data.get('id'))
        category_name = category_data.get('url')
        category_name = ' '.join(word.capitalize() for word in category_name.split('-'))
        categories[category_id] = dict()
        categories[category_id]['Name'] = category_name
        for subcategory_data in category_data.get('categories'):
            subcategory_id = int(subcategory_data.get('id'))
            subcategory_name = subcategory_data.get('url').title()
            subcategory_name = ' '.join(word.capitalize() for word in subcategory_name.split('-'))
            categories[category_id][subcategory_id] = subcategory_name
    return categories


def __retrieve_quests_metadata_from_wowhead(expansion) -> dict[int, QuestMD]:
    all_quests_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            quests = __get_wowhead_quests_search(expansion, start)
            if len(quests) < 1000:
                all_quests_metadata.extend(quests)
                break
        quests = __get_wowhead_quests_search(expansion, start, start + 1000)
        all_quests_metadata.extend(quests)
        i += 1
    return {md.id: md for md in all_quests_metadata}


def get_wowhead_quests_metadata(expansion) -> dict[int, QuestMD]:
    import pickle
    cache_file_name = expansion_data[expansion][METADATA_CACHE]
    if os.path.exists(f'cache/tmp/{cache_file_name}.pkl'):
        print(f'Loading cached Wowhead({expansion}) metadata')
        with open(f'cache/tmp/{cache_file_name}.pkl', 'rb') as f:
            wowhead_metadata = pickle.load(f)
    else:
        print(f'Retrieving Wowhead({expansion}) metadata')
        wowhead_metadata = __retrieve_quests_metadata_from_wowhead(expansion)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/{cache_file_name}.pkl', 'wb') as f:
            pickle.dump(wowhead_metadata, f)
    return wowhead_metadata


def save_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/quest={id}?xml'
    html_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    r = requests.get(url)
    if not r.ok:
        # You download over 90000 quests in one hour - you'll fail
        # You do it async - you fail
        # Have a tea break (or change IP, lol)
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for quest #{id}')
    if (f"Quest #{id} doesn't exist." in r.text):
        return
    with open(html_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_htmls_from_wowhead(expansion, ids: list[int]):
    from functools import partial
    save_func = partial(save_page, expansion)
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}'

    if os.path.exists(cache_dir) and len(os.listdir(cache_dir)) == len(ids):
        print(f'HTML cache for Wowhead({expansion}) exists and seems legit. Skipping.')
        return

    print(f'Saving HTMLs for {len(ids)} quests from Wowhead({expansion}).')
    os.makedirs(cache_dir, exist_ok=True)
    with multiprocessing.Pool(THREADS) as p:
        p.map(save_func, ids)


def __cleanup_text(text):
    return ' '.join(text.strip().split()).replace('$LINEBREAK$', '\n').replace('\n ', '\n')

def __get_forward_text(tag):
    out = ''

    while (tag.next_sibling and tag.next_sibling.name not in ['h1', 'h2', 'h3', 'table']
           and not (tag.next_sibling.name == 'div' and tag.next_sibling.attrs.get('class') and 'pad' in tag.next_sibling.attrs.get('class'))):
        tag = tag.next_sibling
        if tag.name == 'script' or tag.name == 'div' or tag.name == 'ul':
            continue
        out += tag.text

    return out

def __get_wowhead_objective_text(soup: BeautifulSoup):
    out = None

    tag = soup.find('h1', class_='heading-size-1')

    if tag:
        out = __cleanup_text(__get_forward_text(tag))

    return out if out.strip() != '' else None

def __get_wowhead_description_text(soup):
    out = None

    tag = soup.find('h2', class_='heading-size-3', string='Description')
    if tag:
        out = __cleanup_text(__get_forward_text(tag))

    return out

def __get_wowhead_progress_text(soup):
    out = None

    tag = soup.find(id='lknlksndgg-progress')
    if tag:
        out = __cleanup_text(tag.get_text())

    if not out:
        tag = soup.find('h2', class_='heading-size-3', string='Progress')
        if tag:
            text = __cleanup_text(__get_forward_text(tag))
            if text:
                out = text

    return out

def __get_wowhead_completion_text(soup):
    out = None

    tag = soup.find(id='lknlksndgg-completion')
    if tag:
        out = __cleanup_text(tag.get_text())

    if not out:
        tag = soup.find('h2', class_='heading-size-3', string='Completion')
        if tag:
            text = __cleanup_text(__get_forward_text(tag))
            if text:
                out = text

    return out

def parse_wowhead_quest_page(expansion, id) -> Quest:
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html5lib')

    for br in soup.find_all('br'):
        br.replace_with('$LINEBREAK$')

    quest_name = soup.find('h1').text
    objective = __get_wowhead_objective_text(soup)
    description = __get_wowhead_description_text(soup)
    progress = __get_wowhead_progress_text(soup)
    completion = __get_wowhead_completion_text(soup)

    return Quest(id, quest_name, objective, description, progress, completion)


def get_category(metadata: QuestMD) -> str:
    from utils import known_categories, fixed_quest_categories

    # Fix quest categories
    if metadata.id in fixed_quest_categories:
        metadata.category, metadata.subcategory = fixed_quest_categories[metadata.id]

    if metadata.category in known_categories and metadata.subcategory in known_categories[metadata.category]:
        category = f"{known_categories[metadata.category]['Name']}/{known_categories[metadata.category][metadata.subcategory]}"
    else:
        # print(f'Quest #{metadata.id}:{metadata.name} UNCATEGORIZED for {metadata.category}.{metadata.subcategory}!')  # debug
        category = 'Miscellaneous/Uncategorized'

    return category


def merge_quests_and_metadata(quests: dict[int, Quest], metadata: dict[int, QuestMD]) -> dict[int, dict[str, QuestEntity]]:
    if (metadata.keys() != quests.keys()):
        raise Exception("Different number of quests and metadata. Something gone wrong during parsing.")

    wowhead_quest_entities = dict()
    for id in sorted(metadata.keys()):
        quest = quests[id]
        md = metadata[id]

        if (id in expansion_data[md.expansion][IGNORES] or
                '<UNUSED>' in quest.name.upper() or
                'UNUSED' in quest.name or
                'UNUSED' == quest.name.upper() or
                'Faction Test' in quest.name or
                'Classic Random ' in quest.name or # actually exists (like some next ones) but that's how reward for LFG works. vv
                ' Random Heroic ' in quest.name or
                'Daily Heroic Random ' in quest.name or
                'Daily Normal Random ' in quest.name or
                'World Event Dungeon - ' in quest.name or
                ('Daily' in quest.name and 'Protocol' in quest.name and 'Random' in quest.name) or # ^^ yes, up to there it's LFG. Be careful with Mechagon in BfA (lol, we won't ever reach that), but may be useful in Cata
                '<NYI>' in quest.name.upper() or
                'NYI' in quest.name or
                '<TXT>' in quest.name.upper() or
                '[TXT]' in quest.name.upper() or
                '[PH]' in quest.name.upper() or
                '<CHANGE TO GOSSIP>' in quest.name.upper() or
                '<TEST>' in quest.name.upper() or
                '[DEPRECATED]' in quest.name.upper() or
                'DEPRECATED:' in quest.name.upper() or
                'DEPRECATED' in quest.name or
                'DEPRECAED' in quest.name or
                'DEPRICATED' in quest.name or
                'ZZOLD' in quest.name.upper() or
                ('TEST' in quest.name.upper() and 'QUEST' in quest.name.upper()) or
                'iCoke' in quest.name or
                'TEST QUEST' in quest.name.upper() or
                'REUSE' in quest.name or
                'REUSE' == quest.name.upper() or
                'Wrath (80) E' == quest.name or
                '[NEVER USED]' == quest.name.upper() or
                '' == quest.name):
            continue

        # if id in expansion_data[md.expansion][IGNORES]:
        #     print(f'Quest #{id} in IGNORE')

        # if not quest.objective and not quest.description and not quest.progress and not quest.completion:
        #     print(f'Quest #{id} is EMPTY')

        category = get_category(md)
        if wowhead_quest_entities.get(id):
            raise Exception('Saving to same id. Impossible thing, but who knows what can happen.')
        wowhead_quest_entities[id] = dict()
        wowhead_quest_entities[id][md.expansion] = QuestEntity(id, quest.name, quest.objective, quest.description,
                                                               quest.progress, quest.completion, category,
                                                               md.get_side(), md.get_type(), md.lvl, md.rlvl,
                                                               md.expansion)
    return wowhead_quest_entities


def parse_wowhead_pages(expansion, metadata: dict[int, QuestMD]) -> dict[int, dict[str, QuestEntity]]:
    import pickle
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][QUESTS_CACHE]}.pkl'
    parse_func = partial(parse_wowhead_quest_page, expansion)

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) quests')
        with open(cache_path, 'rb') as f:
            wowhead_quests = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) quest pages')
        # wowhead_quests = {id: parse_wowhead_quest_page(expansion, id) for id in ids}
        with multiprocessing.Pool(THREADS) as p:
            quests = p.map(parse_func, metadata.keys())
        wowhead_quests = {quest.id: quest for quest in quests}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_quests, f)

    wowhead_quest_entities = merge_quests_and_metadata(wowhead_quests, metadata)

    return wowhead_quest_entities

def save_quests_to_cache_db(quests: dict[int, dict[str, QuestEntity]]):
    print('Saving quest data to cache DB')
    conn = sqlite3.connect('cache/quests.db')
    conn.execute('DROP TABLE IF EXISTS quests')
    conn.execute('''CREATE TABLE quests (
                        id INTEGER NOT NULL,
                        expansion TEXT NON NULL,
                        title TEXT,
                        objective TEXT,
                        description TEXT,
                        progress TEXT,
                        completion TEXT,
                        cat TEXT NOT NULL,
                        side TEXT NOT NULL,
                        type TEXT NOT NULL,
                        lvl INTEGER NOT NULL,
                        rlvl INTEGER NOT NULL,
	                    UNIQUE("id","expansion")
                )''')

    conn.commit()
    with conn:
        for quest_id, quest_expansions in quests.items():
            for expansion, quest_entity in quest_expansions.items():
                conn.execute(f'''INSERT INTO quests(id, title, objective, description, progress, completion, cat, side, type, lvl, rlvl, expansion) 
                                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                (quest_entity.id, quest_entity.name, quest_entity.objective, quest_entity.description, quest_entity.progress, quest_entity.completion,
                                quest_entity.cat, quest_entity.get_side(), quest_entity.type, quest_entity.lvl, quest_entity.rlvl, quest_entity.expansion))

def __get_quest_from_db(id, conn) -> [Quest, QuestMD_DB]:
    return [(Quest(r[0], r[1], r[2], r[3], r[4], r[5]), QuestMD_DB(r[0], r[1], r[6], r[7], r[8], r[9], r[10]))
            for r in conn.execute('SELECT id, title, objective, description, progress, completion, cat, side, type, lvl, rlvl, expansion FROM quests WHERE id = ?', (id,))][0]

def get_all_quests_from_db(db_path) -> dict[int, dict[str, QuestEntity]]:
    db_conn = sqlite3.connect(db_path)

    entities = [(QuestEntity(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11] or CLASSIC)) for r
                in db_conn.execute('SELECT id, title, objective, description, progress, completion, cat, side, type, lvl, rlvl, expansion FROM quests')]

    quests = dict()
    for entity in entities:
        if quests.get(entity.id) is None:
            quests[entity.id] = dict()
        quests[entity.id][entity.expansion] = entity

    return quests


def fix_metadata(metadata: dict[int, QuestMD_DB]):
    metadata[402].side = 'alliance'  # alliance
    metadata[593].side = 'horde'  # horde
    metadata[708].side = 'alliance'
    metadata[908].side = 'horde'
    metadata[1288].side = 'alliance'
    metadata[6846].side = 'alliance'
    metadata[6861].side = 'horde'
    metadata[6901].side = 'horde'
    metadata[7181].side = 'horde'
    metadata[7202].side = 'alliance'
    metadata[7367].side = 'alliance'
    metadata[7368].side = 'horde'
    metadata[7421].side = 'horde'
    metadata[7422].side = 'horde'
    metadata[7423].side = 'horde'
    metadata[7424].side = 'alliance'
    metadata[7425].side = 'alliance'
    metadata[7426].side = 'alliance'
    metadata[7427].side = 'horde'
    metadata[7428].side = 'alliance'
    metadata[7660].side = 'horde'
    metadata[7661].side = 'horde'
    metadata[7662].side = 'horde'
    metadata[7663].side = 'horde'
    metadata[7664].side = 'horde'
    metadata[7665].side = 'horde'
    metadata[7671].side = 'alliance'
    metadata[7672].side = 'alliance'
    metadata[7673].side = 'alliance'
    metadata[7674].side = 'alliance'
    metadata[7675].side = 'alliance'
    metadata[7676].side = 'alliance'
    metadata[7677].side = 'alliance'
    metadata[7678].side = 'alliance'
    metadata[7788].side = 'alliance'
    metadata[7789].side = 'horde'
    metadata[7871].side = 'alliance'
    metadata[7872].side = 'alliance'
    metadata[7873].side = 'alliance'
    metadata[7874].side = 'horde'
    metadata[7875].side = 'horde'
    metadata[7876].side = 'horde'
    metadata[7886].side = 'alliance'
    metadata[7887].side = 'alliance'
    metadata[7888].side = 'alliance'
    metadata[7921].side = 'alliance'
    metadata[7922].side = 'horde'
    metadata[7923].side = 'horde'
    metadata[7924].side = 'horde'
    metadata[7925].side = 'horde'

def merge_fields(new_field, saved_field):
    if new_field is None:
        return saved_field
    else:
        if '\n\n\n' in new_field: #  If Wowhead skipped emotion
            return saved_field
    return new_field

def merge_side(new_side, saved_side, id):
    if new_side == 'none':
        return 'both'
    if new_side == 'both' or saved_side == 'both':
        return 'both'
    if new_side == saved_side:
        return new_side
    if new_side != saved_side:
        print(f'Sides for quest #{id} differed. Saved as both.')
        return 'both'


def merge_with_db(wowhead_quests: dict[int, dict[str, QuestEntity]], classicua_quests: dict[int, dict[str, QuestEntity]]) -> dict[int, dict[str, QuestEntity]]:
    for id in sorted(wowhead_quests.keys() | classicua_quests.keys()):
        cache_quest = wowhead_quests.get(id).get(CLASSIC) if wowhead_quests.get(id) else None
        saved_quest = classicua_quests.get(id).get(CLASSIC) if classicua_quests.get(id) else None

        if not cache_quest and not saved_quest:
            continue

        changes_in_next_expansions = False
        if len(wowhead_quests.get(id)) > 1:
            changes_in_next_expansions = True

        if cache_quest is None:  # Move #2358 to Wrath
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f"WarningDB0: Quest #{id} '{getattr(saved_quest, 'name')}' doesn't exist in Wowhead Classic")
            continue

        if saved_quest is None:  # Good (27)
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f"WarningDB1: Quest #{id} '{getattr(cache_quest, 'name')}' doesn't exist in ClassicUA")
            continue

        if cache_quest.name != saved_quest.name:  # Good (7)
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB2: Quest #{id} name was changed: "{cache_quest.name}" -> "{saved_quest.name}"')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue

        changes = cache_quest.diff_updates(saved_quest)
        additions = cache_quest.diff_deletes(saved_quest)
        deletions = saved_quest.diff_deletes(cache_quest)

        if len(changes) > 0 and len(additions) > 0 and len(deletions) > 0:  # Good, none
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB3: Quest #{cache_quest.id} "{cache_quest.name}" text is a mess:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue

        if len(changes) > 0 and len(additions) > 0:  # Good (16)
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB4: Quest #{cache_quest.id} "{cache_quest.name}" text has changes and additions:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue

        if len(changes) > 0 and len(deletions) > 0:  # Good (9). No changes needed
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB5: Quest #{cache_quest.id} "{cache_quest.name}" text has changes and deletions:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue

        if len(additions) > 0 and len(deletions) > 0:  # Good (20). No changes needed
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB6: Quest #{cache_quest.id} "{cache_quest.name}" text has additions and deletions:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue

        if len(changes) > 0:  # Good (290). Pure changes, mostly should be fine.
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB7: Quest #{cache_quest.id} "{cache_quest.name}" text was changed:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue

        #  TODO: Check if string also exists in other quest. May be added by mistake from other quest, happens with ClassicDB
        if len(additions) > 0:  # Check (252). Usually needs manual fixes
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB8: Quest #{cache_quest.id} "{cache_quest.name}" text has additions:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            print(f'Merging...')
            cache_quest.accept_text_additions(saved_quest)
            continue

        if len(deletions) > 0:  # Good (42). What can go wrong if we just add text?
            print('-' * 100)
            if changes_in_next_expansions:
                print(f'Quest #{id} has changes in next expansions')
            print(f'WarningDB9: Quest #{cache_quest.id} "{cache_quest.name}" text has deletions:')
            print('\n'.join(cache_quest.diff(saved_quest)))
            continue


def merge_quest(id: int, old_quests: dict[str, QuestEntity], new_quests: dict[str, QuestEntity]) -> dict[str, QuestEntity]:
    # Check "Warning"s manually, you may need to add fixes to fix_<expansion>_quests method. "WARNING!"s are especially dangerous
    if len(old_quests) > 1 and len(new_quests) == 1:
        print(f'Merging more than one instance from previous expansion for Quest #{id}')
        last_old_quest_key = list(old_quests.keys())[-1]
        result = merge_quest(id, {last_old_quest_key: old_quests[last_old_quest_key]}, new_quests)
        del old_quests[last_old_quest_key]
        return {**old_quests, **result}
    if len(old_quests) == 1 and len(new_quests) == 1:
        old_quest = next(iter(old_quests.values()))
        new_quest = next(iter(new_quests.values()))

        old_quest.merge_metadata(new_quest)

        if old_quest.name != new_quest.name:
            print('-' * 100)
            print(f'Warning0: Quest #{id} name was changed: "{old_quest.name}" -> "{new_quest.name}"')
            print('\n'.join(old_quest.diff(new_quest)))
            return {**old_quests, **new_quests}

        changes = old_quest.diff_updates(new_quest)
        additions = old_quest.diff_deletes(new_quest)
        deletions = new_quest.diff_deletes(old_quest)

        if len(changes) > 0 and len(additions) > 0 and len(deletions) > 0:
            print('-' * 100)
            print(f'WARNING1!: Quest #{old_quest.id} "{old_quest.name}" text is a mess:')
            print('\n'.join(old_quest.diff(new_quest)))
            return {**old_quests, **new_quests}

        if len(changes) > 0 and len(additions) > 0:
            print('-' * 100)
            print(f'Warning2: Quest #{old_quest.id} "{old_quest.name}" text has changes and additions:')
            print('\n'.join(old_quest.diff(new_quest)))
            old_quest.accept_text_additions(new_quest)
            return {**old_quests, **new_quests}

        if len(changes) > 0 and len(deletions) > 0:
            print('-' * 100)
            print(f'WARNING3!: Quest #{old_quest.id} "{old_quest.name}" text has changes and deletions:')
            print('\n'.join(old_quest.diff(new_quest)))
            return {**old_quests, **new_quests}

        if len(additions) > 0 and len(deletions) > 0:
            print('-' * 100)
            print(f'WARNING4!: Quest #{old_quest.id} "{old_quest.name}" text has additions and deletions:')
            print('\n'.join(old_quest.diff(new_quest)))
            return {**old_quests, **new_quests}

        if len(changes) > 0:
            print('-' * 100)
            print(f'Warning5: Quest #{old_quest.id} "{old_quest.name}" text was changed:')
            print('\n'.join(changes))
            return {**old_quests, **new_quests}

        if len(additions) > 0:
            print('-' * 100)
            print(f'Warning6: Quest #{old_quest.id} "{old_quest.name}" text has additions:')
            print('\n'.join(additions))
            old_quest.accept_text_additions(new_quest)
            return old_quests

        if len(deletions) > 0:
            print('-' * 100)
            print(f'Warning7: Quest #{old_quest.id} "{old_quest.name}" text has deletions:')
            print('\n'.join(deletions))
            return old_quests

        old_quest.cat = new_quest.cat  # Now it's safe... I guess

        diff = old_quest.diff(new_quest)
        if old_quest != new_quest or len(diff) > 0:
            print('-' * 100)
            print(f'WARNING8!: Quest #{old_quest.id} "{old_quest.name}" still has diffs:')
            print('\n'.join(diff))
            return {**old_quests, **new_quests}

        if old_quest == new_quest:
            return old_quests
    else:
        print('-' * 100)
        print(f'Skip: Quest #{id} instance number unexpected')

    pass

def merge_expansions(old_expansion: dict[int, dict[str, QuestEntity]], new_expansion: dict[int, dict[str, QuestEntity]]) -> dict[int, dict[str, QuestEntity]]:
    result = dict()

    for id in old_expansion.keys() - new_expansion.keys():
        old_quest = next(iter(old_expansion.get(id).values()))
        # print(f"Warning: Quest #{id} '{old_quest.name}', '{old_quest.cat}' was in previous expansion but doesn't exist in new")
        result[id] = old_expansion[id]

    for id in new_expansion.keys() - old_expansion.keys():
        result[id] = new_expansion[id]

    for id in sorted(old_expansion.keys() & new_expansion.keys()):
        merged = merge_quest(id, old_expansion[id], new_expansion[id])
        result[id] = merged
    return result


def fix_classic_quests(classic_quests: dict[int, dict[str, QuestEntity]]):
    # Fixes from TBC
    classic_quests[123][CLASSIC].objective += '.'
    classic_quests[279][CLASSIC].description = classic_quests[279][CLASSIC].description.replace(' Murloc', ' murloc').replace(' Bluegill', ' bluegill')
    classic_quests[345][CLASSIC].description = classic_quests[345][CLASSIC].description.replace('very quickly Unfortunately', 'very quickly. Unfortunately')
    classic_quests[607][CLASSIC].objective += '.'
    classic_quests[621][CLASSIC].description = classic_quests[621][CLASSIC].description.replace('Jubuwai', 'Jubuwal')
    classic_quests[682][CLASSIC].objective = classic_quests[682][CLASSIC].objective.replace('Bring Stromgarde', 'Bring 15 Stromgarde')
    classic_quests[686][CLASSIC].description = classic_quests[686][CLASSIC].description.replace('Mablesten', 'Marblesten')
    classic_quests[729][CLASSIC].description = classic_quests[729][CLASSIC].description.replace('prospector is ok!', 'prospector is okay!')
    classic_quests[915][CLASSIC].objective = classic_quests[915][CLASSIC].objective.replace("Tigule and Foror's", "Tigule's")
    classic_quests[915][CLASSIC].description = classic_quests[915][CLASSIC].description.replace("Tigule and Foror's", "Tigule's")
    classic_quests[915][CLASSIC].completion = classic_quests[915][CLASSIC].completion.replace("Tigule and Foror know to", "Tigule knows how to")
    classic_quests[1062][CLASSIC].description = classic_quests[1062][CLASSIC].description.replace(" -- ", "--")
    classic_quests[1264][CLASSIC].description = classic_quests[1264][CLASSIC].description.replace("discretely", "discreetly")
    classic_quests[1489][CLASSIC].objective += '.'
    classic_quests[1505][CLASSIC].description = classic_quests[1505][CLASSIC].description.replace("Durotar to the east.", "Durotar.")
    classic_quests[1578][CLASSIC].objective += '.'
    classic_quests[1582][CLASSIC].objective = classic_quests[1582][CLASSIC].objective.replace("Embossed Leather Glove", "Embossed Leather Gloves")
    classic_quests[1658][CLASSIC].objective = classic_quests[1658][CLASSIC].objective.replace("in Tirisfal Glade.", "in Tirisfal Glades.")
    classic_quests[1658][CLASSIC].description = classic_quests[1658][CLASSIC].description.replace(" Tirisfal Glade ", " Tirisfal Glades ")
    classic_quests[1678][CLASSIC].description = classic_quests[1678][CLASSIC].description.replace("south of Frostmane Hold", "south of Frostmane Hold.")
    classic_quests[1795][CLASSIC].description = classic_quests[1795][CLASSIC].description.replace("If you're are", "If you are")
    classic_quests[1842][CLASSIC].objective += '.'
    classic_quests[1844][CLASSIC].description = classic_quests[1844][CLASSIC].description.replace(" the northwestern reaches ", " the southwestern reaches ").replace(" Mountains there lies ", " Mountains lies ")
    classic_quests[1899][CLASSIC].objective = classic_quests[1899][CLASSIC].objective.replace("Astor's Ledger", "Andron's Ledger")
    classic_quests[1921][CLASSIC].objective = classic_quests[1921][CLASSIC].objective.replace("10 Linen and", "10 Linen Cloth and")
    classic_quests[1961][CLASSIC].objective = classic_quests[1961][CLASSIC].objective.replace("10 Linen and", "10 Linen Cloth and")
    classic_quests[2200][CLASSIC].objective = classic_quests[2200][CLASSIC].objective.replace("who has it", "who had it")
    classic_quests[3904][CLASSIC].description = classic_quests[3904][CLASSIC].description.replace("Bring me those crates!", "Bring me those buckets!")
    classic_quests[4245][CLASSIC].description = classic_quests[4245][CLASSIC].description.replace("if your prepared", "if you're prepared")
    classic_quests[4506][CLASSIC].objective = classic_quests[4506][CLASSIC].objective.replace("moon well", "moonwell")
    classic_quests[4506][CLASSIC].description = classic_quests[4506][CLASSIC].description.replace("moon well", "moonwell")
    classic_quests[4822][CLASSIC].objective = classic_quests[4822][CLASSIC].objective.replace("Tigule and Foror's", "Tigule's")
    classic_quests[4822][CLASSIC].description = classic_quests[4822][CLASSIC].description.replace("Tigule and Foror's", "Tigule's")
    classic_quests[4822][CLASSIC].completion = classic_quests[4822][CLASSIC].completion.replace("Tigule and Foror know to", "Tigule knows how to")
    classic_quests[5064][CLASSIC].objective += '.'
    classic_quests[5863][CLASSIC].description = classic_quests[5863][CLASSIC].description.replace("large bank of", "large band of")
    classic_quests[6482][CLASSIC].objective = classic_quests[6482][CLASSIC].objective.replace("Spintertree Post", "Splintertree Post")
    classic_quests[6805][CLASSIC].objective = classic_quests[6805][CLASSIC].objective.replace("Desert Rumbers", "Desert Rumblers")
    classic_quests[7845][CLASSIC].objective = classic_quests[7845][CLASSIC].objective.replace("Raventusk", "Revantusk")
    classic_quests[7846][CLASSIC].objective = classic_quests[7846][CLASSIC].objective.replace("Elder Torn'tusk", "Elder Torntusk")
    classic_quests[7927][CLASSIC].progress = classic_quests[7927][CLASSIC].progress.replace("of portals!", "of Portals!")
    classic_quests[7927][CLASSIC].completion = classic_quests[7927][CLASSIC].completion.replace("darkmoon", "Darkmoon")
    classic_quests[7929][CLASSIC].progress = classic_quests[7929][CLASSIC].progress.replace("of elementals!", "of Elementals!")
    classic_quests[7929][CLASSIC].completion = classic_quests[7929][CLASSIC].completion.replace("darkmoon", "Darkmoon")
    classic_quests[8115][CLASSIC].description = classic_quests[8115][CLASSIC].description.replace("are are needed", "are as needed")
    classic_quests[8584][CLASSIC].objective = classic_quests[8584][CLASSIC].objective.replace("Quickcleave", "Quikcleave")
    classic_quests[8584][CLASSIC].description = classic_quests[8584][CLASSIC].description.replace("Quickcleave", "Quikcleave")
    classic_quests[8585][CLASSIC].objective = classic_quests[8585][CLASSIC].objective.replace("Quickcleave", "Quikcleave")
    classic_quests[8586][CLASSIC].objective = classic_quests[8586][CLASSIC].objective.replace("Quickcleave", "Quikcleave")
    classic_quests[8625][CLASSIC].objective = classic_quests[8625][CLASSIC].objective.replace("2 Idols of Rebirth, 5 Silver Scarabs and 5 Ivory Scarabs", "2 Idols of Death, 5 Stone Scarabs and 5 Bronze Scarabs")
    classic_quests[8918][CLASSIC].objective = classic_quests[8918][CLASSIC].objective.replace(" of the Elements", " of Elements")
    classic_quests[8942][CLASSIC].objective = classic_quests[8942][CLASSIC].objective.replace(" of the Elements", " of Elements")
    classic_quests[8968][CLASSIC].description = classic_quests[8968][CLASSIC].description.replace(" the Left Piece of Lord Valthalak's Amulet ", " the left piece of Lord Valthalak's amulet ")
    classic_quests[8991][CLASSIC].description = classic_quests[8991][CLASSIC].description.replace(" the Right Piece of Lord Valthalak's Amulet ", " the right piece of Lord Valthalak's amulet ")
    classic_quests[9416][CLASSIC].completion = classic_quests[9416][CLASSIC].completion.replace(" you're hear, ", " you're here, ")

    #Fixes from Wrath:
    classic_quests[136][CLASSIC].name = classic_quests[136][CLASSIC].name.replace(" Sander's ", " Sanders' ")
    classic_quests[138][CLASSIC].name = classic_quests[138][CLASSIC].name.replace(" Sander's ", " Sanders' ")
    classic_quests[139][CLASSIC].name = classic_quests[139][CLASSIC].name.replace(" Sander's ", " Sanders' ")
    classic_quests[140][CLASSIC].name = classic_quests[140][CLASSIC].name.replace(" Sander's ", " Sanders' ")
    classic_quests[140][CLASSIC].description = classic_quests[140][CLASSIC].description.replace(" Sander's ", " Sanders' ")
    classic_quests[1821][CLASSIC].description = classic_quests[1821][CLASSIC].description.replace("lurking scourge", "lurking Scourge")
    classic_quests[4771][CLASSIC].description = classic_quests[4771][CLASSIC].description.replace(" a team of scourge scholars...", " a team of Scourge scholars...")
    classic_quests[5713][CLASSIC].description = classic_quests[5713][CLASSIC].description.replace(" will be able deliver ", " will be able to deliver ")
    classic_quests[7631][CLASSIC].completion = classic_quests[7631][CLASSIC].completion.replace(" a dreadsteed.", " a Dreadsteed.")
    classic_quests[7907][CLASSIC].progress = classic_quests[7907][CLASSIC].progress.replace(" of beasts!", " of Beasts!")
    classic_quests[7907][CLASSIC].completion = classic_quests[7907][CLASSIC].completion.replace(" darkmoon cards ", " Darkmoon cards ")
    classic_quests[7928][CLASSIC].progress = classic_quests[7928][CLASSIC].progress.replace(" of warlords!", " of Warlords!")
    classic_quests[7928][CLASSIC].completion = classic_quests[7928][CLASSIC].completion.replace(" darkmoon cards ", " Darkmoon cards ")
    classic_quests[8279][CLASSIC].description = classic_quests[8279][CLASSIC].description.replace(" Twilight Keepers, look ", " Twilight Keepers. Look ")
    classic_quests[8903][CLASSIC].description = classic_quests[8903][CLASSIC].description.replace(" the the ", " the ")
    classic_quests[8983][CLASSIC].objective = classic_quests[8983][CLASSIC].objective.replace(" Mage Quarter.", " Magic Quarter.")
    classic_quests[8983][CLASSIC].description = classic_quests[8983][CLASSIC].description.replace(" Mage Quarter.", " Magic Quarter.")
    classic_quests[8984][CLASSIC].description = classic_quests[8984][CLASSIC].description.replace(" point you in the right direction", " point you in the right direction.")
    classic_quests[9310][CLASSIC].description = classic_quests[9310][CLASSIC].description.replace(" a crystal that is faintly ", " a crystal faintly ")

    #Fixes from ClassicDB/Wowpedia (WarningDB7):
    classic_quests[33][CLASSIC].description = classic_quests[33][CLASSIC].description.replace('\ntough wolf meat', '\nTough wolf meat')
    classic_quests[156][CLASSIC].description = classic_quests[156][CLASSIC].description.replace('\nrot blossoms grow', '\nRot blossoms grow')
    classic_quests[812][CLASSIC].completion += ' <sigh>'
    classic_quests[842][CLASSIC].completion = "Alright, <name>. You want to earn your keep with the Horde? Well there's plenty to do here, so listen close and do what you're told.\n\n<I see that look in your eyes, do not think I will tolerate any insolence. Thrall himself has declared the Hordes females to be on equal footing with you men. Disrespect me in the slightest, and you will know true pain./I'm happy to have met you. Thrall will be glad to know that more females like you and I are taking the initiative to push forward in the Barrens.>"
    classic_quests[4981][CLASSIC].completion = classic_quests[4981][CLASSIC].completion.replace("\n\n\n\n", "\n\n<Bijou laughs.>\n\n")
    classic_quests[5282][CLASSIC].progress = 'Compassion is what separates us from the animals, <name>. Remember that...'
    classic_quests[5713][CLASSIC].progress = 'Have you seen of Sentinel Aynasha on the road? She left on an important mission but she has not yet returned.'
    classic_quests[6482][CLASSIC].progress = 'Have you seen my brother Ruul? He walked into the forest days ago and has not returned...'
    classic_quests[7936][CLASSIC].completion = classic_quests[7936][CLASSIC].completion.replace('A prize fit for a king!', 'A prize fit for a <king/queen>!')
    classic_quests[8044][CLASSIC].progress = classic_quests[8044][CLASSIC].progress.replace("\n\n\n\n", "\n\n<Jin'rokh bows.>\n\n")
    classic_quests[8046][CLASSIC].completion += "\n\n<Jin'rokh shudders.>"
    classic_quests[8052][CLASSIC].progress = classic_quests[8052][CLASSIC].progress.replace("\n\n\n\n", "\n\n<Al'tabim sighs.>\n\n")
    classic_quests[8146][CLASSIC].progress = "Ah, <name>, it is good to smell you again.\n\n<Falthir grins.>\n\nYou'll have to excuse my sense of humor. It can be most foul at times.\n\nI sense that you have caused great anguish to our enemies. The forces of Hakkar cry out your name in anger. This is most excellent.\n\nYou have earned another weave on your talisman. Hand it to me."
    classic_quests[8316][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8376][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8377][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8378][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8379][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8380][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8381][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8382][CLASSIC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    classic_quests[8742][CLASSIC].progress = 'The Scepter of the Shifting Sands is whole once more, <name>.\n\nIt must be you who uses the scepter. It must be you who heralds the next age of your people.\n\nYou must wait for the armies of the Horde and the Alliance to arrive in Silithus before you may ring the Scarab Gong.'
    classic_quests[9269][CLASSIC].progress = 'I must not interfere, <race>.'
    classic_quests[9269][CLASSIC].completion = 'The magnitude of this accomplishment must not be understated, <name>. You have done what most would have thought to be impossible. Alas, it was fated. The staff has made its choice...'
    classic_quests[9319][CLASSIC].progress = 'Have you found your way through the dark?'
    classic_quests[9319][CLASSIC].completion = 'Your essence sings with the energy of the flames you found, <name>. The fire you encountered is potent, and with the right knowledge, its power can be harnessed...\n\n<The Flamekeeper mutters an incantation in a strange, arcane tongue, then pulls out a glowing bottle.>\n\nAh! Here we are. May this light your path, no matter where you tread.'
    classic_quests[9322][CLASSIC].progress = 'Are the flames of Kalimdor burning brightly?'
    classic_quests[9323][CLASSIC].progress = 'Are the flames of Eastern Kingdoms burning brightly?'

    #Fixes from ClassicDB/Wowpedia (WarningDB8):
    # Delete manually:
    # classic_quests[5][CLASSIC].progress = None
    # classic_quests[109][CLASSIC].progress = None
    # classic_quests[111][CLASSIC].progress = None
    # classic_quests[163][CLASSIC].progress = None
    # classic_quests[960][CLASSIC].progress = None
    # classic_quests[1361][CLASSIC].progress = None
    # classic_quests[1679][CLASSIC].progress = None
    # classic_quests[1706][CLASSIC].progress = None
    # classic_quests[1794][CLASSIC].progress = None
    # classic_quests[4904][CLASSIC].progress = None
    # classic_quests[7736][CLASSIC].objective = None
    # classic_quests[7736][CLASSIC].description = None
    # classic_quests[7838][CLASSIC].objective = None
    # classic_quests[7838][CLASSIC].description = None
    # classic_quests[9386][CLASSIC].completion = None
    classic_quests[172][CLASSIC].completion = classic_quests[172][CLASSIC].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me')
    classic_quests[895][CLASSIC].description = classic_quests[895][CLASSIC].description.replace('and is WANTED on', 'and is wanted on')
    classic_quests[1468][CLASSIC].completion = classic_quests[1468][CLASSIC].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me').replace(', yes sir.', ', yes <sir/lady>.')
    classic_quests[4081][CLASSIC].progress = "What is it, <race>? Can't you see I have a platoon to command?"
    classic_quests[5044][CLASSIC].completion += ' <snort>'
    classic_quests[5265][CLASSIC].description = classic_quests[5265][CLASSIC].description.replace('\nthe Argent Hold ', '\nThe Argent Hold ')
    classic_quests[9136][CLASSIC].completion = 'I am much obliged, <name>.\n\n<Rayne bows.>\n\nPlease remember that I am always accepting fronds.'


def fix_tbc_quests(tbc_quests: dict[int, dict[str, QuestEntity]]):
    tbc_quests[915][TBC].completion = tbc_quests[915][TBC].completion.replace("Tigule and Foror know to", "Tigule knows how to")
    tbc_quests[1068][TBC].description = tbc_quests[1068][TBC].description.replace(" shaman ", " shamans ")
    tbc_quests[1678][TBC].description = tbc_quests[1678][TBC].description.replace("south of Frostmane Hold", "south of Frostmane Hold.")
    tbc_quests[1844][TBC].description = tbc_quests[1844][TBC].description.replace(" the northwestern reaches ", " the southwestern reaches ").replace(" Mountains there lies ", " Mountains lies ")
    tbc_quests[4822][TBC].completion = tbc_quests[4822][TBC].completion.replace("Tigule and Foror know to", "Tigule knows how to")
    tbc_quests[7792][TBC].progress = 'We are currently gathering wool. A donation of sixty pieces of wool cloth will net you full recognition by our people for your generous actions.\n\nIf you currently have sixty pieces, you may donate them now.'
    tbc_quests[7792][TBC].completion = 'Our thanks for your donation, <name>.'
    tbc_quests[7798][TBC].progress = 'We are currently gathering silk. A donation of sixty pieces of silk cloth will net you full recognition by our people for your generous actions\n\nIf you currently have sixty pieces, you may donate them now.'
    tbc_quests[7798][TBC].completion = 'Our thanks for your donation, <name>.'
    tbc_quests[8801][TBC].objective = tbc_quests[8801][TBC].objective.replace("Caelastrasz", "Caelestrasz")
    tbc_quests[8981][TBC].side = 'horde'

    # Fixes from Wrath:
    tbc_quests[136][TBC].name = tbc_quests[136][TBC].name.replace(" Sander's ", " Sanders' ")
    tbc_quests[138][TBC].name = tbc_quests[138][TBC].name.replace(" Sander's ", " Sanders' ")
    tbc_quests[139][TBC].name = tbc_quests[139][TBC].name.replace(" Sander's ", " Sanders' ")
    tbc_quests[140][TBC].name = tbc_quests[140][TBC].name.replace(" Sander's ", " Sanders' ")
    tbc_quests[140][TBC].description = tbc_quests[140][TBC].description.replace(" Sander's ", " Sanders' ")
    tbc_quests[1821][TBC].description = tbc_quests[1821][TBC].description.replace("lurking scourge", "lurking Scourge")
    tbc_quests[4771][TBC].description = tbc_quests[4771][TBC].description.replace(" a team of scourge scholars...", " a team of Scourge scholars...")
    tbc_quests[5713][TBC].description = tbc_quests[5713][TBC].description.replace(" will be able deliver ", " will be able to deliver ")
    tbc_quests[7631][TBC].completion = tbc_quests[7631][TBC].completion.replace(" a dreadsteed.", " a Dreadsteed.")
    tbc_quests[7907][TBC].progress = tbc_quests[7907][TBC].progress.replace(" of beasts!", " of Beasts!")
    tbc_quests[7907][TBC].completion = tbc_quests[7907][TBC].completion.replace(" darkmoon cards ", " Darkmoon cards ")
    tbc_quests[7928][TBC].progress = tbc_quests[7928][TBC].progress.replace(" of warlords!", " of Warlords!")
    tbc_quests[7928][TBC].completion = tbc_quests[7928][TBC].completion.replace(" darkmoon cards ", " Darkmoon cards ")
    tbc_quests[8279][TBC].description = tbc_quests[8279][TBC].description.replace(" Twilight Keepers, look ", " Twilight Keepers. Look ")
    tbc_quests[8903][TBC].description = tbc_quests[8903][TBC].description.replace(" the the ", " the ")
    tbc_quests[8983][TBC].objective = tbc_quests[8983][TBC].objective.replace(" Mage Quarter.", " Magic Quarter.")
    tbc_quests[8983][TBC].description = tbc_quests[8983][TBC].description.replace(" Mage Quarter.", " Magic Quarter.")
    tbc_quests[8984][TBC].description = tbc_quests[8984][TBC].description.replace(" point you in the right direction", " point you in the right direction.")
    tbc_quests[9310][TBC].description = tbc_quests[9310][TBC].description.replace(" a crystal that is faintly ", " a crystal faintly ")

    # fixes from WotLK (TBC only)
    tbc_quests[9138][TBC].description = tbc_quests[9138][TBC].description.replace(" nerubian ", " Nerubian ")
    tbc_quests[9315][TBC].description = tbc_quests[9315][TBC].description.replace(" nerubians", " Nerubians")
    tbc_quests[9609][TBC].completion = tbc_quests[9609][TBC].completion.replace(" <race> ", " draenei ")
    tbc_quests[9630][TBC].objective = tbc_quests[9630][TBC].objective.replace(" wants you go into ", " wants you to go into ")
    tbc_quests[9875][TBC].completion = tbc_quests[9875][TBC].completion.replace("Purple Leafed Vêcnarium", "Purple Leafed <name>rium")
    tbc_quests[9968][TBC].objective = tbc_quests[9875][TBC].objective.replace(" outside the Cenarion ", " outside of the Cenarion ")
    tbc_quests[9998][TBC].objective = tbc_quests[9998][TBC].objective.replace(" at Allerian Post.", " at the Allerian Post.")
    tbc_quests[10037][TBC].objective = tbc_quests[10037][TBC].objective.replace(" in Shattrath.", " in Shattrath City.")
    tbc_quests[10038][TBC].objective = tbc_quests[10038][TBC].objective.replace("Locate and speak with ", "Speak with ")
    tbc_quests[10039][TBC].objective = tbc_quests[10039][TBC].objective.replace("Locate and speak with ", "Speak with ")
    tbc_quests[10105][TBC].description = tbc_quests[10105][TBC].description.replace(" a lot of a goods ", " a lot of goods ")
    tbc_quests[10273][TBC].description = tbc_quests[10273][TBC].description.replace(" able evade ", " able to evade ")
    tbc_quests[10519][TBC].description = tbc_quests[10519][TBC].description.replace(" you are <female/male>.", " you are a felboar.")
    tbc_quests[10563][TBC].description = tbc_quests[10563][TBC].description.replace(" about the their plans.", " about their plans. ")
    tbc_quests[10588][TBC].description = tbc_quests[10588][TBC].description.replace(" this spell has been used ", " this spell been used ").replace(" This land can not ", " This land cannot ")
    tbc_quests[10707][TBC].objective = tbc_quests[10707][TBC].objective.replace("Atam'al", "Ata'mal")
    tbc_quests[10707][TBC].description = tbc_quests[10707][TBC].description.replace("Atam'al", "Ata'mal")
    tbc_quests[10753][TBC].objective = tbc_quests[10753][TBC].objective.replace("Kill ", "Slay ")
    tbc_quests[10820][TBC].objective = tbc_quests[10820][TBC].objective.replace("Kill ", "Slay ")
    tbc_quests[10840][TBC].objective = tbc_quests[10840][TBC].objective.replace(" to him by the ", " to him at the ")
    tbc_quests[10847][TBC].objective = tbc_quests[10847][TBC].objective.replace(" Lower City district of Shattrath.", " Lower City section of Shattrath City.")
    tbc_quests[10848][TBC].objective = tbc_quests[10848][TBC].objective.replace(" to Kirrik at ", " to Kirrik the Awakened at ")
    tbc_quests[10849][TBC].objective = tbc_quests[10849][TBC].objective.replace(" to Kirrik at ", " to Kirrik the Awakened at ")
    tbc_quests[10861][TBC].objective = tbc_quests[10861][TBC].objective.replace(" to Kirrik at ", " to Kirrik the Awakened at ")
    tbc_quests[10873][TBC].objective = tbc_quests[10873][TBC].objective.replace("Sha'tar Outpost", "Sha'tari Base Camp")
    tbc_quests[10874][TBC].objective = tbc_quests[10874][TBC].objective.replace("Kirrik at ", "Kirrik the Awakened at ")
    tbc_quests[10879][TBC].objective = tbc_quests[10879][TBC].objective.replace(" with Rilak.", " with Rilak the Redeemed.")
    tbc_quests[10908][TBC].objective = tbc_quests[10908][TBC].objective.replace(" Lower City district of Shattrath.", " Lower City section of Shattrath City.")
    tbc_quests[11024][TBC].objective = tbc_quests[11024][TBC].objective.replace(" Lower City inside Shattrath.", " the Lower City section of Shattrath City.")
    tbc_quests[11135][TBC].description = tbc_quests[11135][TBC].description.replace("Tirisfal Glade.", "Tirisfal Glades.")
    tbc_quests[11216][TBC].description = tbc_quests[11216][TBC].description.replace("Archmagae", "Archmage")
    tbc_quests[11220][TBC].description = tbc_quests[11220][TBC].description.replace("Tirisfal Glade.", "Tirisfal Glades.").replace("head of the Horseman's", "head of the Horseman")
    tbc_quests[11389][TBC].description = tbc_quests[11389][TBC].description.replace(" destroy the sentinels", " destroy the sentinels.")
    tbc_quests[11975][TBC].description = tbc_quests[11975][TBC].description.replace("Elite <race> Chieftain", "Elite Tauren Chieftain")

    # Fixes from Wrath (for quests updated in TBC)
    tbc_quests[204][TBC].description = tbc_quests[204][TBC].description.replace("Medicine Men", "medicine men").replace("Jungle Remedies", "jungle remedies").replace("Venom Fern Extracts", "venom fern extracts").replace("Jungle fighers", "jungle fighters")
    tbc_quests[5762][TBC].objective = tbc_quests[5762][TBC].objective.replace("in Stranglethorn.", "in Stranglethorn Vale.")
    tbc_quests[5763][TBC].objective = tbc_quests[5763][TBC].objective.replace("in Stranglethorn.", "in Stranglethorn Vale.")

    #Fixes from ClassicDB/Wowpedia:
    tbc_quests[33][TBC].description = tbc_quests[33][TBC].description.replace('\ntough wolf meat', '\nTough wolf meat')
    tbc_quests[156][TBC].description = tbc_quests[156][TBC].description.replace('\nrot blossoms grow', '\nRot blossoms grow')
    tbc_quests[172][TBC].completion = tbc_quests[172][TBC].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me')
    tbc_quests[812][TBC].completion += ' <sigh>'
    tbc_quests[842][TBC].completion = "Alright, <name>. You want to earn your keep with the Horde? Well there's plenty to do here, so listen close and do what you're told.\n\n<I see that look in your eyes, do not think I will tolerate any insolence. Thrall himself has declared the Hordes females to be on equal footing with you men. Disrespect me in the slightest, and you will know true pain./I'm happy to have met you. Thrall will be glad to know that more females like you and I are taking the initiative to push forward in the Barrens.>"
    tbc_quests[895][TBC].description = tbc_quests[895][TBC].description.replace('and is WANTED on', 'and is wanted on')
    tbc_quests[1468][TBC].completion = tbc_quests[1468][TBC].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me').replace(', yes sir.', ', yes <sir/lady>.')
    tbc_quests[2767][TBC].progress = "Yes, I'm Oglethorpe Obnoticus, master inventor at your service! Now, is there something I could assist you with?"
    tbc_quests[4981][TBC].completion = tbc_quests[4981][TBC].completion.replace("\n\n\n\n", "\n\n<Bijou laughs.>\n\n")
    tbc_quests[5044][TBC].completion += ' <snort>'
    tbc_quests[5265][TBC].description = tbc_quests[5265][TBC].description.replace('\nthe Argent Hold ', '\nThe Argent Hold ')
    tbc_quests[7936][TBC].completion = tbc_quests[7936][TBC].completion.replace('A prize fit for a king!', 'A prize fit for a <king/queen>!')
    tbc_quests[8044][TBC].progress = tbc_quests[8044][TBC].progress.replace("\n\n\n\n", "\n\n<Jin'rokh bows.>\n\n")
    tbc_quests[8046][TBC].completion += "\n\n<Jin'rokh shudders.>"
    tbc_quests[8052][TBC].progress = tbc_quests[8052][TBC].progress.replace("\n\n\n\n", "\n\n<Al'tabim sighs.>\n\n")
    tbc_quests[8146][TBC].progress = "Ah, <name>, it is good to smell you again.\n\n<Falthir grins.>\n\nYou'll have to excuse my sense of humor. It can be most foul at times.\n\nI sense that you have caused great anguish to our enemies. The forces of Hakkar cry out your name in anger. This is most excellent.\n\nYou have earned another weave on your talisman. Hand it to me."
    tbc_quests[8316][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8376][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8377][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8378][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8379][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8380][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8381][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[8382][TBC].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    tbc_quests[9136][TBC].completion = 'I am much obliged, <name>.\n\n<Rayne bows.>\n\nPlease remember that I am always accepting fronds.'
    tbc_quests[9319][TBC].progress = 'Have you found your way through the dark?'
    tbc_quests[9319][TBC].completion = 'Your essence sings with the energy of the flames you found, <name>. The fire you encountered is potent, and with the right knowledge, its power can be harnessed...\n\n<The Flamekeeper mutters an incantation in a strange, arcane tongue, then pulls out a glowing bottle.>\n\nAh! Here we are. May this light your path, no matter where you tread.'



def fix_wrath_quests(wrath_quests: dict[int, dict[str, QuestEntity]]):
    wrath_quests[915][WRATH].completion = wrath_quests[915][WRATH].completion.replace("Tigule and Foror know to", "Tigule knows how to")
    wrath_quests[1068][WRATH].description = wrath_quests[1068][WRATH].description.replace(" shaman ", " shamans ")
    wrath_quests[4822][WRATH].completion = wrath_quests[4822][WRATH].completion.replace("Tigule and Foror know to", "Tigule knows how to")
    wrath_quests[7792][WRATH].progress = 'We are currently gathering wool. A donation of sixty pieces of wool cloth will net you full recognition by our people for your generous actions.\n\nIf you currently have sixty pieces, you may donate them now.'
    wrath_quests[7792][WRATH].completion = 'Our thanks for your donation, <name>.'
    wrath_quests[7798][WRATH].progress = 'We are currently gathering silk. A donation of sixty pieces of silk cloth will net you full recognition by our people for your generous actions\n\nIf you currently have sixty pieces, you may donate them now.'
    wrath_quests[7798][WRATH].completion = 'Our thanks for your donation, <name>.'
    wrath_quests[8801][WRATH].objective = wrath_quests[8801][WRATH].objective.replace("Caelastrasz", "Caelestrasz")
    wrath_quests[9644][WRATH].description = wrath_quests[9644][WRATH].description.replace(" anl ", " and ")
    wrath_quests[9875][WRATH].completion = wrath_quests[9875][WRATH].completion.replace("Purple Leafed Forsäkenrium", "Purple Leafed <name>rium")
    wrath_quests[65604][WRATH].completion = wrath_quests[65604][WRATH].completion.replace("I have known that <race> for many years", "I have known that orc for many years")

    wrath_quests[8981][WRATH].side = 'horde'

    #Fixes from ClassicDB/Wowpedia:
    wrath_quests[172][WRATH].completion = wrath_quests[172][WRATH].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me')
    wrath_quests[812][WRATH].completion += ' <sigh>'
    wrath_quests[842][WRATH].completion = "Alright, <name>. You want to earn your keep with the Horde? Well there's plenty to do here, so listen close and do what you're told.\n\n<I see that look in your eyes, do not think I will tolerate any insolence. Thrall himself has declared the Hordes females to be on equal footing with you men. Disrespect me in the slightest, and you will know true pain./I'm happy to have met you. Thrall will be glad to know that more females like you and I are taking the initiative to push forward in the Barrens.>"
    wrath_quests[895][WRATH].description = wrath_quests[895][WRATH].description.replace('and is WANTED on', 'and is wanted on')
    wrath_quests[1468][WRATH].completion = wrath_quests[1468][WRATH].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me').replace(', yes sir.', ', yes <sir/lady>.')
    wrath_quests[2767][WRATH].progress = "Yes, I'm Oglethorpe Obnoticus, master inventor at your service! Now, is there something I could assist you with?"
    wrath_quests[4981][WRATH].completion = wrath_quests[4981][WRATH].completion.replace("\n\n\n\n", "\n\n<Bijou laughs.>\n\n")
    wrath_quests[5044][WRATH].completion += ' <snort>'
    wrath_quests[5265][WRATH].description = wrath_quests[5265][WRATH].description.replace('\nthe Argent Hold ', '\nThe Argent Hold ')
    wrath_quests[7936][WRATH].completion = wrath_quests[7936][WRATH].completion.replace('A prize fit for a king!', 'A prize fit for a <king/queen>!')
    wrath_quests[8044][WRATH].progress = wrath_quests[8044][WRATH].progress.replace("\n\n\n\n", "\n\n<Jin'rokh bows.>\n\n")
    wrath_quests[8046][WRATH].completion += "\n\n<Jin'rokh shudders.>"
    wrath_quests[8052][WRATH].progress = wrath_quests[8052][WRATH].progress.replace("\n\n\n\n", "\n\n<Al'tabim sighs.>\n\n")
    wrath_quests[8146][WRATH].progress = "Ah, <name>, it is good to smell you again.\n\n<Falthir grins.>\n\nYou'll have to excuse my sense of humor. It can be most foul at times.\n\nI sense that you have caused great anguish to our enemies. The forces of Hakkar cry out your name in anger. This is most excellent.\n\nYou have earned another weave on your talisman. Hand it to me."
    wrath_quests[8316][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8376][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8377][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8378][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8379][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8380][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8381][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[8382][WRATH].completion = "War comes, <name>, and with it comes untold horrors. You have done all that could be asked of you and for that you should be rewarded.\n\nShould this... this prophecy ever come to pass...\n\n<Geologist Larksbane turns pale.>\n\nThe future of us all could be at an end.\n\nThese armaments will prove invaluable to your campaign in this desert."
    wrath_quests[9136][WRATH].completion = 'I am much obliged, <name>.\n\n<Rayne bows.>\n\nPlease remember that I am always accepting fronds.'
    wrath_quests[9319][WRATH].progress = 'Have you found your way through the dark?'
    wrath_quests[9319][WRATH].completion = 'Your essence sings with the energy of the flames you found, <name>. The fire you encountered is potent, and with the right knowledge, its power can be harnessed...\n\n<The Flamekeeper mutters an incantation in a strange, arcane tongue, then pulls out a glowing bottle.>\n\nAh! Here we are. May this light your path, no matter where you tread.'


def populate_cache_db_with_quest_data():
    wowhead_metadata = get_wowhead_quests_metadata(CLASSIC)
    wowhead_metadata_tbc = get_wowhead_quests_metadata(TBC)
    wowhead_metadata_wrath = get_wowhead_quests_metadata(WRATH)

    save_htmls_from_wowhead(CLASSIC, list(wowhead_metadata.keys()))
    save_htmls_from_wowhead(TBC, list(wowhead_metadata_tbc.keys()))
    save_htmls_from_wowhead(WRATH, list(wowhead_metadata_wrath.keys()))

    wowhead_quests = parse_wowhead_pages(CLASSIC, wowhead_metadata)
    wowhead_quests_tbc = parse_wowhead_pages(TBC, wowhead_metadata_tbc)
    wowhead_quests_wrath = parse_wowhead_pages(WRATH, wowhead_metadata_wrath)

    fix_classic_quests(wowhead_quests)
    fix_tbc_quests(wowhead_quests_tbc)
    fix_wrath_quests(wowhead_quests_wrath)

    print('Merging with TBC')
    classic_and_tbc_quests = merge_expansions(wowhead_quests, wowhead_quests_tbc)
    print('Merging with WotLK')
    all_quests = merge_expansions(classic_and_tbc_quests, wowhead_quests_wrath)

    classicua_data = get_all_quests_from_db('classicua.db')
    print('Merging with ClassicUA')
    merge_with_db(all_quests, classicua_data)

    # fix_quests(quests)
    # fix_metadata(metadata)

    start_time = time.time()

    save_quests_to_cache_db(all_quests)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Save time: {elapsed_time} seconds")



def compare_databases(cache_db, main_db):
    cache_conn = sqlite3.connect(cache_db)
    db_conn = sqlite3.connect(main_db)
    cache_quest_ids = [r[0] for r in cache_conn.execute('SELECT id FROM quests')]
    existing_quest_ids = [r[0] for r in db_conn.execute('SELECT id FROM quests')]
    print(f'Missing IDs in cache: {sorted(list(set(existing_quest_ids)-set(cache_quest_ids)))}')
    print(f'Missing IDs in DB: {sorted(list(set(cache_quest_ids)-set(existing_quest_ids)))}')
    for id in sorted(list(set(existing_quest_ids) & set(cache_quest_ids))):
        db_quest, db_metadata = __get_quest_from_db(id, db_conn)
        cache_quest, cache_metadata = __get_quest_from_db(id, cache_conn)
        # if db_quest != cache_quest:
        #     # diff = cache_quest.diff(db_quest) # if cache database is complete and will replace original
        #     # diff = cache_quest.diff_dels(db_quest)
        #     diff = cache_quest.diff_updates(db_quest)
        #     if diff:
        #         #  May be missed row with emotion
        #         if '\n\n\n' in diff:
        #             print('-' * 30)
        #             print('EMPTY ROW:')
        #         print(f"{'-'*100}\nDiff {id}: \n{diff}")

        if db_metadata != cache_metadata:
            print(f'{id} MD FAIL:')
            print(cache_metadata.diff(db_metadata))
        # if db_metadata.lvl != cache_metadata.lvl or db_metadata.rlvl != cache_metadata.rlvl or db_metadata.type != cache_metadata.type:
        #     __update_quest_type_and_lvls(cache_metadata, db_conn)


def compare_directories(dir1, dir2):
    import filecmp, difflib
    print('-'*100)
    print('-'*100)
    print(f'Comparing {dir1} and {dir2}')
    dcmp = filecmp.dircmp(dir1, dir2)

    # List of files that are only in the first directory
    only_in_dir1 = dcmp.left_only

    # List of files that are only in the second directory
    only_in_dir2 = dcmp.right_only

    # Print the results for the current directory
    if len(only_in_dir1) > 0:
        print("Files only in", dir1, ":", only_in_dir1)
    if len(only_in_dir2) > 0:
        print("Files only in", dir2, ":", only_in_dir2)

    for common_file in dcmp.common_files:
        file1 = os.path.join(dir1, common_file)
        file2 = os.path.join(dir2, common_file)

        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            # Read the files as binary and remove line ending differences
            content1 = f1.read().replace('\r\n', '\n')
            content2 = f2.read().replace('\r\n', '\n')
            if content1 != content2:
                print('-'*100)
                print("Diffing file:", common_file)
                differ = difflib.Differ()
                lines1 = content1.splitlines()
                lines2 = content2.splitlines()
                diff = differ.compare(lines1, lines2)
                print('\n'.join(diff))

    # Recursively compare subdirectories
    for subdir in dcmp.common_dirs:
        compare_directories(os.path.join(dir1, subdir), os.path.join(dir2, subdir))


def check_categories():
    from utils import known_categories
    wowhead_categories = get_wowhead_categories(CLASSIC)
    wowhead_categories_tbc = get_wowhead_categories(TBC)
    wowhead_categories_wrath = get_wowhead_categories(WRATH)

    dict1 = known_categories
    dict2 = wowhead_categories_wrath

    added_keys = {k: dict2[k] for k in dict2 if k not in dict1}
    removed_keys = {k: dict1[k] for k in dict1 if k not in dict2}

    changed_values = {}
    added_inner_keys = {}
    removed_inner_keys = {}

    for key in set(dict1.keys()) & set(dict2.keys()):
        inner_dict1 = dict1[key]
        inner_dict2 = dict2[key]

        added_inner_keys[key] = {k: inner_dict2[k] for k in inner_dict2 if k not in inner_dict1}
        removed_inner_keys[key] = {k: inner_dict1[k] for k in inner_dict1 if k not in inner_dict2}

        changed_values[key] = {k: (inner_dict1[k], inner_dict2[k]) for k in inner_dict1 if
                               k in inner_dict2 and inner_dict1[k] != inner_dict2[k]}

    print("Added Keys in Outer Dictionary:", added_keys)
    print("Removed Keys in Outer Dictionary:", removed_keys)
    print("Added Keys in Inner Dictionaries:", added_inner_keys)
    print("Removed Keys in Inner Dictionaries:", removed_inner_keys)
    print("Changed Values in Inner Dictionaries:", changed_values)


def generate_sources():
    from pathlib import Path
    import shutil
    import classicua_utils

    print('Generating sources...')
    if os.path.exists('./source_for_crowdin'):
        shutil.rmtree('./source_for_crowdin')
    count = 0
    quests = get_all_quests_from_db('cache/quests.db')

    for quest_id, quest_expansions in quests.items():
        for expansion, quest_entity in quest_expansions.items():
            if quest_entity.is_empty():
                print(f'Warning: Quest {quest_entity} is empty. Skipping.')
                continue
            if expansion == CLASSIC:
                suffix = ''
            else:
                suffix = '_' + expansion

            path = f'source_for_crowdin/quests{suffix}/{quest_entity.cat}'
            Path(path).mkdir(parents=True, exist_ok=True)

            filename = classicua_utils.get_quest_filename(quest_entity.id, quest_entity.name)
            # print(id, title)

            classicua_utils.write_xml_quest_file(
                f'{path}/{filename}.xml',
                quest_entity.name,
                quest_entity.objective,
                quest_entity.description,
                quest_entity.progress,
                quest_entity.completion)

            count += 1

    print(f'Generated {count} sources.')



if __name__ == '__main__':
    # check_categories() # Check categories and update known_categories in utils if needed

    populate_cache_db_with_quest_data()  # Generate cache/quests.db

    # compare_databases('cache/quests.db', 'classicua.db') # compare cache/quests.db with ./classicua.db (the one we overwrite)

    generate_sources()

    compare_directories('source_from_crowdin', 'source_for_crowdin')

