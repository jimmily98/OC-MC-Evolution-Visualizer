from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterator

from pypdf import PdfReader

from .mc import MCTables, clean_notation_text, load_mc_tables, split_mc_form


_ENTRY_START_RE = re.compile(
    r"(?<!\d)(?P<entry_id>\d{4}[a-z-]?)(?P<char>[\u3400-\u9fff\U00020000-\U0002EBEF])"
)
_MC_TOKEN_RE = re.compile(r"(?P<mc>[A-Za-z'][A-Za-z'()+\-\.\+]*[XH]?)$")
_OC_TOKEN_RE = re.compile(r"\*(?P<oc>\S+)")
_SOURCE_REF_RE = re.compile(r"(?P<source>\d+\.\d+U\+[0-9A-F]+)\s*$")
_STRIP_OC_CHARS = str.maketrans("", "", "[]()‹›><*")


@dataclass(frozen=True)
class BSRecord:
    entry_id: str
    character: str
    modern_reading: str
    mc_form: str
    mc_onset: str
    mc_onset_group: str | None
    mc_rhyme: str
    mc_rhyme_group: str | None
    mc_annotation: str
    oc_form_raw: str
    oc_form_clean: str
    gloss: str
    source_ref: str | None
    pdf_page: int
    raw_text: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def clean_oc_notation(text: str) -> str:
    text = text.translate(_STRIP_OC_CHARS)
    text = re.sub(r"[əә]{2,}", "ə", text)
    return re.sub(r"\s+", "", text)


def _normalize_oc_raw(text: str) -> str:
    return re.sub(r"[əә]{2,}", "ə", text)


def _decorate_rhyme_group(rhyme: str, group: str | None, tables: MCTables) -> str | None:
    if group is None:
        return None
    division = tables.rhyme_division_map.get(clean_notation_text(rhyme).lstrip("-."))
    return f"{group} ({division})" if division else group


def _normalize_mc_annotation(mc_annotation: str) -> str:
    normalized = re.sub(r"[\s+]+", "", mc_annotation)
    normalized = normalized.replace("-", "")
    normalized = re.sub(r"[ABCD]$", "", normalized)
    return normalized


def _extract_pdf_pages(pdf_path: str | Path) -> Iterator[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    for page_index, page in enumerate(reader.pages, start=1):
        yield page_index, page.extract_text() or ""


def _iter_entry_slices(page_text: str) -> Iterator[tuple[int, int]]:
    matches = list(_ENTRY_START_RE.finditer(page_text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page_text)
        yield match.start(), end


def _find_token_before_group(text: str, end_index: int) -> tuple[str, str]:
    prefix = text[:end_index].rstrip()
    match = _MC_TOKEN_RE.search(prefix)
    if match is None:
        raise ValueError(f"Could not locate an MC token in: {text!r}")
    mc_form = match.group("mc")
    modern_reading = prefix[: match.start()].strip()
    return modern_reading, mc_form


def _parse_entry(entry_text: str, pdf_page: int, tables: MCTables) -> BSRecord:
    start_match = _ENTRY_START_RE.search(entry_text)
    if start_match is None:
        raise ValueError(f"Not a source entry: {entry_text!r}")

    entry_id = start_match.group("entry_id")
    character = start_match.group("char")
    remainder = entry_text[start_match.end() :].strip()

    group_start = remainder.find("(")
    if group_start < 0:
        raise ValueError(f"Missing MC annotation for entry {entry_id}: {entry_text!r}")

    modern_reading, mc_form = _find_token_before_group(remainder, group_start)
    group_end = remainder.find(")", group_start)
    if group_end < 0:
        raise ValueError(f"Missing closing parenthesis for entry {entry_id}: {entry_text!r}")

    mc_annotation = remainder[group_start + 1 : group_end].strip()
    after_group = remainder[group_end + 1 :].strip()

    mc_form = _normalize_mc_annotation(mc_annotation)
    if not mc_form:
        raise ValueError(f"Could not normalize MC annotation for entry {entry_id}: {entry_text!r}")

    modern_match = remainder[:group_start].rfind(mc_form)
    if modern_match < 0:
        raise ValueError(f"Could not align modern reading with MC form {mc_form!r} in: {entry_text!r}")

    modern_reading = remainder[:modern_match].strip()

    oc_match = _OC_TOKEN_RE.search(after_group)
    if oc_match is None:
        raise ValueError(f"Missing OC form for entry {entry_id}: {entry_text!r}")

    oc_form_raw = _normalize_oc_raw("*" + oc_match.group("oc"))
    after_oc = after_group[oc_match.end() :].strip()

    source_match = _SOURCE_REF_RE.search(after_oc)
    source_ref = source_match.group("source") if source_match else None
    gloss = after_oc[: source_match.start()].strip() if source_match else after_oc

    mc_onset, mc_rhyme, mc_group = split_mc_form(mc_form, tables)
    mc_onset_group = tables.onset_map.get(mc_onset)
    mc_rhyme_group = _decorate_rhyme_group(mc_rhyme, mc_group, tables)
    oc_form_clean = clean_oc_notation(oc_form_raw)

    return BSRecord(
        entry_id=entry_id,
        character=character,
        modern_reading=modern_reading,
        mc_form=mc_form,
        mc_onset=mc_onset,
        mc_onset_group=mc_onset_group,
        mc_rhyme=mc_rhyme,
        mc_rhyme_group=mc_rhyme_group,
        mc_annotation=mc_annotation,
        oc_form_raw=oc_form_raw,
        oc_form_clean=oc_form_clean,
        gloss=gloss,
        source_ref=source_ref,
        pdf_page=pdf_page,
        raw_text=entry_text.strip(),
    )


def iter_baxter_sagart_records(pdf_path: str | Path, tables: MCTables | None = None) -> Iterator[BSRecord]:
    if tables is None:
        root = Path(__file__).resolve().parents[1]
        tables = load_mc_tables(root / "data" / "MC_onsets_rhymes.md")

    for pdf_page, page_text in _extract_pdf_pages(pdf_path):
        for start, end in _iter_entry_slices(page_text):
            entry_text = page_text[start:end].strip()
            if not entry_text:
                continue
            try:
                yield _parse_entry(entry_text, pdf_page, tables)
            except Exception as e:  # skip malformed entries but continue
                from sys import stderr

                print(f"warning: skipping entry at page {pdf_page} start={start}: {e}", file=stderr)
                continue


def load_baxter_sagart_records(pdf_path: str | Path, tables: MCTables | None = None) -> list[BSRecord]:
    return list(iter_baxter_sagart_records(pdf_path, tables))
