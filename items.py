import requests
import multiprocessing
from lxml import html

WOWHEAD_URL = 'https://classic.wowhead.com'

class Item:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

    def __str__(self):
        return f'{self.id},"{self.name}","{self.description}"'


def parse_npc_page(id, page) -> Item:
    tree = html.fromstring(page)
    item_name = tree.xpath('//h1')[0].text
    if (item_name == "Items"):
        return Item(id, "null", 'null')
    item_description_element = tree.xpath(f"//div[@id='tt{id}']/table/tbody")
    return Item(id, item_name, item_description_element)

def parse_item(id) -> Item:
    url = WOWHEAD_URL + f'/item={id}'
    r = requests.get(url)
    return parse_npc_page(id, r.content)

def save_page(id):
    url = WOWHEAD_URL + f'/item={id}'
    r = requests.get(url)
    if (f"Item #{id} doesn't exist. It may have been removed from the game." in r.text):
        return
    with open(f'./items/{id}.html', 'w') as output_file:
        output_file.write(r.text)

def save_xml_page(id):
    url = WOWHEAD_URL + f'/item={id}?xml'
    r = requests.get(url)
    if (f"Item not found!" in r.text):
        return
    with open(f'./items_xml/{id}.xml', 'w') as output_file:
        output_file.write(r.text)

def parse_page(id):
    content = None
    with open(f'./items/{id}.html', 'r') as input_file:
        content = input_file.read()
    if f"Item #{id} doesn't exist. It may have been removed from the game." in content:
        return f"{id}\tnull\tnull\n"
    tree = html.fromstring(content)
    item_name = tree.xpath('//h1')[0].text
    item_data = None
    for item in content.split("\n"):
        if f"g_items[{id}].tooltip_enus" in item:
            return f'{id}\t"{item_name}"\t"{item.strip()}"\n'
    return f'{id}\terr\terr\n'

def parse_wowhead_items_to_xmls():
    item_range_base = range(1, 25000)
    items_range_25k_to_end = [184937, 184938, 191481, 189426, 189427, 190309, 190179, 180089, 190187, 191477, 190186, 191312, 190232, 190181, 191661, 190307, 191249, 191288, 191550, 189419, 189421, 190180, 191459, 191480, 122270, 122284, 189420, 191268, 191280, 191292, 191414, 172070, 190308, 191204, 191313, 191612, 191613, 191267, 191458, 191607, 191608, 191609, 191610, 191664, 191666, 191270, 191272, 191427, 191605, 191606, 191611, 191614, 191656, 191660]

    with multiprocessing.Pool(128) as p:
        p.map(save_xml_page, item_range_base)
    with multiprocessing.Pool(128) as p:
        p.map(save_xml_page, items_range_25k_to_end)

if __name__ == '__main__':
    parse_wowhead_items_to_xmls()

# if __name__ == '__main__':
#     res = None
#     with multiprocessing.Pool(16) as p:
#         with open(f'items_res.tsv', 'w') as output_file:
#             output_file.writelines(p.map(parse_page, range(1, 24359)))



    # with open(f'items_res.csv', 'w') as output_file:
    #     output_file.write(res)

# print(parse_page(78))

# for i in  range(1, 24359):
#     print(f'{i}')
#     save_page(i)


# with open('npcs.csv', 'w') as output_file:
#     for i in  range(1, 50000):
#         npc = str(parse_npc(i))
#         print(npc)
#         output_file.write(npc+'\n')
    