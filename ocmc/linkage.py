from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from typing import Any, Iterable


def _get_field(record: Any, field: str) -> str | None:
    if isinstance(record, dict):
        value = record.get(field)
    else:
        value = getattr(record, field, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_ndjson_records(ndjson_path: str | Path) -> list[dict[str, object]]:
    path = Path(ndjson_path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _count_links(
    records: Iterable[Any], source_field: str, target_field: str
) -> list[dict[str, object]]:
    counts: Counter[tuple[str, str]] = Counter()
    for record in records:
        source = _get_field(record, source_field)
        target = _get_field(record, target_field)
        if source is None or target is None:
            continue
        counts[(source, target)] += 1

    return [
        {"source": source, "target": target, "count": count}
        for (source, target), count in sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    ]


def _count_sources(records: Iterable[Any], source_field: str) -> list[dict[str, object]]:
    counts: Counter[str] = Counter()
    for record in records:
        source = _get_field(record, source_field)
        if source is None:
            continue
        counts[source] += 1

    return [
        {"source": source, "count": count}
        for source, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _build_linkage_spec(records: list[Any], source_field: str, target_field: str) -> dict[str, object]:
    return {
        "source_field": source_field,
        "target_field": target_field,
        "links": _count_links(records, source_field, target_field),
        "source_totals": _count_sources(records, source_field),
    }


def build_linkage_summary(
    records: Iterable[Any],
    linkage_specs: tuple[tuple[str, str], ...] = (
        ("oc_onset", "mc_onset_group"),
        ("oc_rhyme", "mc_rhyme_group"),
    ),
) -> dict[str, object]:
    records = list(records)
    linkages = [_build_linkage_spec(records, source_field, target_field) for source_field, target_field in linkage_specs]

    return {
        "record_count": len(records),
        "linkages": linkages,
    }


def write_linkage_summary(
    records: Iterable[Any],
    output_path: str | Path,
    linkage_specs: tuple[tuple[str, str], ...] = (
        ("oc_onset", "mc_onset_group"),
        ("oc_rhyme", "mc_rhyme_group"),
    ),
) -> dict[str, object]:
    summary = build_linkage_summary(records, linkage_specs=linkage_specs)
    Path(output_path).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary