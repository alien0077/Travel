#!/usr/bin/env python3
"""從行程 JSON 的 days 規劃資料生成 actualDays（未來路線）
用法: python3 gen-planned-route.py --trip 2026-shikoku [--apply]

功能：
1. 讀取 days 中的 timeline（含 mapcode/placeName）
2. 使用 Mapcode API 或 Nominatim 取得 GPS 座標
3. 生成 actualDays（route + stops），讓地圖可顯示規劃路線
4. 行程完成後再跑 enrich_gps.py 即可覆蓋為真實 GPS 資料
"""

import json
import sys
import argparse
import subprocess
import re
from pathlib import Path
from datetime import datetime

TRIPS_DIR = Path(__file__).parent.parent / "trips"


def mapcode_to_gps(mapcode: str):
    """嘗試將 mapcode 轉為 GPS（使用 mapcode.org API）"""
    import urllib.request
    import urllib.parse
    clean = mapcode.strip().replace('*', ' ')
    url = f"https://mapcode.org/api/v1/decode?code={urllib.parse.quote(clean)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            lat = data.get("lat") or data.get("latitude")
            lon = data.get("lon") or data.get("longitude")
            if lat and lon:
                return float(lat), float(lon)
    except Exception:
        pass
    return None, None


def nominatim_geocode(query: str):
    """使用 Nominatim 從地名取得 GPS 座標"""
    import urllib.request
    import urllib.parse
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1&countrycodes=jp"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TravelBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


def extract_coords_from_day(day_data: dict, verbose=False):
    """從一天的規劃中提取所有 GPS 座標"""
    coords = []  # [(lat, lon, label), ...]
    timeline = day_data.get("timeline", [])

    for item in timeline:
        lat, lon = None, None
        label = item.get("title", "")

        # 1) 嘗試 mapcode
        detail = item.get("detail", "")
        mc_match = re.search(r'MAPCODE:\s*([\d\s\*]+)', detail)
        if mc_match:
            lat, lon = mapcode_to_gps(mc_match.group(1))
            if lat and verbose:
                print(f"  mapcode → {lat:.4f}, {lon:.4f} ({label})")

        # 2) 嘗試地名 geocode
        if lat is None:
            # 從 title 提取地名（移除 emoji 和動詞）
            clean_name = re.sub(r'[🚗🏯🌀🛍️♨️🛬📋🎯]', '', label).strip()
            clean_name = re.sub(r'^(完攻|前往|移動|入住|出發|返回)', '', clean_name).strip()
            if clean_name:
                lat, lon = nominatim_geocode(clean_name)
                if lat and verbose:
                    print(f"  geocode → {lat:.4f}, {lon:.4f} ({label})")

        if lat and lon:
            coords.append((lat, lon, label))

    return coords


def generate_actual_days(trip_data: dict, verbose=False):
    """從 days 規劃生成 actualDays"""
    days = trip_data.get("days", {})
    actual_days = {}

    for day_key in sorted(days.keys()):
        day_data = days[day_key]
        if verbose:
            print(f"\n📅 {day_key}: {day_data.get('title', '')}")

        coords = extract_coords_from_day(day_data, verbose)

        if not coords:
            if verbose:
                print(f"  ⚠ 無法取得 GPS 座標，跳過")
            continue

        # 生成 route（座標陣列）
        route = [[lat, lon] for lat, lon, _ in coords]

        # 生成 timeline stops
        timeline = []
        for lat, lon, label in coords:
            timeline.append({
                "type": "stop",
                "category": "sight",
                "placeName": label,
                "lat": lat,
                "lon": lon,
            })

        actual_days[day_key] = {
            "date": day_data.get("date", ""),
            "timeline": timeline,
            "route": route,
            "source": "planned",  # 標記為規劃路線（非真實 GPS）
        }

        if verbose:
            print(f"  ✅ {len(route)} 個路線點, {len(timeline)} 個停留點")

    return actual_days


def main():
    parser = argparse.ArgumentParser(description="從行程規劃生成 actualDays")
    parser.add_argument("--trip", required=True, help="行程 ID（如 2026-shikoku）")
    parser.add_argument("--apply", action="store_true", help="直接寫入行程 JSON")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    trip_file = TRIPS_DIR / f"{args.trip}.json"
    if not trip_file.exists():
        print(f"❌ 找不到: {trip_file}")
        sys.exit(1)

    trip_data = json.load(open(trip_file))

    if trip_data.get("actualDays"):
        print(f"⚠️  {args.trip} 已有 actualDays（{len(trip_data['actualDays'])} 天）")
        if not args.apply:
            print("   使用 --apply 強制覆蓋")
            return

    print(f"📋 處理: {trip_data.get('title', args.trip)}")
    print(f"   日期: {trip_data.get('dateStart')} → {trip_data.get('dateEnd')}")

    actual_days = generate_actual_days(trip_data, args.verbose)

    if not actual_days:
        print("❌ 無法生成任何 actualDays（所有日期都無法取得 GPS）")
        sys.exit(1)

    print(f"\n📊 生成: {len(actual_days)} 天的規劃路線")

    if args.apply:
        trip_data["actualDays"] = actual_days
        with open(trip_file, "w") as f:
            json.dump(trip_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 已寫入: {trip_file}")
    else:
        # 輸出到 stdout
        print(json.dumps({"actualDays": actual_days}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
