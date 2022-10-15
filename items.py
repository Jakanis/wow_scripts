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
    with open(f'./items/{id}.html', 'w') as output_file:
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


# if __name__ == '__main__':
#     with multiprocessing.Pool(128) as p:
#         p.map(save_page, range(1, 24359))

if __name__ == '__main__':
    res = None
    with multiprocessing.Pool(16) as p:
        with open(f'items_res.tsv', 'w') as output_file:
            output_file.writelines(p.map(parse_page, range(1, 24359)))



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
    