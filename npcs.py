import requests
import multiprocessing
from lxml import html
from slpp import slpp as lua

WOWHEAD_URL = 'https://wowhead.com'

class NPC:
    def __init__(self, id, name, desc):
        self.id = id
        self.name = name
        self.desc = desc

    def __str__(self):
        name_txt = str(self.name).replace('"', '""')
        desc_txt = str(self.desc).replace('"', '""')
        return f'{self.id}\t"{name_txt}"\t"{desc_txt}"'
    
class NPC_TR:
    def __init__(self, id, name_en, desc_en, name_ua, desc_ua):
        self.id = id
        self.name_en = name_en
        self.desc_en = desc_en
        self.name_ua = name_ua
        self.desc_ua = desc_ua

    def __str__(self):
        name_en_txt = str(self.name_en).replace('"', '""')
        desc_en_txt = str(self.desc_en).replace('"', '""')
        name_ua_txt = str(self.name_ua).replace('"', '""')
        desc_ua_txt = str(self.desc_ua).replace('"', '""')
        return f'{self.id}\t"{name_en_txt}"\t"{desc_en_txt}"\t"{name_ua_txt}"\t"{desc_ua_txt}"'
    
def get_all_wowhead_npc_ids() -> list:
    with open(f'wowhead_npc_ids.csv', 'r') as input_file:
        all_ids_str = input_file.readline()
    return list(map(lambda x: int(x), all_ids_str.split(', ')))

def save_npc_page(id) -> str:
    url = WOWHEAD_URL + f'/classic/npc={id}'
    r = requests.get(url)
    with open(f'npc_htmls/{id}.html', 'w') as output_file:
        output_file.write(r.text)

def save_npc_htmls_from_wowhead():
    all_ids = get_all_wowhead_npc_ids()

    with multiprocessing.Pool(64) as p:
        p.map(save_npc_page, all_ids)

def parse_npc_page(id, page) -> NPC:
    tree = html.fromstring(page)
    npc_name = tree.xpath('//h1')[0].text
    if (npc_name == "Classic NPCs" or npc_name is None): # 15384, 15672, 17689, 17690, 17696, 17698 are corrupt and not used
        print(f'{id} is null')
        return NPC(id, '', '')
    splitted_name = npc_name.split(' <')
    if (len(splitted_name) == 1):
        return NPC(id, npc_name, '')
    elif (len(splitted_name) == 2):
        return NPC(id, splitted_name[0], '<'+splitted_name[1])
    else:
        print(f'error for {id}')
        return NPC(id, 'error', 'error')

def parse_npc(id) -> NPC:
    with open(f'npc_htmls/{id}.html', 'r') as input_file:
        page_content = input_file.read()
    return parse_npc_page(id, page_content)


def parse_all_npcs_from_wowhead_htmls():
    all_ids = get_all_wowhead_npc_ids()
    all_npcs = dict()
    with open(f'npcs_res.tsv', 'w') as output_file:
        output_file.write('ID\tEN Name\tEN Desc\n')
        for id in all_ids:
            npc = parse_npc(id)
            if (npc.name):
                all_npcs[id]=parse_npc(id)
            #     output_file.write(str(npc) + '\n')
    return all_npcs

def parse_npcs_lua():
    import re
    all_npcs = dict()
    with open('entries/npc.lua', 'r') as input_file:
        lua_file = input_file.read()
    for line in lua_file.split('\n'):
        res = re.findall('\[(\d+)\] = { \"(.+)\".+-- (.+)', line)[0]
        if (len(res) != 3):
            print(f'check {line}')
        id = int(res[0])
        splitted_name_ua = res[1].split('", "')
        name_ua = splitted_name_ua[0]
        desc_ua = f'<{splitted_name_ua[1]}>' if len(splitted_name_ua) == 2 else ''
        splitted_name_en = res[2].split(' <')
        name_en = splitted_name_en[0]
        desc_en = f'<{splitted_name_en[1]}' if len(splitted_name_en) == 2 else ''
        npc = NPC_TR(id, name_en, desc_en, name_ua, desc_ua)
        all_npcs[id] = npc
    return all_npcs

if __name__ == '__main__':
    # save_npc_htmls_from_wowhead()
    # npcs_from_wowhead = parse_all_npcs_from_wowhead_htmls()
    
    npcs_from_lua = parse_npcs_lua()





# from slpp import slpp as lua

# with open('wowhead_npc_ids.csv', 'r') as input_file:
#     all_ids_str = input_file.readline()
#     res = sorted(map(lambda x: int(x), all_ids_str.split(', ')))
#     with open('wowhead_npc_ids1.csv', 'w') as output_file:
#         res = map(lambda x: str(x), res)
#         output_file.write(', '.join(res))
