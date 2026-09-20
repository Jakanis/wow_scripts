import re

from bs4 import BeautifulSoup

# Wowhead mirrors the markup the game itself returns from ItemTextGetText(), so a book page carries
# exactly what ItemTextPageText - a SimpleHTML frame - knows how to render: headings, paragraphs,
# line breaks and images, each able to carry an align. Anything richer than a line break has to stay
# markup: flattening it to text loses the layout, and an <img> disappears without a trace.
STRUCTURAL_TAGS = ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img')

# SimpleHTML only parses a page that is a whole document; without the wrapper it shows the markup as
# literal text. ClassicUA's entries/<expansion>/object_text.lua carries pages in this exact shape.
__HTML_OPEN = '<html>\n<body>\n'
__HTML_CLOSE = '\n</body>\n</html>'

# The images are client textures that Wowhead serves from its own mirror, so the src has to go back
# to the path the game loads: //wow.zamimg.com/images/wow/interface/Pictures/21037_crudemap_256.jpg
# becomes Interface\Pictures\21037_crudemap_256.
__ZAMIMG_SRC = re.compile(r'(<img[^>]*?\bsrc=")//wow\.zamimg\.com/images/wow/([^"]+)(")', re.I)

# One block per line, with the breaks that follow it, so a translator on Crowdin sees the structure
# instead of a single long line.
__BLOCK_END = re.compile(r'(</(?:p|h[1-6])>|<img[^>]*/?>)((?:\s*<br\s*/?>)*)', re.I)


def __to_game_texture(match: re.Match) -> str:
    path = re.sub(r'\.(jpg|jpeg|png|gif|blp)$', '', match.group(2), flags=re.I)
    path = '\\'.join(part for part in path.split('/') if part)
    # the game's own paths spell it Interface; Wowhead lowercases the first segment
    path = re.sub(r'^interface\\', 'Interface\\\\', path, flags=re.I)
    return match.group(1) + path + match.group(3)


def __as_markup(page: str) -> str:
    page = __ZAMIMG_SRC.sub(__to_game_texture, page)
    page = __BLOCK_END.sub(lambda m: m.group(1) + m.group(2).strip() + '\n', page)
    return __HTML_OPEN + page.strip() + __HTML_CLOSE


def __as_text(soup: BeautifulSoup) -> str:
    for element in soup.find_all('br'):
        element.replace_with('\n')
    for element in soup.find_all('p'):
        if element.next_sibling:
            element.replace_with(element.text + '\n')
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        element.replace_with(element.text + '\n')
    # the game pads sentence breaks with a non-breaking space; dropping it leaves the single space
    # that is already beside it, which is what the translated sources have always been written against
    return soup.text.replace(' ', '')


def parse_book_page(page: str) -> str:
    """A page of Wowhead's book blob, as text when a line break is all it holds and as markup when
    it holds more. Returns '' for a page with neither text nor an image."""
    soup = BeautifulSoup(page, 'html5lib')
    if soup.find(STRUCTURAL_TAGS):
        return __as_markup(page)

    text = __as_text(soup)
    return text if text.strip() else ''


def parse_book_pages(html: str) -> list[str]:
    """The pages of the new Book({...}) blob on a Wowhead item or object page."""
    import json5

    for line in html.split('\n'):
        if 'new Book(' not in line:
            continue
        start = line.find('new Book({') + 9
        end = line.find('})', start) + 1
        raw_pages = json5.loads(line[start:end]).get('pages') or []
        # An empty page is dropped, as it always was - but an image-only page is not empty, it is a
        # page whose whole content used to vanish in the flattening, taking the page numbering with it.
        return [page for page in (parse_book_page(raw) for raw in raw_pages) if page]

    return []


def is_markup(page: str) -> bool:
    return page.startswith('<html>')
