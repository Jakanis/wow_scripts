from slpp import slpp as lua
import os
import xml.etree.ElementTree as ET
import sqlite3
from lxml import html


Object = lambda **kwargs: type("Object", (), kwargs)

def parse_html_tooltip(html_tooltip_tree):
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
        print(span_text)
        if (span_text != "Item Level " and span_text != '<Random enchantment>' and span_text != None):
            descs.append(span_text)
    spans = res.findall('table[2]/tr/td/span')
    for span in spans:
        span_text = span.text
        if (span_text is not None):
            if (span_text == 'Equip: '):
                a_tag = span.findall('a')
                if a_tag is not None and len(a_tag):
                    equip.append(a_tag[0].text)
                else:
                    print('ERROR')

            if (span_text == 'Chance on hit: '):
                a_tag = span.findall('a')
                if a_tag is not None and len(a_tag):
                    chance_on_hit.append(a_tag[0].text)
                else:
                    print('ERROR')

            if (span_text == 'Use: '):
                a_tag = span.findall('a')
                if a_tag is not None and len(a_tag):
                    use.append(a_tag[0].text)
                else:
                    print('ERROR')

            if (span_text.startswith('"') and span_text.endswith('"')):
                flavor.append(span_text)

            if (span_text == '<Right Click to Read>'):
                readable = True

    return Object(descs = descs,
                  equips = equip, 
                  hits = chance_on_hit, 
                  uses = use, 
                  flavor = flavor, 
                  readable = readable)
    
def parse_wowhead_item_data(id, tree):
    print(f'Item#{id}')
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

    item = parse_html_tooltip(root.find('item/htmlTooltip'))

def parse_item(id, tree):
    print(f'Item#{id}')
    root = tree.getroot()

    xml_id = root.find('item').attrib['id']
    name = root.find('item/name').text

    item = parse_html_tooltip(root.find('item/htmlTooltip'))
    return Object(id = xml_id,
                  name = name,
                  descs = str(item.descs),
                  equips = str(item.equips), 
                  hits = str(item.hits), 
                  uses = str(item.uses), 
                  flavor = str(item.flavor[0]) if len(item.flavor) else None, 
                  readable = str(item.readable))

def parse_items_from_xmls_to_db():
    conn = sqlite3.connect('wow_db.db')

    for root, dirs, files in os.walk('./items_xml'):
        for fileName in files:
            print(fileName)
            tree = ET.parse(f'items_xml/{fileName}')
            root = tree.getroot()
            file_id = fileName.replace('.xml', '')

            item = parse_item(file_id, tree)

            item_xml = (item.id,item.name,item.descs,item.equips,item.hits,item.uses,item.flavor,item.readable)
            sql = ''' INSERT INTO items_classic(id,name,desc,equip,hit,use,flavor,readable)
                VALUES(?,?,?,?,?,?,?,?) '''
            cur = conn.cursor()
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
    str = ''
    return f'[{item.id}] = {{ "{item.name_ua}" ' + ''



if __name__ == '__main__':
    # parse_items_from_xmls_to_db()
    # parse_items_lua()





    print("22250.xml")
    tree = ET.parse(f'items_xml/22250.xml')
    root = tree.getroot()

    item = parse_item(22250, tree)






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