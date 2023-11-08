import json
import os

import requests
import multiprocessing
from bs4 import BeautifulSoup
import sqlite3

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
            8325, 8326, 8327, 8328, 8329, 8334, 8335, 8338, 8344, 8347, 8350, 8463, 8468, 8472, 8473, 8474, 8475, 8476, 8477, 8479, 8480, 8482, 8483, 8486, 8487, 8488, 8490, 8491, 8547, 8563, 8564, 8884, 8885, 8886, 8887, 8888, 8889, 8890, 8891, 8892, 8894, 8895, 9249 # TBC
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
            10383, 10386, 10387, 10999, 11334, 11345, 11976, 24508, 24509  # Appeared in TBC, not used
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
            10383, 10386, 10387, 10999, 11334, 11345, 11976, 24508, 24509,  # Appeared in TBC, not used
            25055, 25092,  # TODO: Looks like pre-Cata. Check later
            60860, 70685,  # Rewards for... ergh... TCG? Doesn't exist for other expansions though
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
        return '\n'.join(diffs) if len(diffs) else None

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
        return '\n'.join(diffs) if len(diffs) else None


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
        return f'{self.id}, "{self.name}"'

    def __eq__(self, other):
        if not isinstance(other, QuestEntity):
            return False

        return (self.id == other.id and self.name == other.name and self.objective == other.objective and self.description == other.description
                and self.progress == other.progress and self.completion == other.completion and self.cat == other.cat and self.side == other.side
                and self.type == other.type and self.lvl == other.lvl and self.rlvl == other.rlvl and self.expansion == other.expansion)

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
        return '\n'.join(diffs) if len(diffs) else None

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
        return '\n'.join(diffs) if len(diffs) else None



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

def merge_quests_and_metadata(quests: dict[int, Quest], metadata: dict[int, QuestMD]) -> dict[tuple[int, str], QuestEntity]:
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
                ('TEST' in quest.name.upper() and 'QUEST' in quest.name.upper()) or
                'iCoke' in quest.name or
                'TEST QUEST' in quest.name.upper() or
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
        wowhead_quest_entities[(id, md.expansion)] = QuestEntity(id, quest.name, quest.objective, quest.description, quest.progress,
                                                 quest.completion, category, md.get_side(), md.get_type(),
                                                 md.lvl, md.rlvl, md.expansion)
    return wowhead_quest_entities

def parse_wowhead_pages(expansion, metadata: dict[int, QuestMD]) -> dict[tuple[int, str], QuestEntity]:
    import pickle
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][QUESTS_CACHE]}.pkl'
    parse_func = partial(parse_wowhead_quest_page, expansion)

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) quests')
        with open(cache_path, 'rb') as f:
            wowhead_quest_entities = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) quest pages')
        # wowhead_quests = {id: parse_wowhead_quest_page(expansion, id) for id in ids}
        with multiprocessing.Pool(THREADS) as p:
            quests = p.map(parse_func, metadata.keys())

        wowhead_quests = {quest.id: quest for quest in quests}
        wowhead_quest_entities = merge_quests_and_metadata(wowhead_quests, metadata)

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_quest_entities, f)

    return wowhead_quest_entities

def save_quests_to_cache_db(quests: dict[int, Quest], metadata: dict[int, QuestMD_DB]):
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
                        PRIMARY KEY("id","expansion")
                )''')

    conn.commit()
    for id in metadata.keys():
        quest = quests.get(id)
        quest_md = metadata.get(id)
        if quest is None:
            continue

        with conn:
            conn.execute(f'''INSERT INTO quests(id, title, objective, description, progress, completion, cat, side, type, lvl, rlvl, expansion) 
                                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (id, quest.name, quest.objective, quest.description, quest.progress, quest.completion,
                          quest_md.cat, quest_md.side, quest_md.type, quest_md.lvl, quest_md.rlvl, 'classic'))

def __get_quest_from_db(id, conn) -> [Quest, QuestMD_DB]:
    return [(Quest(r[0], r[1], r[2], r[3], r[4], r[5]), QuestMD_DB(r[0], r[1], r[6], r[7], r[8], r[9], r[10]))
            for r in conn.execute('SELECT id, title, objective, description, progress, completion, cat, side, type, lvl, rlvl, expansion FROM quests WHERE id = ?', (id,))][0]

def get_all_quests_from_db(db_path):
    db_conn = sqlite3.connect(db_path)

    return {r[0]: (Quest(r[0], r[1], r[2], r[3], r[4], r[5]), QuestMD_DB(r[0], r[1], r[6], r[7], r[8], r[9], r[10], r[11])) for r in
            db_conn.execute('SELECT id, title, objective, description, progress, completion, cat, side, type, lvl, rlvl, expansion FROM quests')}


def fix_quests(quests):
    quests[5].progress = None
    quests[109].progress = None
    quests[111].progress = None
    quests[163].progress = None
    quests[960].progress = None
    quests[1267].progress = None
    quests[1462].progress = None
    quests[1463].progress = None
    quests[1464].progress = None
    quests[1679].progress = None
    quests[1706].progress = None
    quests[1794].progress = None
    quests[33].description = quests[33].description.replace('\ntough wolf meat', '\nTough wolf meat')
    quests[156].description = quests[156].description.replace('\nrot blossoms grow in strange places.', '\nRot blossoms grow in strange places.')
    quests[172].completion = quests[172].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me')
    quests[812].completion += ' <sigh>'
    quests[842].completion = "Alright, <name>. You want to earn your keep with the Horde? Well there's plenty to do here, so listen close and do what you're told.\n\n<I see that look in your eyes, do not think I will tolerate any insolence. Thrall himself has declared the Hordes females to be on equal footing with you men. Disrespect me in the slightest, and you will know true pain./I'm happy to have met you. Thrall will be glad to know that more females like you and I are taking the initiative to push forward in the Barrens.>"
    quests[895].description = quests[895].description.replace('and is WANTED on', 'and is wanted on')
    quests[1468].completion = quests[1468].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me').replace(', yes sir.', ', yes <sir/lady>.')
    quests[5044].completion = 'Your enemies should fear you even more, <race>. <snort>\n\nTell Mangletooth tales of your cunning in battle when next we meet--be it in this life, or the next. <snort>'
    quests[5265].description = quests[5265].description.replace('\nthe Argent Hold is now open', '\nThe Argent Hold is now open')
    quests[7936].completion = quests[7936].completion.replace('A prize fit for a king!', 'A prize fit for a <king/queen>!')
    quests[8046].completion += "\n\n<Jin'rokh shudders.>"
    quests[8115].description = quests[8115].description.replace('Arathor are are needed', 'Arathor are as needed')
    quests[9416].completion = quests[9416].completion.replace("It's good that you're hear, but", "It's good that you're here, but")

    #  fix empty rows in wowhead
    quests[8146].progress = "Ah, <name>, it is good to smell you again.\n\n<Falthir grins.>\n\nYou'll have to excuse my sense of humor. It can be most foul at times.\n\nI sense that you have caused great anguish to our enemies. The forces of Hakkar cry out your name in anger. This is most excellent.\n\nYou have earned another weave on your talisman. Hand it to me."
    quests[9136].completion = 'I am much obliged, <name>.\n\n<Rayne bows.>\n\nPlease remember that I am always accepting fronds.'
    quests[9319].completion = 'Your essence sings with the energy of the flames you found, <name>. The fire you encountered is potent, and with the right knowledge, its power can be harnessed...\n\n<The Flamekeeper mutters an incantation in a strange, arcane tongue, then pulls out a glowing bottle.>\n\nAh! Here we are. May this light your path, no matter where you tread.'


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


def merge_all_quests(wowhead_quests: dict[int, Quest], classicua_quests: dict[int, Quest], wowhead_metadata: dict[int, QuestMD], classicua_metadata: dict[int, QuestMD_DB]) -> (dict[int, Quest], dict[int, QuestMD_DB]):
    quests = {}
    metadata = {}

    for id in wowhead_quests.keys() | classicua_quests.keys():
        wowhead_quest = wowhead_quests.get(id)
        classicua_quest = classicua_quests.get(id)
        classicua_md = classicua_metadata.get(id)

        if wowhead_quest is None:
            print(f"Quest #{id} wasn't found in Wowhead. Taking existing one from ClassicUA DB.")
            quests[id] = classicua_quest
            metadata[id] = classicua_md
            continue

        wowhead_md_raw = wowhead_metadata.get(id)
        wowhead_md = QuestMD_DB(wowhead_md_raw.id, wowhead_md_raw.name, category,
                                wowhead_md_raw.get_side(), wowhead_md_raw.get_type(), wowhead_md_raw.lvl,
                                wowhead_md_raw.rlvl)

        if classicua_quest is None:
            print(f"Adding new quest #{id}")
            quests[id] = wowhead_quest
            metadata[id] = wowhead_md
            continue

        name = wowhead_quest.name
        objective = merge_fields(wowhead_quest.objective, classicua_quest.objective)
        description = merge_fields(wowhead_quest.description, classicua_quest.description)
        progress = merge_fields(wowhead_quest.progress, classicua_quest.progress)
        completion = merge_fields(wowhead_quest.completion, classicua_quest.completion)
        quests[id] = Quest(id, name, objective, description, progress, completion)

        cat = wowhead_md.cat
        side = merge_side(wowhead_md.side, classicua_md.side, id)
        type = wowhead_md.type
        lvl = wowhead_md.lvl if wowhead_md.lvl > 0 else classicua_md.lvl
        rlvl = wowhead_md.rlvl if wowhead_md.rlvl > 0 else classicua_md.rlvl

        metadata[id] = QuestMD_DB(id, name, cat, side, type, lvl, rlvl)

    return quests, metadata


def merge_quest(old_quest, new_quest):
    pass

def merge_expansions(old_expansion: dict[tuple[int, str], QuestEntity], new_expansion: dict[tuple[int, str], QuestEntity]) -> dict[tuple[int, str], QuestEntity]:
    pass


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

    classic_and_tbc_quests = merge_expansions(wowhead_quests, wowhead_quests_tbc)
    all_quests = merge_expansions(classic_and_tbc_quests, wowhead_quests_wrath)
    return

    classicua_data = get_all_quests_from_db('classicua.db')

    classicua_quests = {t[0].id: t[0] for t in classicua_data.values()}
    classicua_metadata = {t[1].id: t[1] for t in classicua_data.values()}

    quests, metadata = merge_all_quests(wowhead_quests, classicua_quests, wowhead_metadata, classicua_metadata)

    fix_quests(quests)
    # fix_metadata(metadata)

    save_quests_to_cache_db(quests, metadata)



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
                print("Differing file:", common_file)
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



if __name__ == '__main__':
    # check_categories() # Check categories and update known_categories in utils if needed

    populate_cache_db_with_quest_data()  # Generate cache/quests.db
    # compare_databases('cache/quests.db', 'classicua.db') # compare cache/quests.db with ./classicua.db (the one we overwrite)

    # generate Crowdin folder for classic with gen_source_for_crowdin.py, put in source_for_crowdin
    # copy existing Crowdin folder, put in source_from_crowdin

    # compare_directories('source_from_crowdin', 'source_for_crowdin')

