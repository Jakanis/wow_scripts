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

    with open(f'npcs_res.tsv', 'w') as output_file:
        output_file.write('ID\tEN Name\tEN Desc\n')
        for id in all_ids:
            # print(id)
            npc = parse_npc(id)
            if (npc.name):
                output_file.write(str(npc) + '\n')

def parse_npcs_lua():
    with open('entries/npc.lua', 'r') as input_file:
        lua_file = input_file.read()
        decoded_npcs_lua = lua.decode(lua_file)
        # item_117 = decoded_npcs_lua[117]
        # print(item_117)
        reencoded_npcs_lua = lua.encode(decoded_npcs_lua)
        # print(reencoded_items_lua)
        with open(f'npcs_temp.lua', 'w') as output_file:
            output_file.writelines(reencoded_npcs_lua)


if __name__ == '__main__':
    # save_npc_htmls_from_wowhead()
    parse_all_npcs_from_wowhead_htmls()
    # parse_npcs_lua()




# from slpp import slpp as lua

# with open('wowhead_npc_ids.csv', 'r') as input_file:
#     all_ids_str = input_file.readline()
#     res = sorted(map(lambda x: int(x), all_ids_str.split(', ')))
#     with open('wowhead_npc_ids1.csv', 'w') as output_file:
#         res = map(lambda x: str(x), res)
#         output_file.write(', '.join(res))
