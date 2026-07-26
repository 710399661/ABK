"""增量更新 GKI 内核版本数据。

读取现有 JSON 数据，仅抓取缺失的月份，同时更新 LTS 版本。
"""

import time

from gki_fetch import (
    TARGETS,
    make_date_range, get_end_date,
    fetch_date_version, json_path,
    print_branch_prefix, read_json, refresh_lts, write_json,
)


def update_target(android_ver: str, kernel_ver: str,
                  date_start: str, date_end: str | None,
                  dep_cutoff: str) -> bool:
    """增量更新单个目标，返回是否有数据变更"""
    path = json_path(android_ver, kernel_ver)
    end = get_end_date(date_end)
    changed = False

    # 读取现有数据
    data = read_json(path) or {
        "android_version": android_ver,
        "kernel_version": kernel_ver,
        "lts": None,
        "entries": [],
    }
    entries = data.get("entries", [])

    # 确定需要抓取的日期范围
    # 从 date_start 开始扫描，过滤掉已有日期，可自动填补之前遗漏的月份
    existing_dates = {e["date"] for e in entries}
    all_dates = make_date_range(date_start, end)
    new_dates = [d for d in all_dates if d not in existing_dates]

    if not new_dates:
        print(f"  No new months to fetch")
    else:
        print(f"  Fetching {len(new_dates)} new month(s): {new_dates[0]} ~ {new_dates[-1]}")
        for date in new_dates:
            print_branch_prefix(android_ver, kernel_ver, date, indent="    ")
            detail = fetch_date_version(android_ver, kernel_ver, date, dep_cutoff)
            if detail is None:
                continue

            entries.append({"date": date, "kernel": detail})
            changed = True
            print(f"-> {detail}")
            time.sleep(0.3)

    # 按日期排序
    entries.sort(key=lambda e: e["date"])

    # 更新 LTS
    if refresh_lts(data, android_ver, kernel_ver):
        changed = True

    # 保存
    data["entries"] = entries
    if changed:
        write_json(path, data)
        print(f"  => Saved {len(entries)} entries to {path}")
    else:
        print(f"  => No changes")

    return changed


def main():
    any_changed = False
    for (android_ver, kernel_ver), (date_start, date_end, dep_cutoff) in TARGETS.items():
        print(f"\n=== {android_ver} / {kernel_ver} ===")
        if update_target(android_ver, kernel_ver, date_start, date_end, dep_cutoff):
            any_changed = True

    print(f"\n{'Data updated.' if any_changed else 'All data up-to-date.'}")
    return any_changed


if __name__ == "__main__":
    import sys
    try:
        changed = main()
    except Exception as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        sys.exit(1)
    # Exit 0 = data changed, 2 = no changes (both are success)
    sys.exit(0 if changed else 2)
