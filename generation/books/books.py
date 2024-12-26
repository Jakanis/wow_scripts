import os, requests
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
    os.makedirs('pages', exist_ok=True)
    url = WOWHEAD_URL + f'/item={id}'
    r = requests.get(url)
    with open(f'./pages/{id}.html', 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)

def parse_page(id):
    import json5
    content = None
    with open(f'./pages/{id}.html', 'r', encoding="utf-8") as input_file:
        content = input_file.read()
        
    tree = html.fromstring(content)
    item_name = tree.xpath('//h1')[0].text
    for item in content.split("\n"):
        if f"new Book(" in item:
            start = item.find('new Book({') + 9
            end = item.find('})', start) + 1
            json_raw = item[start:end]
            pages = map(lambda page: page.replace('"', '""'), json5.loads(json_raw).get('pages'))
            lines = '"\t"'.join(pages)
            return f'{id}\t"{item_name}"\t"{lines}"\n'
    return f'{id}\t"{item_name}"\t"err"\n'


def parse_to_xml():
    import csv
    lines = 0
    content = None
    with open(f'books_res.tsv', 'r') as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        os.makedirs('book_xmls', exist_ok=True)
        for row in reader:
            item_name = row[1].replace("'", "")
            print(f"{item_name}_{row[0]}.xml")
            with open(f'./book_xmls/{item_name}_{row[0]}.xml', 'w') as output_file:
                output_file.write('<?xml version="1.0" encoding="utf-8"?>\n')
                output_file.write('<resources>\n')
                for count, item in enumerate(row[2:], start=1):
                    line = item.replace(r'<br />', '\n').replace('&lt;', '<').replace(r'&gt;', '>')
                    if line:
                        output_file.write(f'<string name="PAGE_{count}"><![CDATA[{line}]]></string>\n')
                        lines = lines + 1
                output_file.write('</resources>\n')
    print(lines)

if __name__ == '__main__':
    # book_ids = [745,748,889,910,916,921,938,939,957,1078,1164,1208,1252,1283,1284,1293,1294,1327,1353,1356,1358,1361,1362,1381,1407,1408,1409,1410,1637,1656,1971,2004,2005,2006,2007,2008,2113,2154,2161,2188,2223,2560,2619,2628,2637,2639,2720,2724,2725,2728,2730,2732,2734,2735,2738,2740,2742,2744,2745,2748,2749,2750,2751,2755,2756,2757,2758,2759,2793,2832,2837,2885,2891,2956,3017,3117,3248,3252,3255,3518,3601,3657,3677,3686,3711,3718,3899,3921,4100,4101,4102,4429,4432,4514,4649,4650,4834,4883,4992,4995,5006,5041,5088,5174,5353,5354,5359,5428,5455,5505,5520,5535,5536,5594,5628,5688,5737,5790,5799,5804,5807,5826,5827,5838,5839,5860,5861,5882,5897,5917,5947,5948,5998,6167,6276,6277,6278,6279,6280,6283,6304,6305,6306,6488,6489,6490,6491,6492,6493,6494,6495,6496,6497,6498,6499,6500,6501,6620,6842,6846,6847,6929,6996,7266,7516,7587,7668,7907,7908,8046,8463,9242,9279,9280,9281,9282,9316,9329,9330,9542,9543,9544,9545,9546,9547,9548,9550,9551,9552,9553,9554,9555,9556,9557,9558,9559,9560,9561,9562,9563,9564,9565,9566,9567,9568,9569,9570,9571,9573,9574,9575,9576,9577,9578,9579,9580,9581,10022,10789,10832,10839,10840,11108,11125,11368,11482,11727,11732,11733,11734,11736,11737,11886,12438,12562,12564,12635,12730,12762,12765,12766,12768,12900,13158,13202,13507,14679,15790,15847,15998,16189,16209,16263,16307,16310,16785,17355,17735,17781,18229,18332,18333,18334,18401,18646,18664,18675,18708,18818,19483,19484,19978,20009,20010,20405,20415,20541,20545,20552,20676,20677,20678,20679,20949,21037,21130,21142,21314,22344,22595,22765,22930,22932,22944,22945,22946,22948,23008,23010,23011,23012,23013,23016]
    # book_ids = [18664, 203723, 205184, 205864, 207098, 208205, 208224, 209029, 211777] # SoD
    # book_ids = [219929, 210967, 213563, 221017, 220170, 216610, 213421, 216956, 221314] # SoD
    # book_ids = [213563] # SoD
    book_ids = [217017, 227549, 227658, 227748, 227929, 228144, 228680, 231882, 234181] # SoD
    # 217017
    # save_page(18664)
    # print(parse_page(18664))

    for i in book_ids:
        save_page(i)

    with open(f'books_res.tsv', 'w', encoding="utf-8") as output_file:
        for i in book_ids:
            output_file.writelines(parse_page(i))

    parse_to_xml()

