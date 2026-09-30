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
    python fetch/pack.py                              # -> fetch/fetched_<date>.tar.gz

Back home, extract over the repository root and run the generators as usual:

    tar -xzf fetched_<date>.tar.gz -C D:/dev/wow_scripts

Ids in the inventory count as present and are never fetched. The search
metadata is fetched once and kept in `cache/tmp`; delete that pickle on the
fetch machine to pick up ids Wowhead has added since.

Each run appends to `fetch/manifest.txt`, and `pack.py` sets it aside as
`fetch/packed_<date>_<time>.txt`, so every archive holds only what was fetched
after the previous one. To pack the same files again, rename that list back to
`manifest.txt`.

Once an archive is home and checked, its files can go from the fetch machine
to free the disk: the module's `cache/wowhead_*` folders and `cache/tmp`. Not
the whole `cache/`, which also holds `.db` files that git tracks.

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
    venv/bin/python fetch/fetch.py --module items spells --expansion forever 2>&1 | tee -a fetch.log

`tee -a` appends, so a restart keeps the earlier log; `tail -f fetch.log` from
another session follows it. Detach from tmux with Ctrl-B then D, return with
`tmux attach -t fetch`. A restart resumes: every page already on disk is skipped.

A CX22 is enough: nothing here renders a page, every file is a plain download.

`requirements.txt` pulls in `crowdin_api_client` because `generation/utils`
imports it at module level; no token is needed, nothing in fetch talks to
Crowdin.

Fetch back: `scp root@<host>:wow_scripts/fetch/fetched_*.tar.gz .`
