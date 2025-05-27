import os
import pathlib
from crowdin_api import CrowdinClient

CROWDIN_PROJECT_ID = 393919


def compare_directories(dir1, dir2) -> tuple[list[str], list[str], list[str]]:
    import os
    import filecmp, difflib
    # print('-'*100)
    # print('-'*100)
    # print(f'Comparing {dir1} and {dir2}')
    dcmp = filecmp.dircmp(dir1, dir2)

    # List of files that are only in the first directory
    only_in_dir1 = dcmp.left_only

    # List of files that are only in the second directory
    only_in_dir2 = dcmp.right_only

    diffed_files = list()
    removed_files = list()
    added_files = list()

    # Print the results for the current directory
    if len(only_in_dir1) > 0:
        print("Files only in", dir1, ":", only_in_dir1)
        for filename in only_in_dir1:
            removed_files.append(os.path.join(dir1, filename))
    if len(only_in_dir2) > 0:
        print("Files only in", dir2, ":", only_in_dir2)
        for filename in only_in_dir2:
            added_files.append(os.path.join(dir2, filename))

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


def __get_crowdin_files(client: CrowdinClient) -> dict[str, int]:
    print('Getting Crowdin files...', end='')
    crowdin_dirs = dict()
    offset = 0
    page_size = 500
    while (True):
        files = client.source_files.list_files(CROWDIN_PROJECT_ID, offset=offset, limit=page_size)
        if not files['data']:
            break
        for file in files['data']:
            file_id = file['data']['id']
            file_path = file['data']['path']
            crowdin_dirs[file_path] = file_id
        offset += page_size
    print(' done')
    return crowdin_dirs


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
            print(f'Creating directory {current_path} on Crowdin')
            new_dir = client.source_files.add_directory(projectId=CROWDIN_PROJECT_ID,
                                                        name=sub_dir,
                                                        directoryId=last_parent_dir_id)
            existing_dirs[current_path] = new_dir['data']['id']
            last_parent_dir_id = new_dir['data']['id']


def update_on_crowdin(diffs: list[str], removals: list[str], additions: list[str]) -> None:
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
        file_path = '/' + pathlib.Path(*pathlib.Path(diff).parts[1:]).as_posix()
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
        file_path = '/' + pathlib.Path(*pathlib.Path(removal).parts[1:]).as_posix()
        if file_path in crowdin_files:
            print(f'Removing {file_path}...', end='')
            deleted_file = client.source_files.delete_file(projectId=CROWDIN_PROJECT_ID,
                                                           fileId=crowdin_files[file_path])
            print(' done')
        else:
            print(f'File path "{file_path}" not found')

    for addition in additions:
        file_path = '/' + pathlib.Path(*pathlib.Path(addition).parts[1:]).as_posix()
        if file_path in crowdin_files:
            print(f'File path "{file_path}" already exists')
        else:
            print(f'Adding {file_path}...', end='')
            dir_path = pathlib.Path(*pathlib.Path(addition).parts[1:-1])
            __ensure_path_exists(client, dir_path, crowdin_dirs)
            storage = client.storages.add_storage(open(addition, 'rb'))
            uploaded_file = client.source_files.add_file(projectId=CROWDIN_PROJECT_ID,
                                                         storageId=storage['data']['id'],
                                                         directoryId=crowdin_dirs['/' + dir_path.as_posix()],
                                                         name=pathlib.Path(addition).name)
            print(' done')
