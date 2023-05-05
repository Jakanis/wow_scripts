import re
import sqlite3
from pathlib import Path
import utils


conn = sqlite3.connect('database/classicua.db')

pat = re.compile(r'^\[([\d]*)\][\s\S]*?--\[\[title\]\]\s(?:nil|\[===\[([\s\S]*?)\]===\]),[\s\S]*?--\[\[description\]\]\s(?:nil|\[===\[([\s\S]*?)\]===\]),[\s\S]*?--\[\[objective\]\]\s(?:nil|\[===\[([\s\S]*?)\]===\]),[\s\S]*?--\[\[progress\]\]\s(?:nil|\[===\[([\s\S]*?)\]===\]),[\s\S]*?--\[\[reward\]\]\s(?:nil|\[===\[([\s\S]*?)\]===\]),', re.MULTILINE)

for q in [ 'quest_h.lua', 'quest_a.lua', 'quest_n.lua' ]:
    print(f'Processing {q}')
    with open(f'D:/games/World of Warcraft/_classic_/Interface/AddOns/ClassicUA/entries/{q}', encoding='utf-8', mode='r') as f:
        for id, title_uk, description_uk, objective_uk, progress_uk, completion_uk in pat.findall(f.read()):
            print(id, title_uk)

            cat, title = conn.execute(f'SELECT cat, title FROM quests WHERE id={id}').fetchone()
            path = f'translation_for_crowdin/uk/quests/{cat}'
            Path(path).mkdir(parents=True, exist_ok=True)
            filename = utils.get_quest_filename(id, title)

            utils.write_xml_quest_file(
                f'{path}/{filename}.xml',
                title_uk,
                objective_uk,
                description_uk,
                progress_uk,
                completion_uk)

            # break

    # break
