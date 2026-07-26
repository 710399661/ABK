from gki_fetch import TARGETS, json_path, read_json, refresh_lts, write_json


def update_lts():
    for (android_ver, kernel_ver) in TARGETS:
        path = json_path(android_ver, kernel_ver)
        print(f"\n=== {android_ver} / {kernel_ver} ===")

        data = read_json(path)
        if data is None:
            print(f"  JSON not found: {path}, skip")
            continue

        if refresh_lts(data, android_ver, kernel_ver):
            write_json(path, data)

    print("\nDone.")


if __name__ == "__main__":
    update_lts()
