from slpp import slpp as lua
import os
import xml.etree.ElementTree as ET
import sqlite3
from lxml import html


Object = lambda **kwargs: type("Object", (), kwargs)

def parse_html_tooltip(id, html_tooltip_tree):
    import re
    descs = list()
    equip = list()
    chance_on_hit = list()
    use = list()
    flavor = list()
    readable = False
    recipe = False
    replaced_tooltip = html_tooltip_tree.text.replace('<br>', '').replace('<br />', '')
    replaced_tooltip = re.sub(r'<!--ppl.+?-->', '', replaced_tooltip)
    res = html.fromstring(replaced_tooltip)
    spans1 = res.findall('table[1]/tr/td/span')
    for span in spans1:
        span_text = span.text
        if (span_text != None and span_text != "Item Level " and span_text != '<Random enchantment>'):
            descs.append(span_text)
    spans = res.findall('table[2]/tr/td/span')
    for span in spans:
        a_tag = span.findall('a')
        if a_tag is not None and len(a_tag) and a_tag[0] is not None:
            href = a_tag[0].attrib.get('href')
            if href is not None and '/item=' in href:
                recipe = True
                break 
        span_text = span.text
        # print(span_text)
        if (span_text is not None):
            if (span_text == 'Equip: '):
                a_tag = span.findall('a')
                if (len(a_tag)!=1):
                    print(f'Check #{id}')
                for tag in a_tag:
                    tag_text = tag.text
                    # print(tag.text)
                    if tag_text is not None:
                        equip.append(tag_text)
                if a_tag is None or not len(a_tag):
                    print('ERROR')

            if (span_text == 'Chance on hit: '):
                a_tag = span.findall('a')
                if (len(a_tag)!=1):
                    print(f'Check #{id}')
                for tag in a_tag:
                    tag_text = tag.text
                    # print(tag.text)
                    if tag_text is not None:
                        chance_on_hit.append(tag_text)
                if a_tag is None or not len(a_tag):
                    print('ERROR')

            if (span_text == 'Use: '):
                a_tag = span.findall('a')
                if (len(a_tag)!=1):
                    print(f'Check #{id}')
                for tag in a_tag:
                    if tag.text is not None:
                        tag_text = tag.text
                        if tag.tail is not None:
                            tag_text += tag.tail
                        use.append(tag_text)
                if a_tag is None or not len(a_tag):
                    print('ERROR')

            if (span_text.startswith('"') and span_text.endswith('"')):
                flavor.append(span_text[1:-1])

            if (span_text == '<Right Click to Read>'):
                readable = True

    return Object(descs = descs,
                  equips = equip, 
                  hits = chance_on_hit, 
                  uses = use, 
                  flavor = flavor, 
                  readable = readable,
                  recipe = recipe)
    
def parse_wowhead_item_data(id, tree):
    # print(f'Item#{id}')
    root = tree.getroot()

    xml_id = root.find('item').attrib['id']
    name = root.find('item/name').text
    level = root.find('item/level').text
    quality_id = root.find('item/quality').attrib['id']
    quality_id = root.find('item/quality').text
    class_id = root.find('item/class').attrib['id']
    class_name = root.find('item/class').text
    subclass_id = root.find('item/subclass').attrib['id']
    subclass_name = root.find('item/subclass').text
    inventory_slot_id = root.find('item/inventorySlot').attrib['id']
    inventory_slot_name = root.find('item/inventorySlot').text
    html_tooltip = root.find('item/htmlTooltip').text
    json = root.find('item/json').text
    json_equip = root.find('item/jsonEquip').text
    link = root.find('item/link').text

    item = parse_html_tooltip(id, root.find('item/htmlTooltip'))

def parse_item_lists(id, tree):
    # print(f'Item#{id}')
    root = tree.getroot()

    xml_id = root.find('item').attrib['id']
    name = root.find('item/name').text

    item = parse_html_tooltip(id, root.find('item/htmlTooltip'))
    return Object(id = xml_id,
                  name = name,
                  descs = item.descs,
                  equips = item.equips, 
                  hits = item.hits, 
                  uses = item.uses, 
                  flavor = item.flavor, 
                  readable = item.readable, 
                  recipe = item.recipe)

def parse_item_str(id, tree):
    # print(f'Item#{id}')
    root = tree.getroot()

    xml_id = root.find('item').attrib['id']
    name = root.find('item/name').text

    item = parse_html_tooltip(id, root.find('item/htmlTooltip'))
    return Object(id = xml_id,
                  name = name,
                  descs = '\n'.join(item.descs) if len(item.descs) else None,
                  equips = '\n'.join(item.equips) if len(item.equips) else None, 
                  hits = '\n'.join(item.hits) if len(item.hits) else None, 
                  uses = '\n'.join(item.uses) if len(item.uses) else None, 
                  flavor = '\n'.join(item.flavor) if len(item.flavor) else None, 
                  readable = item.readable, 
                  recipe = item.recipe)

def parse_items_from_xmls_to_db():
    conn = sqlite3.connect('wow_db.db')
    cur = conn.cursor()

    for root, dirs, files in os.walk('./items_xml'):
        for fileName in files:
            # print(fileName)
            tree = ET.parse(f'items_xml/{fileName}')
            root = tree.getroot()
            file_id = fileName.replace('.xml', '')

            item = parse_item_str(file_id, tree)

            item_xml = (item.id,item.name,item.descs,item.equips,item.hits,item.uses,item.flavor,item.readable,item.recipe)
            sql = ''' INSERT INTO items_classic(id,name,desc,equip,hit,use,flavor,readable,recipe)
                VALUES(?,?,?,?,?,?,?,?,?) '''
            cur.execute(sql, item_xml)
    conn.commit()

def parse_items_lua():
    with open('entries/item.lua', 'r') as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)
        item_117 = decoded_items_lua[117]
        print(item_117)
        reencoded_items_lua = lua.encode(item_117)
        # print(reencoded_items_lua)
        with open(f'items_temp.lua', 'w') as output_file:
            output_file.writelines(reencoded_items_lua)

def item_to_lua_line(item):
    res_str = ''
    if (item.name_ua):
        escaped_name = item.name_ua.replace('"', '\\"')
        res_str+=f'[{item.id}] = {{ "{escaped_name}"'
    else:
        res_str+=f'[{item.id}] = {{ '
    if (item.descs_ua):
        if type(item.descs_ua) == int:
            res_str+=f', use={item.uses_ua}'
        else:
            arr = list(map(lambda x: x.replace('"', '\\"'), item.descs_ua))
            if (len(arr) == 1):
                res_str+=f', desc="{arr[0]}"'
            else:
                res_str+=', desc={ "' + '", "'.join(arr) + '" }'

    if (item.equips_ua):
        if type(item.equips_ua) == int:
            res_str+=f', use={item.uses_ua}'
        else:
            arr = list(map(lambda x: x.replace('"', '\\"'), item.equips_ua))
            if (len(arr) == 1):
                res_str+=f', equip="{arr[0]}"'
            else:
                res_str+=', equip={ "' + '", "'.join(arr) + '" }'

    if (item.hits_ua):
        if type(item.hits_ua) == int:
            res_str+=f', use={item.uses_ua}'
        else:
            arr = list(map(lambda x: x.replace('"', '\\"'), item.hits_ua))
            if (len(arr) == 1):
                res_str+=f', hit="{arr[0]}"'
            else:
                res_str+=', hit={ "' + '", "'.join(arr) + '" }'
            
    if (item.uses_ua):
        if type(item.uses_ua) == int:
            res_str+=f', use={item.uses_ua}'
        else:
            arr = list(map(lambda x: x.replace('"', '\\"'), item.uses_ua))
            if (len(arr) == 1):
                res_str+=f', use="{arr[0]}"'
            else:
                res_str+=', use={ "' + '", "'.join(arr) + '" }'
            
    if (item.flavor_ua):
        if type(item.flavor_ua) == int:
            res_str+=f', use={item.uses_ua}'
        else:
            arr = list(map(lambda x: x.replace('"', '\\"'), item.flavor_ua))
            if (len(arr) == 1):
                res_str+=f', flavor="{arr[0]}"'
            else:
                res_str+=', flavor={ "' + '", "'.join(arr) + '" }'

    if (item.ref):
        if (item.name_ua):
            res_str+=f', ref={item.ref}'
        else:
            res_str+=f'ref={item.ref}'
    
    res_str+=f' }}, -- {item.name}'
    if not item.ref:
        res_str += ''.join([f', @desc {desc}' for desc in item.descs]) if item.descs else ''
        res_str += ''.join([f', @equip {equip}' for equip in item.equips]) if item.equips else ''
        res_str += ''.join([f', @hit {hit}' for hit in item.hits]) if item.hits else ''
        res_str += ''.join([f', @use {use}' for use in item.uses]) if item.uses else ''
        res_str += ''.join([f', @flavor {flavor}' for flavor in item.flavor]) if item.flavor else ''
    return res_str

def get_item_from_db(cursor, id):
    sql = f'SELECT * FROM items_classic WHERE id={id}'
    res = cursor.execute(sql)
    item = res.fetchone()
    if item:
        return Object(id = item[0],
                      name = item[1],
                      equips = item[2].split("\n") if item[2] else None,
                      hits = item[3].split("\n") if item[3] else None,
                      uses = item[4].split("\n") if item[4] else None,
                      flavor = item[5].split("\n") if item[5] else None,
                      descs = item[6].split("\n") if item[6] else None,
                      readable = item[7])
    else:
        return Object(id = id,
                      name = None,
                      equips = None,
                      hits = None,
                      uses = None,
                      flavor = None,
                      descs = None,
                      readable = None)


def decoded_item_to_item(id, item):
    if type(item) == list:
        return Object(id = id,
                      name = item[0],
                      equips = None,
                      hits = None,
                      uses = None,
                      flavor = None,
                      descs = None,
                      ref = None)
    return Object(id = id,
                  name = item.get(0),
                  equips = [item.get('equip')] if type(item.get('equip')) == str else item.get('equip'), 
                  hits = [item.get('hit')] if type(item.get('hit')) == str else item.get('hit'),
                  uses = [item.get('use')] if type(item.get('use')) == str else item.get('use'), 
                  flavor = [item.get('flavor')] if type(item.get('flavor')) == str else item.get('flavor'),
                  descs = [item.get('desc')] if type(item.get('desc')) == str else item.get('desc'),
                  ref = item.get('ref') or None)

def items_to_lua_line(original, translated):
    item = Object(id = original.id,
                  name = original.name,
                  descs = original.descs,
                  equips = original.equips, 
                  hits = original.hits,
                  uses = original.uses, 
                  flavor = original.flavor,
                  name_ua = translated.name,
                  descs_ua = translated.descs,
                  equips_ua = translated.equips, 
                  hits_ua = translated.hits,
                  uses_ua = translated.uses, 
                  flavor_ua = translated.flavor,
                  ref = translated.ref)
    return item_to_lua_line(item)

def combine_existing_translation():
    decoded_items_lua = None

    with open('entries/item.lua', 'r', encoding="utf-8") as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)

    conn = sqlite3.connect('wow_db.db')
    cursor = conn.cursor()
    result_lines = list()
    for id in sorted(decoded_items_lua):
        print(id)
        orig_item = get_item_from_db(cursor, id)
        translated_item = decoded_item_to_item(id, decoded_items_lua[id])
        lua_line = items_to_lua_line(orig_item, translated_item)
        result_lines.append(lua_line+'\n')
    cursor.close()
    with open(f'items_temp.lua', 'w', encoding="utf-8") as output_file:
        output_file.writelines(result_lines)

def items_to_tsv_line(original_item, translated_item):
    result_str = ''
    result_str += str(original_item.id) + '\t'
    result_str += str(original_item.name) + '\t'
    result_str += str(translated_item.name) + '\t'

    desc_en = ''
    desc_en += '\n'.join(map(lambda x: 'Desc: ' + x, original_item.descs)) if original_item.descs else ''
    desc_en += '\n' if (desc_en != '' and original_item.equips) else ''
    desc_en += '\n'.join(map(lambda x: 'Equip: ' + x, original_item.equips)) if original_item.equips else ''
    desc_en += '\n' if (desc_en != '' and original_item.hits) else ''
    desc_en += '\n'.join(map(lambda x: 'Hit: ' + x, original_item.hits)) if original_item.hits else ''
    desc_en += '\n' if (desc_en != '' and original_item.uses) else ''
    desc_en += '\n'.join(map(lambda x: 'Use: ' + x, original_item.uses)) if original_item.uses else ''
    desc_en += '\n' if (desc_en != '' and original_item.flavor) else ''
    desc_en += '\n'.join(map(lambda x: 'Flavor: ' + x, original_item.flavor)) if original_item.flavor else ''
    desc_en = desc_en.replace('"', '""')
    result_str += f'"{desc_en}"\t'
    desc_ua = ''
    desc_ua += '\n'.join(map(lambda x: 'Desc: ' + x, translated_item.descs)) if translated_item.descs else ''
    desc_ua += '\n' if (desc_ua != '' and translated_item.equips) else ''
    desc_ua += '\n'.join(map(lambda x: 'Equip: ' + x, translated_item.equips)) if translated_item.equips else ''
    desc_ua += '\n' if (desc_ua != '' and translated_item.hits) else ''
    desc_ua += '\n'.join(map(lambda x: 'Hit: ' + x, translated_item.hits)) if translated_item.hits else ''
    desc_ua += '\n' if (desc_ua != '' and translated_item.uses) else ''
    desc_ua += '\n'.join(map(lambda x: 'Use: ' + x, translated_item.uses)) if translated_item.uses else ''
    desc_ua += '\n' if (desc_ua != '' and translated_item.flavor) else ''
    desc_ua += '\n'.join(map(lambda x: 'Flavor: ' + x, translated_item.flavor)) if translated_item.flavor else ''
    desc_ua = desc_ua.replace('"', '""')
    result_str += f'"{desc_ua}"\t'

    if (original_item.readable == 'True'):
        result_str += 'READABLE'
    return result_str


def items_lua_to_tsv() -> None:
    decoded_items_lua = None

    # with open('entries/item.lua', 'r') as input_file:
    with open('entries/item.lua', 'r') as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)

    conn = sqlite3.connect('wow_db.db')
    cursor = conn.cursor()
    result_lines = list()
    result_lines += 'ID\tName(EN)\tName(UA)\tDescription(EN)\t"Description(UA)"\tNote\n'
    for id in sorted(decoded_items_lua):
        print(id)
        orig_item = get_item_from_db(cursor, id)
        translated_item = decoded_item_to_item(id, decoded_items_lua[id])
        tsv_line = items_to_tsv_line(orig_item, translated_item)
        result_lines.append(str(tsv_line)+'\n')

    cursor.close()
    with open(f'items_temp.tsv', 'w') as output_file:
        output_file.writelines(result_lines)

def combine_pending_item_with_db_to_tsv_line(pending_item, original_item):
    desc_db = ''
    desc_db += '\n'.join(map(lambda x: 'Desc: ' + x, original_item.descs)) if original_item.descs else ''
    desc_db += '\n' if (desc_db != '' and original_item.equips) else ''
    desc_db += '\n'.join(map(lambda x: 'Equip: ' + x, original_item.equips)) if original_item.equips else ''
    desc_db += '\n' if (desc_db != '' and original_item.hits) else ''
    desc_db += '\n'.join(map(lambda x: 'Hit: ' + x, original_item.hits)) if original_item.hits else ''
    desc_db += '\n' if (desc_db != '' and original_item.uses) else ''
    desc_db += '\n'.join(map(lambda x: 'Use: ' + x, original_item.uses)) if original_item.uses else ''
    desc_db += '\n' if (desc_db != '' and original_item.flavor) else ''
    desc_db += '\n'.join(map(lambda x: 'Flavor: ' + x, original_item.flavor)) if original_item.flavor else ''

    result_str = ''
    result_str += '"' + pending_item.id.replace('"', '""') + '"\t'
    result_str += '"' + pending_item.name.replace('"', '""') + '"\t'
    result_str += '"' + pending_item.name_ua.replace('"', '""') + '"\t'
    result_str += '"' + pending_item.desc.replace('"', '""') + '"\t'
    result_str += '"' + pending_item.desc_ua.replace('"', '""') + '"\t'
    result_str += '"' + pending_item.note.replace('"', '""') + '"\t'
    result_str += '"' + original_item.name.replace('"', '""') + '"\t'
    result_str += '"' + desc_db.replace('"', '""') + '"\t'
    if (original_item.readable):
        result_str += 'READABLE'

    return result_str


def combine_pending_items_with_db():
    import csv
    pending_items = list()

    with open('pending_items.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            if (row[0] == 'ID'):
                continue
            item = Object(id = row[0],
                  name = row[1],
                  name_ua = row[2],
                  desc = row[3], 
                  desc_ua = row[4],
                  note = row[5])
            pending_items.append(item)

    print(f'Pending items count: {len(pending_items)}')
    conn = sqlite3.connect('wow_db.db')
    cursor = conn.cursor()
    result_lines = list()
    result_lines += 'ID\tName(EN)\tName(UA)\tDescription(EN)\tDescription(UA)\tNote\tName(DB)\tDescription(DB)\tReadable(DB)\n'
    for pending_item in pending_items:
        original_item = get_item_from_db(cursor, pending_item.id)
        tsv_line = combine_pending_item_with_db_to_tsv_line(pending_item, original_item)
        result_lines.append(str(tsv_line)+'\n')

    with open(f'combined_pending_items.tsv', 'w', encoding="utf-8") as output_file:
        output_file.writelines(result_lines)


def check_pending_items():
    import csv
    decoded_items_lua = None
    with open('entries/item.lua', 'r', encoding="utf-8") as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)
    existing_items_ids = set(decoded_items_lua.keys())
    pending_items_ids = set()

    clashing_translations = list()
    with open('pending_items.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            if (row[0] == 'ID'):
                continue
            pending_id = int(row[0])
            if pending_id in pending_items_ids:
                print(f"Duplicate: {pending_id}")
            if pending_id in existing_items_ids:
                existing_item = decoded_item_to_item(pending_id, decoded_items_lua.get(pending_id))
                clashing_item = Object(id = int(row[0]),
                  name_en = row[1],
                  pending_name = row[2],
                  existing_name = existing_item.name,
                  pending_desc = row[4],
                #   existing_desc = f'{existing_item.equips if existing_item.equips else ""}\n{existing_item.hits if existing_item.hits else ""}\n{existing_item.uses if existing_item.uses else ""}\n{existing_item.flavor if existing_item.flavor else ""}\n{existing_item.descs if existing_item.descs else ""}')
                  existing_desc = '')
                if (existing_item.name == row[2]):
                    print(f"Exists: {pending_id}. {row[2]} == {decoded_items_lua.get(pending_id)[0]}")
                else:
                    print(f"Exists: {pending_id}. {row[2]} <> {decoded_items_lua.get(pending_id)[0]}")
                clashing_translations.append(clashing_item)
            pending_items_ids.add(pending_id)


    with open(f'clashing_items.tsv', 'w', encoding="utf-8") as output_file:
        output_file.write('ID\tEN Name\tPending name\tExisting name\tPending desc\tExisting desc\n')
        for item in clashing_translations:
            escaped_name_en = item.name_en.replace('"', '\\"')
            escaped_pending_name = item.pending_name.replace('"', '\\"')
            escaped_existing_name = item.existing_name.replace('"', '\\"')
            escaped_pending_desc = item.pending_desc.replace('"', '\\"')
            output_file.write(f'{item.id}\t{escaped_name_en}\t{escaped_pending_name}\t{escaped_existing_name}\t"{escaped_pending_desc}"\t"{item.existing_desc}"\n')

def pending_item_row_to_item(row):
    descs_ua = list()
    equips_ua = list()
    hits_ua = list()
    uses_ua = list()
    flavor_ua = list()
    if len(row) > 4:
        for desc in row[4].split("\n"):
            if (desc.startswith('Desc:')):
                descs_ua.append(desc.replace('Desc: ', ''))
            if (desc.startswith('Equip:')):
                equips_ua.append(desc.replace('Equip: ', ''))
            if (desc.startswith('Hit:')):
                hits_ua.append(desc.replace('Hit: ', ''))
            if (desc.startswith('Use:')):
                uses_ua.append(desc.replace('Use: ', ''))
            if (desc.startswith('Flavor:')):
                flavor_ua.append(desc.replace('Flavor: ', ''))
    elif len(row) > 3:
        print('Warning! Desc not translated?')

    item = Object(id=int(row[0].replace(':sod', '').replace(':tbc', '')),
                  name=row[2],
                  descs=descs_ua if descs_ua else None,
                  equips=equips_ua if equips_ua else None,
                  hits=hits_ua if hits_ua else None,
                  uses=uses_ua if uses_ua else None,
                  flavor=flavor_ua if flavor_ua else None,
                  ref=None)
    return item

def combine_pending_and_existing_translation():
    import csv
    decoded_items_lua = None

    with open('entries/item.lua', 'r', encoding="utf-8") as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)
        decoded_items_lua = {k: decoded_item_to_item(k, v) for k, v in decoded_items_lua.items()}

    pending_items = dict()

    with open('pending_items.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            if (row[0] == 'ID'):
                continue
            id = int(row[0].replace(':sod', '').replace(':tbc', ''))
            pending_item = pending_item_row_to_item(row)
            pending_items[pending_item.id] = pending_item

    conn = sqlite3.connect('wow_db.db')
    cursor = conn.cursor()
    result_lines = list()
    
    all_items = decoded_items_lua | pending_items
    for id in sorted(all_items):
        print(id)
        orig_item = get_item_from_db(cursor, id)
        lua_line = items_to_lua_line(orig_item, all_items[id])
        result_lines.append(lua_line+'\n')
    cursor.close()
    with open(f'items_merged.lua', 'w', encoding="utf-8") as output_file:
        output_file.writelines(result_lines)

def merge_pending_and_existing_items_to_tsv():
    import csv
    decoded_items_lua = None

    with open('entries/item.lua', 'r', encoding="utf-8") as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)
        decoded_items_lua = {k: decoded_item_to_item(k, v) for k, v in decoded_items_lua.items()}

    pending_items = dict()

    with open('pending_items.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            if (row[0] == 'ID'):
                continue
            id = int(row[0])
            pending_item = pending_item_row_to_item(row)
            pending_items[pending_item.id] = pending_item

    conn = sqlite3.connect('wow_db.db')
    cursor = conn.cursor()
    result_lines = list()
    
    all_items_ids = sorted(decoded_items_lua.keys() | pending_items.keys())
    for id in all_items_ids:
        print(id)
        orig_item = get_item_from_db(cursor, id)
        existing_item = decoded_items_lua.get(id)
        pending_item = pending_items.get(id)

        escaped_name_en = orig_item.name.replace('"', '""')
        escaped_pending_name = pending_item.name.replace('"', '""') if pending_item else ''
        escaped_existing_name = existing_item.name.replace('"', '""') if existing_item else ''

        pending_desc = ''
        if pending_item:
            pending_desc += '\n'.join(map(lambda x: 'Desc: ' + x, pending_item.descs)) if pending_item.descs else ''
            pending_desc += '\n' if (pending_desc != '' and pending_item.equips) else ''
            pending_desc += '\n'.join(map(lambda x: 'Equip: ' + x, pending_item.equips)) if pending_item.equips else ''
            pending_desc += '\n' if (pending_desc != '' and pending_item.hits) else ''
            pending_desc += '\n'.join(map(lambda x: 'Hit: ' + x, pending_item.hits)) if pending_item.hits else ''
            pending_desc += '\n' if (pending_desc != '' and pending_item.uses) else ''
            pending_desc += '\n'.join(map(lambda x: 'Use: ' + x, pending_item.uses)) if pending_item.uses else ''
            pending_desc += '\n' if (pending_desc != '' and pending_item.flavor) else ''
            pending_desc += '\n'.join(map(lambda x: 'Flavor: ' + x, pending_item.flavor)) if pending_item.flavor else ''
        escaped_pending_desc = pending_desc.replace('"', '""')

        existing_desc = ''
        if existing_item:
            existing_desc += '\n'.join(map(lambda x: 'Desc: ' + x, existing_item.descs)) if existing_item.descs else ''
            existing_desc += '\n' if (existing_desc != '' and existing_item.equips) else ''
            existing_desc += '\n'.join(map(lambda x: 'Equip: ' + x, existing_item.equips)) if existing_item.equips else ''
            existing_desc += '\n' if (existing_desc != '' and existing_item.hits) else ''
            existing_desc += '\n'.join(map(lambda x: 'Hit: ' + x, existing_item.hits)) if existing_item.hits else ''
            existing_desc += '\n' if (existing_desc != '' and existing_item.uses) else ''
            existing_desc += '\n'.join(map(lambda x: 'Use: ' + x, existing_item.uses)) if existing_item.uses else ''
            existing_desc += '\n' if (existing_desc != '' and existing_item.flavor) else ''
            existing_desc += '\n'.join(map(lambda x: 'Flavor: ' + x, existing_item.flavor)) if existing_item.flavor else ''
        escaped_existing_desc = existing_desc.replace('"', '""')

        desc_db = ''
        desc_db += '\n'.join(map(lambda x: 'Desc: ' + x, orig_item.descs)) if orig_item.descs else ''
        desc_db += '\n' if (desc_db != '' and orig_item.equips) else ''
        desc_db += '\n'.join(map(lambda x: 'Equip: ' + x, orig_item.equips)) if orig_item.equips else ''
        desc_db += '\n' if (desc_db != '' and orig_item.hits) else ''
        desc_db += '\n'.join(map(lambda x: 'Hit: ' + x, orig_item.hits)) if orig_item.hits else ''
        desc_db += '\n' if (desc_db != '' and orig_item.uses) else ''
        desc_db += '\n'.join(map(lambda x: 'Use: ' + x, orig_item.uses)) if orig_item.uses else ''
        desc_db += '\n' if (desc_db != '' and orig_item.flavor) else ''
        desc_db += '\n'.join(map(lambda x: 'Flavor: ' + x, orig_item.flavor)) if orig_item.flavor else ''
        escaped_desc_en = desc_db.replace('"', '""')

        tsv_line = f'{id}\t"{escaped_name_en}"\t"{escaped_pending_name}"\t"{escaped_existing_name}"\t"{escaped_pending_desc}"\t"{escaped_existing_desc}"\t"{escaped_desc_en}"'
        result_lines.append(tsv_line+'\n')
    cursor.close()
    
    with open(f'all_items.tsv', 'w', encoding="utf-8") as output_file:
        output_file.write('ID\tEN Name\tPending name\tExisting name\tPending desc\tExisting desc\tEN Desc\n')
        output_file.writelines(result_lines)


if __name__ == '__main__':
    # parse_items_from_xmls_to_db()
    # parse_items_lua()
    # combine_existing_translation()
    # items_lua_to_tsv()
    # combine_pending_items_with_db()
    # check_pending_items()
    combine_pending_and_existing_translation()
    # merge_pending_and_existing_items_to_tsv()

# tree = ET.parse(f'items_xml/1127.xml')
# root = tree.getroot()

# item = parse_item_str(1127, tree)

# item_xml = (item.id,item.name,item.descs,item.equips,item.hits,item.uses,item.flavor,item.readable,item.recipe)    
# print(item_xml)

# tree = ET.parse(f'items_xml/10644.xml')
# root = tree.getroot()

# item = parse_item_str(10644, tree)


# lua_keys = decoded_items_lua.keys().sorted()
    # for key in lua_keys:
    #     tree = ET.parse(f'items_xml/{key}.xml')
    #     root = tree.getroot()
    #     item = parse_item_lists(key, tree)

    #     print(item_to_lua_line(item))


# conn = sqlite3.connect('wow_db.db')

# tree = ET.parse(f'items_xml/117.xml')
# root = tree.getroot()
# file_id = 117

# item = parse_item_str(file_id, tree)

# item_xml = (item.id,item.name,item.descs,item.equips,item.hits,item.uses,item.flavor,item.readable)
# sql = ''' INSERT INTO items_classic(id,name,desc,equip,hit,use,flavor,readable)
#     VALUES(?,?,?,?,?,?,?,?) '''
# cur = conn.cursor()
# cur.execute(sql, item_xml)
# conn.commit()




# for root, dirs, files in os.walk('./items_xml'):
#     for fileName in files:
#         # print(fileName)
#         tree = ET.parse(f'items_xml/{fileName}')
#         root = tree.getroot()
#         file_id = fileName.replace('.xml', '')

#         # parse_item(file_id, tree)
#         print(f'Item#{file_id}')

#         xml_id = root.find('item').attrib['id']
#         name = root.find('item/name').text
#         level = root.find('item/level').text
#         quality_id = root.find('item/quality').attrib['id']
#         quality_id = root.find('item/quality').text
#         class_id = root.find('item/class').attrib['id']
#         class_name = root.find('item/class').text
#         subclass_id = root.find('item/subclass').attrib['id']
#         subclass_name = root.find('item/subclass').text
#         inventory_slot_id = root.find('item/inventorySlot').attrib['id']
#         inventory_slot_name = root.find('item/inventorySlot').text
#         html_tooltip = root.find('item/htmlTooltip').text
#         json = root.find('item/json').text
#         json_equip = root.find('item/jsonEquip').text
#         link = root.find('item/link').text

#         item_xml = (file_id,xml_id,name,level,quality_id,quality_id,class_id,class_name,subclass_id,subclass_name,inventory_slot_id,inventory_slot_name,html_tooltip,json,json_equip,link)
#         sql = ''' INSERT INTO items_classic_wowhead_xml(id,xmlId,name,level,qualityId,quality,classId,class,subclassId,subclass,inventorySlotId,inventorySlot,htmlTooltip,json,jsonEquip,link)
#               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
#         cur = conn.cursor()
#         cur.execute(sql, item_xml)
#         conn.commit()