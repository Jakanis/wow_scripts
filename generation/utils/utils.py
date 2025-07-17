import os
import pathlib
import re

from crowdin_api import CrowdinClient

CROWDIN_PROJECT_ID = 393919

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


def update_on_crowdin(diffs: list[str], removals: list[str], additions: list[str], skip_parent_dirs = 2) -> None:
    from crowdin_api.api_resources.source_files.enums import FileUpdateOption

    if not diffs and not removals and not additions:
        print('No diffs in files.')
        return
    print('Going to update diffed files on Crowdin. Type "UPDATE" to confirm: ')
    user_input = input()
    if user_input != 'UPDATE':
        print('Ok, cancelling update')
        return
    token = os.getenv('CROWDIN_TOKEN')
    client = CrowdinClient(token=token)
    crowdin_files = __get_crowdin_files(client)
    crowdin_dirs = __get_crowdin_directories(client)
    for diff in diffs:
        file_path = '/' + pathlib.Path(*pathlib.Path(diff).parts[skip_parent_dirs:]).as_posix()
        if file_path in crowdin_files:
            print(f'Updating {file_path}...', end='')
            storage = client.storages.add_storage(open(diff, 'rb'))
            uploaded_file = client.source_files.update_file(projectId=CROWDIN_PROJECT_ID,
                                                            storageId=storage['data']['id'],
                                                            fileId=crowdin_files[file_path],
                                                            updateOption=FileUpdateOption.KEEP_TRANSLATIONS)
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
            print(' done')
        else:
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
            print(' done')
    __store_crowdin_files(crowdin_files)

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
    return string_hash(text.strip().lower()) if isinstance(text, str) else 0

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
                elif template_type in ('name', 'target'):
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