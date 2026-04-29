#!/usr/bin/env python3
"""580件すべてのYAMLパース検証 + ID重複/カテゴリ件数チェック"""
import sys
from pathlib import Path
from collections import Counter

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

ROOT = Path("/Users/robby2/robby-the-match/scripts/audit/cases")

EXPECTED_TOTAL = 580
EXPECTED_BY_CATEGORY = {
    "aica_4turn": 60,
    "aica_condition": 55,
    "richmenu_escape": 35,
    "emergency_keyword": 25,
    "apply_intent": 20,
    "edge_case": 5,
    "persona": 70,
    "matching": 60,
    "audio": 30,
    "resume": 40,
    "edge_advanced": 80,
    "regression": 50,
    "contrarian": 50,
}


def main():
    yaml_files = list(ROOT.rglob("*.yaml"))
    print(f"Found {len(yaml_files)} YAML files")

    parse_errors = []
    ids = []
    categories = Counter()
    personas = Counter()
    sources = Counter()

    for fp in yaml_files:
        try:
            data = yaml.safe_load(fp.read_text(encoding="utf-8"))
        except Exception as e:
            parse_errors.append((str(fp), str(e)))
            continue
        if not isinstance(data, dict):
            parse_errors.append((str(fp), "not a dict"))
            continue
        if "id" not in data:
            parse_errors.append((str(fp), "missing id"))
            continue
        ids.append(data["id"])
        categories[data.get("category", "?")] += 1
        personas[data.get("persona", "?")] += 1
        meta = data.get("metadata") or {}
        sources[meta.get("source", "n/a")] += 1

    # IDダブリ
    id_counts = Counter(ids)
    dups = {k: v for k, v in id_counts.items() if v > 1}

    print("=" * 60)
    print("VALIDATION RESULT")
    print("=" * 60)
    print(f"Total files: {len(yaml_files)}")
    print(f"Parsed OK: {len(ids)}")
    print(f"Parse errors: {len(parse_errors)}")
    if parse_errors:
        for fp, err in parse_errors[:10]:
            print(f"  - {fp}: {err}")

    print(f"\nDuplicate IDs: {len(dups)}")
    if dups:
        for did, n in list(dups.items())[:10]:
            print(f"  - {did}: {n}")

    print("\nCategory breakdown:")
    for cat, expected in EXPECTED_BY_CATEGORY.items():
        actual = categories.get(cat, 0)
        mark = "OK" if actual == expected else "MISMATCH"
        print(f"  {cat:20s}: {actual:4d} (expected {expected}) [{mark}]")
    extra = set(categories) - set(EXPECTED_BY_CATEGORY)
    if extra:
        print("  Unexpected categories:")
        for c in extra:
            print(f"    {c}: {categories[c]}")

    print("\nPersona breakdown:")
    for p in sorted(personas):
        print(f"  {p}: {personas[p]}")

    print("\nSource breakdown:")
    for s in sorted(sources):
        print(f"  {s}: {sources[s]}")

    grand_total = sum(categories.values())
    print(f"\nGRAND TOTAL: {grand_total} (target {EXPECTED_TOTAL})")
    ok = (grand_total == EXPECTED_TOTAL and not dups and not parse_errors)
    print(f"FINAL: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
