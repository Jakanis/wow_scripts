"""
Point-in-time copy of the Crowdin project: sources, translations and the glossary.

The layout mirrors ClassicUA's dev/translation_from_crowdin, so a snapshot can stand in for it:

    snapshots/2026-09-17_18-30-00/
        en/...            source strings, one XML file per Crowdin file
        uk/...            the translation export
        ClassicUA.tbx     the glossary
        manifest.txt

That folder is the only place the old string keys survive once a source update renames them, so take
a snapshot before pushing generated sources to Crowdin.

Reads CROWDIN_TOKEN_READ_ONLY from .env, falling back to CROWDIN_TOKEN.

Usage:
    python crowdin/snapshot.py [--out DIR] [--skip-sources]
"""

import argparse
import io
import os
import pathlib
import sys
import time
import zipfile

import requests
from crowdin_api import CrowdinClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from generation.utils.utils import CROWDIN_PROJECT_ID

LANGUAGE = 'uk'
PAGE = 500


def get_client() -> CrowdinClient:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / '.env')
    # a snapshot only reads, so prefer the read-only token and keep the writing one out of it
    token = os.getenv('CROWDIN_TOKEN_READ_ONLY') or os.getenv('CROWDIN_TOKEN')
    if not token:
        raise Exception('Neither CROWDIN_TOKEN_READ_ONLY nor CROWDIN_TOKEN is set. '
                        'Put one in .env in the repository root, or set it in the environment.')
    return CrowdinClient(token=token)


def __attr(value: str) -> str:
    return (value or '').replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')


def __cdata(text: str) -> str:
    # a literal ']]>' would close the section early, so split it across two of them
    return (text or '').replace(']]>', ']]]]><![CDATA[>')


def write_source_file(path: pathlib.Path, strings: list[tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n')
        for key, context, text in strings:
            comment = f' comment="{__attr(context)}"' if context else ''
            f.write(f'  <string name="{__attr(key)}"{comment}><![CDATA[{__cdata(text)}]]></string>\n')
        f.write('</resources>\n')


def download_sources(client: CrowdinClient, root: pathlib.Path) -> tuple[int, int]:
    """
    Crowdin has no bulk download for source files, and fetching 20k of them one by one takes hours,
    so the sources are rebuilt from the strings API instead. The text and the keys are exact; the
    formatting is Crowdin's normalised one rather than each file's own.
    """
    print('Listing Crowdin files...', end='', flush=True)
    files = {f['data']['id']: f['data']['path'].lstrip('/')
             for f in client.source_files.with_fetch_all().list_files(projectId=CROWDIN_PROJECT_ID)['data']}
    print(f' {len(files)}')

    by_file: dict[int, list[tuple[str, str, str]]] = {}
    seen = set()
    offset = 0
    while True:
        page = client.source_strings.list_strings(projectId=CROWDIN_PROJECT_ID, limit=PAGE, offset=offset)['data']
        if not page:
            break
        for item in page:
            s = item['data']
            if s['id'] in seen:
                continue
            seen.add(s['id'])
            by_file.setdefault(s['fileId'], []).append((s['identifier'], s.get('context') or '', s['text']))
        offset += len(page)
        print(f'\rReading strings... {len(seen)}', end='', flush=True)
    print()

    for file_id, strings in by_file.items():
        path = files.get(file_id)
        if path:
            write_source_file(root / path, strings)
    # a file with no strings still belongs in the snapshot, or it looks deleted
    for file_id, path in files.items():
        if file_id not in by_file:
            write_source_file(root / path, [])
    return len(files), len(seen)


def download_translations(client: CrowdinClient, root: pathlib.Path) -> tuple[int, int]:
    build = None
    for attempt in range(30):
        try:
            build = client.translations.build_project_translation(
                request_data={'targetLanguageIds': [LANGUAGE], 'skipUntranslatedStrings': True},
                projectId=CROWDIN_PROJECT_ID)['data']
            break
        except Exception as exc:
            # Crowdin allows one build at a time, so wait for whoever started the other one
            if '409' not in str(exc):
                raise
            print(f'\rAnother build is running, waiting... {attempt * 10}s', end='', flush=True)
            time.sleep(10)
    if build is None:
        raise Exception('Crowdin stayed busy with another build')

    print(f'Building {LANGUAGE} translations (build {build["id"]})...', end='', flush=True)
    status = build
    for _ in range(300):
        if status['status'] in ('finished', 'failed', 'canceled'):
            break
        time.sleep(2)
        status = client.translations.check_project_build_status(projectId=CROWDIN_PROJECT_ID,
                                                                buildId=build['id'])['data']
    if status['status'] != 'finished':
        raise Exception(f'Crowdin translation build {status["status"]}')

    url = client.translations.download_project_translations(projectId=CROWDIN_PROJECT_ID,
                                                            buildId=build['id'])['data']['url']
    print(' downloading...', end='', flush=True)
    response = requests.get(url)
    if not response.ok:
        raise Exception(f'Crowdin translation download returned {response.status_code}')

    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(root)
        written = sum(1 for n in archive.namelist() if not n.endswith('/'))
    print(f' {written} files, {len(response.content)} bytes')
    return written, build['id']


def download_glossary(client: CrowdinClient, path: pathlib.Path, name: str = None) -> int:
    from crowdin_api.api_resources.glossaries.enums import GlossaryFormat

    glossaries = [g['data'] for g in client.glossaries.list_glossaries(limit=PAGE)['data']]
    matches = [g for g in glossaries
               if (name and g['name'] == name) or (not name and CROWDIN_PROJECT_ID in g.get('projectIds', []))]
    if len(matches) != 1:
        known = ', '.join(repr(g['name']) for g in glossaries)
        raise Exception(f'Expected one glossary for {name or f"project {CROWDIN_PROJECT_ID}"}, '
                        f'found {len(matches)}. Available: {known}')
    glossary = matches[0]

    print(f'Exporting glossary "{glossary["name"]}" ({glossary.get("terms")} terms)...', end='', flush=True)
    export_id = client.glossaries.export_glossary(glossary['id'], data={'format': GlossaryFormat.TBX})['data']['identifier']
    for _ in range(60):
        status = client.glossaries.check_glossary_export_status(glossary['id'], export_id)['data']['status']
        if status == 'finished':
            break
        if status in ('canceled', 'failed'):
            raise Exception(f'Crowdin glossary export {status}')
        time.sleep(2)
    else:
        raise Exception('Crowdin glossary export did not finish in time')

    url = client.glossaries.download_glossary(glossary['id'], export_id)['data']['url']
    response = requests.get(url)
    if not response.ok:
        raise Exception(f'Crowdin glossary download returned {response.status_code}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print(f' {glossary.get("terms")} terms, {len(response.content)} bytes')
    return glossary.get('terms') or 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parent / 'snapshots',
                        help='where to put the timestamped folder (default: crowdin/snapshots)')
    parser.add_argument('--skip-sources', action='store_true',
                        help='skip the sources, which are the slow part')
    parser.add_argument('--glossary', help='glossary name, if the project has more than one')
    args = parser.parse_args()

    started = time.time()
    root = args.out / time.strftime('%Y-%m-%d_%H-%M-%S')
    print(f'Snapshot of Crowdin project {CROWDIN_PROJECT_ID} into {root}')
    client = get_client()

    files = strings = 0
    if args.skip_sources:
        print('Sources skipped')
    else:
        files, strings = download_sources(client, root / 'en')
    translated, build_id = download_translations(client, root / LANGUAGE)
    terms = download_glossary(client, root / 'ClassicUA.tbx', args.glossary)

    took = time.time() - started
    with open(root / 'manifest.txt', 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'taken       {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'project     {CROWDIN_PROJECT_ID}\n')
        f.write(f'sources     {"skipped" if args.skip_sources else f"{files} files, {strings} strings"}\n')
        f.write(f'{LANGUAGE:<12}{translated} files, from build {build_id}\n')
        f.write(f'glossary    {terms} terms\n')
        f.write('note        en/ is rebuilt from the strings API, so the keys and text are exact '
                'but the formatting is normalised\n')
    print(f'Done in {took / 60:.1f} min -> {root}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
