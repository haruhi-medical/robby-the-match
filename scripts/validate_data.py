#!/usr/bin/env python3
"""
データベース検証スクリプト
areas.js / jobs.js のデータ品質を自動チェック
"""

import subprocess
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent


def load_js_data(filepath: Path, var_name: str):
    """Node.jsでJSファイルを読み込んでJSONとして返す"""
    script = f"""
    const data = require('{filepath.resolve()}');
    console.log(JSON.stringify(data));
    """
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True, text=True, cwd=str(project_root)
    )
    if result.returncode != 0:
        print(f"Error loading {filepath.name}: {result.stderr}")
        return None
    return json.loads(result.stdout)


def validate_areas(data):
    """areas.jsの検証"""
    errors = []
    warnings = []
    areas = data.get("AREA_DATABASE", [])

    facility_names = []
    total = 0

    for area in areas:
        area_name = area.get("name", "UNKNOWN")
        facilities = area.get("majorFacilities", [])

        if not facilities:
            warnings.append(f"[{area_name}] 施設が0件")

        for f in facilities:
            total += 1
            name = f.get("name", "NO_NAME")
            facility_names.append(name)

            # 必須フィールドチェック
            required = ["name", "type", "access", "features"]
            for field in required:
                if not f.get(field):
                    errors.append(f"[{area_name}/{name}] 必須フィールド '{field}' が未設定")

            # 給与レンジ整合性
            min_sal = f.get("nurseMonthlyMin")
            max_sal = f.get("nurseMonthlyMax")
            if min_sal is not None and max_sal is not None:
                if min_sal > max_sal:
                    errors.append(f"[{area_name}/{name}] 給与レンジ不正: min={min_sal} > max={max_sal}")
                if min_sal < 150000 or max_sal > 600000:
                    warnings.append(f"[{area_name}/{name}] 給与レンジが通常範囲外: {min_sal}〜{max_sal}")

            # 看護師数 vs 病床数の比率チェック（病院のみ）
            beds = f.get("beds")
            nurses = f.get("nurseCount")
            if beds and nurses and beds > 0:
                ratio = nurses / beds
                if ratio < 0.2:
                    warnings.append(f"[{area_name}/{name}] 看護師/病床比率が低い: {ratio:.2f} ({nurses}名/{beds}床)")
                if ratio > 2.0:
                    warnings.append(f"[{area_name}/{name}] 看護師/病床比率が異常に高い: {ratio:.2f}")

            # matchingTags確認
            tags = f.get("matchingTags", [])
            if not tags:
                warnings.append(f"[{area_name}/{name}] matchingTagsが未設定")

    # 重複チェック
    seen = set()
    for name in facility_names:
        if name in seen:
            errors.append(f"施設名重複: {name}")
        seen.add(name)

    return total, errors, warnings


def validate_jobs(data):
    """jobs.jsの検証"""
    errors = []
    warnings = []

    jdb = data.get("JOB_DATABASE", {})
    external = jdb.get("externalJobs", {})

    if not external:
        # externalJobsがJOB_DATABASEの外にある場合
        external = data.get("externalJobs", jdb)

    nurse_jobs = external.get("nurse", [])
    pt_jobs = external.get("pt", [])

    total = len(nurse_jobs) + len(pt_jobs)

    for job in nurse_jobs + pt_jobs:
        facility = job.get("facility", "UNKNOWN")

        # 必須フィールド
        required = ["facility", "area", "type", "salary", "shift"]
        for field in required:
            if not job.get(field):
                errors.append(f"[求人/{facility}] 必須フィールド '{field}' が未設定")

        # lastUpdated確認（新フィールド）
        if not job.get("lastUpdated"):
            warnings.append(f"[求人/{facility}] lastUpdated未設定")

    return len(nurse_jobs), len(pt_jobs), errors, warnings


def main():
    print("=" * 60)
    print("ROBBY THE MATCH データベース検証")
    print("=" * 60)

    all_errors = []
    all_warnings = []

    # areas.js検証
    print("\n--- areas.js ---")
    areas_data = load_js_data(project_root / "data" / "areas.js", "AREA_DATABASE")
    if areas_data:
        total, errors, warnings = validate_areas(areas_data)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        print(f"  施設数: {total}")
        print(f"  エラー: {len(errors)}")
        print(f"  警告: {len(warnings)}")
    else:
        all_errors.append("areas.jsの読み込みに失敗")

    # jobs.js検証
    print("\n--- jobs.js ---")
    jobs_data = load_js_data(project_root / "data" / "jobs.js", "JOB_DATABASE")
    if jobs_data:
        nurse_count, pt_count, errors, warnings = validate_jobs(jobs_data)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        print(f"  看護師求人: {nurse_count}件")
        print(f"  PT求人: {pt_count}件")
        print(f"  エラー: {len(errors)}")
        print(f"  警告: {len(warnings)}")
    else:
        all_errors.append("jobs.jsの読み込みに失敗")

    # 結果サマリ
    print("\n" + "=" * 60)
    if all_errors:
        print(f"\nERRORS ({len(all_errors)}):")
        for e in all_errors:
            print(f"  {e}")

    if all_warnings:
        print(f"\nWARNINGS ({len(all_warnings)}):")
        for w in all_warnings[:20]:  # 最大20件表示
            print(f"  {w}")
        if len(all_warnings) > 20:
            print(f"  ... 他 {len(all_warnings) - 20}件")

    if not all_errors:
        print("\n ALL CHECKS PASSED")
        return 0
    else:
        print(f"\n FAILED: {len(all_errors)} errors found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
