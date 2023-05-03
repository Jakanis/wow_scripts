from slpp import slpp as lua
import os
import xml.etree.ElementTree as ET
import sqlite3
from lxml import html


Object = lambda **kwargs: type("Object", (), kwargs)

def parse_html_tooltip(id, html_tooltip_tree):
    descs = list()
    equip = list()
    chance_on_hit = list()
    use = list()
    flavor = list()
    readable = False
    res = html.fromstring(html_tooltip_tree.text.replace('<br>', ''))
    spans1 = res.findall('table[1]/tr/td/span')
    for span in spans1:
        span_text = span.text
        if (span_text != "Item Level " and span_text != '<Random enchantment>' and span_text != None):
            descs.append(span_text)
    spans = res.findall('table[2]/tr/td/span')
    for span in spans:
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
                    tag_text = tag.text 
                    # print(tag.text)
                    if tag_text is not None:
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
                  readable = readable)
    
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
                  readable = str(item.readable))

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
                  readable = str(item.readable))

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

            item_xml = (item.id,item.name,item.descs,item.equips,item.hits,item.uses,item.flavor,item.readable)
            sql = ''' INSERT INTO items_classic(id,name,desc,equip,hit,use,flavor,readable)
                VALUES(?,?,?,?,?,?,?,?) '''
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
    res_str+=f'[{item.id}] = {{ "{item.name_ua}"'
    if (item.descs_ua):
        arr = item.descs_ua
        if (len(arr) == 1):
            res_str+=f', desc="{arr[0]}"'
        else:
            res_str+=', desc={ "' + '", "'.join(arr) + '" }'

    if (item.equips_ua):
        arr = item.equips_ua
        if (len(arr) == 1):
            res_str+=f', equip="{arr[0]}"'
        else:
            res_str+=', equip={ "' + '", "'.join(arr) + '" }'
    if (item.hits_ua):
        arr = item.hits_ua
        if (len(arr) == 1):
            res_str+=f', hit="{arr[0]}"'
        else:
            res_str+=', hit={ "' + '", "'.join(arr) + '" }'
            
    if (item.uses_ua):
        arr = item.uses_ua
        if (len(arr) == 1):
            res_str+=f', use="{arr[0]}"'
        else:
            res_str+=', use={ "' + '", "'.join(arr) + '" }'
            
    if (item.flavor_ua):
        arr = item.flavor_ua
        if (len(arr) == 1):
            res_str+=f', flavor="{arr[0]}"'
        else:
            res_str+=', flavor={ "' + '", "'.join(arr) + '" }'
    
    res_str+=f' }}, -- {item.name}'
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
    return Object(id = item[0],
                  name = item[1],
                  equips = item[2].split("\n") if item[2] else None, 
                  hits = item[3].split("\n") if item[3] else None, 
                  uses = item[4].split("\n") if item[4] else None, 
                  flavor = item[5].split("\n") if item[5] else None, 
                  descs = item[6].split("\n") if item[6] else None)


def decoded_item_to_item(item):
    if type(item) == list:
        return Object(name = item[0],
                  equips = None, 
                  hits = None, 
                  uses = None, 
                  flavor = None, 
                  descs = None)
    return Object(name = item[0],
                  equips = [item.get('equip')] if type(item.get('equip')) == str else item.get('equip'), 
                  hits = [item.get('hit')] if type(item.get('hit')) == str else item.get('hit'),
                  uses = [item.get('use')] if type(item.get('use')) == str else item.get('use'), 
                  flavor = [item.get('flavor')] if type(item.get('flavor')) == str else item.get('flavor'),
                  descs = [item.get('desc')] if type(item.get('desc')) == str else item.get('desc'))

def items_to_lua_line(original, translated):
    item = Object(id = original.id,
                  name = original.name,
                  equips = original.equips, 
                  hits = original.hits,
                  uses = original.uses, 
                  flavor = original.flavor,
                  descs = original.descs,
                  name_ua = translated.name,
                  equips_ua = translated.equips, 
                  hits_ua = translated.hits,
                  uses_ua = translated.uses, 
                  flavor_ua = translated.flavor,
                  descs_ua = translated.descs)
    return item_to_lua_line(item)

def combine_existing_translation():
    decoded_items_lua = None

    with open('entries/item.lua', 'r') as input_file:
        lua_file = input_file.read()
        decoded_items_lua = lua.decode(lua_file)

    conn = sqlite3.connect('wow_db.db')
    cursor = conn.cursor()
    result_strs = list()
    for id in sorted(decoded_items_lua):
        print(id)
        orig_item = get_item_from_db(cursor, id)
        translated_item = decoded_item_to_item(decoded_items_lua[id])
        lua_line = items_to_lua_line(orig_item, translated_item)
        result_strs.append(lua_line+'\n')
    cursor.close()
    with open(f'items_temp.lua', 'w') as output_file:
        output_file.writelines(result_strs)



if __name__ == '__main__':
    # parse_items_from_xmls_to_db()
    ## parse_items_lua()
    combine_existing_translation()



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