

def compare_directories(dir1, dir2) -> list:
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

    # Print the results for the current directory
    if len(only_in_dir1) > 0:
        print("Files only in", dir1, ":", only_in_dir1)
    if len(only_in_dir2) > 0:
        print("Files only in", dir2, ":", only_in_dir2)

    diffed_files = list()

    for common_file in dcmp.common_files:
        file1 = os.path.join(dir1, common_file)
        file2 = os.path.join(dir2, common_file)

        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            # Read the files as binary and remove line ending differences
            content1 = f1.read().replace('\r\n', '\n')
            content2 = f2.read().replace('\r\n', '\n')
            if content1 != content2:
                print('-'*100)
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
        diffed_files.extend(compare_directories(os.path.join(dir1, subdir), os.path.join(dir2, subdir)))

    return diffed_files

def get_quest_filename(quest_id, quest_title):
    valid_chars = frozenset('-.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return ''.join(c for c in quest_title if c in valid_chars) + '_' + str(quest_id)


def write_xml_quest_file(filename, title, objective, description, progress, completion):
    with open(filename, mode='w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<resources>\n')
        f.write(f'<string name="TITLE"><![CDATA[{title}]]></string>\n')
        if objective:
            f.write(f'<string name="OBJECTIVE"><![CDATA[{objective}]]></string>\n')
        if description:
            f.write(f'<string name="DESCRIPTION"><![CDATA[{description}]]></string>\n')
        if progress:
            f.write(f'<string name="PROGRESS"><![CDATA[{progress}]]></string>\n')
        if completion:
            f.write(f'<string name="COMPLETION"><![CDATA[{completion}]]></string>\n')
        f.write('</resources>\n')