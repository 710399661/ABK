import time

from gki_fetch import (
    TARGETS,
    make_date_range, get_end_date,
    fetch_date_version, fetch_lts_version, json_path,
    print_branch_prefix, write_json,
)


def fetch_all():
    for (android_ver, kernel_ver), (date_start, date_end, dep_cutoff) in TARGETS.items():
        print(f"\n=== {android_ver} / {kernel_ver} ===")

        end = get_end_date(date_end)
        entries = []
        for date in make_date_range(date_start, end):
            print_branch_prefix(android_ver, kernel_ver, date)
            detail = fetch_date_version(android_ver, kernel_ver, date, dep_cutoff)
            if detail is None:
                continue

            entries.append({"date": date, "kernel": detail})
            print(f"-> {detail}")
            time.sleep(0.2)

        # 抓取 LTS
        print_branch_prefix(android_ver, kernel_ver, "lts")
        lts_value = fetch_lts_version(android_ver, kernel_ver)
        if lts_value is not None:
            print(f"-> {lts_value}")

        if not entries and lts_value is None:
            print(f"  No data for {android_ver}/{kernel_ver}\n")
            continue

        data = {
            "android_version": android_ver,
            "kernel_version": kernel_ver,
            "lts": lts_value,
            "entries": entries,
        }

        out = json_path(android_ver, kernel_ver)
        write_json(out, data)

        print(f"  => Saved {len(entries)} entries to {out}\n")

    print("Done.")


if __name__ == "__main__":
    fetch_all()
