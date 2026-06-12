from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .ingest import iter_baxter_sagart_records
from .linkage import load_ndjson_records, write_linkage_summary
from .mc import load_mc_tables, split_mc_form


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=root / "data" / "Baxter-Sagart Old Chinese reconstruction, version 1.1 (20 September 2014).pdf")
    parser.add_argument("--records", type=Path, default=root / "data" / "baxter_sagart_records.oc_parsed.ndjson")
    parser.add_argument("--linkage-json", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    md_path = root / "data" / "MC_onsets_rhymes.md"
    tables = load_mc_tables(md_path)
    print(f"onsets: {len(tables.onset_map)}")
    print(f"rhymes: {len(tables.rhyme_map)}")
    for sample in ["gjenX", "tshjeng", "xj+n", "'uwk"]:
        onset, rhyme, group = split_mc_form(sample, tables)
        print(f"{sample} -> onset={onset} rhyme={rhyme} group={group}")

    if args.linkage_json:
        records = load_ndjson_records(args.records)
        summary = write_linkage_summary(records, args.linkage_json)
        print(f"linkage_json: {args.linkage_json}")
        print(f"records: {summary['record_count']}")
        for linkage in summary["linkages"]:
            print(f"{linkage['source_field']} -> {linkage['target_field']}: {len(linkage['links'])} links")
        return 0

    for index, record in enumerate(iter_baxter_sagart_records(args.pdf, tables), start=1):
        if args.json:
            print(json.dumps(record.to_dict(), ensure_ascii=False))
        else:
            print(
                f"{index:04d} {record.entry_id} {record.character} mc={record.mc_form} "
                f"oc={record.oc_form_clean} rhyme_group={record.mc_rhyme_group} gloss={record.gloss}"
            )
        if index >= args.limit:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())