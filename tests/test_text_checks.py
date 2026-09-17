import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from generation.utils.text_checks import mixed_script_words

CASES = [
    # (text, expected words)
    ('святилище співпраці', []),
    ('святилище співпраці', []),
    ('святилище співпрацi', ['співпрацi']),          # latin i
    ('коло виклику', []),
    ('Світла', []),                              # cyrillic С
    ('Cвітла', ['Cвітла']),                           # latin C
    ('Аркатраc', ['Аркатраc']),                       # latin c
    ('ти зробиkf це', ['зробиkf']),                   # wrong keyboard layout
    ('Hey, <race>, over here', []),                   # all latin, left alone
    ('Псс! Гей, {раса:к}, сюди.#Hey, <race>, over', []),
    ('Збільшує швидкість на {1} с.#haste by {1} for {2} sec', []),
    ('%s налякано тікає геть!', []),
    ('', []),
    (None, []),
    ('cкіпетр cріблястий', ['cкіпетр', 'cріблястий']),  # two in one string
    ('WoW', []),
    ('5м 10с', []),
    # the client's own markup sits against the text and is not a typo
    ('|cFFFFFFFFРозпалення душі:|r', []),
    ('|cFF8282FFМиттєва вимова.|r', []),
    ('|TInterface\\Icons\\x:16|tЗброя', []),
    ('|Hitem:123|hПосилання|h', []),
    ('%d |4мідна монета:мідні монети:мідних монет;', []),
    # a case ending glued to a format placeholder is not a word
    ('Воля %sа слабшає.', []),
    ('%dх %sу та %1$sа', []),
    ('|cFFFFFFFFcекунд|r', ['cекунд']),      # a real typo inside markup
    # one issue per distinct word, however often it repeats
    ('{1} cекунд, {2} cекунд, {3} cекунд', ['cекунд']),
]


def main() -> int:
    failures = 0
    for text, expected in CASES:
        got = mixed_script_words(text)
        if got != expected:
            print(f'  FAIL {text!r}: expected {expected}, got {got}')
            failures += 1
    print(f'{len(CASES) - failures}/{len(CASES)} cases pass')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
