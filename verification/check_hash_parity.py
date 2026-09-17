#!/usr/bin/env python3
"""
Compare the three copies of the chat/gossip keying functions.

  wow_scripts/generation/utils/utils.py   builds Crowdin string keys
  ClassicUA/dev/utils.py                  builds the keys stored in entries/
  ClassicUA/scripts/utils.lua             computes the key in game and matches it

A divergence means a chat or gossip line is stored under one key and looked up
under another, so the translation silently never appears. Nothing here is
currently broken; the point is that the three drift apart quietly, so this pins
the behaviour and fails when one of them changes.

  python verification/check_hash_parity.py [--wow-scripts DIR] [--classicua DIR]

With no arguments it uses this repository and CLASSICUA_ROOT from the .env
in the repository root.

Exit code is 1 when a vector diverges from what the file records.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

# run from anywhere, not only with the repository root on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generation.utils.utils import classicua_root  # noqa: E402

# Lua computes the key from the rendered line, so for text carrying a <template>
# it produces a literal where Python produces a Lua pattern. Those go through
# match_text_code instead, below.
VECTORS = [
    "Greetings, hero!",
    "The night elf waits.",
    "I have 50/50 odds.",
    "Ma'am, the boss-lady is out.",
    "A\u00a0line  with   odd   spacing.",
    "Multi\nline\ntext.",
    "Caf\u00e9 na\u00efve r\u00e9sum\u00e9.",
    "UPPER and lower",
    "a",
    "ab",
    "Numbers 1 22 333 4444.",
    "Ends with a single letter x",
    "Number of Necropolises remaining: {1}",
    "Trailing punctuation...",
    "Symbols & ampersands + pluses.",
    "Very long line " + "word " * 40,
]

# Divergences already understood. A vector not listed here that differs is new
# drift and fails the run.
KNOWN = {
    "Café naïve résumé.":
        "Python word classes and character iteration vs Lua %w and byte iteration; affects "
        "both the code and the hash",
    "Number of Necropolises remaining: {1}":
        "expected: Python emits the pattern .- for {n}, Lua reads the rendered "
        "number; the match check below covers it",
    "Very long line " + "word " * 40:
        "expected: Python caps at 42 because utils.lua never matches a longer "
        "candidate, Lua itself does not cap when computing",
}

TEMPLATE_VECTORS = [
    ("<name>, you have disturbed me!", "Thrall, you have disturbed me!"),
    ("This <class> intrudes.", "This warrior intrudes."),
    ("The <race> approaches.", "The orc approaches."),
    ("<his/her> blade is sharp.", "his blade is sharp."),
    ("Greetings, <name>. Your <class> training awaits.",
     "Greetings, Thrall. Your warrior training awaits."),
    ("Number of Necropolises remaining: {1}",
     "Number of Necropolises remaining: 5"),
    ("Um, hello! If you are here about fee collection and/or a summons.",
     "Um, hello! If you are here about fee collection and/or a summons."),
    # a gender template whose variants are one word and two
    ("<Son/Young lady>, I'm not going to lie to you about the bugs.",
     "Son, I'm not going to lie to you about the bugs."),
    ("<Son/Young lady>, I'm not going to lie to you about the bugs.",
     "Young lady, I'm not going to lie to you about the bugs."),
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_lua(classicua: Path, mode: str, lines: list[str]) -> list[str]:
    harness = Path(__file__).with_name("lua_harness.lua")
    payload = "\n".join(lines) + "\n"
    proc = subprocess.run(
        ["lua", str(harness), classicua.as_posix(), mode],
        input=payload, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"lua harness failed:\n{proc.stderr}")
    return proc.stdout.splitlines()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wow-scripts", type=Path, default=ROOT)
    ap.add_argument("--classicua", type=Path, default=classicua_root(),
                    help="ClassicUA checkout (default: CLASSICUA_ROOT from .env)")
    args = ap.parse_args()
    if not args.classicua:
        raise SystemExit("no ClassicUA checkout: set CLASSICUA_ROOT in .env or pass --classicua")

    ws = load(args.wow_scripts / "generation" / "utils" / "utils.py", "ws_utils")
    ua = load(args.classicua / "dev" / "utils.py", "ua_utils")

    escaped = [t.replace("\n", "\\n") for t in VECTORS]
    lua_rows = [row.split("\t") for row in run_lua(args.classicua, "code", escaped)]

    print(f"{'text':<42} {'wow_scripts':<18} {'ClassicUA':<18} {'Lua':<18}")
    print("-" * 100)
    divergences = []
    for text, (lua_code, lua_hash) in zip(VECTORS, lua_rows):
        ws_code = ws.get_text_code(text)[0]
        ua_code = ua.get_text_code(text)[0]
        ws_hash = ws.get_text_hash(text)
        ua_hash = ua.get_text_hash(text)

        label = (text[:39] + "...") if len(text) > 42 else text
        label = label.replace("\n", "\\n")
        differs = (len({ws_code, ua_code, lua_code}) > 1
                   or len({str(ws_hash), str(ua_hash), lua_hash}) > 1)
        if differs:
            tag = "known" if text in KNOWN else "NEW"
            if text not in KNOWN:
                divergences.append(text)
            print(f"{label:<42} {ws_code[:17]:<18} {ua_code[:17]:<18} {lua_code[:17]:<18}  {tag}")
            if len({str(ws_hash), str(ua_hash), lua_hash}) > 1:
                print(f"{'':<42} hash {ws_hash} / {ua_hash} / {lua_hash}")
            if text in KNOWN:
                print(f"{'':<42} {KNOWN[text]}")

    # A pattern built from template text has to match the code the game computes
    # from the rendered line.
    print()
    rendered_codes = run_lua(args.classicua,
                             "code", [r for _, r in TEMPLATE_VECTORS])
    pairs = []
    for (source, _), row in zip(TEMPLATE_VECTORS, rendered_codes):
        pattern = ua.get_text_code(source)[0][:ua.MAX_TEXT_CODE_LENGTH]
        pairs.append(f"{row.split(chr(9))[0]}\t{pattern}")
    results = run_lua(args.classicua, "match", pairs)
    for (source, rendered), pair, hit in zip(TEMPLATE_VECTORS, pairs, results):
        code, pattern = pair.split("\t")
        ok = hit == "true"
        print(f"{'match' if ok else 'NO MATCH':<9} pattern {pattern!r} vs code {code!r}"
              f"   <- {source}")
        if not ok:
            divergences.append(source)

    print(f"\n{len(KNOWN)} known divergence(s), {len(divergences)} new")
    return 1 if divergences else 0


if __name__ == "__main__":
    sys.exit(main())
