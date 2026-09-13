import pathlib
import re
from xml.etree import ElementTree

# Reader for the Crowdin glossary export (TBX v2), kept as a single shared copy in Crowdin/glossary.tbx.
#
# [!] Term and tag semantics here must be kept in sync with ClassicUA's dev/terms.py - that script turns
# this very glossary into the addon's entries, so any divergence in tag parsing or term resolution means
# we validate one thing and ClassicUA generates another.

NPC_TAG = 'нпц'
FEMALE_TAG = 'жін'
LOCATION_TAG = 'локація'

_XML_NS = {'xml': 'http://www.w3.org/XML/1998/namespace'}


def glossary_path() -> pathlib.Path:
    # Downloaded from Crowdin and shared by every module, so it is never hand-edited.
    return pathlib.Path(__file__).parents[2] / 'Crowdin' / 'glossary.tbx'


def get_clean_text(text: str) -> str:
    # Mirrors ClassicUA's utils.get_clean_text: normalises typographic characters and drops trailing blanks.
    lines = text.split('\n')
    last_non_empty_line_idx = -1
    for i in range(len(lines)):
        lines[i] = lines[i].rstrip().replace('’', "'").replace('”', '"').replace('–', '—')
        if lines[i]:
            last_non_empty_line_idx = i
    return '\n'.join(lines[:last_non_empty_line_idx + 1]) if last_non_empty_line_idx >= 0 else ''


class GlossaryTerm:
    def __init__(self, text_en: str, text_uk: str, tags: list[str]):
        self.text_en = text_en
        self.text_uk = text_uk
        self.tags = tags

    def __repr__(self) -> str:
        return f'@term {self.text_en} -> {self.text_uk}'

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def is_npc(self) -> bool:
        return self.has_tag(NPC_TAG)

    def is_female(self) -> bool:
        return self.has_tag(FEMALE_TAG)

    def is_location(self) -> bool:
        return self.has_tag(LOCATION_TAG)

    def translation(self, is_female=False) -> str:
        # A term may carry both cases as "masculine/feminine"
        cases = self.text_uk.split('/', maxsplit=1)
        return cases[1] if is_female and len(cases) > 1 else cases[0]

    def descs(self) -> list[str]:
        # Every <...> description written under this term, both term-level and inside a #id tag
        result = []
        for tag in self.tags:
            if tag.startswith('<') and tag.endswith('>'):
                result.append(tag[1:-1].strip())
            elif tag.startswith('#'):
                match = re.search(r'<(.*)>$', tag)
                if match:
                    result.append(match[1].strip())
        return result

    def npc_ids(self) -> list[tuple[int, str]]:
        # #ID[:EXPANSION][ NAME][ <DESC>] - expansion defaults to classic
        result = []
        for tag in self.tags:
            match = re.match(r'#(\d+)(?::(\w+))?', tag)
            if match:
                result.append((int(match[1]), match[2] or 'classic'))
        return result

    def location_aliases(self) -> list[str]:
        result = []
        for tag in self.tags:
            if tag.startswith('~') and tag.endswith('~') and len(tag) > 2:
                alias = tag[1:-1].strip()
                if alias:
                    result.append(alias)
        return result


class Glossary(list[GlossaryTerm]):
    @staticmethod
    def load(path=None, download_if_absent=True) -> 'Glossary':
        path = pathlib.Path(path or glossary_path())
        if not path.exists():
            if not download_if_absent:
                raise Exception(f'No glossary at {path}')
            print(f'No glossary at {path}, fetching a fresh one from Crowdin')
            # Imported here so that reading an existing glossary needs neither a token nor crowdin_api
            from generation.utils.utils import download_crowdin_glossary
            download_crowdin_glossary(path)
        print(f'Loading glossary from {path}...', end='')
        root = ElementTree.parse(path).getroot()
        result = Glossary()
        for entry in root.findall('.//termEntry', namespaces=_XML_NS):
            term_en = entry.find('langSet[@xml:lang="en"]/tig/term', namespaces=_XML_NS)
            term_uk = entry.find('langSet[@xml:lang="uk"]/tig/term', namespaces=_XML_NS)
            definition = entry.find('langSet[@xml:lang="en"]/tig/descrip[@type="definition"]', namespaces=_XML_NS)
            if term_en is None or term_uk is None or definition is None:
                continue
            desc_en = get_clean_text(', '.join((definition.text or '').split('\n')))
            tags = list(x.replace('_', ',') for x in map(str.strip, desc_en.split(',')))
            result.append(GlossaryTerm(get_clean_text(term_en.text), get_clean_text(term_uk.text), tags))
        print(f' done, {len(result)} terms')
        return result

    def __repr__(self) -> str:
        return f'@glossary len={len(self)}'

    def npcs(self) -> list[GlossaryTerm]:
        return [t for t in self if t.is_npc()]

    def resolve(self, text_en: str, fallback=None, is_female=False) -> str:
        # Mirrors ClassicUA's Terms.translate, including its normalisations - a tag written in English
        # only reaches the addon translated if this returns something.
        text_en_lower = text_en.lower()
        patterns = [
            text_en_lower,
            text_en_lower.replace('&', 'and'),
            text_en_lower.replace('weapons', 'weapon'),  # in "... weapon vendor"
        ]
        if text_en_lower.startswith('the '):
            patterns.append(text_en_lower[4:])

        for term in self:
            if term.text_en.lower() in patterns:
                return term.translation(is_female=is_female)
            if term.is_location():
                for alias in term.location_aliases():
                    if alias.lower() in patterns:
                        return term.text_uk
        return fallback

    def terms_by_en(self) -> dict[str, list[GlossaryTerm]]:
        result = dict()
        for term in self:
            result.setdefault(term.text_en.lower(), []).append(term)
        return result

    def terms_by_translation(self) -> dict[str, set[str]]:
        # Reverse index: a Ukrainian translation -> the English terms that produce it
        result = dict()
        for term in self:
            for is_female in (False, True):
                result.setdefault(term.translation(is_female=is_female), set()).add(term.text_en)
        return result

    def npc_id_owners(self) -> dict[tuple[int, str], list[str]]:
        result = dict()
        for term in self.npcs():
            for npc_id in term.npc_ids():
                result.setdefault(npc_id, []).append(term.text_en)
        return result
