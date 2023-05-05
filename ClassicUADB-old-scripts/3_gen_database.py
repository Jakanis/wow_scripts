import sqlite3
import re
from bs4 import BeautifulSoup, element


known_cats = {
    0: ('Eastern Kingdoms', {
        36:     'Alterac Mountains',
        2839:   'Alterac Valley',
        45:     'Arathi Highlands',
        3:      'Badlands',
        25:     'Blackrock Mountain',
        4:      'Blasted Lands',
        46:     'Burning Steppes',
        2257:   'Deeprun Tram',
        1:      'Dun Morogh',
        10:     'Duskwood',
        139:    'Eastern Plaguelands',
        12:     'Elwynn Forest',
        267:    'Hillsbrad Foothills',
        1537:   'Ironforge',
        38:     'Loch Modan',
        44:     'Redridge Mountains',
        51:     'Searing Gorge',
        130:    'Silverpine Forest',
        1519:   'Stormwind City',
        33:     'Stranglethorn Vale',
        8:      'Swamp of Sorrows',
        47:     'The Hinterlands',
        85:     'Tirisfal Glades',
        1497:   'Undercity',
        28:     'Western Plaguelands',
        40:     'Westfall',
        11:     'Wetlands',
    }),
    1: ('Kalimdor', {
        331:    'Ashenvale',
        16:     'Azshara',
        148:    'Darkshore',
        1657:   'Darnassus',
        405:    'Desolace',
        14:     'Durotar',
        15:     'Dustwallow Marsh',
        361:    'Felwood',
        357:    'Feralas',
        493:    'Moonglade',
        215:    'Mulgore',
        1637:   'Orgrimmar',
        702:    'Rut\'theran Village',
        1377:   'Silithus',
        406:    'Stonetalon Mountains',
        440:    'Tanaris',
        141:    'Teldrassil',
        17:     'The Barrens',
        400:    'Thousand Needles',
        1638:   'Thunder Bluff',
        1216:   'Timbermaw Hold',
        490:    'Un\'Goro Crater',
        618:    'Winterspring',
    }),
    2: ('Dungeons', {
        719:    'Blackfathom Deeps',
        1584:   'Blackrock Depths',
        1583:   'Blackrock Spire',
        2557:   'Dire Maul',
        721:    'Gnomeregan',
        2100:   'Maraudon',
        2437:   'Ragefire Chasm',
        722:    'Razorfen Downs',
        491:    'Razorfen Kraul',
        796:    'Scarlet Monastery',
        2057:   'Scholomance',
        209:    'Shadowfang Keep',
        2017:   'Stratholme',
        1581:   'The Deadmines',
        717:    'The Stockade',
        1477:   'The Temple of Atal\'Hakkar',
        1337:   'Uldaman',
        718:    'Wailing Caverns',
        1176:   'Zul\'Farrak',
    }),
    3: ('Raids', {
        2677:   'Blackwing Lair',
        2717:   'Molten Core',
        3456:   'Naxxramas',
        2159:   'Onyxia\'s Lair',
        3429:   'Ruins of Ahn\'Qiraj',
        3428:   'Temple of Ahn\'Qiraj',
        1977:   'Zul\'Gurub',
    }),
    4: ('Classes', {
        -263:   'Druid',
        -261:   'Hunter',
        -161:   'Mage',
        -141:   'Paladin',
        -262:   'Priest',
        -162:   'Rogue',
        -82:    'Shaman',
        -61:    'Warlock',
        -81:    'Warrior',
    }),
    5: ('Professions', {
        -181:   'Alchemy',
        -121:   'Blacksmithing',
        -304:   'Cooking',
        -201:   'Engineering',
        -324:   'First Aid',
        -101:   'Fishing',
        -24:    'Herbalism',
        -182:   'Leatherworking',
        -264:   'Tailoring',
    }),
    6: ('Battlegrounds', {
        2597:   'Alterac Valley',
        3358:   'Arathi Basin',
        -25:    'Battlegrounds',
        3277:   'Warsong Gulch',
    }),
    9: ('World Events', {
        -1002:  'Children\'s Week',
        -364:   'Darkmoon Faire',
        -1003:  'Hallow\'s End',
        -1005:  'Harvest Festival',
        -22:    'Love is in the Air',
        -366:   'Lunar Festival',
        -369:   'Midsummer',
        -1006:  'New Year\'s Eve',
        -1001:  'Winter Veil',
    }),
    7: ('Miscellaneous', {
        -365:   'Ahn\'Qiraj War Effort',
        -1:     'Epic',
        -344:   'Legendary',
        -367:   'Reputation',
        -368:   'Scourge Invasion',
        -22:    'Seasonal',
    }),
}

#######
# utils
#######

def cleanup_text(text):
    return ' '.join(text.strip().split()).replace('$LINEBREAK$', '\n')

def get_forward_text(tag):
    out = ''

    while type(tag.next_sibling) == element.NavigableString:
        tag = tag.next_sibling
        out += str(tag)

    return out

#################
# Wowhead parsing
#################

def get_cat_text(html, title):
    if title == 'The Hunter\'s Path':
        return f'{known_cats[4][0]}/{known_cats[4][1][-261]}' # Classes/Hunter
    elif title == 'Cuergo\'s Gold':
        return f'{known_cats[1][0]}/{known_cats[1][1][440]}' # Kalimdor/Tanaris
    elif title == 'To The Victor...':
        return f'{known_cats[2][0]}/{known_cats[2][1][2017]}' # Dungeons/Stratholme
    elif title == 'Concerted Efforts':
        return 'Uncategorized'

    out = None
    found = re.findall(r'WH.Layout.set\({breadcrumb: \[0, 3, (-?\d+), (-?\d+)\]}\)', html)
    if len(found) == 1:
        # print(found[0])
        cat_id, subcat_id = (int(x) for x in found[0])
        if cat_id == -2:
            if subcat_id == -22:
                out = f'{known_cats[7][0]}/{known_cats[7][1][-22]}' # Miscellaneous/Seasonal
            elif subcat_id == -284:
                out = f'{known_cats[9][0]}/{known_cats[9][1][-1001]}' # World Events/Children's Week
            else:
                out = 'Uncategorized'
        else:
            out = f'{known_cats[cat_id][0]}/{known_cats[cat_id][1][subcat_id]}'

    return out

def get_side_text(html):
    if '[li]Side: [span class=icon-alliance]Alliance[\\/span][\\/li]' in html:
        return 'alliance'
    elif '[li]Side: [span class=icon-horde]Horde[\\/span][\\/li]' in html:
        return 'horde'
    else:
        return 'both'

def get_type_text(html):
    found = re.findall(r'\[li\]Type: (\w+)\[\\/li\]', html)
    if len(found) == 1:
        return found[0].lower()
    return 'normal'

def get_level_ints(html):
    lvl, rlvl = 0, 0

    found = re.findall(r'\[li\]Level: (\d+)\[\\/li\]', html)
    if len(found) == 1:
        lvl = int(found[0])

    found = re.findall(r'\[li\]Requires level (\d+)\[\\/li\]', html)
    if len(found) == 1:
        rlvl = int(found[0])

    return lvl, rlvl

def get_objective_text(soup):
    out = None

    tag = soup.find('h1', class_='heading-size-1')
    if tag:
        text = cleanup_text(get_forward_text(tag.next_sibling.next_sibling.next_sibling))
        if text:
            out = text
        else:
            # check if objective is empty (other section ahead) like in quest#7633
            if tag.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.name != 'h2':
                # skip 'see updated quest page' box like in quest#290
                text = cleanup_text(get_forward_text(tag.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling))
                if text:
                    out = text

    return out

def get_description_text(soup):
    out = None

    tag = soup.find('h2', class_='heading-size-3', text='Description')
    if tag:
        out = cleanup_text(get_forward_text(tag))

    return out

def get_progress_text(soup):
    out = None

    tag = soup.find(id='lknlksndgg-progress')
    if tag:
        out = cleanup_text(tag.get_text())

    if not out:
        tag = soup.find('h2', class_='heading-size-3', text='Progress')
        if tag:
            text = cleanup_text(get_forward_text(tag))
            if text:
                out = text

    return out

def get_completion_text(soup):
    out = None

    tag = soup.find(id='lknlksndgg-completion')
    if tag:
        out = cleanup_text(tag.get_text())

    if not out:
        tag = soup.find('h2', class_='heading-size-3', text='Completion')
        if tag:
            text = cleanup_text(get_forward_text(tag))
            if text:
                out = text

    return out

###################
# ClassicDB parsing
###################

def get_side_text2(html2):
    if '<span class="alliance-icon">Alliance</span>' in html2:
        return 'alliance'
    elif '<span class="horde-icon">Horde</span>' in html2:
        return 'horde'
    else:
        return 'both'

def get_type_text2(html2):
    found = re.findall(r'<div>Type: (\w+)<\/div>', html2)
    if len(found) == 1:
        return found[0].lower()
    return 'normal'

def get_cat_text2(html2):
    found = re.findall(r'g_initPath\(\[0,3,(-?\d+),(-?\d+)\]\);', html2)
    if len(found) == 1:
        # print(found[0])
        cat_id, subcat_id = (int(x) for x in found[0])
        return f'{known_cats[cat_id][0]}/{known_cats[cat_id][1][subcat_id]}'
    return 'Uncategorized'

def get_objective_text2(soup2):
    tag = soup2.find('div', class_='text')
    if tag:
        h1 = tag.find('h1')
        if h1:
            text = cleanup_text(get_forward_text(h1))
            if 'Additional requirements to obtain this quest' in text:
                line = h1.parent.find('div', class_='line')
                if line:
                    text = cleanup_text(get_forward_text(line))
                    if text:
                        return text
            else:
                if text:
                    return text

def get_description_text2(soup2):
    tag = soup2.find('div', class_='text')
    if tag:
        h3 = tag.find('h3', text='Description')
        if h3:
            text = cleanup_text(get_forward_text(h3))
            if text:
                return text

def get_progress_text2(soup2):
    tag = soup2.find('div', id='progress')
    if tag:
        text = cleanup_text(tag.get_text())
        if text:
            return text

def get_completion_text2(soup2):
    tag = soup2.find('div', id='completion')
    if tag:
        text = cleanup_text(tag.get_text())
        if text:
            return text

#############
# main script
#############

ua_conn = sqlite3.connect('database/classicua.db')
ua_conn.execute('''CREATE TABLE IF NOT EXISTS quests (
                            id INTEGER NOT NULL UNIQUE,
                            cat TEXT NOT NULL,
                            side TEXT NOT NULL,
                            type TEXT NOT NULL,
                            lvl INTEGER NOT NULL,
                            rlvl INTEGER NOT NULL,
                            title TEXT NOT NULL,
                            objective TEXT,
                            description TEXT,
                            progress TEXT,
                            completion TEXT
                          )''')
ua_conn.commit()
ua_existing_quest_ids = [ r[0] for r in ua_conn.execute('SELECT id FROM quests') ]

wh_conn = sqlite3.connect('database/wowhead-classicdb-cache.db')
wh_quests = wh_conn.execute(f'SELECT id, title FROM quests WHERE status="ok" ORDER BY id').fetchall() # !! debug: AND id=7633

for id, title in wh_quests:
    if id in ua_existing_quest_ids:
        continue

    print(f'Processing quest #{id} {title}')

    html, html2 = wh_conn.execute(f'SELECT html, html2 FROM quests WHERE id={id}').fetchone()
    soup = BeautifulSoup(html, 'html5lib')
    # print(soup.prettify()) # !! debug

    for br in soup.find_all('br'):
        br.replace_with('$LINEBREAK$')

    cat = get_cat_text(html, title)
    side = get_side_text(html)
    type_ = get_type_text(html)
    lvl, rlvl = get_level_ints(html)
    objective = get_objective_text(soup)
    description = get_description_text(soup)
    progress = get_progress_text(soup)
    completion = get_completion_text(soup)

    if '<span class=q10>This quest doesn\'t exist in our database</span>.' not in html2:
        soup2 = BeautifulSoup(html2, 'html5lib')
        # print(soup2.prettify()) # ! debug

        for br in soup2.find_all('br'):
            br.replace_with('$LINEBREAK$')

        if cat == 'Uncategorized':
            cat = get_cat_text2(html2)

        if side == 'both':
            side = get_side_text2(html2)

        if type_ == 'normal':
            type_ = get_type_text2(html2)

        if not objective:
            objective = get_objective_text2(soup2)

        if not description:
            description = get_description_text2(soup2)

        if not progress:
            progress = get_progress_text2(soup2)

        if not completion:
            completion = get_completion_text2(soup2)

    if objective == 'null':
        objective = None

    if objective and not description and not progress:
        progress = objective
        objective = None

    if objective and objective == description and progress:
        objective = None
        description = None

    if not objective or not description:
        objective = None
        description = None

    if id == 812:
        completion += ' <sigh>'

    if id == 842:
        completion = '''Alright, <name>. You want to earn your keep with the Horde? Well there's plenty to do here, so listen close and do what you're told.

<I see that look in your eyes, do not think I will tolerate any insolence. Thrall himself has declared the Hordes females to be on equal footing with you men. Disrespect me in the slightest, and you will know true pain./I'm happy to have met you. Thrall will be glad to know that more females like you and I are taking the initiative to push forward in the Barrens.>'''

    if id == 8242:
        objective = None
        description = None

    # print(f'id          ---{id}---')
    # print(f'cat         ---{cat}---')
    # print(f'side        ---{side}---')
    # print(f'type        ---{type_}---')
    # print(f'lvl         ---{lvl}---')
    # print(f'rlvl        ---{rlvl}---')
    # print(f'title       ---{title}---')
    # print(f'objective   ---{objective}---')
    # print(f'description ---{description}---')
    # print(f'progress    ---{progress}---')
    # print(f'completion  ---{completion}---')

    if objective or description or progress or completion:
        with ua_conn:
            ua_conn.execute(
                f'INSERT INTO quests(id, side, type, lvl, rlvl, cat, title, objective, description, progress, completion) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (id, side, type_, lvl, rlvl, cat, title, objective, description, progress, completion))

    # break # !! debug
