import requests
import multiprocessing
from lxml import html
from slpp import slpp as lua


def translations_sheet_to_objects_lua():
    import csv
    translations = dict()
    with open('input/translations.tsv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            if row[0] in translations and row[1] != translations[row[0]]:
                print(f'Duplicate for {row[0]}: {translations[row[0]]} and {row[1]}')
            translations[row[0]] = row[1]

    with open(f'output/objects.lua', 'w', encoding="utf-8") as output_file:
        for key, translation in sorted(translations.items()):
            output_file.writelines(f'["{key}"] = "{translation}",\n')


if __name__ == '__main__':
    translations_sheet_to_objects_lua()
