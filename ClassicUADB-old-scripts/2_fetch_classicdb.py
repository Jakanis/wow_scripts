import sqlite3
import urllib.request
import re
import time


# added quests.html2 TEXT
conn = sqlite3.connect('database/wowhead-classicdb-cache.db')

quest_ids = [ r[0] for r in conn.execute('SELECT id FROM quests WHERE status="ok" AND html2 IS NULL') ]

for id in quest_ids:
    if id % 3 == 0:
        print('Sleeping 2 sec')
        time.sleep(2)

    if id % 17 == 0:
        print('Sleeping 5 sec')
        time.sleep(5)

    print(f'Processing quest #{id}')

    html = None
    for i in range(3):
        try:
            response = urllib.request.urlopen(f'https://classicdb.ch/?quest={id}')
            data = response.read()
            html = data.decode('utf-8')
            break
        except Exception as x:
            print('Error:', x)
            print('Sleeping 15 sec and try again')
            time.sleep(15)

    if not html:
        html = 'error/not-loaded'

    with conn:
        conn.execute(f'UPDATE quests SET html2=? WHERE id=?', (html, id))
