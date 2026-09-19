# fetch — download Wowhead data elsewhere

The generators spend most of their time waiting on Wowhead's rate limit, and
that limit is per public IP, so a crawl at home competes with browsing. This
folder moves the download half to another machine and brings the files back
as one archive. Nothing here parses a page.

## Round trip

On the machine with the caches:

    python fetch/inventory.py               # -> fetch/inventory.json

On the fetch machine, with the repository and `fetch/inventory.json` in place:

    python fetch/fetch.py                             # everything
    python fetch/fetch.py --module items spells       # some modules
    python fetch/fetch.py --expansion forever         # one expansion of each
    python fetch/fetch.py --module spells --render    # plus rendered spell pages
    python fetch/pack.py                              # -> fetch/fetched_<date>.tar.gz

Back home, extract over the repository root and run the generators as usual:

    tar -xzf fetched_<date>.tar.gz -C D:/dev/wow_scripts

Ids in the inventory count as present and are never fetched. The metadata is
always refreshed, since that is where new ids come from. Each run appends to
`fetch/manifest.txt`; delete it to start a new archive.

Parsed-page pickles (`cache/tmp/*_npc_cache.pkl` and the like) are not in the
archive and stay whatever they were locally. After a fetch that added pages
to an expansion, delete that expansion's parse pickle so the generator parses
the new pages.

## Hetzner setup (Ubuntu 24.04)

    apt install -y python3-venv git tmux
    git clone <wow_scripts> && cd wow_scripts
    python3 -m venv venv && venv/bin/pip install -r requirements.txt
    # copy fetch/inventory.json from home: scp fetch/inventory.json root@<host>:wow_scripts/fetch/
    tmux new -s fetch
    venv/bin/python fetch/fetch.py --module items spells --expansion forever

`--render` needs Chromium: `requests_html` downloads its own on first use and
needs `apt install -y libnss3 libatk-bridge2.0-0 libgbm1 libasound2t64
libxkbcommon0 libgtk-3-0`. A CX32 (8 GB) is comfortable for rendering; a CX22
is enough without it.

`requirements.txt` pulls in `crowdin_api_client` because `generation/utils`
imports it at module level; no token is needed, nothing in fetch talks to
Crowdin.

Fetch back: `scp root@<host>:wow_scripts/fetch/fetched_*.tar.gz .`
