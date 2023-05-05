import sqlite3
from pathlib import Path
import utils


conn = sqlite3.connect('database/classicua.db')

quest_ids = [ r[0] for r in conn.execute('SELECT id FROM quests ORDER BY id') ]
for id in quest_ids:
    cat, title, objective, description, progress, completion = \
        conn.execute(f'SELECT cat, title, objective, description, progress, completion FROM quests WHERE id={id}').fetchone()

    path = f'source_for_crowdin/quests/{cat}'
    Path(path).mkdir(parents=True, exist_ok=True)

    filename = utils.get_quest_filename(id, title)
    print(id, title)

    utils.write_xml_quest_file(
        f'{path}/{filename}.xml',
        title,
        objective,
        description,
        progress,
        completion)

    # break
