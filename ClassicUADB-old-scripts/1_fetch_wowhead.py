import sqlite3
import urllib.request
import re
import time


conn = sqlite3.connect('database/wowhead-classicdb-cache.db')
conn.execute('''CREATE TABLE IF NOT EXISTS quests (
                    id INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    title TEXT,
                    html TEXT,
                    html2 TEXT
                )''') # html for wowhead, html2 for classicdb (and filled by separate script)
conn.commit()

existing_quest_ids = [ r[0] for r in conn.execute('SELECT id FROM quests') ]
# print('existing_quest_ids', existing_quest_ids)

for id in range(1, 10000):
    if id in existing_quest_ids:
        continue

    if id % 3 == 0:
        print('Sleeping 3 sec')
        time.sleep(3)

    if id % 20 == 0:
        print('Sleeping 10 sec')
        time.sleep(10)

    print(f'Processing quest #{id}')
    try:
        response = urllib.request.urlopen(f'https://classic.wowhead.com/quest={id}')
        data = response.read()
        html = data.decode('utf-8')
    except Exception as x:
        print('Error:', x)
        print('Sleeping 20 sec and skip this quest')
        time.sleep(20)
        continue

    with conn:
        if html.find('database-detail-page-not-found-message') >= 0:
            print('ok/not-found')
            conn.execute(f'INSERT INTO quests(id, status) VALUES(?, ?)', (id, 'ok/not-found'))
        else:
            title = None
            found = re.findall(r'<h1 class="heading-size-1">([\s\S]+)<\/h1>', html)
            if len(found) == 1:
                title = ' '.join(found[0].strip().split())
                for k, v in {
                        '<br />': '\n',
                        '&nbsp;': ' ',
                        '&quot;': '"',
                        '&apos;': "'",
                        '&lt;': '<',
                        '&gt;': '>',
                    }.items():
                    title = title.replace(k, v)

            if ('<UNUSED>' in title.upper() or
                    '<NYI>' in title.upper() or
                    '<TXT>' in title.upper() or
                    '<CHANGE TO GOSSIP>' in title.upper() or
                    'REUSE' in title.upper()):
                print('ok/unused:', title)
                conn.execute(f'INSERT INTO quests(id, status, title) VALUES(?, ?, ?)', (id, 'ok/unused', title))
            else:
                print('ok:', title)
                conn.execute(f'INSERT INTO quests(id, status, title, html) VALUES(?, ?, ?, ?)', (id, 'ok', title, html))
