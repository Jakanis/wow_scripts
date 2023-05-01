import requests
import multiprocessing
from lxml import html

WOWHEAD_URL = 'https://wowhead.com'

class NPC:
    def __init__(self, id, name, locations = []):
        self.id = id
        self.name = name
        self.locations = locations

    def __str__(self):
        return f'{self.id}\t"{self.name}"\t"{self.locations}"'


def parse_npc_page(id, page) -> NPC:
    tree = html.fromstring(page)
    npc_name = tree.xpath('//h1')[0].text
    if (npc_name == "NPCs"):
        return NPC(id, "null", 'null')
    npc_locations_element = tree.xpath("/html[@class='js-focus-visible pointer-device']/body[@class='standard-layout locale-0 has-ads webp']/div[@class='layout-wrapper']/div[@class='layout']/div[@id='page-content']/div[@id='main']/div[@id='main-contents']/div[@class='text']/div[3]")
    if (not npc_locations_element):
        return NPC(id, npc_name, 'null')

    npc_locations = npc_locations_element[0].xpath('.//a')
    npc_locations_str = ",".join(list(map(lambda x: x.text, npc_locations)))
    return NPC(id, npc_name, npc_locations_str)

def parse_npc(id) -> str:
    url = WOWHEAD_URL + f'/npc={id}'
    r = requests.get(url)
    return str(parse_npc_page(id, r.content)) + "\n"


# print(parse_npc(3690))

# with open('npcs.csv', 'w') as output_file:
#     for i in  range(6946, 50000):
#         npc = str(parse_npc(i))
#         print(npc)
#         output_file.write(npc+'\n')

if __name__ == '__main__':
    res = None
    with multiprocessing.Pool(48) as p:
        with open(f'npcs_res.tsv', 'w') as output_file:
            output_file.writelines(p.map(parse_npc, range(1, 20000)))