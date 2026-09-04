#!/usr/bin/env python3
"""Gate for edits to the rust-ffmpeg SKILL.md frontmatter `description`.

Checks two things:
  1. Length against the Agent Skills spec cap (1024 chars). Claude Code also
     truncates each listing entry at 1536 chars, so anything past 1024 is
     both non-compliant and at risk of never reaching the model.
  2. Every row of claudedocs/skill-trigger-regression-corpus.md: at least one
     anchor token must appear (case-insensitive substring) in the description,
     unless the row is SEMANTIC or ACCEPTED-MISS.

Usage:
  python3 claudedocs/check_trigger_corpus.py            # checks SKILL.md
  python3 claudedocs/check_trigger_corpus.py --text f   # checks a candidate
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugin/skills/rust-ffmpeg/SKILL.md"
CORPUS = ROOT / "claudedocs/skill-trigger-regression-corpus.md"
SPEC_CAP = 1024
CLAUDE_CODE_CAP = 1536


def read_description(path: Path) -> str:
    text = path.read_text()
    m = re.search(r'^description:\s*"(.*)"\s*$', text, re.M)
    if not m:
        sys.exit(f"no single-line quoted description found in {path}")
    return m.group(1)


def whole_token(token: str, haystack: str) -> bool:
    # `vs` must not match inside `AVSEEK_SIZE`; identifiers must not match a prefix.
    pattern = r"(?<![a-z0-9_])" + re.escape(token.lower()) + r"(?![a-z0-9_])"
    return re.search(pattern, haystack) is not None


def corpus_rows(path: Path):
    for line in path.read_text().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|(.*?)\|(.*?)\|(.*?)\|\s*$", line)
        if not m:
            continue
        num, query, anchors, cls = (s.strip() for s in m.groups())
        yield int(num), query, anchors, cls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", type=Path, help="file holding a candidate description")
    args = ap.parse_args()

    desc = args.text.read_text().strip() if args.text else read_description(SKILL)
    n = len(desc)
    print(f"description: {n} chars, {len(desc.split())} words, ~{n // 4} tokens")
    failed = False
    if n > SPEC_CAP:
        print(f"FAIL length: {n} > {SPEC_CAP} (Agent Skills spec cap)")
        failed = True
    if n > CLAUDE_CODE_CAP:
        print(f"FAIL visibility: {n - CLAUDE_CODE_CAP} chars past the {CLAUDE_CODE_CAP} listing cap are invisible to Claude")
        failed = True

    # Anchors only count if they land inside the window Claude actually sees.
    low = desc[:CLAUDE_CODE_CAP].lower()
    counts = {"PASS": 0, "SEMANTIC": 0, "ACCEPTED-MISS": 0, "FAIL": 0}
    for num, query, anchors, _cls in corpus_rows(CORPUS):
        if anchors.startswith("SEMANTIC"):
            verdict = "SEMANTIC"
        elif anchors.startswith("ACCEPTED-MISS"):
            verdict = "ACCEPTED-MISS"
        else:
            tokens = re.findall(r"`([^`]+)`", anchors)
            hit = [t for t in tokens if whole_token(t, low)]
            verdict = "PASS" if hit else "FAIL"
            if not hit:
                print(f"FAIL row {num}: {query!r} needs one of {tokens}")
        counts[verdict] += 1
    print("corpus:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    failed = failed or counts["FAIL"] > 0
    print("RESULT:", "FAIL" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
