import requests
import multiprocessing
from lxml import html
from slpp import slpp as lua


def add_translations_to_objects_lua():
    import csv
    from slpp import slpp as lua
    translations = dict()
    with open('input/translations.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            if row[0] in translations and row[1] != translations[row[0]]:
                print(f'Duplicate for {row[0]}: {translations[row[0]]} and {row[1]}')
            translations[row[0]] = row[1]

    with open('input/object.lua', 'r', encoding="utf-8") as input_file:
        lua_file = input_file.read()
        decoded_objects = lua.decode(lua_file)
        for original, translation in decoded_objects.items():
            if original in translations and translation != translations[original]:
                print(f'Duplicate for {row[0]}: {translations[original]} and {translation}')
            translations[original] = translation

    with open(f'output/object.lua', 'w', encoding="utf-8") as output_file:
        for key, translation in sorted(translations.items()):
            output_file.writelines(f'["{key}"] = "{translation}",\n')


if __name__ == '__main__':
    add_translations_to_objects_lua()
