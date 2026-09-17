#!/usr/bin/env python3
"""
Text linter for ClassicUA translations.

Replicates the runtime grammar in ClassicUA/scripts/entries.lua so that a
malformed translation is caught before it ships, instead of rendering as
garbage or raising a Lua error in front of a player.

Runs over the complete generated entries after a release, rather than inside a
generation step. A rule belongs in the generator that owns the text whenever
one exists; this covers what no generator reaches yet.

Usage:
    python verification/lint_text.py [entries-dir] [--expansion classic] [--format tsv|text]

With no path it uses CLASSICUA_ROOT/entries from the .env in the repository
root, then input/entries.

Every entries file is compiled with luac first; if any of them does not parse
the run stops there, because no content rule means anything on a file the game
cannot load.

Findings go to the shared issue log, so a run reports what is new, what is
already accepted in verified_issues.tsv and what no longer occurs. --accept
writes the new ones into that file.

Exit code is 2 if an entries file does not compile, 1 on a new error-severity
finding, 0 otherwise.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# run from anywhere, not only with the repository root on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation.utils import issues  # noqa: E402
from generation.utils.text_checks import mixed_script_words  # noqa: E402
from generation.utils.utils import classicua_root  # noqa: E402

log = issues.IssueLog('lint', str(Path(__file__).with_name('verified_issues.tsv')))
OUTPUT = Path(__file__).with_name('output') / 'issues.tsv'

# --------------------------------------------------------------------------
# The runtime grammar (scripts/entries.lua)
# --------------------------------------------------------------------------

# prepare_codes() cases, entries.lua:47
CASES = ("н", "р", "д", "з", "о", "м", "к")

# Plural forms. entries/race.lua and entries/class.lua each end with a loop
# that copies every case table to a "м"-prefixed key holding the plural form
# (element 3 of the case row), so {раса:мр} is the plural of {раса:р}.
# prepare_codes() iterates those tables with pairs() (entries.lua:74, 90), so
# the plural keys become real codes. Verified 2026-09-16: all 91 race and 77
# class case rows carry a plural element, so every plural code resolves.
PLURAL_CASES = tuple("м" + c for c in CASES)

# Latin -> Cyrillic look-alikes, used to repair a mistyped code name or case.
HOMOGLYPHS = str.maketrans({
    "c": "с", "p": "р", "o": "о", "a": "а", "e": "е", "x": "х", "y": "у",
    "i": "і", "k": "к", "r": "р", "m": "м", "t": "т", "h": "н", "b": "в",
    "C": "С", "P": "Р", "O": "О", "A": "А", "E": "Е", "X": "Х", "Y": "У",
    "I": "І", "K": "К", "M": "М", "T": "Т", "H": "Н", "B": "В",
})

# Any letter in any alphabet, as opposed to digits, punctuation and spacing.
HAS_LETTERS = re.compile(r"[^\W\d_]", re.UNICODE)

LATIN = re.compile(r"[a-zA-Z]")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def MIXED_SCRIPT(text: str) -> bool:
    """True when one token mixes Latin and Cyrillic letters."""
    return bool(LATIN.search(text) and CYRILLIC.search(text))


# Personal names have no plural: prepare_codes walks the fixed CASES list
# against options.character.name_cases (entries.lua:50-64), and make_chat_text
# reads name_cases[case] directly (entries.lua:247).
CASES_BY_CODE = {
    "ім'я": CASES,
    "раса": CASES + PLURAL_CASES,
    "клас": CASES + PLURAL_CASES,
    "ціль": CASES + PLURAL_CASES,
}

# Code names built into addon_table.codes by prepare_codes(), entries.lua:44-107.
# make_text() (quests, gossips, books, misc) knows these four.
QUEST_CODE_NAMES = ("ім'я", "раса", "клас", "стать")
# make_chat_text() (entries.lua:196) additionally resolves "ціль".
CHAT_CODE_NAMES = QUEST_CODE_NAMES + ("ціль",)

# make_chat_text() known_templates, entries.lua:197
CHAT_TEMPLATES = ("name", "race", "class", "target")

# Which inline code needs which "#<template>" part present in the same chat
# string. Without it the runtime indexes a nil and the string errors out.
CODE_REQUIRES_TEMPLATE = {
    "ім'я": "name",
    "раса": "race",
    "клас": "class",
    "ціль": "target",
}

CODE_RE = re.compile(r"\{(.-?)\}".replace("-?", ""))  # non-greedy {...}
CODE_RE = re.compile(r"\{([^{}]*)\}")


def casings(word: str) -> tuple[str, str, str]:
    """The three casings push_code_group_to_table() generates (entries.lua:30)."""
    lower = word.lower()
    return lower, lower[:1].upper() + lower[1:], lower.upper()


ALL_CASINGS: dict[str, str] = {}
for _name in CHAT_CODE_NAMES:
    for _form in casings(_name):
        ALL_CASINGS[_form] = _name


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

ERROR, WARN, INFO = issues.ERROR, issues.WARNING, issues.NOTE


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    key: str
    message: str
    excerpt: str
    suggestion: str = ""
    # the stable half of a finding, which is what the issue log compares. The
    # file, line and excerpt move whenever entries are regenerated, so they
    # stay here for reading and never reach an Issue.
    entity: str = ""
    unit_id: str = ""
    expansion: str = ""
    field: str = ""

    def to_issue(self) -> issues.Issue:
        return issues.Issue(self.severity, self.rule, self.entity or "entries",
                            str(self.unit_id), self.expansion, self.field, self.message)

    def as_row(self) -> str:
        def clean(t: str) -> str:
            return t.replace("\t", " ").replace("\n", "\\n")

        return "\t".join(
            [self.severity, self.rule, self.file, str(self.line), self.key,
             self.message, clean(self.excerpt)[:160], clean(self.suggestion)]
        )


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_codes(text: str, kind: str) -> list[tuple[str, str, str]]:
    """
    Inline {code} grammar. Returns (severity, rule, message) tuples.

    Two different symptoms, depending on which builder renders the string:

    * quests, books, gossips go through make_text() (entries.lua:171), a plain
      gsub over the prepared code table, so an unknown code is left alone and
      the player reads "{клас:мр}" on screen.
    * chats go through safe_make_chat_text() (entries.lua:302), which pcalls
      make_chat_text(); a bad code raises inside, the pcall swallows it, the
      line stays English and dev mode logs an issue. Nothing crashes, but the
      translation never appears and only a dev-mode player would notice.
    """
    out = []
    allowed = CHAT_CODE_NAMES if kind in ("chat",) else QUEST_CODE_NAMES
    symptom = ("the line stays English and is logged as a dev-mode issue"
               if kind == "chat" else "renders literally on screen")

    for raw in CODE_RE.findall(text):
        if not raw:
            out.append((ERROR, "code-empty", "empty {} code"))
            continue

        # {1}, {2}: numeric placeholders, only meaningful inside an optional
        # block or a spell template (resolve_optional_variant, entries.lua:401).
        if raw.isdigit():
            if "[" not in text:
                out.append((WARN, "code-number-outside-block",
                            f"{{{raw}}} outside an optional block renders literally"))
            continue

        parts = raw.split(":")
        name = parts[0]
        canonical = ALL_CASINGS.get(name)

        # Two different Latin-letter bugs live inside a {code}, and they need
        # different handling, so keep them apart:
        #   * the code name or its case letter contains a look-alike
        #     ({клас:r}, {cтать:...}). Invisible in review, and repairable by
        #     mapping the Latin letter to its Cyrillic twin.
        #   * a gender variant's own text contains Latin letters
        #     ({стать:зробив:зробиkf}). That is a keyboard-layout slip inside a
        #     Ukrainian word, and only a human can say what was meant.
        head = ":".join(parts[:2]) if canonical != "стать" and len(parts) > 1 else parts[0]
        if MIXED_SCRIPT(head):
            repaired_head = head.translate(HOMOGLYPHS)
            rest = parts[2:]
            repaired = ":".join([repaired_head] + rest) if rest else repaired_head
            rp = repaired.split(":")
            ok = (ALL_CASINGS.get(rp[0]) is not None
                  and (len(rp) < 2 or rp[0].lower() == "стать"
                       or rp[1] in CASES + PLURAL_CASES))
            out.append((ERROR, "code-homoglyph",
                        f"{{{raw}}}: the code name or case mixes Latin and Cyrillic "
                        f"letters, so it never matches; {symptom}",
                        f"{{{repaired}}}" if ok else ""))
            continue

        if any(MIXED_SCRIPT(part) for part in parts[1:]):
            out.append((ERROR, "latin-in-word",
                        f"{{{raw}}}: a Ukrainian word inside the code contains Latin "
                        f"letters, most likely a keyboard-layout slip"))
            continue

        if canonical is None:
            out.append((ERROR, "code-unknown",
                        f"unknown code {{{raw}}}; {symptom}"))
            continue

        if canonical not in allowed:
            out.append((ERROR, "code-wrong-context",
                        f"{{{raw}}} is only resolved in chat text, not in {kind}"))
            continue

        if canonical == "стать":
            # codes["{стать:(.-):(.-)}"], entries.lua:103, and
            # pattern_uk_split[sex+1] in make_chat_text, entries.lua:293
            if len(parts) != 3:
                out.append((ERROR, "gender-arity",
                            f"{{{raw}}} needs exactly two variants, got {len(parts) - 1}"))
            elif any(p == "" for p in parts[1:]):
                out.append((ERROR, "gender-empty",
                            f"{{{raw}}} has an empty gender variant"))
        else:
            if len(parts) > 2:
                out.append((ERROR, "code-extra-args",
                            f"{{{raw}}} takes at most one case letter; {symptom}"))
            else:
                valid = CASES_BY_CODE.get(canonical, CASES)
                if len(parts) == 2 and parts[1] not in valid:
                    if parts[1] in PLURAL_CASES:
                        out.append((ERROR, "code-no-plural",
                                    f"{{{raw}}}: '{canonical}' has no plural forms, only "
                                    f"{'/'.join(CASES)}; {symptom}"))
                    else:
                        near = next((c for c in valid if parts[1].startswith(c)), "")
                        hint = f"{{{parts[0]}:{near}}}" if near else ""
                        msg = (f"{{{raw}}}: '{parts[1]}' is not a case; singular "
                               f"{'/'.join(CASES)}, plural {'/'.join(PLURAL_CASES)}; {symptom}")
                        out.append((ERROR, "code-bad-case", msg, hint))
    return out


def suggest_template(en: str, placeholder: str, context: int = 10) -> str:
    """
    Build the '#<name>...' part a chat string needs, from the English source.

    make_chat_text turns the part into a Lua pattern by replacing <type> with
    "(.-)" and matching it against the live chat line, so the part has to carry
    enough literal context around the placeholder to anchor the capture.
    """
    tag = f"<{placeholder}>"
    i = en.find(tag)
    if i < 0:
        return ""
    before, after = en[:i], en[i + len(tag):]
    # keep whole words only, so the anchor stays readable and stable
    if len(before) > context:
        before = before[-context:]
        if " " in before:
            before = before[before.index(" "):]
    if len(after) > context:
        after = after[:context]
        if " " in after:
            after = after[:after.rindex(" ")]
    return f"#{before}{tag}{after.rstrip()}"


def check_chat_templates(text: str, en: str | None = None) -> list[tuple]:
    """
    Chat strings are "text#<name>template#<class>template...".
    make_chat_text() (entries.lua:196) raises on a '#' part with no <...> in
    it, and gsubs with a nil replacement when a code has no matching template
    part. safe_make_chat_text pcalls it, so the effect is not a crash: the NPC
    line stays English and dev mode logs "Помилка перекладу чату".
    """
    out = []
    parts = text.split("#")
    body, templates = parts[0], parts[1:]

    present = set()
    for tpl in templates:
        m = re.search(r"<([^<>]+)>", tpl)
        if not m:
            out.append((ERROR, "chat-hash-no-template",
                        f"'#{tpl[:24]}' has no <template>; the line stays English"))
            continue
        ttype = m.group(1)
        if ttype in CHAT_TEMPLATES:
            present.add(ttype)
        elif "/" in ttype:
            if not re.match(r"^[^/]+/[^/]+$", ttype):
                out.append((ERROR, "chat-gender-template",
                            f"<{ttype}> must be exactly 'male/female'"))
        else:
            out.append((ERROR, "chat-unknown-template",
                        f"unknown template type <{ttype}>"))

    for raw in CODE_RE.findall(body):
        name = raw.split(":")[0]
        canonical = ALL_CASINGS.get(name)
        needed = CODE_REQUIRES_TEMPLATE.get(canonical)
        if needed and needed not in present:
            hint = suggest_template(en, needed) if en else ""
            msg = f"{{{raw}}} has no '#<{needed}>...' part to read from; the line stays English"
            if hint:
                msg += f"; the English contains <{needed}>, so this is mechanically fixable"
            out.append((ERROR, "chat-template-missing", msg, hint))
    return out


FORMAT_SPEC = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[diouxXeEfgGqcs%]")


def check_percent(text: str, en: str | None, owner: str = "") -> list[tuple[str, str, str]]:
    """
    chats.lua:107 calls string.format(chat_text_uk, npc_name_uk) ONLY when the
    *Ukrainian* text matches "%s". So:

    * uk has %s and also a bare % elsewhere -> string.format raises. Real error.
    * uk has no %s -> format is never called and every % is shown literally.
      If the English line had %s, the NPC name is simply never substituted.
    * the English itself sometimes carries a bare % (a Wowhead artifact where
      %s lost its 's'); that is a scrape bug to fix upstream, not a runtime one.
    """
    out = []
    specs = FORMAT_SPEC.findall(text)
    placeholders = sum(1 for s in specs if s == "%s")
    conversions = [s for s in specs if s not in ("%s", "%%")]
    stripped = FORMAT_SPEC.sub("", text)
    has_s = placeholders > 0

    # format is handed exactly one argument, the NPC name, so a single %s and
    # any number of %% are the only safe constructs.
    if placeholders > 1:
        out.append((ERROR, "percent-many-placeholders",
                    f"{placeholders} '%s' placeholders but string.format is given only the "
                    "NPC name, so it raises 'no value'"))
    if conversions:
        out.append((ERROR, "percent-conversion",
                    f"'{conversions[0]}' would receive the NPC name, which is a string, "
                    "so string.format raises"))

    if has_s and "%" in stripped:
        out.append((ERROR, "percent-bare",
                    "text contains %s so string.format runs; the other bare '%' raises. Escape it as '%%'"))
    elif "%" in stripped and not has_s:
        if en and "%" in FORMAT_SPEC.sub("", en):
            out.append((INFO, "percent-english-artifact",
                        "both English and translation carry a bare '%'; the English was likely scraped from a truncated %s"))
        else:
            out.append((WARN, "percent-literal",
                        "bare '%' is displayed as-is because the text has no %s to trigger string.format"))

    if en is not None:
        want, got = en.count("%s"), text.count("%s")
        if want and not got:
            # Under a specific NPC key the translator may legitimately write the
            # name out in full, which often reads better in Ukrainian. Under
            # "!common" the same line is reused for every NPC, so dropping %s
            # hard-codes the wrong name.
            shared = owner == "!common"
            out.append((WARN if shared else INFO, "percent-parity",
                        f"English has {want} %s but the translation has none"
                        + ("; this line is shared by every NPC, so the name is wrong for all but one"
                           if shared else
                           f"; harmless under a single NPC key, the name is written out instead")))
        elif want != got:
            out.append((INFO, "percent-parity",
                        f"English has {want} %s, translation has {got}"))
    return out


def check_optional_blocks(text: str) -> list[tuple[str, str, str]]:
    """
    resolve_optional_entry_text (entries.lua:438) replaces any [..#..] block
    with "" when no variant matches, so a block with no unconditional default
    can silently delete text.
    """
    out = []
    if text.count("[") != text.count("]"):
        out.append((ERROR, "bracket-unbalanced",
                    f"{text.count('[')} '[' vs {text.count(']')} ']'"))
        return out

    for block in re.findall(r"\[([^\[\]]*)\]", text):
        if "#" not in block:
            continue  # not an optional block; left as is
        variants = block.split("||")
        if all("#" in v for v in variants):
            out.append((WARN, "optional-no-default",
                        "every variant is conditional; renders as empty text when none match"))
        for v in variants:
            if v.startswith("#"):
                out.append((ERROR, "optional-empty-variant",
                            "a variant has no text before its '#'"))
    return out


def check_misc(text: str, en: str | None) -> list[tuple[str, str, str]]:
    out = []
    # the inside of a {code} is left to code-homoglyph and latin-in-word,
    # which say more about it than the shared rule does
    for word in mixed_script_words(re.sub(r"\{[^}]*\}", " ", text)):
        out.append((ERROR, "mixed-script",
                    f"{word!r} mixes Cyrillic and Latin letters, so it reads "
                    f"correctly on screen but never matches a lookup"))
    if "]===]" in text:
        out.append((ERROR, "long-bracket",
                    "']===]' terminates the generated Lua long string early"))
    # Runs of three or more newlines are only worth reporting when the English
    # source does not have them too. Most of the shipped ones are faithful
    # copies of a Wowhead page that already had the blank lines, so without the
    # English this rule cannot tell a defect from a match, and stays quiet
    # rather than guessing.
    def newline_runs(t: str) -> int:
        return len(re.findall(r"\n{3,}", t))

    if newline_runs(text) and en is not None and newline_runs(en) < newline_runs(text):
        out.append((INFO, "triple-newline",
                    f"{newline_runs(text)} runs of three or more newlines, "
                    f"the English has {newline_runs(en)}"))
    if text != text.strip() and (en is None or en == en.strip()):
        out.append((INFO, "whitespace", "leading or trailing whitespace"))
    # data_hooks.set_translation returns nil when en == uk (data_hooks.lua:59),
    # so an identical translation silently falls back to English. That is only
    # worth reporting when there was something to translate in the first place:
    # a string with no letters in any alphabet is identical on purpose, such as
    # "..." or the binary-code page of item 9316, and nobody can act on it.
    if en is not None and en.strip() and text.strip() == en.strip():
        if HAS_LETTERS.search(text):
            out.append((WARN, "identical-to-english",
                        "translation equals the English text; set_translation returns "
                        "nil so the field falls back to English"))
    return out


def lint_string(text: str, en: str | None, kind: str, owner: str = "") -> list[tuple[str, str, str]]:
    out = []
    out += check_codes(text, kind)
    out += check_optional_blocks(text)
    out += check_misc(text, en)
    if kind == "chat":
        out += check_chat_templates(text, en)
        out += check_percent(text, en, owner)
    return out


# --------------------------------------------------------------------------
# Extraction from the generated Lua
# --------------------------------------------------------------------------

LONG_STRING = re.compile(r"\[===\[(.*?)\]===\]", re.S)
ENTRY_KEY = re.compile(r"^\[([^\]]+)\]\s*=|^\[(\"[^\"]+\")\]\s*=")


NPC_IN_NPC_LUA = re.compile(r'^\[(\d+)\]\s*=\s*\{\s*"([^"\n]*)"', re.M)
NPC_IN_CHAT_LUA = re.compile(r'^\["([^"\n]+)"\]\s*=\s*\{\s*"([^"\n]*)"', re.M)


def check_npc_names(root: Path) -> list[Finding]:
    """
    chats.lua substitutes the NPC name into the translation with gsub, and gsub
    reads "%" in a replacement as an escape: "%1" is a capture reference and "%"
    before anything else raises. No NPC name contains one today, so the runtime
    does not guard against it; this rule is the guard.
    """
    out = []
    for path in sorted(root.rglob("*.lua")):
        if path.name == "npc.lua":
            pattern, label = NPC_IN_NPC_LUA, "npc"
        elif path.name == "chat.lua":
            pattern, label = NPC_IN_CHAT_LUA, "chat speaker"
        else:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        src = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(src):
            key, name = match.group(1), match.group(2)
            if "%" not in name:
                continue
            line = src.count("\n", 0, match.start()) + 1
            out.append(Finding(
                ERROR, "npc-name-percent", rel, line, f"{label} {key}",
                "a '%' in an NPC name is an escape to gsub, so the chat "
                "substitution would corrupt or fail on it", name,
                entity=path.stem, unit_id=key, expansion=folder_of(path, root)))
    return out


def folder_of(path: Path, root: Path) -> str:
    # the expansion folder, or nothing for the files that sit at the top
    return path.parent.name if path.parent != root else ""


def check_lua_syntax(root: Path, luac: str) -> list[Finding]:
    """
    A translation carrying a stray ']===]' or an unbalanced quote produces a
    file the game cannot load at all, which no content rule would notice.
    """
    files = sorted(root.rglob("*.lua"))
    out = []
    for i in range(0, len(files), 32):
        chunk = files[i:i + 32]
        # one call per batch, then per file only for a batch that failed
        if subprocess.run([luac, "-p", *map(str, chunk)],
                          capture_output=True).returncode == 0:
            continue
        for path in chunk:
            proc = subprocess.run([luac, "-p", str(path)], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace")
            if proc.returncode == 0:
                continue
            first = ((proc.stderr or proc.stdout).strip().splitlines() or ["luac failed"])[0]
            at = re.search(r":(\d+):", first)
            out.append(Finding(
                ERROR, "lua-syntax", str(path.relative_to(root)).replace("\\", "/"),
                int(at.group(1)) if at else 0, path.name,
                re.sub(r"^.*?:\d+:\s*", "", first), ""))
    return out


TABLE_KEY = re.compile(r"^\[([^\]]{1,80})\]\s*=")
OPENS_BLOCK = re.compile(r"^\[[^\]]{1,80}\]\s*=\s*\{")


def check_duplicate_keys(root: Path) -> list[Finding]:
    """
    A repeated key in a Lua table literal keeps the last value, so a second
    translation under the same key disappears with nothing to show for it.
    """
    out = []
    for path in sorted(root.rglob("*.lua")):
        rel = str(path.relative_to(root)).replace("\\", "/")
        src = path.read_text(encoding="utf-8", errors="replace")

        starts, pos = [], 0
        for ln in src.splitlines():
            starts.append(pos)
            pos += len(ln) + 1

        def value_at(at: tuple[int, int]) -> str:
            # a value is either a long string or a plain quoted one on the line
            off = starts[at[0] - 1] + at[1]
            rest = src[off:].split("\n", 1)[0].strip()
            if rest.startswith("[===["):
                m = LONG_STRING.search(src, off)
                return m.group(1) if m else ""
            return rest.rstrip(",").strip()

        # blank the long strings, so their text cannot look like table syntax
        skeleton = LONG_STRING.sub(lambda m: "\n" * m.group(0).count("\n"), src)
        stack = [({}, "")]
        for no, line in enumerate(skeleton.splitlines(), 1):
            if line.startswith("}") and len(stack) > 1:
                stack.pop()
                continue
            match = TABLE_KEY.match(line)
            if not match:
                continue
            key, opens = match.group(1), OPENS_BLOCK.match(line) is not None
            here = (no, match.end())
            seen, owner = stack[-1]
            if key in seen:
                same = not opens and value_at(seen[key]) == value_at(here)
                out.append(Finding(
                    WARN if same else ERROR, "duplicate-key", rel, no,
                    f"{owner} {key}".strip(),
                    # no line number: it moves on every regeneration, and the
                    # message is half of an issue's identity
                    "the key is already used in this block, lua keeps the last "
                    "value, so the " + ("earlier copy is redundant" if same
                                        else "earlier value is lost"),
                    value_at(here),
                    entity=path.stem, unit_id=key,
                    expansion=folder_of(path, root), field=owner))
            else:
                seen[key] = here
            if opens:
                stack.append(({}, key.strip('"')))
    return out


def kind_for(path: Path) -> str:
    n = path.name
    if n.startswith("chat"):
        return "chat"
    if n.startswith("gossip"):
        return "gossip"
    if n.startswith("quest"):
        return "quest"
    if n.startswith("book"):
        return "book"
    return "other"


def extract(path: Path):
    """
    Yield (line_no, key, english_or_None, ukrainian) for every translated
    string in a generated entries file.

    Generated chat/gossip files put the English line in a '-- ' comment
    immediately above the translation; quest files carry en="Title" on the
    entry line.
    """
    src = path.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()

    # offset -> line number, for reporting
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1

    def line_of(off: int) -> int:
        lo, hi = 0, len(offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offsets[mid] <= off:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    key = ""
    owner = ""
    en_comment: str | None = None
    en_title: str | None = None
    quest_field = 0
    QUEST_FIELDS = ("title", "description", "objective", "progress", "completion")
    kind = kind_for(path)

    page = 0
    idx = 0
    while idx < len(src):
        m = LONG_STRING.search(src, idx)
        if not m:
            break
        head = src[idx:m.start()]

        # entry key and English hints from the text between the previous
        # string and this one
        for hm in re.finditer(r"(?m)^\s*\[([^\]]{1,80})\]\s*=", head):
            key = hm.group(1)
            quest_field = 0
            page = 0
            # in chat.lua and gossip.lua the outer key is the NPC (a quoted
            # name or an id) and the inner key is the text hash
            if key.startswith('"'):
                owner = key.strip('"')
        tm = re.search(r'en\s*=\s*"((?:[^"\\]|\\.)*)"', head)
        if tm:
            en_title = tm.group(1).encode().decode("unicode_escape", errors="replace")
            quest_field = 0
        cm = None
        for cm in re.finditer(r"(?m)^--\s?(.*)$", head):
            pass
        en_comment = cm.group(1) if cm else None

        # Empty quest fields are written as a bare "nil," placeholder
        # (dev/utils.py:164-173), so the array always has five positions.
        # Count those to keep the field index aligned; skipping them would
        # mislabel every field after the first empty one.
        if kind == "quest":
            quest_field += len(re.findall(r"(?m)^\s*nil\s*,", head))

        text = m.group(1)
        if kind == "quest":
            en = en_title if quest_field == 0 else None
            field = QUEST_FIELDS[quest_field] if quest_field < len(QUEST_FIELDS) else "extra"
            yield line_of(m.start()), f"{key}.{field}", en, text, (key, field)
            quest_field += 1
        elif kind == "book":
            page += 1
            yield line_of(m.start()), f"{key}.PAGE_{page}", None, text, (key, f"PAGE_{page}")
        else:
            yield line_of(m.start()), key, en_comment, text, ("owner", owner)

        idx = m.end()


class EnglishSource:
    """
    Supplies the English original for entries files that do not carry it.

    Chat and gossip files already print the English line in a comment above
    each translation, but quests and books do not, so the comparative checks
    (newline runs, %s parity, identical-to-English) have nothing to compare
    against. Two local sources fill that gap:

      * quests: ClassicUA/dev/database/classicua.db, table `quests`
      * books:  ClassicUA/dev/translation_from_crowdin/en/books*/**/*_<id>.xml

    Both are optional. When a unit's English is unknown the comparative rules
    stay quiet instead of reporting something they cannot verify.
    """

    QUEST_FIELDS = ("title", "description", "objective", "progress", "completion")

    def __init__(self, db: "Path | None" = None, crowdin_en: "Path | None" = None):
        self.quests: dict[str, dict[str, str]] = {}
        self.books: dict[str, dict[str, str]] = {}
        if db and db.is_file():
            self._load_quests(db)
        if crowdin_en and crowdin_en.is_dir():
            self._load_books(crowdin_en)

    def _load_quests(self, db: "Path") -> None:
        import sqlite3
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            cols = ", ".join(self.QUEST_FIELDS)
            for row in con.execute(f"select id, {cols} from quests"):
                # the same id can appear once per expansion; the first row wins,
                # matching the generator's merge order where older text wins
                self.quests.setdefault(
                    str(row[0]),
                    {f: (row[i + 1] or "") for i, f in enumerate(self.QUEST_FIELDS)})
        finally:
            con.close()

    def _load_books(self, en_root: "Path") -> None:
        from xml.etree import ElementTree
        for xml in en_root.glob("books*/**/*.xml"):
            m = re.search(r"_(\d+)\.xml$", xml.name)
            if not m:
                continue
            try:
                tree = ElementTree.parse(xml)
            except ElementTree.ParseError:
                continue
            pages = {n.get("name"): n.text
                     for n in tree.iter("string") if n.get("name") and n.text}
            if pages:
                self.books.setdefault(m.group(1), pages)

    def lookup(self, kind: str, expansion: str, entry_id: str, field: str) -> "str | None":
        entry_id = entry_id.strip().strip('"')
        if kind == "quest":
            return (self.quests.get(entry_id) or {}).get(field) or None
        if kind == "book":
            return (self.books.get(entry_id) or {}).get(field) or None
        return None

    def __bool__(self) -> bool:
        return bool(self.quests or self.books)


def lint_file(path: Path, root: Path, english: "EnglishSource | None" = None) -> list[Finding]:
    kind = kind_for(path)
    if kind == "other":
        return []
    rel = str(path.relative_to(root)).replace("\\", "/")
    expansion = path.parent.name
    out = []
    for line, key, en, text, unit in extract(path):
        if en is None and english is not None and unit is not None:
            en = english.lookup(kind, expansion, unit[0], unit[1])
        owner = unit[1] if unit and unit[0] == "owner" else ""
        # chat and gossip key by hash, quest and book by entry id and field.
        # Either way the pair survives a regeneration. The owner rides along
        # only for chat: extract() tracks a quoted key, which is the NPC name
        # there but a stale "!code" entry under gossip's numeric owners.
        if unit and unit[0] == "owner":
            unit_id, field = key, (owner if kind == "chat" else "")
        else:
            unit_id, field = unit[0], unit[1]
        for item in lint_string(text, en, kind, owner):
            severity, rule, message = item[0], item[1], item[2]
            suggestion = item[3] if len(item) > 3 else ""
            out.append(Finding(severity, rule, rel, line, key, message, text, suggestion,
                               entity=kind, unit_id=unit_id, expansion=expansion, field=field))
    return out


# --------------------------------------------------------------------------

def default_entries() -> Path:
    root = classicua_root()
    return root / "entries" if root else Path("input/entries")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entries", type=Path, nargs="?",
                    help="path to ClassicUA/entries "
                         "(default: CLASSICUA_ROOT/entries, then input/entries)")
    ap.add_argument("--expansion", action="append",
                    help="limit to these expansion folders (repeatable)")
    ap.add_argument("--rule", action="append", help="limit to these rules (repeatable)")
    ap.add_argument("--severity", default=INFO, choices=[ERROR, WARN, INFO])
    ap.add_argument("--format", default="text", choices=["text", "tsv"])
    ap.add_argument("--db", type=Path,
                    help="classicua.db, supplies the English quest text "
                         "(default: <entries>/../dev/database/classicua.db)")
    ap.add_argument("--crowdin-en", type=Path,
                    help="Crowdin English export root, supplies English book pages "
                         "(default: <entries>/../dev/translation_from_crowdin/en)")
    ap.add_argument("--luac", help="luac used for the syntax check (default: from PATH)")
    ap.add_argument("--accept", nargs="?", const="", metavar="NOTE",
                    help="write the new issues into verified_issues.tsv, with an optional note")
    args = ap.parse_args()

    root = (args.entries or default_entries()).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    luac = args.luac or shutil.which("luac")
    syntax_note = "lua syntax: not checked, luac was not found on PATH"
    if not luac:
        print(syntax_note, file=sys.stderr)
    else:
        syntax_note = f"lua syntax: {len(list(root.rglob('*.lua')))} files compile"
        broken = check_lua_syntax(root, luac)
        if broken:
            # a file the game cannot load makes every content rule meaningless,
            # so this is a failed run rather than a finding to triage
            for f in broken:
                log.fail(f"{f.file}:{f.line} does not compile: {f.message}")
            return log.finish(write_to=str(OUTPUT))

    files = sorted(p for p in root.rglob("*.lua")
                   if kind_for(p) != "other"
                   and (not args.expansion or p.parent.name in args.expansion))

    db = args.db or root.parent / "dev" / "database" / "classicua.db"
    crowdin_en = args.crowdin_en or root.parent / "dev" / "translation_from_crowdin" / "en"
    english = EnglishSource(db, crowdin_en)

    findings: list[Finding] = []
    for p in files:
        findings.extend(lint_file(p, root, english))
    findings.extend(check_npc_names(root))
    findings.extend(check_duplicate_keys(root))

    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings.sort(key=lambda f: (order[f.severity], f.rule, f.file, f.line))

    # the log always sees every finding: --severity and --rule narrow what is
    # printed below, never what is compared, or a filtered run would report the
    # rest as gone
    for f in findings:
        log.issues.append(f.to_issue())

    cut = order[args.severity]
    shown = [f for f in findings if order[f.severity] <= cut
             and (not args.rule or f.rule in args.rule)]

    if args.format == "tsv":
        print("severity\trule\tfile\tline\tkey\tmessage\texcerpt")
        for f in shown:
            print(f.as_row())
    else:
        counts: dict[tuple[str, str], int] = {}
        for f in shown:
            counts[(f.severity, f.rule)] = counts.get((f.severity, f.rule), 0) + 1
        print(f"scanned {len(files)} files under {root}")
        print(syntax_note)
        print(f"english: {len(english.quests)} quests and {len(english.books)} books "
              f"available for the comparative rules" if english
              else "english: none found, comparative rules are off")
        print()
        for (severity, rule), n in sorted(counts.items(), key=lambda kv: (order[kv[0][0]], -kv[1])):
            print(f"  {severity:<8} {rule:<28} {n:>6}")
        print()
        for f in shown:
            if f.severity == ERROR:
                print(f"{f.file}:{f.line} [{f.rule}] {f.key}: {f.message}")
                print(f"    {f.excerpt[:200]!r}")
                if f.suggestion:
                    print(f"    suggested fix: {f.suggestion!r}")

    if args.accept is not None:
        accepted = log.accept_new(args.accept)
        print(f"accepted {accepted} new issue(s) into {log.verified_path}")
        return 0

    return log.finish(write_to=str(OUTPUT))


if __name__ == "__main__":
    sys.exit(main())
