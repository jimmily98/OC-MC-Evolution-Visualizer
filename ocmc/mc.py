from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


_STRIP_CHARS = str.maketrans("", "", "[]()‹›><")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]+")
_TOKEN_RE = re.compile(r"[A-Za-z'()+\-]+")
_BOLD_PAIR_RE = re.compile(r"\*\*([^*]+)\*\*\s*([^,|]+)")
_CHONGNIU_DIVISION_MAP: dict[str, str] = {
    "je": "III",
    "jwe": "III",
    "jie": "IV",
    "jwie": "IV",
    "ij": "III",
    "wij": "III",
    "jij": "IV",
    "jwij": "IV",
    "jew": "III",
    "jiew": "IV",
    "in": "III",
    "win": "III",
    "jin": "IV",
    "jwin": "IV",
    "jen": "III",
    "jwen": "III",
    "jien": "IV",
    "jwien": "IV",
    "im": "III",
    "jim": "IV",
    "jem": "III",
    "jiem": "IV",
    "jej": "III",
    "jwej": "III",
    "jiej": "IV",
    "jwiej": "IV",
    "it": "III",
    "jit": "IV",
    "wit": "III",
    "wiet": "III",
    "iet": "III",
    "jwit": "IV",
    "jwiet": "IV",
    "jet": "III",
    "jiet": "IV",
    "ip": "III",
    "jip": "IV",
    "jep": "III",
    "jiep": "IV",
}

_CHONGNIU_RHYME_OVERRIDES: dict[str, str] = {
    "iet": "薛",
    "wiet": "薛",
    "jiet": "薛",
    "jwiet": "薛",
    "jwej": "祭",
    "jwiej": "祭",
}


@dataclass(frozen=True)
class MCTables:
    onset_map: dict[str, str]
    rhyme_map: dict[str, str]
    rhyme_division_map: dict[str, str]
    surface_map: dict[str, str]


def clean_notation_text(text: str) -> str:
    text = text.translate(_STRIP_CHARS)
    return re.sub(r"\s+", "", text)


def _read_section(source_text: str, start_marker: str, end_marker: str | None) -> str:
    start = source_text.index(start_marker)
    if end_marker is None:
        return source_text[start:]
    try:
        end = source_text.index(end_marker, start)
    except ValueError:
        end = len(source_text)
    return source_text[start:end]


def _table_rows(section_text: str) -> list[str]:
    rows: list[str] = []
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if set(line) <= {"|", "-", " ", ":"}:
            continue
        rows.append(line)
    return rows


def _first_chinese_token(text: str) -> str | None:
    match = _CHINESE_RE.search(text)
    return match.group(0) if match else None


def _token_after_chinese(text: str, chinese: str) -> str | None:
    idx = text.find(chinese)
    if idx < 0:
        return None
    tail = text[idx + len(chinese) :]
    match = _TOKEN_RE.search(tail)
    return match.group(0) if match else None


def _normalize_onset_token(token: str) -> str:
    token = clean_notation_text(token)
    return token.rstrip("-")


def _strip_known_onset(token: str, onset_map: dict[str, str]) -> tuple[str, str]:
    cleaned = clean_notation_text(token)
    for candidate in sorted(onset_map, key=len, reverse=True):
        if cleaned.startswith(candidate):
            return candidate, cleaned[len(candidate) :]
    return "", cleaned


def _split_final_labels(text: str) -> list[str]:
    labels: list[str] = []
    for raw_label in text.replace("…", "").replace("...", "").split(","):
        label = clean_notation_text(raw_label).strip(".")
        if label:
            labels.append(label)
    return labels


def _normalize_rhyme_key(text: str) -> str:
    cleaned = clean_notation_text(text).lstrip("-.")
    return cleaned.removesuffix("X").removesuffix("H")


def _parse_rhyme_variant_block(text: str) -> list[tuple[str, str | None]]:
    variants: list[tuple[str, str | None]] = []
    for token, division in re.findall(r"`([^`]+)`\s*(?:\((III|IV)\))?", text):
        variants.append((token, division))
    return variants


def _parse_onset_section(section_text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _table_rows(section_text):
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        for cell in cells[1:]:
            for token, group in re.findall(r"\*\*([^*]+)\*\*\s*([^,|]+)", cell):
                normalized = _normalize_onset_token(token)
                if not normalized:
                    continue
                group = group.strip()
                existing = mapping.get(normalized)
                if existing is not None and existing != group:
                    raise ValueError(
                        f"Conflicting onset mapping for {normalized!r}: {existing!r} vs {group!r}"
                    )
                mapping[normalized] = group
    return mapping


def _add_rhyme_mapping(mapping: dict[str, str], token: str, group: str) -> None:
    normalized = _normalize_rhyme_key(token)
    if not normalized:
        return
    existing = mapping.get(normalized)
    if existing is not None and existing != group:
        mapping.pop(normalized, None)
        return
    mapping[normalized] = group


def _parse_rhyme_rows(
    section_text: str, tone_cell_count: int, has_entering_cell: bool, onset_map: dict[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
    mapping: dict[str, str] = {}
    surface_map: dict[str, str] = {}
    for row in _table_rows(section_text):
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < tone_cell_count + 1:
            continue

        label_cell = cells[0]
        canonical = None
        canonical_cell_index = None
        for index, cell in enumerate(cells[1 : 1 + tone_cell_count], start=1):
            chinese = _first_chinese_token(cell)
            if chinese:
                canonical = chinese
                canonical_cell_index = index
                break
        if canonical is None:
            continue

        for label_block in re.findall(r"\*\*([^*]+)\*\*", label_cell):
            for label in _split_final_labels(label_block):
                _add_rhyme_mapping(mapping, label, canonical)

        for index, cell in enumerate(cells[1 : 1 + tone_cell_count], start=1):
            bold_labels = re.findall(r"\*\*([^*]+)\*\*", cell)
            if bold_labels:
                for label_block in bold_labels:
                    for label in _split_final_labels(label_block):
                        _add_rhyme_mapping(mapping, label, canonical)
                chinese = _first_chinese_token(cell)
                if chinese:
                    token = _token_after_chinese(cell, chinese)
                    if token:
                        surface_map[clean_notation_text(token)] = canonical
            elif index == canonical_cell_index:
                chinese = _first_chinese_token(cell)
                if chinese:
                    token = _token_after_chinese(cell, chinese)
                    if token:
                        surface_map[clean_notation_text(token)] = canonical

        if has_entering_cell and len(cells) > tone_cell_count + 1:
            entering_cell = cells[1 + tone_cell_count]
            entering_group = _first_chinese_token(entering_cell)
            if entering_group:
                bold_labels = re.findall(r"\*\*([^*]+)\*\*", entering_cell)
                for label_block in bold_labels:
                    for label in _split_final_labels(label_block):
                        _add_rhyme_mapping(mapping, label, entering_group)
                token = _token_after_chinese(entering_cell, entering_group)
                if token:
                    surface_map[clean_notation_text(token)] = entering_group
    return mapping, surface_map


def _parse_special_rhyme_table(section_text: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    rhyme_map: dict[str, str] = {}
    surface_map: dict[str, str] = {}
    division_map: dict[str, str] = {}
    for row in _table_rows(section_text):
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label_cell, variant_cell = cells[0], cells[1]
        canonical = _first_chinese_token(label_cell)
        if canonical is None:
            continue
        for token, division in _parse_rhyme_variant_block(variant_cell):
            _add_rhyme_mapping(rhyme_map, token, canonical)
            normalized = _normalize_rhyme_key(token)
            if division:
                division_map[normalized] = division
            surface_map[normalized] = canonical
    return rhyme_map, surface_map, division_map


def _parse_rhyme_notation_mapping(section_text: str) -> tuple[dict[str, str], dict[str, str]]:
    rhyme_map: dict[str, str] = {}
    division_map: dict[str, str] = {}
    for row in _table_rows(section_text):
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 3:
            continue
        notation, rhyme_group, division = cells[:3]
        if not notation or notation.lower() == "notation":
            continue
        normalized = _normalize_rhyme_key(notation)
        if not normalized:
            continue
        if rhyme_group:
            rhyme_map[normalized] = rhyme_group
        if division and division != "(none)":
            division_map[normalized] = division
    return rhyme_map, division_map


def load_mc_tables(md_path: str | Path) -> MCTables:
    source_path = Path(md_path)
    source_text = source_path.read_text(encoding="utf-8")
    mapping_path = source_path.with_name("rhyme_notation_mapping.md")
    mapping_text = mapping_path.read_text(encoding="utf-8") if mapping_path.exists() else ""

    onset_section = _read_section(source_text, "Table 2.3", "Table 2.5")
    table_25 = _read_section(source_text, "Table 2.5", "Table 2.6")
    table_26 = _read_section(source_text, "Table 2.6", "Table 2.7")
    table_27 = _read_section(source_text, "Table 2.7", "Table 2.8")
    table_28 = _read_section(source_text, "Table 2.8", "Table 2.9")
    table_29 = _read_section(source_text, "Table 2.9", None)
    table_special = _read_section(source_text, "Table 祭泰夬廢", "Eight chongniu rhymes")

    onset_map = _parse_onset_section(onset_section)
    rhyme_map: dict[str, str] = {}
    rhyme_division_map: dict[str, str] = {}
    surface_map: dict[str, str] = {}
    parsed_rhymes, parsed_surfaces = _parse_rhyme_rows(
        table_25, tone_cell_count=3, has_entering_cell=True, onset_map=onset_map
    )
    rhyme_map.update(parsed_rhymes)
    surface_map.update(parsed_surfaces)
    parsed_rhymes, parsed_surfaces = _parse_rhyme_rows(
        table_26, tone_cell_count=1, has_entering_cell=True, onset_map=onset_map
    )
    rhyme_map.update(parsed_rhymes)
    surface_map.update(parsed_surfaces)
    parsed_rhymes, parsed_surfaces = _parse_rhyme_rows(
        table_27, tone_cell_count=1, has_entering_cell=True, onset_map=onset_map
    )
    rhyme_map.update(parsed_rhymes)
    surface_map.update(parsed_surfaces)
    parsed_rhymes, parsed_surfaces = _parse_rhyme_rows(
        table_28, tone_cell_count=3, has_entering_cell=False, onset_map=onset_map
    )
    rhyme_map.update(parsed_rhymes)
    surface_map.update(parsed_surfaces)
    parsed_rhymes, parsed_surfaces = _parse_rhyme_rows(
        table_29, tone_cell_count=3, has_entering_cell=True, onset_map=onset_map
    )
    rhyme_map.update(parsed_rhymes)
    surface_map.update(parsed_surfaces)
    parsed_rhymes, parsed_surfaces, parsed_divisions = _parse_special_rhyme_table(table_special)
    rhyme_map.update(parsed_rhymes)
    surface_map.update(parsed_surfaces)
    rhyme_division_map.update(parsed_divisions)
    if mapping_text:
        mapped_rhymes, mapped_divisions = _parse_rhyme_notation_mapping(mapping_text)
        rhyme_map.update(mapped_rhymes)
        rhyme_division_map.update(mapped_divisions)
    rhyme_division_map.update(_CHONGNIU_DIVISION_MAP)
    rhyme_map.update(_CHONGNIU_RHYME_OVERRIDES)
    return MCTables(
        onset_map=onset_map,
        rhyme_map=rhyme_map,
        rhyme_division_map=rhyme_division_map,
        surface_map=surface_map,
    )


def split_mc_form(form: str, tables: MCTables) -> tuple[str, str, str | None]:
    cleaned = clean_notation_text(form)
    if not cleaned:
        return "", "", None

    onset = ""
    for candidate in sorted(tables.onset_map, key=len, reverse=True):
        if cleaned.startswith(candidate):
            onset = candidate
            break

    rhyme = cleaned[len(onset) :]
    group = tables.surface_map.get(cleaned)
    if group is None:
        group = tables.rhyme_map.get(_normalize_rhyme_key(rhyme))
    normalized_rhyme = rhyme if rhyme.startswith(("-", ".")) else f"-{rhyme}"
    return onset, normalized_rhyme, group
