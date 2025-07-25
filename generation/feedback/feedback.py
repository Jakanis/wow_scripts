
def merge_dicts(a: dict, b: dict):
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key])
        else:
            a[key] = b[key]
    return a


def load_feedbacks() -> dict:
    import os
    from slpp import slpp as lua
    feedbacks = dict()
    for foldername, subfolders, filenames in os.walk('./input/feedbacks'):
        for filename in filenames:
            # Construct the full path to the file
            file_path = foldername + '/' + filename

            # Read the contents of the file
            with open(file_path, 'r', encoding="utf-8") as file:
                file_content = file.read()
                lua_table = file_content[file_content.find('ClassicUA_DevLog = {') + 19:]
                decoded_table = lua.decode(lua_table)
                feedbacks[filename] = decoded_table

    __detect_redundant_feedbacks(feedbacks)

    single_feedback = dict()

    for filename, feedback in feedbacks.items():
        single_feedback = merge_dicts(single_feedback, feedback)
    # for filename, feedback in feedbacks.items():
    #     for feedback_type, feedback_values in feedback.items():
    #         if isinstance(feedback_values, dict):
    #             single_feedback_values = single_feedback.setdefault(feedback_type, {})
    #             for feedback_key, feedback_value in feedback_values.items():
    #                 if isinstance(feedback_value, dict):
    #                     single_feedback_values[feedback_key] = single_feedback_values.get(feedback_key, {})
    #                     for sub_key, sub_value in feedback_value.items():
    #                         single_feedback_values[feedback_key][sub_key] = single_feedback_values[feedback_key].get(sub_key, set())
    #                         single_feedback_values[feedback_key][sub_key].add(sub_value)

    return single_feedback


def __detect_redundant_feedbacks(feedbacks: dict[str, dict]):
    previous_filename = None
    previous_feedback = None
    for filename, feedback in feedbacks.items():
        if previous_feedback is None:
            previous_feedback = feedback
            previous_filename = filename
            continue
        absent_keys = set(previous_feedback.keys()) - set(feedback.keys())
        if absent_keys:
            print(f'[!] Previous feedback ({previous_filename}) contains more keys ({sorted(previous_feedback.keys())}) than {filename} ({sorted(feedback.keys())}). Diff: {sorted(absent_keys)}')
            continue

        is_redundant = True
        for key in previous_feedback.keys():
            if isinstance(previous_feedback[key], dict) and isinstance(feedback.get(key), dict):
                absent_feedbacks = set(previous_feedback[key].keys()) - set(feedback[key].keys())
                if absent_feedbacks:
                    # print(f'absent_feedbacks({previous_filename}.{key}): {sorted(absent_feedbacks)}')
                    is_redundant = False

        if is_redundant:
            print(f'[!] Previous feedback ({previous_filename}) is a subset of {filename}.')

        previous_feedback = feedback
        previous_filename = filename


def store_missings(feedback: dict, name: str, store_key = True, store_value = True) -> set[int]:
    feedback_values = feedback.get(name)
    missing_keys = set()
    with open(f'output/{name}.tsv', 'w', encoding="utf-8") as output_file:
        for feedback_key, feedback_name in sorted(feedback_values.items()):
            if store_key:
                output_file.write(f'{feedback_key}')
            if store_key and store_value:
                output_file.write('\t')
            if store_value:
                output_file.write(f'{feedback_name}')
            output_file.write(f'\n')
            missing_keys.add(feedback_key)
    # print(f'{name} keys({len(missing_keys)}): {sorted(missing_keys)}')
    print(f'{name} keys: {len(missing_keys)}')
    return missing_keys


def pickle_missings(feedback: dict, name: str) -> set[int]:
    import pickle
    feedback_values = feedback.get(name)
    with open(f'output/{name}.pkl', 'wb') as f:
        pickle.dump(feedback_values, f)
    return feedback_values


def verify_engravings(missing_engravings: set[int]):
    from slpp import slpp as lua
    with open('input/entries/engraving.lua', 'r', encoding="utf-8") as file:
        file_content = file.read()
        lua_table = file_content[file_content.find('sod_engraving = {') + 16:]
        decoded_table = lua.decode(lua_table)
        present_engraving_ids = decoded_table.keys()
        print(f'Verified missing_sod_engravings keys: {sorted(missing_engravings - set(present_engraving_ids))}')


def cleanup_objects(missing_objects: set[str]):
    cleaned_objects = set()

    for missing_object in missing_objects:
        if (missing_object.startswith('Corpse of ')
                or missing_object.startswith('Grand Marshal ')
                or missing_object.startswith('Field Marshal ')
                or missing_object.startswith('Marshal ')
                or missing_object.startswith('Commander ')
                or missing_object.startswith('Lieutenant Commander ')
                or missing_object.startswith('Knight-Champion ')
                or missing_object.startswith('Knight-Captain ')
                or missing_object.startswith('Knight-Lieutenant ')
                or missing_object.startswith('Knight ')
                or missing_object.startswith('Sergeant Major ')
                or missing_object.startswith('Master Sergeant ')
                or missing_object.startswith('Sergeant ')
                or missing_object.startswith('Corporal ')
                or missing_object.startswith('Private ')
                or missing_object.startswith('High Warlord ')
                or missing_object.startswith('Warlord ')
                or missing_object.startswith('General ')
                or missing_object.startswith('Lieutenant General ')
                or missing_object.startswith('Champion ')
                or missing_object.startswith('Centurion ')
                or missing_object.startswith('Legionnaire ')
                or missing_object.startswith('Blood Guard ')
                or missing_object.startswith('Stone Guard ')
                or missing_object.startswith('First Sergeant ')
                or missing_object.startswith('Senior Sergeant ')
                or missing_object.startswith('Sergeant ')
                or missing_object.startswith('Grunt ')
                or missing_object.startswith('Scout ')
                or r'\n' in missing_object):
            continue
        if not ' ' in missing_object:  # Definitely not a player
            continue
        cleaned_objects.add(missing_object)

    with open(f'output/missing_objects_cleaned.tsv', 'w', encoding="utf-8") as output_file:
        output_file.write('\n'.join(sorted(cleaned_objects)))
    print(f'! Cleaned missing_objects keys({len(cleaned_objects)}): {sorted(cleaned_objects)}')
    return cleaned_objects


if __name__ == '__main__':
    feedbacks = load_feedbacks()

    store_missings(feedbacks, 'missing_spells')  # Check in corresponding folder
    store_missings(feedbacks, 'missing_npcs')  # Check in corresponding folder
    store_missings(feedbacks, 'missing_items')  # Check in corresponding folder
    store_missings(feedbacks, 'missing_zones', store_value=False)  # Check in corresponding folder
    store_missings(feedbacks, 'missing_quests', store_value=False)  # Check in corresponding folder
    store_missings(feedbacks, 'missing_books')

    missing_engravings = store_missings(feedbacks, 'missing_sod_engravings')
    verify_engravings(missing_engravings)

    missing_objects = store_missings(feedbacks, 'missing_objects', store_value=False)
    cleanup_objects(missing_objects)

    pickle_missings(feedbacks, 'missing_chats')
    pickle_missings(feedbacks, 'missing_gossips')

    print('Voila!')
