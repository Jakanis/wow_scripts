#!/usr/bin/env python3
"""
Rule tests for lint_text.py.

Each case is (kind, english, ukrainian, expected rules). An empty expectation
means the string must produce no findings at all, which is how the false
positives found on real data are pinned down so they cannot come back.

Run:  python tests/run.py
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# loaded by path: the linter is a script under generation/lint, not something
# the package layout exposes as a module
_spec = importlib.util.spec_from_file_location(
    "lint_text_under_test", ROOT / "generation" / "lint" / "lint_text.py")
L = importlib.util.module_from_spec(_spec)
# registered before exec: @dataclass resolves its own module through sys.modules
sys.modules[_spec.name] = L
_spec.loader.exec_module(L)

CASES = [
    # --- inline codes --------------------------------------------------
    ("quest", None, "Вітаю, {ім'я:к}!", []),
    ("quest", None, "Вітаю, {ім'я:кл}!", ["code-bad-case"]),
    ("quest", None, "Тобі треба тренер {клас:мр}.", []),          # plural case
    ("quest", None, "Смерть усім {раса:мн}!", []),                # plural case
    ("quest", None, "Привіт, {ім'я:мр}!", ["code-no-plural"]),    # names have none
    ("quest", None, "Ти {стать:зробив:зробила} це.", []),
    ("quest", None, "Ти {стать:зробив} це.", ["gender-arity"]),
    ("quest", None, "Ти {стать:стать:хлопче:дівчино}.", ["gender-arity"]),
    ("quest", None, "Ти {стать;зробив:зробила} це.", ["code-unknown"]),
    ("quest", None, "{Вандріл починає читати листа.}", ["code-unknown"]),
    ("quest", None, "Гаразд, {клас:r}.", ["code-homoglyph"]),     # latin r
    ("quest", None, "{cтать:хоробрий:хоробра}", ["code-homoglyph"]),  # latin c
    ("quest", None, "Ти {стать:зробив:зробиkf}.", ["latin-in-word"]),
    ("quest", None, "Привіт, {ціль:н}!", ["code-wrong-context"]),  # chat only
    ("quest", None, "Як проникнути в Аркатраc", ["mixed-script"]),   # latin c
    ("quest", None, "Як проникнути в Аркатраз", []),
    ("quest", None, "Мені потрібен OOX-17/TН", ["mixed-script"]),    # latin T
    ("quest", None, "|cFFFFFFFFРозпалення душі:|r", []),             # client markup
    ("chat", None, "Гей!#Hey, <race>, over here", []),               # english template

    # --- chat templates ------------------------------------------------
    ("chat", "<name>, you have disturbed me!", "{Ім'я:н}, ти мене потривожив!",
     ["chat-template-missing"]),
    ("chat", "<name>, you have disturbed me!",
     "{Ім'я:н}, ти мене потривожив!#<name>, you have", []),
    ("chat", "This <class> intrudes!", "{Раса:н} заважає!#This <class> intrudes",
     ["chat-template-missing"]),                                   # code/template mismatch
    ("chat", "Die, scoundrel!", "Помри, {ім'я:к}!scoundrel", ["chat-template-missing"]),

    # --- percent handling ----------------------------------------------
    ("chat", "%s laughs.", "%s сміється.", []),
    ("chat", "% giggles.", "% сміється.", ["percent-literal"]),
    # "%%" is a correctly escaped percent, so only the missing second %s shows
    ("chat", "%s laughs at %s.", "%s сміється з 50%% шансом.", ["percent-parity"]),
    # a real bare % alongside a %s: string.format runs and raises on it
    ("chat", "%s laughs.", "%s сміється 50% часу.", ["percent-bare"]),
    # format gets one argument, so a second placeholder raises "no value"
    ("chat", "%s greets %s.", "%s вітає %s", ["percent-many-placeholders"]),
    # any other conversion receives the NPC name, which is a string
    ("chat", "%s has %d gold.", "%s має %d золота", ["percent-conversion"]),
    # an escaped percent is fine
    ("chat", "%s and 50%% more.", "%s і %% разом", []),

    # --- optional blocks -----------------------------------------------
    ("quest", None, "[від {1} до {2}#for {1} to {2}||{1}#for {1}]",
     ["optional-no-default"]),
    ("quest", None, "[від {1}#for {1}||решта]", []),
    ("quest", None, "Текст [без умов] далі", []),
    ("quest", None, "Текст [незакрита дужка", ["bracket-unbalanced"]),

    # --- comparative rules ---------------------------------------------
    # identical to English, but nothing to translate: must stay silent
    ("quest", "...", "...", []),
    ("quest", "01001101 01100101", "01001101 01100101", []),
    # identical to English with real words: worth a warning
    ("quest", "Kill the boar.", "Kill the boar.", ["identical-to-english"]),
    # newline runs that faithfully copy the original: must stay silent
    ("quest", "A\n\n\nB", "А\n\n\nБ", []),
    ("quest", "A\nB", "А\n\n\nБ", ["triple-newline"]),
    # no English available: the comparative rules cannot judge, so stay silent
    ("quest", None, "А\n\n\nБ", []),

    # --- misc ----------------------------------------------------------
    # the stray "]" is unbalanced as well, and both findings are worth having
    ("quest", None, "Текст ]===] далі", ["long-bracket", "bracket-unbalanced"]),
]


def main() -> int:
    failures = 0
    for i, (kind, en, uk, expected) in enumerate(CASES, 1):
        got = sorted({f[1] for f in L.lint_string(uk, en, kind)})
        want = sorted(set(expected))
        if got != want:
            failures += 1
            print(f"FAIL case {i} ({kind}): {uk[:48]!r}")
            print(f"     expected {want}")
            print(f"     got      {got}")
    total = len(CASES)
    print(f"\n{total - failures}/{total} cases pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
