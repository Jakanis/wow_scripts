import csv
import os
import re
import sys

import requests

from generation.utils import wago
from generation.utils.glossary import Glossary
from generation.utils.issues import IssueLog
from generation.utils.utils import feedback_path

log = IssueLog('zones')

CLASSIC = 'classic'
SOD = 'sod'
FOREVER = 'forever'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
MISTS = 'mists'
INDEX = 'index'
WAGO_PRODUCT = 'wago_product'
WAGO_BUILD = 'wago_build'

# Zone names come from the clients' own tables, as wago.tools exports them per build. The builds are pinned like
# the other modules pin their Wowhead URLs: check_newer_builds() only reports a newer one, because the names it
# brings are a change to look at, not something to take in silently.
expansion_data = {
    CLASSIC: {
        INDEX: 0,
        WAGO_PRODUCT: 'wow_classic_era',
        WAGO_BUILD: '1.14.4.51829'  # the era client just before SoD arrived with 1.15.0
    },
    SOD: {
        INDEX: 0.1,
        WAGO_PRODUCT: 'wow_classic_era',
        WAGO_BUILD: '1.15.9.69722'  # shared with classic, so what it has beyond 1.14.4 is SoD's
    },
    # WoW: Forever, in beta since 2026-09-17: a branch of classic and SoD.
    FOREVER: {
        INDEX: 0.2,
        WAGO_PRODUCT: 'wow_classic_beta',
        WAGO_BUILD: '1.60.1.69977'
    },
    TBC: {
        INDEX: 1,
        WAGO_PRODUCT: 'wow_anniversary',
        WAGO_BUILD: '2.5.6.69795'
    },
    WRATH: {
        INDEX: 2,
        WAGO_PRODUCT: 'wow_classic',
        WAGO_BUILD: '3.4.3.58936'  # ClassicUA_Wrath.toc is 30403, not the later 3.4.4 and 3.4.5 clients
    },
    CATA: {
        INDEX: 3,
        WAGO_PRODUCT: 'wow_classic',
        WAGO_BUILD: '4.4.2.60895'
    },
    MISTS: {
        INDEX: 4,
        WAGO_PRODUCT: 'wow_classic',
        WAGO_BUILD: '5.5.4.69934'
    }
}
# Forever's client is built on retail's and carries retail's rooms as well, most of which no Forever map places.
# A room this retail build has and the SoD client does not is taken for one of those.
RETAIL_BUILD = '12.1.0.69933'

WAGO_CACHE = 'cache/wago'

AREA = 'AreaTable'
MAP = 'Map'
UI_MAP = 'UiMap'
WMO_AREA = 'WMOAreaTable'
UI_MAP_FLOOR = 'UiMapGroupMember'
TAXI = 'TaxiNodes'
POI = 'AreaPOI'
LFG = 'LfgDungeons'
# DB2 table -> the columns read from it, the name first
TABLES = {
    AREA: ('AreaName_lang', 'ID', 'ContinentID', 'ParentAreaID'),
    MAP: ('MapName_lang', 'ID', 'MapType', 'InstanceType', 'ParentMapID', 'Flags_0'),
    UI_MAP: ('Name_lang', 'ID', 'ParentUiMapID'),
    WMO_AREA: ('AreaName_lang', 'ID', 'WMOID', 'AreaTableID'),
    UI_MAP_FLOOR: ('Name_lang', 'ID', 'UiMapID'),
    TAXI: ('Name_lang', 'ID', 'Flags', 'CharacterBitNumber'),
    POI: ('Name_lang', 'ID', 'ContinentID'),
    LFG: ('Name_lang', 'ID')
}
OPTIONAL_TABLES = (UI_MAP_FLOOR,)  # only the Cata and Mists clients have it
# The names that reach ClassicUA as zone text and so go on the translation sheet: zone and room text, map titles,
# instance names, flight points and the pins of a battleground's map. Nothing hooks the dungeon floor menu, and
# dungeon finder names never arrive as zone text; those rows only tell a location term the glossary keeps for
# them apart from a stale one.
LISTED_SOURCES = (AREA, MAP, UI_MAP, WMO_AREA, TAXI, POI)

INSTANCE_TYPES = {1: 'dungeon', 2: 'raid', 3: 'battleground', 4: 'arena', 5: 'scenario'}  # Map.InstanceType
CATEGORIES = {
    'dungeon': 'підземелля',
    'raid': 'рейд',
    'battleground': 'поле битви',
    'arena': 'арена',
    'scenario': 'сценарій'
}
DEVELOPMENT_MAP = 0x2  # Map.Flags_0
ON_FLIGHT_MAP = 0x3  # TaxiNodes.Flags: shown to the Alliance, to the Horde

# Rows the clients carry but never show. They stay in zones.db and are only kept off the translation sheet, so a
# wrong match costs a missing row there, never a translation. [!] Do not match a bare "OLD": ScholomanceOLD is a
# live map name players reported.
UNUSED = re.compile(
    r'unused|\bDNT\b|\*\*\*|\[(?:PH|PL|TEMP|TEMPNAME\s*|RENAME ME)\]|\((?:PH|TEMP|STM)\)|TEMPNAME|RENAME ME|'
    r'do not (?:use|reuse)|not used|delete me|^reuse\b|deprecated|\bprototype\b|\bplaceholder\b|'
    r'\btest(?:ing)?\b|test\d*$|^test|smoketest|'
    r'programmer isle|designer island|development land|dev only|\bdev\b|'
    r'\bjeff [ns][ew] quadrant|\(old\b|\bOLD\)|\bOLD$|^\d+\.\d+[\d.]* ?(?:-|\w)|hackathon|\bcopy$|\w_\w|'
    r'wowedit|spooky area|happy fun land|nothing to see here|^zz|\ufffd',
    re.I)
DEVELOPMENT_MAP_NAME = re.compile(r'\btest\b|test$|unused|development land|dev only|nothing to see here', re.I)
# Flight paths of quests, vehicles and lifts that still show on the flight map
TAXI_INTERNAL = re.compile(r' - |->|\b(?:quest|generic|world target|test|start|end|begin|stop|target|log ride)\b|'
                           r'^AAA|\(new\)', re.I)
# Unmarked names the clients never show
IGNORES = ['Nine', 'Class Quest', 'Force Interior', 'CashTest', 'ElevatorSpawnTest', 'CTF3', 'Sarahland',
           'Pattymack Land', 'Familiars', 'Sub zone', 'TrevorsHouse', 'VaultDungeon', 'LostIsles', 'Gilneas2',
           'Firelands Terrain 2', 'foo', 'always draw', 'SunkenTemple']


class Zone:
    # One named row of one client table. A name usually has several: a dungeon is an AreaTable row, a Map row and
    # a UiMap row, in every client that has it.
    def __init__(self, expansion, source, id, name, parent=None, category=None, unused=None, translation=None):
        self.expansion = expansion
        self.source = source
        self.id = id
        self.name = name
        self.parent = parent
        self.category = category
        self.unused = unused  # why the row stays off the translation sheet
        self.translation = translation

    def __str__(self):
        res = f'{self.source}#{self.id}:{self.expansion} '
        res += f'{self.parent}/' if self.parent else ''
        res += self.name
        res += f' -> {self.translation}' if self.translation else ''
        return res


def __version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split('.'))


def read_wago_table(table: str, build: str) -> list[dict[str, str]]:
    return wago.read_table(table, build, WAGO_CACHE, TABLES[table], optional=table in OPTIONAL_TABLES)


def __trim(text: str) -> str:
    return text.strip(' \t\r\n')  # string.trim in WoW's Lua, which leaves any other whitespace be


def __unused_name(name: str) -> str:
    if name in IGNORES:
        return 'ignored'
    if UNUSED.search(name):
        return 'marked unused'
    return None


def __is_development_map(map: dict[str, str]) -> bool:
    return bool(int(map['Flags_0']) & DEVELOPMENT_MAP) or bool(DEVELOPMENT_MAP_NAME.search(map['MapName_lang']))


def __retail_rooms(rows: list[dict[str, str]]) -> set[str]:
    # Forever's rooms that are retail's and not SoD's, unless Forever uses their building with a room of its own
    sod_rooms = {row['ID'] for row in read_wago_table(WMO_AREA, expansion_data[SOD][WAGO_BUILD])}
    retail_only = {row['ID'] for row in read_wago_table(WMO_AREA, RETAIL_BUILD)} - sod_rooms
    own_buildings = {row['WMOID'] for row in rows if row['ID'] not in retail_only}
    return {row['ID'] for row in rows if row['ID'] in retail_only and row['WMOID'] not in own_buildings}


def parse_zones(expansion) -> list[Zone]:
    build = expansion_data[expansion][WAGO_BUILD]
    tables = {table: read_wago_table(table, build) for table in TABLES}
    maps = {int(row['ID']): row for row in tables[MAP]}
    areas = {int(row['ID']): row for row in tables[AREA]}
    ui_maps = {int(row['ID']): row for row in tables[UI_MAP]}
    rows = []  # (source, id, name, parent, category, unused)

    area_unused = dict()
    for id, row in areas.items():
        map = maps.get(int(row['ContinentID']))
        if not map:
            area_unused[id] = 'no map'
        elif __is_development_map(map):
            area_unused[id] = 'development map'
        else:
            area_unused[id] = __unused_name(__trim(row['AreaName_lang']))
    for id, row in areas.items():
        map = maps.get(int(row['ContinentID']))
        parent = areas.get(int(row['ParentAreaID']))
        unused = area_unused[id] or ('parent unused' if parent and area_unused[int(row['ParentAreaID'])] else None)
        category = None
        if parent:
            parent_name = parent['AreaName_lang']
        elif map and int(map['InstanceType']) in INSTANCE_TYPES:
            parent_name = None  # the top area of an instance, whose map is the instance itself
            category = INSTANCE_TYPES[int(map['InstanceType'])]
        else:
            parent_name = map['MapName_lang'] if map else None  # a top-level zone sits on its continent
        rows.append((AREA, id, row['AreaName_lang'], parent_name, category, unused))

    for id, row in maps.items():
        unused = None
        if __is_development_map(row):
            unused = 'development map'
        elif row['MapType'] == '3':
            unused = 'transport'
        elif row['ParentMapID'] != '-1':
            unused = 'phase map'  # a phase or a terrain swap of another map
        rows.append((MAP, id, row['MapName_lang'], None, INSTANCE_TYPES.get(int(row['InstanceType'])), unused))

    for id, row in ui_maps.items():
        parent = ui_maps.get(int(row['ParentUiMapID']))
        rows.append((UI_MAP, id, row['Name_lang'], parent['Name_lang'] if parent else None, None, None))

    retail_rooms = __retail_rooms(tables[WMO_AREA]) if expansion == FOREVER else set()
    for row in tables[WMO_AREA]:
        # [!] In Forever, a room taken over from retail can point at an area id Forever uses for something else
        # (Utgarde Keep's rooms at 206, Westfall), so trust such a parent less than a classic one
        area = areas.get(int(row['AreaTableID']))
        rows.append((WMO_AREA, int(row['ID']), row['AreaName_lang'], area['AreaName_lang'] if area else None, None,
                     'retail room' if row['ID'] in retail_rooms else None))

    for row in tables[UI_MAP_FLOOR]:
        ui_map = ui_maps.get(int(row['UiMapID']))
        rows.append((UI_MAP_FLOOR, int(row['ID']), row['Name_lang'], ui_map['Name_lang'] if ui_map else None,
                     None, None))

    for row in tables[TAXI]:
        # [!] ClassicUA looks a flight point up whole, or split at the last ", " into two parts it looks up as zones
        # (entries.lua translate_taxi_node_name)
        name = __trim(row['Name_lang'])
        unused = None
        if not int(row['Flags']) & ON_FLIGHT_MAP:
            unused = 'not on the flight map'
        elif row['CharacterBitNumber'] == '0':
            unused = 'never learned'  # a quest's or a vehicle's: every node a player learns carries its own bit
        elif TAXI_INTERNAL.search(name):
            unused = 'internal flight path'
        node, _, zone = name.rpartition(', ')
        if node:
            rows.append((TAXI, int(row['ID']), node, zone, None, unused))
            rows.append((TAXI, int(row['ID']), zone, None, None, unused))
        else:
            rows.append((TAXI, int(row['ID']), name, None, None, unused))

    for row in tables[POI]:
        # A pin's name reaches the map's area label on a battleground or an arena; elsewhere pins are mostly
        # NPCs and trainers
        map = maps.get(int(row['ContinentID']))
        pvp_map = map['MapName_lang'] if map and int(map['InstanceType']) in (3, 4) else None
        rows.append((POI, int(row['ID']), row['Name_lang'], pvp_map, None,
                     None if pvp_map else 'map pin off a battleground'))

    for row in tables[LFG]:
        rows.append((LFG, int(row['ID']), row['Name_lang'], None, None, None))

    zones = []
    for source, id, name, parent, category, unused in rows:
        name = __trim(name)
        if name:
            parent = __trim(parent) if parent else None
            zones.append(Zone(expansion, source, id, name, parent if parent != name else None, category,
                              unused or __unused_name(name)))
    return zones


def retrieve_zone_data() -> list[Zone]:
    zones = {expansion: parse_zones(expansion) for expansion in expansion_data}
    # Classic is read from the era client as it was before SoD, but players see today's: a name that client has
    # dropped since - a typo fixed, a room gone - is shown to no one
    era_names = {zone.name.lower() for zone in zones[SOD]}
    for zone in zones[CLASSIC]:
        if not zone.unused and zone.name.lower() not in era_names:
            zone.unused = 'gone from the era client'

    all_zones = []
    for expansion, expansion_zones in zones.items():
        print(f'Wago({expansion}) {expansion_data[expansion][WAGO_BUILD]}: {len(expansion_zones)} named rows, '
              f'{len({zone.name.lower() for zone in expansion_zones})} names')
        all_zones.extend(expansion_zones)
    return all_zones


def check_newer_builds():
    try:
        builds = wago.wago_get(f'{wago.WAGO_URL}/api/builds').json()
    except (requests.RequestException, ValueError) as e:
        log.warning('newer-build-check-failed', 'zone', f'wago.tools builds are out of reach: {type(e).__name__}')
        return
    for expansion, expansion_properties in expansion_data.items():
        pinned = expansion_properties[WAGO_BUILD]
        versions = [build['version'] for build in builds.get(expansion_properties[WAGO_PRODUCT], [])
                    if build['version'].split('.')[:2] == pinned.split('.')[:2] and not build.get('is_bgdl')]
        newest = max(versions, key=__version_key, default=pinned)
        if __version_key(newest) > __version_key(pinned):
            log.note('newer-build', 'zone', f'wago.tools has {newest} ({expansion_properties[WAGO_PRODUCT]}), '
                                            f'zones read {pinned}', expansion=expansion)


def read_classicua_translations(glossary: Glossary) -> dict[str, str]:
    # [!] Mirrors ClassicUA's dev/gen_zone_lua.py collect_zones, which writes entries/zone.lua from this glossary:
    # every location term in order, each followed by its ~aliases~ where the key is still free
    translations = dict()
    aliases = set()
    for term in glossary:
        if not term.is_location():
            continue
        if term.text_en in aliases and translations[term.text_en] != term.text_uk:
            log.warning('alias-overwritten', 'zone', f'the term "{term.text_en}" -> "{term.text_uk}" replaces an '
                                                     f'alias of the same name -> "{translations[term.text_en]}"',
                        id=term.text_en)
        translations[term.text_en] = term.text_uk
        for alias in term.location_aliases():
            if alias not in translations:
                translations[alias] = term.text_uk
                aliases.add(alias)
            elif alias not in aliases:
                log.warning('alias-taken', 'zone', f'the alias "{alias}" of "{term.text_en}" is a term of its own',
                            id=alias)
    return translations


__ASCII_LOWER = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')


def __lower(text: str) -> str:
    return text.translate(__ASCII_LOWER)  # Lua's lower() changes ASCII letters only


def build_addon_glossary(translations: dict[str, str]) -> dict[str, str]:
    # [!] Mirrors ClassicUA's scripts/entries.lua prepare_glossary for the zone entries: a key is trimmed and
    # lowered, and also takes its "the " twin - the one without "the " only when the key is longer than 8 bytes.
    # The first write wins. The addon puts misc, string and object entries in before zone ones; they are left out
    # here, so a zone name another entry takes (object's "Rock of Durotan") still counts as the zone's.
    glossary = dict()
    for key, value in translations.items():
        key = __lower(__trim(key))
        glossary.setdefault(key, value)
        if key.startswith('the ') and len(key.encode('utf-8')) > 8:
            glossary.setdefault(key[4:], value)
        else:
            glossary.setdefault('the ' + key, value)
    return glossary


def __glossary_key(text: str) -> str:
    # [!] Mirrors how ClassicUA's get_glossary_text prepares a text: utils.lua strip_color_codes pass by pass,
    # first_line_only, then trimmed and lowered
    text = re.sub(r'\|c[0-9a-fA-F]{8}', '', text)
    text = re.sub(r'\|c[0-9a-fA-F]{6} [0-9a-fA-F]', '', text)
    text = text.replace('|r', '')
    text = re.split(r'\n|\r|\|n', text, maxsplit=1)[0]
    return __lower(__trim(text))


def translate(glossary: dict[str, str], text: str) -> str:
    # [!] Mirrors ClassicUA's scripts/entries.lua get_glossary_text: the text itself, Questie's "[..] X" and
    # "[..] X (Y)", and "X (Y)", which answers with X's translation, followed by Y's in brackets when Y has one
    key = __glossary_key(text)
    if key in glossary:
        return glossary[key]
    match = re.search(r'\[.+\] (.*)', key)
    if match and match[1] in glossary:
        return glossary[match[1]]
    match = re.search(r'\[.+\] (.*) \((.*)\)', key)
    if match and match[1] in glossary:
        return glossary[match[1]]
    match = re.match(r'(.*) \((.*)\)', key)
    if match and match[1] in glossary:
        return glossary[match[1]] + (f' ({glossary[match[2]]})' if match[2] in glossary else '')
    return None


def apply_translations_to_data(zones: list[Zone], glossary: dict[str, str]):
    for zone in zones:
        zone.translation = translate(glossary, zone.name)


def save_zones_to_db(zones: list[Zone]):
    import sqlite3
    print('Saving zones to DB')
    conn = sqlite3.connect('cache/zones.db')
    conn.execute('DROP TABLE IF EXISTS zones')
    conn.execute('DROP TABLE IF EXISTS zones_temp')  # the old side-by-side of the scraped sites
    conn.execute('''CREATE TABLE zones (
                        expansion TEXT NOT NULL,
                        source TEXT NOT NULL,
                        id INT NOT NULL,
                        name TEXT NOT NULL,
                        parent TEXT,
                        category TEXT,
                        unused TEXT,
                        translation TEXT
                )''')
    conn.commit()

    with conn:
        for zone in zones:
            conn.execute('INSERT INTO zones(expansion, source, id, name, parent, category, unused, translation) '
                         'VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                         (zone.expansion, zone.source, zone.id, zone.name, zone.parent, zone.category, zone.unused,
                          zone.translation))


def load_zones_from_db(db_path: str = 'cache/zones.db') -> list[Zone]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    return [Zone(*row) for row in conn.execute('SELECT expansion, source, id, name, parent, category, unused, '
                                               'translation FROM zones')]


def __names_glossary(names) -> dict[str, str]:
    # The addon's lookup over plain names, which answers with the name it matched
    return build_addon_glossary({name: name for name in names})


def check_glossary_locations(translations: dict[str, str], zones: list[Zone]):
    # A location term no client shows is often fine - lore and short names that quests use - but it is also how a
    # renamed zone or a typo in a term shows up. Every client name is looked up the way the addon looks it up,
    # noting the term that answers: the "the " rule works one way for keys of 8 bytes or less.
    terms = dict()  # addon key -> every term that has it, as "Jade Forest" and "The Jade Forest" share theirs
    for term in translations:
        for key in build_addon_glossary({term: term}):
            terms.setdefault(key, set()).add(term)
    seen = set()
    for name in {zone.name for zone in zones}:
        key = __glossary_key(name)
        match = re.match(r'(.*) \((.*)\)', key)
        for candidate in (key, *(match.groups() if match else ())):
            seen |= terms.get(candidate, set())
    for term in sorted(translations.keys() - seen):
        log.note('not-in-client', 'zone', f'"{term}" -> "{translations[term]}" is no name in any client', id=term)


def read_zone_feedback() -> set[str]:
    # Zone feedback holds names rather than ids, so check_feedback and read_feedback do not fit it
    names = set()
    with open(feedback_path('zones'), 'r', encoding='utf-8') as input_file:
        for row in csv.reader(input_file, delimiter='\t'):
            if row and __trim(row[0]):
                names.add(__trim(row[0]))
    return names


def check_zone_feedback(zones: list[Zone], feedback: set[str], glossary: dict[str, str]):
    names = __names_glossary(zone.name for zone in zones)
    unknown = sorted(name for name in feedback if translate(names, name) is None)
    untranslated = sorted(name for name in feedback if translate(glossary, name) is None)
    print(f'[feedback] Zone: {len(feedback)} reported, {len(unknown)} unknown, {len(untranslated)} untranslated')
    for name in unknown:
        log.warning('feedback-unknown', 'zone', f'"{name}" is no name in any client', id=name)


def __group_key(name: str) -> str:
    # One key per name the way the addon sees it: "The X" and "X" are one once the key is longer than 8 bytes
    key = __lower(__trim(name))
    return key[4:] if key.startswith('the ') and len(key.encode('utf-8')) > 8 else key


def __first(zones: list[Zone]) -> Zone:
    # The row a name's parent and category come from: the earliest client, then the table a zone name comes from
    # first - an area before its map, a map before a room
    sources = list(TABLES)
    return min(zones, key=lambda zone: (expansion_data[zone.expansion][INDEX], sources.index(zone.source), zone.id))


def __listed(zones: list[Zone]) -> list[Zone]:
    return [zone for zone in zones if zone.source in LISTED_SOURCES and not zone.unused]


def create_translation_sheet(zones: list[Zone], feedback: set[str], glossary: dict[str, str],
                             path: str = 'output/translate_this.tsv'):
    reported = __names_glossary(feedback)
    by_name = dict()
    for zone in zones:
        if zone.translation is None:
            by_name.setdefault(__group_key(zone.name), []).append(zone)

    rows = []
    for name_zones in by_name.values():
        in_feedback = any(translate(reported, zone.name) is not None for zone in name_zones)
        shown = __listed(name_zones) or (name_zones if in_feedback else [])
        if not shown:
            continue
        first = __first(shown)
        expansions = sorted({zone.expansion for zone in shown}, key=lambda exp: expansion_data[exp][INDEX])
        sources = [source for source in TABLES if any(zone.source == source for zone in shown)]
        rows.append([first.name, '', ', '.join(expansions), ', '.join(sources), first.parent or '',
                     translate(glossary, first.parent) or '' if first.parent else '', first.category or '',
                     'feedback' if in_feedback else '',
                     expansion_data[expansions[0]][INDEX]])

    names = __names_glossary(zone.name for zone in zones)
    for name in sorted(feedback):
        if translate(names, name) is None and translate(glossary, name) is None:
            rows.append([name, '', '', '', '', '', '', 'feedback', -1])

    rows.sort(key=lambda row: (row[-1], row[0].lower()))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as output_file:
        writer = csv.writer(output_file, delimiter='\t', lineterminator='\n')
        writer.writerow(['Name(EN)', 'Name(UA)', 'expansions', 'sources', 'Parent(EN)', 'Parent(UA)', 'category',
                         'Note'])
        writer.writerows(row[:-1] for row in rows)
    print(f'Wrote {len(rows)} untranslated zone name(s) to {path}')


def read_new_translations(path: str = 'input/new_translations.tsv') -> list[tuple[str, str, str]]:
    # English name, its translation and, optionally, the parent: in English when the clients' parent is not the
    # one, or already in Ukrainian as the older rows have it
    result = []
    if not os.path.exists(path):
        return result
    with open(path, 'r', encoding='utf-8') as input_file:
        for row in csv.reader(input_file, delimiter='\t'):
            if len(row) < 2 or not row[0].strip() or not row[1].strip():
                print(f'Skipping {row}')
                continue
            result.append((row[0].strip(), row[1].strip(), row[2].strip() if len(row) > 2 else ''))
    return result


def create_glossary_import(zones: list[Zone], glossary: dict[str, str],
                           path: str = 'output/new_zones_dictionary.csv'):
    # New location terms for Crowdin's glossary import, in the shape existing terms have: "локація", then the kind
    # of an instance, then the parent's Ukrainian name
    new_translations = read_new_translations()
    new_glossary = build_addon_glossary({name: name_ua for name, name_ua, _ in new_translations})
    by_name = dict()
    for zone in zones:
        by_name.setdefault(__group_key(zone.name), []).append(zone)

    lines = ['"Term [uk]","Term [en]","Description [en]"']
    for name, name_ua, given_parent in new_translations:
        if translate(glossary, name) is not None:
            log.note('already-translated', 'zone', f'"{name}" -> "{translate(glossary, name)}" is in the glossary '
                                                   f'already, "{name_ua}" is left out', id=name)
            continue
        name_zones = by_name.get(__group_key(name)) or by_name.get(__group_key(name[4:] if name.startswith('The ')
                                                                               else 'The ' + name))
        first = __first(__listed(name_zones) or name_zones) if name_zones else None
        parent = given_parent or (first.parent if first else None)
        description = ['локація']
        if first and first.category:
            description.append(CATEGORIES[first.category])
        if parent:
            parent_ua = translate(glossary, parent) or translate(new_glossary, parent)
            if not parent_ua and given_parent:
                parent_ua = given_parent  # taken as the Ukrainian text itself
            if not parent_ua:
                log.warning('parent-untranslated', 'zone', f'the parent "{parent}" of "{name}" has no translation',
                            id=name)
            elif parent_ua not in description:
                description.append(parent_ua)
        # The addon puts "the " back in front of a key itself, so the term goes without it
        name_en = name[4:] if name.startswith('The ') else name
        lines.append('"{}","{}","{}"'.format(name_ua.replace('"', '""'), name_en.replace('"', '""'),
                                             ', '.join(description).replace('"', '""')))

    with open(path, 'w', encoding='utf-8') as out_file:
        out_file.writelines('\n'.join(lines))
    print(f'Wrote {len(lines) - 1} new glossary term(s) to {path}')


if __name__ == '__main__':
    glossary = Glossary.load()

    all_zones = retrieve_zone_data()  # Downloads cache/wago/<table>_<build>.csv once per build
    translations = read_classicua_translations(glossary)  # What ClassicUA's entries/zone.lua holds
    addon_glossary = build_addon_glossary(translations)
    apply_translations_to_data(all_zones, addon_glossary)
    save_zones_to_db(all_zones)  # Generate cache/zones.db

    check_glossary_locations(translations, all_zones)
    feedback = read_zone_feedback()
    check_zone_feedback(all_zones, feedback, addon_glossary)

    create_translation_sheet(all_zones, feedback, addon_glossary)  # Generate output/translate_this.tsv
    create_glossary_import(all_zones, addon_glossary)  # input/new_translations.tsv -> output/new_zones_dictionary.csv

    check_newer_builds()
    sys.exit(log.finish())
