"""
Text rules shared by the generators, so a check written once runs over every
kind of translated string instead of once per module.

Each function returns findings; the caller decides which log they go to and
which entity, id and field to record them under.
"""

import re

WORD = re.compile(r'[^\W\d_]+')
CYRILLIC = re.compile(r'[Ѐ-ӿ]')
LATIN = re.compile(r'[A-Za-z]')

# the client's own markup: a colour, a texture, a link, a plural form. Its
# payload is ASCII and sits right against the text, so it has to go before
# anything looks at word shape.
UI_ESCAPE = re.compile(
    r'\|c[0-9A-Fa-f]{8}'   # colour open
    r'|\|r'                # colour reset
    r'|\|T.*?\|t'          # texture
    r'|\|H.*?\|h'          # link head
    r'|\|h'                # link tail
    r'|\|n'                # newline
    r'|\|[14][^;]*;'       # plural or declension form
)


def strip_ui_escapes(text: str) -> str:
    return UI_ESCAPE.sub(' ', text) if text else ''


def mixed_script_words(text: str) -> list[str]:
    """
    A word holding both Cyrillic and Latin letters is a typo: a Latin c, o, e,
    i or C standing in for its Cyrillic twin, or a word typed in the wrong
    keyboard layout. It reads correctly on screen but never matches a lookup.

    A word that is entirely Latin is left alone, so English templates after
    '#' and English names inside a translation do not register. Each distinct
    word is returned once, however often it repeats.
    """
    if not text:
        return []
    found = [word for word in WORD.findall(strip_ui_escapes(text))
             if CYRILLIC.search(word) and LATIN.search(word)]
    return list(dict.fromkeys(found))


def report_mixed_script(log, entity: str, text: str, **where) -> None:
    for word in mixed_script_words(text):
        log.error('mixed-script', entity,
                  f'{word!r} mixes Cyrillic and Latin letters', **where)
