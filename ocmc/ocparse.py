from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Tuple


VOWELS = set("ieəauoA")


def _first_vowel_index(s: str) -> int:
    for i, ch in enumerate(s):
        if ch in VOWELS:
            return i
    return -1


def _parse_core_syllable(segment: str) -> Tuple[str | None, str | None]:
    """Parse a single syllable segment without minor-syllable separators."""
    if not segment:
        return None, None

    vpos = _first_vowel_index(segment)
    if vpos < 0:
        return None, None

    pre = segment[:vpos]
    vowel = segment[vpos]
    rest = segment[vpos + 1 :]

    # Omit postcoda markers from the rhyme extraction.
    if rest.endswith("ʔ"):
        rest = rest[:-1]

    medial = ""
    initial = pre
    if pre == "r":
        initial = pre
    elif pre.endswith("r"):
        initial = pre[:-1]
        medial = "r"

    rest_lower = rest.casefold()
    coda_match = re.match(r"^[mnŋrjwptk]+", rest_lower)
    if coda_match:
        clen = len(coda_match.group(0))
        coda = rest[:clen]
    else:
        coda = ""

    oc_onset = initial if initial else None
    rhyme = (medial + vowel + coda) if vowel else None
    return oc_onset, rhyme


def parse_oc_form(oc: str) -> Tuple[str | None, str | None]:
    """Parse a cleaned OC form into (oc_onset, oc_rhyme).

    Heuristic parser following project spec. Returns (None, None) when parsing fails.
    """
    if not oc:
        return None, None
    s = str(oc).strip()
    # Remove trailing morphological suffix -s if present (authors treat as suffix)
    if s.endswith("-s"):
        s = s[: -2]
    sep = ""
    prefix = None
    full = s
    if "." in s:
        prefix, full = s.split(".", 1)
        sep = "."
    elif "-" in s:
        prefix, full = s.split("-", 1)
        sep = "-"

    tail_onset, tail_rhyme = _parse_core_syllable(full)
    if tail_onset is None and tail_rhyme is None:
        return None, None

    if prefix:
        oc_onset = f"{prefix}{sep}{tail_onset}" if tail_onset else prefix
    else:
        oc_onset = tail_onset

    return oc_onset, tail_rhyme


def add_oc_categories(in_path: Path, out_path: Path) -> int:
    in_path = Path(in_path)
    out_path = Path(out_path)
    out_lines = []
    count = 0
    with in_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            oc = record.get("oc_form_clean")
            oc_onset, oc_rhyme = parse_oc_form(oc)
            # insert oc_onset and oc_rhyme immediately after oc_form_clean
            new_record = {}
            inserted = False
            for k, v in record.items():
                new_record[k] = v
                if k == "oc_form_clean":
                    new_record["oc_onset"] = oc_onset
                    new_record["oc_rhyme"] = oc_rhyme
                    inserted = True
            # if oc_form_clean wasn't present for some reason, append at end
            if not inserted:
                new_record["oc_onset"] = oc_onset
                new_record["oc_rhyme"] = oc_rhyme
            out_lines.append(json.dumps(new_record, ensure_ascii=False))
            count += 1

    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    args = parser.parse_args()
    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    n = add_oc_categories(in_path, out_path)
    print(f"wrote {out_path} ({n} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
