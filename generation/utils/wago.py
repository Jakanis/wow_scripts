"""The clients' own tables, as wago.tools exports them per build.

A build never changes, so neither does its export: each table is downloaded once into the calling module's cache
directory and read from there afterwards.
"""
import csv
import os
import time

import requests

WAGO_URL = 'https://wago.tools'


def wago_get(url: str) -> requests.Response:
    time.sleep(1)  # wago.tools publishes no limits, so stay at a polite one request a second
    return requests.get(url, headers={'User-Agent': 'ClassicUA wow_scripts'}, timeout=120)


def download_table(table: str, build: str, cache_dir: str, optional: bool = False) -> str:
    path = os.path.join(cache_dir, f'{table}_{build}.csv')
    if os.path.exists(path):  # a build never changes, so neither does its export
        return path
    print(f'Downloading {table} of {build} from wago.tools')
    r = wago_get(f'{WAGO_URL}/db2/{table}/csv?build={build}')
    # A table the build lacks comes back as "Table not found" with a 404, or a 400 since September 2026. A build
    # wago.tools does not know is a 400 too, but an HTML page without those words, so it still fails.
    if r.status_code in (400, 404) and 'Table not found' in r.text and optional:
        text = ''  # not in this client; the empty file remembers that
    elif r.ok:
        text = r.text
    else:
        raise Exception(f'wago.tools returned {r.status_code} for {table} of {build}')
    os.makedirs(cache_dir, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    os.replace(path + '.tmp', path)
    return path


def read_table(table: str, build: str, cache_dir: str, columns=(), optional: bool = False) -> list[dict[str, str]]:
    # newline='' because quoted fields hold line breaks; columns go by name, since their order and the
    # Field_* extras differ between builds
    with open(download_table(table, build, cache_dir, optional), 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows and not optional:
        raise Exception(f'{table} of {build} is empty')
    missing = [column for column in columns if rows and column not in rows[0]]
    if missing:
        raise Exception(f'{table} of {build} has no {", ".join(missing)} column')
    return rows
