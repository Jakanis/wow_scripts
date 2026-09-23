import ast
import json
import math
import operator
import re

# A Wowhead page arrives with its tooltip divs empty and the markup for them in a script:
# g_spells[<id>].tooltip_enus and .buff_enus. The page's own script puts that markup into #tt<id> and
# #btt<id> and works out the expressions in it, which is the only reason the pages were ever rendered in
# a browser. Everything the browser uses is already in the page, so the same work is done here.
FRAME = ('<table><tr><td>%s</td><th style="background-position: top right"></th></tr><tr>'
         '<th style="background-position: bottom left"></th>'
         '<th style="background-position: bottom right"></th></tr></table>')

__COMMENT = re.compile(r'<!--.*?-->', re.S)
# A number the script can work out again - points, a talent, a character level - carries one of these
# markers. Parentheses are worked out only where one appears, so that prose in brackets is left alone.
__MARKER = re.compile(r'<!--(?:pts|sp|ppl|pl|lvl)')
# Letters in either case, for the functions: the TBC and Mists pages write Max and Min where the Wrath and
# Cata pages write max and min, the same formula on the same level marker. A letter lets a formula through
# to the evaluator, not into the result - a name it does not know, a Spell Power say, still leaves the
# formula as the page wrote it.
__EXPRESSION = re.compile(r'[\d\s.+\-*/()^,<>=!?:a-zA-Z]*')
__TALENT_BLOCK = re.compile(r'(<!--sp(\d+):\d+-->)(.*?)(<!--sp\2-->)', re.S)
# nothing but a number, or arithmetic on numbers
__NUMERIC = re.compile(r'[\d\s.+\-*/()]*\d[\d\s.+\-*/()]*')
# a real tag, as against the < of a comparison such as "85 <= 70"
__TAG = re.compile(r'</?[a-zA-Z]')
# a div the page leaves without any text of its own, which the browser drops
__EMPTY_QUALITY = re.compile(r'<div class="q">(?:\s|<!--.*?-->)*</div>', re.S)

__OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
    ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    # the page is worked out by JavaScript, where ^ is exclusive or rather than a power: the page for
    # [200 * (2^1)] shows 600, not 400
    ast.BitXor: lambda left, right: int(left) ^ int(right),
}
__FUNCTIONS = {'abs': abs, 'floor': math.floor, 'ceil': math.ceil, 'round': round,
               'min': min, 'max': max}


def __script_string(html: str, collection: str, id: int, field: str) -> str | None:
    match = re.search(r'g_%s\[%d\]\.%s\s*=\s*("(?:[^"\\]|\\.)*")' % (collection, id, field), html)
    return json.loads(match.group(1)) if match else None


def __matching(expression: str, start: int) -> int:
    depth = 0
    for i in range(start, len(expression)):
        if expression[i] == '(':
            depth += 1
        elif expression[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def __as_python(expression: str) -> str:
    # the expressions are JavaScript, where a condition reads "a ? b : c" and has no Python spelling.
    # Whatever stands in parentheses is turned first, so that by the time a condition is looked for here
    # every condition inside one has gone - the page always puts a condition within a condition in
    # parentheses.
    turned, i = [], 0
    while i < len(expression):
        if expression[i] == '(':
            end = __matching(expression, i)
            if end > 0:
                turned.append('(%s)' % __as_python(expression[i + 1:end]))
                i = end + 1
                continue
        turned.append(expression[i])
        i += 1
    expression = ''.join(turned)

    depth = 0
    question = -1
    for i, character in enumerate(expression):
        if character == '(':
            depth += 1
        elif character == ')':
            depth -= 1
        elif depth:
            continue
        elif character == '?' and question < 0:
            question = i
        elif character == ':' and question >= 0:
            return '(%s) if (%s) else (%s)' % (expression[question + 1:i], expression[:question],
                                               __as_python(expression[i + 1:]))
    return expression


def __evaluate(expression: str):
    def value(node):
        if isinstance(node, ast.Expression):
            return value(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in __OPERATORS:
            return __OPERATORS[type(node.op)](value(node.left), value(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in __OPERATORS:
            return __OPERATORS[type(node.op)](value(node.operand))
        if isinstance(node, ast.IfExp):
            return value(node.body) if value(node.test) else value(node.orelse)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in __OPERATORS:
            return __OPERATORS[type(node.ops[0])](value(node.left), value(node.comparators[0]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = __FUNCTIONS.get(node.func.id.lower())
            if function:
                return function(*[value(argument) for argument in node.args])
        raise ValueError(expression)

    expression = expression.replace('true', '1').replace('false', '0')
    return value(ast.parse(__as_python(expression.strip()), mode='eval'))


def __as_text(value) -> str:
    if isinstance(value, bool):
        value = int(value)
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return ('%.3f' % value).rstrip('0').rstrip('.')


def __worked_out(fragment: str) -> str | None:
    """The fragment as the number it comes to, or None when it is not an expression at all - it names a
    Spell Power or an Attack Power, say, which the page cannot put a number to either."""
    expression = __COMMENT.sub('', fragment)
    if not __EXPRESSION.fullmatch(expression) or not re.search(r'\d|true|false', expression):
        return None
    try:
        return __as_text(__evaluate(expression))
    except Exception:
        return None


def __closing(markup: str, start: int, opening: str, closing: str) -> int:
    depth, i = 0, start
    while i < len(markup):
        if markup.startswith('<!--', i):
            i = markup.find('-->', i) + 3
            if i < 3:
                return -1
            continue
        if markup[i] == '<' and __TAG.match(markup, i):
            return -1  # a tag in the middle of it: whatever this is, it is not an expression
        if markup[i] == opening:
            depth += 1
        elif markup[i] == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def __closing_note(markup: str, start: int) -> int:
    depth, i = 0, start
    while i < len(markup):
        if markup.startswith('<!--', i):
            i = markup.find('-->', i) + 3
            if i < 3:
                return -1
            continue
        if markup[i] == '[':
            depth += 1
        elif markup[i] == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def __work_out(markup: str) -> str:
    out, i = [], 0
    while i < len(markup):
        character = markup[i]
        if character in '[(':
            end = __closing(markup, i, character, ']' if character == '[' else ')')
            if end > 0:
                # a bracket is always meant as an expression; parentheses are prose unless they carry a
                # marker, or every "(see below)" would be read as one
                if character == '[' or __MARKER.search(markup[i:end + 1]):
                    value = __worked_out(markup[i + 1:end])
                    if value is not None:
                        out.append(value)
                        i = end + 1
                        continue
        if character == '[':
            # a bracket that does not come to a number holds a note of its own, such as a glyph's
            # effect or a tuning note, and the page leaves all of it alone - the numbers within it
            # included. A note may have tags and brackets of its own in it, so only the brackets are
            # counted to find where it ends.
            end = __closing_note(markup, i)
            if end > 0:
                out.append(markup[i:end + 1])
                i = end + 1
                continue
        out.append(character)
        i += 1
    return ''.join(out)


def __as_talent_values(markup: str) -> str:
    # A talent's block holds what the tooltip says with no points in the talent, and the page writes it
    # back without the &nbsp; of a sentence break. A number it writes back as it writes any value:
    # trimmed, and one that stands in parentheses inside a second pair - " (1)" comes out as "((1))".
    # Text keeps its spaces, or "sec. &nbsp;Cannot" would lose the one it needs. A block may hold another.
    def written_back(match):
        value = __as_talent_values(match.group(3)).replace('&nbsp;', '').replace(' ', '')
        if __NUMERIC.fullmatch(__COMMENT.sub('', value)):
            value = value.strip()
            if value.startswith('(') and value.endswith(')'):
                value = '(%s)' % value
        return match.group(1) + value + match.group(4)
    return __TALENT_BLOCK.sub(written_back, markup)


def render_tooltips(html: str, collection: str, id: int) -> str:
    """The page as its own script would leave it: the tooltip markup moved out of the script and into the
    divs it belongs to, with the expressions in it worked out."""
    for field, div_id in (('tooltip_enus', 'tt%d' % id), ('buff_enus', 'btt%d' % id)):
        markup = __script_string(html, collection, id, field)
        if not markup:
            continue
        markup = __as_talent_values(markup)
        markup = __work_out(markup)
        markup = __EMPTY_QUALITY.sub('', markup)
        html = re.sub(r'(<div[^>]*\bid="%s"[^>]*>)\s*(</div>)' % div_id,
                      lambda m: m.group(1) + FRAME % markup + m.group(2), html, count=1)
    return html
