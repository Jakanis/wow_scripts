import os
import pathlib
import random
import re
import shutil
import sys
import time

import requests
from crowdin_api import CrowdinClient

CROWDIN_PROJECT_ID = 393919
TRANSLATIONS_SHEET_ID = '1xwoaO6U-jXQChHecEzzqG-leESTmRKm2WXHev4GOFho'

_WOWHEAD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'uk',
}


def wowhead_get(url: str) -> requests.Response:
    # return requests.get(url)
    time.sleep(random.uniform(1.0, 5.0))
    wait = 60
    attempt = 0
    while True:
        # r = requests.get(url, headers=_WOWHEAD_HEADERS)
        r = requests.get(url)
        if r.ok or r.status_code == 404:
            return r
        else:
            attempt += 1
            print(f'[wowhead] {r.status_code} — waiting {wait}s (attempt {attempt})...')
            time.sleep(wait)
            wait = int(wait * 1.5)


class ValidationError:
    def __init__(self, id: int, expansion: str, entry_type: str, severity: str, field: str, error_message: str):
        self.id = id
        self.expansion = expansion
        self.entry_type = entry_type
        self.severity = severity
        self.field = field
        self.error_message = error_message

    def __str__(self):
        return f'[{self.severity}] {self.entry_type}#{self.id}:{self.expansion} - {self.field}: {self.error_message}'


def gather_files_in_subfolders(parent_dir: str) -> list[str]:
    file_list = []
    for dirpath, _, filenames in os.walk(parent_dir):
        for filename in filenames:
            file_list.append(os.path.join(dirpath, filename))
    return file_list


def compare_directories(dir1, dir2) -> tuple[list[str], list[str], list[str]]:
    import filecmp, difflib

    dcmp = filecmp.dircmp(dir1, dir2)
    only_in_dir1 = dcmp.left_only
    only_in_dir2 = dcmp.right_only

    diffed_files = list()
    removed_files = list()
    added_files = list()

    if len(only_in_dir1) > 0:
        print("Files only in", dir1, ":", only_in_dir1)
        for filename in only_in_dir1:
            path = os.path.join(dir1, filename)
            if os.path.isdir(path):
                removed_files.extend(gather_files_in_subfolders(path))
            if os.path.isfile(path):
                removed_files.append(path)

    if len(only_in_dir2) > 0:
        print("Files only in", dir2, ":", only_in_dir2)
        for filename in only_in_dir2:
            path = os.path.join(dir2, filename)
            if os.path.isdir(path):
                added_files.extend(gather_files_in_subfolders(path))
            if os.path.isfile(path):
                added_files.append(path)

    for common_file in dcmp.common_files:
        file1 = os.path.join(dir1, common_file)
        file2 = os.path.join(dir2, common_file)

        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            # Read the files as binary and remove line ending differences
            content1 = f1.read().replace('\r\n', '\n')
            content2 = f2.read().replace('\r\n', '\n')
            if content1 != content2:
                print('-' * 100)
                print(f'Diffing in {dir1} and {dir2}')
                print("Diffing file:", common_file)
                differ = difflib.Differ()
                lines1 = content1.splitlines()
                lines2 = content2.splitlines()
                diff = differ.compare(lines1, lines2)
                print('\n'.join(diff))
                diffed_files.append(file2)

    # Recursively compare subdirectories
    for subdir in dcmp.common_dirs:
        diffs, removals, additions = compare_directories(os.path.join(dir1, subdir), os.path.join(dir2, subdir))
        diffed_files.extend(diffs)
        removed_files.extend(removals)
        added_files.extend(additions)

    return diffed_files, removed_files, added_files


def get_quest_filename(quest_id, quest_title):
    valid_chars = frozenset('-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return ''.join(c for c in quest_title if c in valid_chars) + '_' + str(quest_id)


def write_crowdin_xml_file(path: str, content: dict[str, str]) -> None:
    with open(path, mode='w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        for key in content.keys():
            f.write(f'<string name="{key}"><![CDATA[{content[key]}]]></string>\n')
        f.write('</resources>\n')


# Was used to add ids in chats and gossips on Crowdin
# def __update_crowdin_string_keys(client: CrowdinClient, folder_filter: str) -> None:
#     from crowdin_api.api_resources.source_strings.enums import StringBatchOperations
#     dirs = __get_crowdin_directories(client)
#     for dir_path in dirs.keys():
#         if dir_path.startswith(folder_filter):
#             print(f'Updating string keys in directory {dir_path}...')
#             files = client.source_files.list_files(CROWDIN_PROJECT_ID, directoryId=dirs[dir_path], limit=500)
#             for file in files['data']:
#                 file_id = file['data']['id']
#                 file_name = file['data']['name']
#                 print(f'Updating strings in file {file_name}...')
#                 strings = client.source_strings.list_strings(CROWDIN_PROJECT_ID, fileId=file_id, limit=500)
#                 for string in strings['data']:
#                     string_identifier = string['data']['identifier']
#                     if string_identifier is not None:
#                         continue
#                     string_id = string['data']['id']
#                     string_text = string['data']['text']
#                     text_context = get_text_code(string_text)[0]
#                     text_key = text_context
#                     if not '.' in text_key:
#                         text_key = str(get_text_hash(string_text))
#                     client.source_strings.string_batch_operation(projectId=CROWDIN_PROJECT_ID, data=[{'op': StringBatchOperations.REPLACE, 'value': text_key, 'path': f'/{string_id}/identifier'}, {'op': StringBatchOperations.REPLACE, 'value': text_context, 'path': f'/{string_id}/context'}])



def download_csv_from_google_sheet(sheet_name: str, output_file: str = 'input/translations.csv') -> None:
    # Every module pulls its translations from a tab of the same workbook, so the id lives here and
    # the caller only names the tab.
    import requests
    url = f'https://docs.google.com/spreadsheets/d/{TRANSLATIONS_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    print(f'Downloading "{sheet_name}" from Google Sheet... ', end='')
    response = requests.get(url)
    if response.status_code != 200:
        # Raise rather than report: the module would otherwise carry on against whatever copy of
        # output_file happens to be on disk and quietly apply an old set of translations.
        raise Exception(f'Could not download "{sheet_name}" from Google Sheet: '
                        f'{response.status_code} - {response.text}')

    # [!] A tab name that does not exist is not an error to Google - gviz answers 200 with the first
    # sheet of the workbook instead, so a typo here reads the wrong tab rather than failing.
    content = response.text.replace('\r\n', '\n')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(content)
    print('Done!')


# A note cell holds one marker per line, so a row can say several things at once: that it was
# pretranslated *and* that it is not finished, for instance. NOT_TRANSLATED is the only marker that
# changes behaviour - on any line of any note cell it means the row is not ready and the readers
# must ignore it. Everything else is there for the person reading the sheet.
NOTE_NOT_TRANSLATED = 'NOT TRANSLATED'
NOTE_PRETRANSLATED = 'PRETRANSLATED'
NOTE_ALREADY_TRANSLATED = 'ALREADY TRANSLATED'


def parse_notes(*cells: str) -> list[str]:
    # Notes arrive as one cell per note column, each holding zero or more lines.
    return [line.strip() for cell in cells if cell for line in cell.split('\n') if line.strip()]


def notes_hold_back_row(notes: list[str]) -> bool:
    return NOTE_NOT_TRANSLATED in notes


def format_notes(notes: list[str]) -> str:
    # Keep the order the markers were added in, but never repeat one.
    seen, ordered = set(), []
    for note in notes:
        if note and note not in seen:
            seen.add(note)
            ordered.append(note)
    return '\n'.join(ordered)


FEEDBACK_OUTPUT_DIR = '../feedback/output'


def feedback_path(kind: str) -> str:
    # [!] Read feedback.py's output where it is written. Copying it into a module's own input/ makes
    # the copy the thing that rots: before this, items was validating against a feedback list 19
    # months older than the one feedback.py had produced, and quests against one 21 months older.
    return f'{FEEDBACK_OUTPUT_DIR}/missing_{kind}.tsv'


def read_feedback(kind: str) -> dict[int, str]:
    import csv
    entries = dict()
    with open(feedback_path(kind), 'r', encoding='utf-8') as input_file:
        for row in csv.reader(input_file, delimiter='	'):
            if not row:
                continue
            entries[int(row[0])] = row[1] if len(row) > 1 else ''
    return entries


def check_feedback(kind: str, entity_name: str, entities: dict[int, dict],
                   is_translated=None) -> tuple[set[int], set[int]]:
    # What players reported as missing, against what we actually generated. Unknown ids are usually
    # entries Wowhead does not list for any expansion we scrape; untranslated ones are real gaps and
    # feed the translation sheets.
    feedback = read_feedback(kind)
    unknown = set()
    untranslated = set()
    for id in feedback:
        if id not in entities:
            unknown.add(id)
        elif is_translated and not any(is_translated(entry) for entry in entities[id].values()):
            untranslated.add(id)

    print(f'[feedback] {entity_name}: {len(feedback)} reported, {len(unknown)} unknown, '
          f'{len(untranslated)} untranslated')
    if unknown:
        print(f'  unknown ids     : {sorted(unknown)}')
    if untranslated:
        print(f'  untranslated ids: {sorted(untranslated)}')
    return unknown, untranslated


def __getenv(name: str) -> str:
    # Read settings where they are used, not at import time. A real environment variable still wins
    # (PyCharm run configs, CI); otherwise it comes from the gitignored .env in the repository root - the
    # modules run from their own subdirectory, so anchor the path to this file, not the working directory.
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).parents[2] / '.env')
    return os.getenv(name)


def __get_crowdin_client() -> CrowdinClient:
    token = __getenv('CROWDIN_TOKEN')
    if not token:
        raise Exception('CROWDIN_TOKEN is not set. Put it in .env in the repository root, or set it in the environment.')
    return CrowdinClient(token=token)


def classicua_root() -> pathlib.Path:
    # Optional: the ClassicUA checkout whose dev/gen_*_lua.py scripts turn Crowdin exports into addon
    # entries. Without it the generation steps are skipped and the existing input/entries are kept.
    root = __getenv('CLASSICUA_ROOT')
    return pathlib.Path(root) if root else None


def __classicua_python(root: pathlib.Path) -> str:
    # Prefer ClassicUA's own interpreter - some of its dev scripts need luaparser, which we do not have
    for candidate in (root / '.venv' / 'Scripts' / 'python.exe', root / '.venv' / 'bin' / 'python'):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run_classicua_generator(script: str, glossary: pathlib.Path = None) -> str:
    # Runs one of ClassicUA's dev/gen_*_lua.py scripts in place. Its stdout carries that script's own
    # validation report, so it is printed rather than swallowed.
    import subprocess

    root = classicua_root()
    if not root:
        raise Exception('CLASSICUA_ROOT is not set - add it to .env in the repository root')
    dev_dir = root / 'dev'
    if not (dev_dir / script).exists():
        raise Exception(f'No {script} in {dev_dir}')

    if glossary:
        # dev/translation_from_crowdin is gitignored in ClassicUA, so dropping the glossary there is clean
        target = dev_dir / 'translation_from_crowdin' / 'ClassicUA.tbx'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(glossary, target)
        print(f'Copied glossary to {target}')

    print(f'Running {script} in {dev_dir}')
    result = subprocess.run([__classicua_python(root), script], cwd=dev_dir,
                            capture_output=True, text=True, encoding='utf-8')
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        raise Exception(f'{script} failed with code {result.returncode}:\n{result.stderr}')
    return result.stdout


def copy_classicua_entries(filename: str, expansions, target_dir: str) -> None:
    # ClassicUA writes the generated entries into its own (git tracked) entries/<expansion>/ folder, so
    # report what landed - a glossary that regressed shows up as a drop in the count here.
    root = classicua_root()
    for expansion in expansions:
        source = root / 'entries' / expansion / filename
        if not source.exists():
            print(f'Warning! {source} was not generated')
            continue
        target = pathlib.Path(target_dir) / expansion / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        before = __count_lua_entries(target)
        shutil.copyfile(source, target)
        after = __count_lua_entries(target)
        delta = after - before
        print(f'  {expansion:8s} {after:6d} entries' + (f'  ({delta:+d})' if delta else '') +
              f' -> {target}')


def __count_lua_entries(path: pathlib.Path) -> int:
    if not path.exists():
        return 0
    with open(path, 'r', encoding='utf-8') as input_file:
        return sum(1 for line in input_file if line.startswith('['))


def __select_crowdin_glossary(client: CrowdinClient, glossary_name: str = None) -> dict:
    # [!] Needs a token with the glossaries scope - the files-only token used for update_on_crowdin
    # gets "Endpoint isn't allowed for token scopes" here.
    from crowdin_api.exceptions import CrowdinException

    try:
        glossaries = [g['data'] for g in client.glossaries.list_glossaries()['data']]
    except CrowdinException as error:
        raise Exception(
            f'Crowdin refused to list glossaries ({error}).\n'
            f'Glossaries are an account-level resource, so CROWDIN_TOKEN needs the "Glossaries" scope - a '
            f'project-files token is enough for update_on_crowdin but not for this. Either add that scope '
            f'to the token in .env, or export the glossary from Crowdin by hand (TBX v2).') from error
    # The account holds several glossaries, so pick the one attached to this project rather than the first
    if glossary_name:
        matches = [g for g in glossaries if g['name'] == glossary_name]
    else:
        matches = [g for g in glossaries if CROWDIN_PROJECT_ID in g.get('projectIds', [])]
    if len(matches) != 1:
        known = ', '.join(f'"{g["name"]}" (id={g["id"]}, projects={g.get("projectIds")})' for g in glossaries)
        raise Exception(f'Expected exactly one Crowdin glossary for '
                        f'{f"name {glossary_name!r}" if glossary_name else f"project {CROWDIN_PROJECT_ID}"}, '
                        f'found {len(matches)}. Available: {known}')

    return matches[0]


def download_crowdin_glossary(path, glossary_name: str = None) -> None:
    # TBX v2 is what ClassicUA's generator reads, and Crowdin serves it much faster than v3.
    from crowdin_api.api_resources.glossaries.enums import GlossaryFormat

    client = __get_crowdin_client()
    glossary = __select_crowdin_glossary(client, glossary_name)
    print(f'Exporting Crowdin glossary "{glossary["name"]}" ({glossary.get("terms")} terms)...', end='')
    export_id = client.glossaries.export_glossary(glossary['id'], data={'format': GlossaryFormat.TBX})['data']['identifier']

    for attempt in range(60):
        status = client.glossaries.check_glossary_export_status(glossary['id'], export_id)['data']['status']
        if status == 'finished':
            break
        if status in ('canceled', 'failed'):
            raise Exception(f'Crowdin glossary export {status}')
        time.sleep(2)
    else:
        raise Exception('Crowdin glossary export did not finish in time')

    url = client.glossaries.download_glossary(glossary['id'], export_id)['data']['url']
    print(' downloading...', end='')
    response = requests.get(url)
    if not response.ok:
        raise Exception(f'Crowdin glossary download returned {response.status_code}')

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print(f' done, {path.stat().st_size} bytes')


def __get_crowdin_glossary_terms(client: CrowdinClient, glossary_id: int) -> dict[str, dict]:
    # English term text (lowercased) -> term record. The description holding the tags lives on the
    # English side of a concept; the Ukrainian term of the same concept carries none.
    result = dict()
    offset, page_size = 0, 500
    print('Getting Crowdin glossary terms...', end='')
    while True:
        page = client.glossaries.list_terms(glossary_id, languageId='en', offset=offset, limit=page_size)['data']
        for term in page:
            result[term['data']['text'].lower()] = term['data']
        if len(page) < page_size:
            break
        offset += page_size
    print(f' done, {len(result)} English terms')
    return result


def update_glossary_on_crowdin(new_terms: list[tuple[str, str, str]],
                               description_updates: list[tuple[str, str]] = (),
                               glossary_name: str = None) -> None:
    # new_terms: (text_en, text_uk, description). description_updates: (text_en, whole new description).
    from crowdin_api.api_resources.enums import PatchOperation
    from crowdin_api.api_resources.glossaries.enums import TermPatchPath

    if not new_terms and not description_updates:
        print('No glossary changes.')
        return

    client = __get_crowdin_client()
    glossary = __select_crowdin_glossary(client, glossary_name)
    existing = __get_crowdin_glossary_terms(client, glossary['id'])

    # Compare against what Crowdin has right now rather than against the downloaded copy, which may
    # already be behind - a term added since the last download must not be added a second time.
    to_add, to_edit, present, absent = [], [], [], []
    for text_en, text_uk, description in new_terms:
        if text_en.lower() in existing:
            present.append(text_en)
        else:
            to_add.append((text_en, text_uk, description))
    for text_en, description in description_updates:
        term = existing.get(text_en.lower())
        if not term:
            absent.append(text_en)
        elif (term.get('description') or '') != description:
            to_edit.append((term, description))
        else:
            present.append(text_en)

    print('-' * 100)
    if to_add:
        print(f'{len(to_add)} term(s) to add:')
        for text_en, text_uk, description in to_add:
            print(f'  + "{text_en}" -> "{text_uk}"')
            print(f'      {description}')
    if to_edit:
        print(f'{len(to_edit)} description(s) to change:')
        for term, description in to_edit:
            print(f'  ~ "{term["text"]}"')
            print(f'      - {term.get("description") or ""}')
            print(f'      + {description}')
    if present:
        print(f'{len(present)} term(s) already up to date on Crowdin: {", ".join(present[:10])}'
              + (' ...' if len(present) > 10 else ''))
    if absent:
        print(f'{len(absent)} term(s) meant to be edited are not in the glossary: {", ".join(absent[:10])}'
              + (' ...' if len(absent) > 10 else ''))

    if not to_add and not to_edit:
        print('Nothing to change in the glossary.')
        return

    print(f'Going to update glossary "{glossary["name"]}" on Crowdin '
          f'({len(to_add)} added, {len(to_edit)} changed). Type "UPDATE" to confirm: ')
    if input() != 'UPDATE':
        print('Ok, cancelling update')
        return

    for text_en, text_uk, description in to_add:
        print(f'Adding "{text_en}"...', end='')
        # The English term creates the concept, the Ukrainian one joins it
        added = client.glossaries.add_term(glossary['id'], 'en', text_en, description=description)
        client.glossaries.add_term(glossary['id'], 'uk', text_uk, conceptId=added['data']['conceptId'])
        print(' done')

    for term, description in to_edit:
        print(f'Updating "{term["text"]}"...', end='')
        client.glossaries.edit_term(glossary['id'], term['id'],
                                    data=[{'op': PatchOperation.REPLACE,
                                           'path': TermPatchPath.DESCRIPTION,
                                           'value': description}])
        print(' done')

    print(f'Glossary updated: {len(to_add)} term(s) added, {len(to_edit)} description(s) changed')


def __get_crowdin_files(client: CrowdinClient) -> dict[str, int]:
    import pickle
    crowdin_files = dict()
    if os.path.exists(f'../.cache/crowdin_files.pkl'):
        print(f'Loading Crowdin files...', end='')
        with open(f'../.cache/crowdin_files.pkl', 'rb') as f:
            crowdin_files = pickle.load(f)
    else:
        print('Getting Crowdin files...', end='')
        offset = 0
        page_size = 500
        while (True):
            files = client.source_files.list_files(CROWDIN_PROJECT_ID, offset=offset, limit=page_size)
            if not files['data']:
                break
            for file in files['data']:
                file_id = file['data']['id']
                file_path = file['data']['path']
                crowdin_files[file_path] = file_id
            offset += page_size
        with open(f'../.cache/crowdin_files.pkl', 'wb') as f:
            pickle.dump(crowdin_files, f)
    print(' done')
    return crowdin_files

def __store_crowdin_files(crowdin_files: dict[str, int]) -> None:
    import pickle
    with open(f'../.cache/crowdin_files.pkl', 'wb') as f:
        print('Storing Crowdin files...', end='')
        pickle.dump(crowdin_files, f)
        print(' done')


def __get_crowdin_directories(client: CrowdinClient) -> dict[str, int]:
    print('Getting Crowdin directories...', end='')
    crowdin_dirs = dict()
    offset = 0
    page_size = 500
    while (True):
        dirs = client.source_files.list_directories(CROWDIN_PROJECT_ID, offset=offset, limit=page_size)
        if not dirs['data']:
            break
        for dir in dirs['data']:
            dir_id = dir['data']['id']
            dir_path = dir['data']['path']
            crowdin_dirs[dir_path] = dir_id
        offset += page_size
    print(' done')
    return crowdin_dirs


def __ensure_path_exists(client: CrowdinClient, path: pathlib.Path, existing_dirs: dict[str, int]) -> None:
    if path.as_posix() in existing_dirs:
        return

    last_parent_dir_id = None
    current_path = ''
    for sub_dir in path.parts:
        current_path += '/' + sub_dir
        if current_path in existing_dirs:
            last_parent_dir_id = existing_dirs[current_path]
            continue
        else:
            print(f'Creating directory {current_path} on Crowdin...', end='')
            new_dir = client.source_files.add_directory(projectId=CROWDIN_PROJECT_ID,
                                                        name=sub_dir,
                                                        directoryId=last_parent_dir_id)
            existing_dirs[current_path] = new_dir['data']['id']
            last_parent_dir_id = new_dir['data']['id']
            print(' done')


def __update_local_crowdin_input(updated: list[str], removed: list[str], added: list[str],
                                 input_dir: str, output_dir: str) -> None:
    """Mirrors files already pushed to Crowdin into the local input folder, so that the
    next generation run compares against the actual Crowdin state and shows no diffs."""
    import shutil

    for source_path in updated + added:
        target_path = os.path.join(input_dir, os.path.relpath(source_path, output_dir))
        print(f'Copying {source_path} to {target_path}...', end='')
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copyfile(source_path, target_path)
        print(' done')

    for target_path in removed:
        print(f'Deleting {target_path}...', end='')
        os.remove(target_path)
        print(' done')
        # drop directories left empty by the removal, up to (but not including) the input root
        dir_path = os.path.dirname(target_path)
        while (os.path.normpath(dir_path) != os.path.normpath(input_dir)
               and os.path.isdir(dir_path) and not os.listdir(dir_path)):
            os.rmdir(dir_path)
            dir_path = os.path.dirname(dir_path)


def update_on_crowdin(diffs: list[str], removals: list[str], additions: list[str], skip_parent_dirs = 2,
                      input_dir = 'input/source_from_crowdin', output_dir = 'output/source_for_crowdin') -> None:
    from crowdin_api.api_resources.source_files.enums import FileUpdateOption

    if not diffs and not removals and not additions:
        print('No diffs in files.')
        return
    print('Going to update diffed files on Crowdin. Type "UPDATE" to confirm: ')
    user_input = input()
    if user_input != 'UPDATE':
        print('Ok, cancelling update')
        return
    client = __get_crowdin_client()
    crowdin_files = __get_crowdin_files(client)
    crowdin_dirs = __get_crowdin_directories(client)
    updated_files = list()
    removed_files = list()
    added_files = list()
    for diff in diffs:
        file_path = '/' + pathlib.Path(*pathlib.Path(diff).parts[skip_parent_dirs:]).as_posix()
        if file_path in crowdin_files:
            print(f'Updating {file_path}...', end='')
            storage = client.storages.add_storage(open(diff, 'rb'))
            uploaded_file = client.source_files.update_file(projectId=CROWDIN_PROJECT_ID,
                                                            storageId=storage['data']['id'],
                                                            fileId=crowdin_files[file_path],
                                                            updateOption=FileUpdateOption.KEEP_TRANSLATIONS)
            updated_files.append(diff)
            print(' done')
        else:
            print(f'File path "{file_path}" not found')

    for removal in removals:
        file_path = '/' + pathlib.Path(*pathlib.Path(removal).parts[skip_parent_dirs:]).as_posix()
        if file_path in crowdin_files:
            print(f'Removing {file_path}...', end='')
            deleted_file = client.source_files.delete_file(projectId=CROWDIN_PROJECT_ID,
                                                           fileId=crowdin_files[file_path])
            del crowdin_files[file_path]
            removed_files.append(removal)
            print(' done')
        else:
            removed_files.append(removal)
            print(f'File path "{file_path}" not found')

    for addition in additions:
        file_path = '/' + pathlib.Path(*pathlib.Path(addition).parts[skip_parent_dirs:]).as_posix()
        if file_path in crowdin_files:
            print(f'File path "{file_path}" already exists')
        else:
            dir_path = pathlib.Path(*pathlib.Path(addition).parts[skip_parent_dirs:-1])
            __ensure_path_exists(client, dir_path, crowdin_dirs)
            print(f'Adding {file_path}...', end='')
            storage = client.storages.add_storage(open(addition, 'rb'))
            uploaded_file = client.source_files.add_file(projectId=CROWDIN_PROJECT_ID,
                                                         storageId=storage['data']['id'],
                                                         directoryId=crowdin_dirs['/' + dir_path.as_posix()],
                                                         name=pathlib.Path(addition).name)
            crowdin_files[file_path] = uploaded_file['data']['id']
            added_files.append(addition)
            print(' done')
    __store_crowdin_files(crowdin_files)
    __update_local_crowdin_input(updated_files, removed_files, added_files, input_dir, output_dir)

# [!] Any changes made to string_hash() func must be kept in sync with Lua impl
def string_hash(text: str) -> int:
    import math
    if not text:
        return 0

    counter = 1
    text_len = len(text)
    for i in range(0, text_len, 3):
        counter = math.fmod(counter * 8161, 4294967279) +\
            (ord(text[i]) * 16776193) +\
            ((ord(text[i+1]) if text_len > i+1 else (text_len - (i+1) + 256)) * 8372226) +\
            ((ord(text[i+2]) if text_len > i+2 else (text_len - (i+1) + 256)) * 3932164)

    return int(math.fmod(counter, 4294967291))

# [!] Any changes made to get_text_hash() func must be kept in sync with Lua impl
def get_text_hash(text: str) -> int:
    if not isinstance(text, str):
        return 0
    # Replacing multiple NBSPs and spaces with single space
    text = re.sub(r'[ \u00A0]+', ' ', text).strip().lower()
    return string_hash(text)

known_gossip_dynamic_seq_with_multiple_words_for_get_text_code = (
    ("night elf", "nightelf"),
    ("blood elf", "bloodelf"),
    ("death knight", "deathknight"),
    ("demon hunter", "demonhunter"),
    ("void elf", "voidelf"),
    ("lightforged draenei", "lightforgeddraenei"),
    ("dark iron dwarf", "darkirondwarf"),
    ("kul tiran", "kultiran"),
    ("highmountain tauren", "highmountaintauren"),
    ("mag'har orc", "magharorc"),
    ("zandalari troll", "zandalaritroll"),
)
MAX_CODE_LENGTH = 42

# [!] Any changes made to get_text_code() func must be kept in sync with Lua impl in main.lua and utils.lua in ClassicUA
def get_text_code(text) -> (str, str):
    text = text.lower()
    for p in known_gossip_dynamic_seq_with_multiple_words_for_get_text_code:
        text = text.replace(p[0], p[1])

    # "{1}" marks a spot where the original text has a dynamic number, e.g.
    # "Number of Necropolises remaining: {1}"
    text = re.sub(r'\{\d+\}', '<number>', text)

    words = re.findall(r"""([\w<][\w\-'/]*[\w>])""", text)  # matches words with at least 2 word-characters and allows punctuation characters inside (boss-lady, ma'am, etc)
    result = list()
    for word in words:
        if len(word) > 0:
            if word.startswith('<') and word.endswith('>'):
                #  It should be <class>, <race>, <name>, <target> or gender-specific text (<his/her>)
                # TODO: if gender template contains space - it will not work (like <he's a king/she's a queen>)
                template_type = word[1:-1]
                if template_type in ('class', 'race'):
                    result.append('..')
                elif template_type in ('name', 'target', 'number'):
                    result.append('.-')
                elif '/' in template_type:
                    male_word, female_word = template_type.split('/')
                    if male_word[0] == female_word[0]:
                        result.append(male_word[0])
                    else:
                        result.append('.')
                    if male_word[-1] == female_word[-1]:
                        result.append(male_word[-1])
                    else:
                        result.append('.')
            else:
                cleaned_word = word.replace('<', '').replace('>', '') # Removing characters that aren't captured in game
                result.append(cleaned_word[0])
                result.append(cleaned_word[-1])
        if len(result) >= MAX_CODE_LENGTH:
            break

    return ''.join(result), None


def are_texts_equal_ignoring_values(text1: str, text2: str) -> bool:
    if text1 == text2:
        return True
    if text1 is None or text2 is None:
        return False
    # Remove numeric values from both texts. Removes all numeric values, including decimal numbers.

    text1_cleaned = re.sub(r'\d+\.?\d*', '', text1)
    text2_cleaned = re.sub(r'\d+\.?\d*', '', text2)

    return text1_cleaned.strip() == text2_cleaned.strip()


def __to_tsv_val(value) -> str:
    if value:
        value_str = str(value).replace('"', '""')
        if value_str.startswith('+'):
            value_str = "'" + value_str
        return f'"{value_str}"'
    else:
        return ''