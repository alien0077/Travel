#!/usr/bin/env python3
"""
從 NAS 下載所有行程的 GPS 資料到本地快取。
之後 enrich_gps.py 可以直接讀取快取，不需要連線 NAS。

用法：
  python3 scripts/download-gps-cache.py              # 下載所有行程
  python3 scripts/download-gps-cache.py --trip 2024-kanazawa  # 只下載特定行程
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

NAS_PATH = Path("/Volumes/photo")
SCAN_SOURCES = [
    "MobileBackup/iPhone",
    "MobileBackup/AlienChang/iPhone",
    "MobileBackup/nini/iPhone",
    "PhotoLibrary",
    "Other_Picture/iphone6s_alien/DCIM",
    "Other_Picture/iphone6_nini/backup_20170720/DCIM",
    "Other_Picture/iphone6_nini/backup_20181111/DCIM",
]
TRIPS_DIR = Path(__file__).parent.parent / "trips"
CACHE_DIR = TRIPS_DIR / "gps-cache"


def extract_gps_from_nas(source, date_start, date_end, verbose=True):
    """從 NAS 目錄萃取指定日期範圍的 GPS 資料"""
    base = NAS_PATH / source
    if not base.exists():
        return []

    # 找出需要的月份
    months_needed = set()
    d = date_start
    while d <= date_end:
        months_needed.add((d.year, d.month))
        d += timedelta(days=1)

    # 收集照片檔案
    photo_files = []
    has_year_dirs = any(yr_dir.is_dir() and yr_dir.name.isdigit() for yr_dir in base.iterdir()) if base.exists() else False
    
    if has_year_dirs:
        # 標準 year/month 結構
        for yr_dir in sorted(base.iterdir()):
            if not yr_dir.is_dir() or not yr_dir.name.isdigit():
                continue
            year = int(yr_dir.name)
            for m_dir in sorted(yr_dir.iterdir()):
                if not m_dir.is_dir() or not m_dir.name.isdigit():
                    continue
                month = int(m_dir.name)
                if (year, month) not in months_needed:
                    continue
                for f in m_dir.iterdir():
                    if f.is_file() and f.suffix.upper() in (".HEIC", ".HEIF", ".JPG", ".JPEG"):
                        photo_files.append(f)
    else:
        # 扁平 DCIM 結構（*APPLE 目錄）
        for subdir in sorted(base.iterdir()):
            if not subdir.is_dir():
                continue
            for f in subdir.iterdir():
                if f.is_file() and f.suffix.upper() in (".HEIC", ".HEIF", ".JPG", ".JPEG"):
                    photo_files.append(f)

    if not photo_files:
        return []

    # 批次萃取 GPS
    batch_size = 200
    all_data = []
    file_paths = [str(f) for f in photo_files]

    for i in range(0, len(file_paths), batch_size):
        chunk = file_paths[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(file_paths) + batch_size - 1) // batch_size

        try:
            result = subprocess.run(
                ["exiftool", "-d", "%Y-%m-%d %H:%M:%S",
                 "-DateTimeOriginal", "-GPSLatitude", "-GPSLongitude",
                 "-GPSLatitudeRef", "-GPSLongitudeRef",
                 "-GPSAltitude", "-GPSAltitudeRef",
                 "-json"] + chunk,
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                all_data.extend(data)
                if verbose:
                    print(f"    ✓ 批次 {batch_num}/{total_batches}: {len(data)} 張", end=" ", flush=True)
        except subprocess.TimeoutExpired:
            if verbose:
                print(f"\n    ⚠️ 批次 {batch_num}/{total_batches} 逾時，改用逐檔...", end=" ", flush=True)
            for fp in chunk:
                try:
                    r = subprocess.run(
                        ["exiftool", "-d", "%Y-%m-%d %H:%M:%S",
                         "-DateTimeOriginal", "-GPSLatitude", "-GPSLongitude",
                         "-GPSLatitudeRef", "-GPSLongitudeRef",
                         "-GPSAltitude", "-GPSAltitudeRef",
                         "-json", fp],
                        capture_output=True, text=True, timeout=30,
                    )
                    if r.returncode == 0:
                        all_data.extend(json.loads(r.stdout))
                except Exception:
                    pass
        except json.JSONDecodeError:
            continue

    if verbose:
        print(f"\n    📊 共 {len(all_data)} 張含 GPS")

    if not all_data:
        return []

    # 按精確日期範圍篩選
    filtered = []
    for item in all_data:
        dt_str = item.get("DateTimeOriginal", "")
        if not dt_str:
            continue
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            ds = date_start.date() if hasattr(date_start, 'date') else date_start
            de = date_end.date() if hasattr(date_end, 'date') else date_end
            if ds <= dt.date() <= de:
                filtered.append(item)
        except ValueError:
            continue

    return filtered


def download_trip_gps(trip_id, verbose=True):
    """下載單一行程的 GPS 資料到本地快取"""
    trip_file = TRIPS_DIR / f"{trip_id}.json"
    if not trip_file.exists():
        print(f"  ❌ 找不到行程: {trip_id}")
        return False

    trip = json.load(open(trip_file))
    date_start = datetime.strptime(trip["dateStart"], "%Y-%m-%d")
    date_end = datetime.strptime(trip["dateEnd"], "%Y-%m-%d")

    cache_file = CACHE_DIR / f"{trip_id}.json"

    if verbose:
        print(f"  📅 日期: {trip['dateStart']} → {trip['dateEnd']}")

    all_photos = []
    for source in SCAN_SOURCES:
        if verbose:
            print(f"  🔍 {source}...")
        photos = extract_gps_from_nas(source, date_start, date_end, verbose)
        all_photos.extend(photos)

    # 存入快取
    cache_data = {
        "trip_id": trip_id,
        "date_start": trip["dateStart"],
        "date_end": trip["dateEnd"],
        "downloaded_at": datetime.now().isoformat(),
        "photo_count": len(all_photos),
        "photos": all_photos,
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(cache_data, f, ensure_ascii=False)

    if verbose:
        print(f"  ✅ 已儲存: {cache_file.name} ({len(all_photos)} 張)")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="下載 NAS GPS 資料到本地快取")
    parser.add_argument("--trip", help="只下載特定行程")
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 取得所有行程
    manifest = json.load(open(TRIPS_DIR / "manifest.json"))
    trips = [args.trip] if args.trip else manifest

    print(f"📦 將下載 {len(trips)} 個行程的 GPS 資料到 {CACHE_DIR}")
    print()

    success = 0
    for trip_id in trips:
        print(f"📋 {trip_id}")
        if download_trip_gps(trip_id):
            success += 1
        print()

    print(f"✅ 完成: {success}/{len(trips)} 個行程已下載")


if __name__ == "__main__":
    main()
