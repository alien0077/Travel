#!/usr/bin/env python3
"""從照片 GPS 與 OpenStreetMap 補上實際／規劃景點狀態。

用法：
  python3 scripts/enrich-attractions.py --trip 2025-nagoya --apply
  python3 scripts/enrich-attractions.py --all --apply

OSM 查詢結果會寫入 trips/osm-cache/，行程 JSON 只保存精簡且可追溯的景點資料。
頁面不會在瀏覽器直接呼叫 Overpass。
"""

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIPS_DIR = ROOT / "trips"
GPS_CACHE_DIR = TRIPS_DIR / "gps-cache"
OSM_CACHE_DIR = TRIPS_DIR / "osm-cache"
GEOCODE_CACHE_FILE = OSM_CACHE_DIR / "nominatim.json"
GEOCODE_CACHE_VERSION = "v2-name-only"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "Travel-Globe-attractions/1.0 (static travel journal)"
MATCH_RADIUS_M = 250
QUERY_RADIUS_M = 350
MAX_QUERY_RETRIES = 4
MAX_CENTERS_PER_REQUEST = 1
REQUEST_PAUSE_SECONDS = 2.0
CACHE_SCHEMA_VERSION = "v3-stop-centers"
MAX_ATTRACTIONS_PER_DAY = 20


class OSMQueryError(RuntimeError):
    pass


def haversine_m(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def dms_to_decimal(value):
    if isinstance(value, (int, float)):
        return float(value)
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*deg\s*(\d+(?:\.\d+)?)?\s*'\s*(\d+(?:\.\d+)?)?", str(value), re.I)
    if not match:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    deg, minute, second = (float(x or 0) for x in match.groups())
    return deg + minute / 60 + second / 3600


def photo_point(photo):
    lat = dms_to_decimal(photo.get("GPSLatitude"))
    lon = dms_to_decimal(photo.get("GPSLongitude"))
    if lat is None or lon is None:
        return None
    if str(photo.get("GPSLatitudeRef", "N")).upper().startswith("S"):
        lat = -lat
    if str(photo.get("GPSLongitudeRef", "E")).upper().startswith("W"):
        lon = -lon
    return lat, lon


def trip_days(trip):
    start = datetime.strptime(trip["dateStart"], "%Y-%m-%d").date()
    end = datetime.strptime(trip["dateEnd"], "%Y-%m-%d").date()
    return start, end


def load_photo_points(trip):
    cache_file = GPS_CACHE_DIR / f"{trip['id']}.json"
    if not cache_file.exists():
        return {}
    start, end = trip_days(trip)
    by_date = {}
    for photo in json.loads(cache_file.read_text()).get("photos", []):
        raw_date = str(photo.get("DateTimeOriginal", ""))[:10]
        try:
            photo_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (start <= photo_date <= end):
            continue
        point = photo_point(photo)
        if point:
            by_date.setdefault(raw_date, []).append(point)
    return by_date


def cluster_points(points):
    """以約 200m 網格合併照片，避免每張照片都造成一個查詢中心。"""
    buckets = {}
    for lat, lon in points:
        key = (round(lat / 0.002), round(lon / 0.002))
        buckets.setdefault(key, []).append((lat, lon))
    result = []
    for values in buckets.values():
        result.append((sum(p[0] for p in values) / len(values), sum(p[1] for p in values) / len(values), len(values)))
    return result


def iso_date_for_day(trip, day_key):
    keys = list(trip.get("days", {}))
    try:
        offset = keys.index(day_key)
        start = datetime.strptime(trip["dateStart"], "%Y-%m-%d").date()
        return (start.fromordinal(start.toordinal() + offset)).isoformat()
    except (ValueError, IndexError):
        return None


def overpass_query(centers):
    clauses = []
    selectors = [
        '["tourism"~"attraction|museum|gallery|zoo|theme_park|viewpoint"]',
        '["historic"~"castle|fort"]',
        '["leisure"~"park|garden"]',
        '["natural"~"beach|waterfall|peak|cave"]',
    ]
    for lat, lon, _ in centers:
        for selector in selectors:
            clauses.extend([
                f'node{selector}(around:{QUERY_RADIUS_M},{lat:.7f},{lon:.7f});',
                f'way{selector}(around:{QUERY_RADIUS_M},{lat:.7f},{lon:.7f});',
            ])
    return "[out:json][timeout:60];(\n" + "\n".join(clauses) + "\n);out center tags;"


def fetch_osm(trip_id, day_key, centers, refresh=False):
    cache_file = OSM_CACHE_DIR / f"{trip_id}-{day_key}-{CACHE_SCHEMA_VERSION}.json"
    if cache_file.exists() and not refresh:
        return json.loads(cache_file.read_text())
    if not centers:
        return []
    all_elements = []
    center_batches = [centers[i:i + MAX_CENTERS_PER_REQUEST] for i in range(0, len(centers), MAX_CENTERS_PER_REQUEST)]
    for batch_index, batch in enumerate(center_batches):
        batch_cache_file = OSM_CACHE_DIR / f"{trip_id}-{day_key}-{CACHE_SCHEMA_VERSION}-batch-{batch_index + 1}.json"
        if batch_cache_file.exists() and not refresh:
            all_elements.extend(json.loads(batch_cache_file.read_text()))
            continue
        last_error = None
        success = False
        for attempt in range(MAX_QUERY_RETRIES):
            request = urllib.request.Request(
                OVERPASS_URL,
                data=urllib.parse.urlencode({"data": overpass_query(batch)}).encode(),
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=75) as response:
                    batch_elements = json.loads(response.read()).get("elements", [])
                    all_elements.extend(batch_elements)
                OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                batch_cache_file.write_text(json.dumps(batch_elements, ensure_ascii=False, indent=2))
                success = True
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                transient = exc.code in {408, 429, 502, 503, 504}
                if not transient or attempt == MAX_QUERY_RETRIES - 1:
                    break
                retry_after = exc.headers.get("Retry-After")
                wait_seconds = min(int(retry_after), 90) if retry_after and retry_after.isdigit() else 15 * (attempt + 1)
                print(f"  ⚠ OSM 暫時錯誤 day={day_key} batch={batch_index + 1}/{len(center_batches)} HTTP {exc.code}，{wait_seconds} 秒後重試", file=sys.stderr)
                time.sleep(wait_seconds)
            except Exception as exc:
                last_error = exc
                break
        if not success:
            raise OSMQueryError(f"{day_key} batch {batch_index + 1}/{len(center_batches)}: {last_error}") from last_error
        if batch_index + 1 < len(center_batches):
            time.sleep(REQUEST_PAUSE_SECONDS)
    elements = all_elements
    OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(elements, ensure_ascii=False, indent=2))
    time.sleep(1.1)
    return elements


def osm_point(element):
    if "lat" in element:
        return element["lat"], element["lon"]
    center = element.get("center") or {}
    if "lat" in center:
        return center["lat"], center["lon"]
    return None


def osm_category(tags):
    for key in ("tourism", "historic", "leisure", "natural"):
        if tags.get(key):
            return tags[key]
    return "attraction"


def is_supported_attraction(tags):
    return (
        tags.get("tourism") in {"attraction", "museum", "gallery", "zoo", "theme_park", "viewpoint"}
        or tags.get("historic") in {"castle", "fort", "archaeological_site"}
        or tags.get("leisure") in {"park", "garden"}
        or tags.get("natural") in {"beach", "waterfall", "peak", "cave"}
    )


def attraction_priority(tags):
    if tags.get("tourism") in {"attraction", "museum", "gallery", "zoo", "theme_park", "viewpoint"}:
        return 0
    if tags.get("historic") in {"castle", "fort", "archaeological_site"}:
        return 1
    return 2


def osm_attractions(elements, centers, evidence):
    found = {}
    for element in elements:
        point = osm_point(element)
        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("name:ja") or tags.get("official_name")
        if not point or not name or not is_supported_attraction(tags):
            continue
        query_distance = min(haversine_m(point, c[:2]) for c in centers)
        evidence_distance = min(haversine_m(point, e[:2]) for e in evidence)
        if query_distance > QUERY_RADIUS_M or evidence_distance > MATCH_RADIUS_M:
            continue
        key = f"{element.get('type')}-{element.get('id')}"
        found[key] = {
            "id": key,
            "name": name,
            "lat": round(point[0], 7),
            "lng": round(point[1], 7),
            "category": osm_category(tags),
            "source": "osm",
            "sourceUrl": f"https://www.openstreetmap.org/{element.get('type')}/{element.get('id')}",
            "_priority": attraction_priority(tags),
            "_evidenceDistance": evidence_distance,
        }
    selected = []
    seen_names = set()
    for attraction in sorted(found.values(), key=lambda x: (x["_priority"], x["_evidenceDistance"], x["name"])):
        name_key = re.sub(r"\s+", "", attraction["name"]).casefold()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        attraction.pop("_priority", None)
        attraction.pop("_evidenceDistance", None)
        selected.append(attraction)
        if len(selected) >= MAX_ATTRACTIONS_PER_DAY:
            break
    return selected


def clean_planned_name(item):
    title = item.get("title") or item.get("name", "")
    title = re.sub(r"[🚗🏯🌀🛍️♨️🛬📋🎯]", "", title)
    title = re.sub(r"^(完攻|前往|移動|入住|出發|返回)", "", title).strip()
    return title


def nominatim_geocode(query):
    """以 OSM Nominatim 補上沒有 mapUrl 座標的規劃景點。"""
    cache = {}
    cache_file = OSM_CACHE_DIR / f"nominatim-{GEOCODE_CACHE_VERSION}.json"
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            cache = {}
    if query in cache:
        return cache[query]
    request = urllib.request.Request(
        "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            "q": query, "format": "jsonv2", "limit": 1, "countrycodes": "jp"
        }),
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            rows = json.loads(response.read())
        result = [float(rows[0]["lat"]), float(rows[0]["lon"])] if rows else None
    except Exception:
        result = None
    cache[query] = result
    OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    time.sleep(1.1)
    return result


def planned_points(day, trip, day_key):
    result = []
    for item in day.get("timeline", []):
        if item.get("type") not in ("act", "sight", "visit"):
            continue
        name = clean_planned_name(item)
        if not name or re.search(r"機場|租車|還車|入住|check.?in|check.?out|航班|辦理|移動|前往", name, re.I):
            continue
        coords = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", item.get("mapUrl") or "")
        if coords:
            result.append((float(coords.group(1)), float(coords.group(2)), name))
            continue
        point = nominatim_geocode(name)
        if point:
            result.append((point[0], point[1], name))
    for item in trip.get("sightsList", []):
        if item.get("day") != day_key:
            continue
        name = clean_planned_name(item)
        if not name:
            continue
        point = nominatim_geocode(name)
        if point:
            result.append((point[0], point[1], name))
    return result


def nearest_evidence(point, evidence):
    if not evidence:
        return None, None
    candidate = min(evidence, key=lambda x: haversine_m(point, x[:2]))
    return candidate, haversine_m(point, candidate[:2])


def gps_fallback_attractions(actual_day, evidence, day_key):
    """OSM 暫時不可用時，保留真實 GPS 停留點，不偽裝成 OSM 景點。"""
    fallback = []
    seen = set()
    for index, stop in enumerate(actual_day.get("timeline", [])):
        lat = stop.get("lat")
        lng = stop.get("lng", stop.get("lon"))
        if lat is None or lng is None:
            continue
        name = (stop.get("placeName") or stop.get("name") or "GPS 實際停留點").strip()
        if len(name) < 2:
            name = f"GPS 實際停留點（{name or '未命名'}）"
        key = (name, round(lat, 4), round(lng, 4))
        if key in seen:
            continue
        seen.add(key)
        fallback.append({
            "id": f"gps-{day_key}-{index}",
            "name": name,
            "lat": round(lat, 7),
            "lng": round(lng, 7),
            "category": "gps_stop",
            "source": "gps",
            "status": "unplanned_visited",
            "distanceMeters": 0,
            "photoCount": stop.get("photoCount", 0),
        })
    if fallback:
        return fallback[:MAX_ATTRACTIONS_PER_DAY]
    for index, (lat, lng, photo_count) in enumerate(evidence):
        fallback.append({
            "id": f"gps-{day_key}-{index}",
            "name": "GPS 實際停留點",
            "lat": round(lat, 7),
            "lng": round(lng, 7),
            "category": "gps_stop",
            "source": "gps",
            "status": "unplanned_visited",
            "distanceMeters": 0,
            "photoCount": photo_count,
        })
    return fallback[:MAX_ATTRACTIONS_PER_DAY]


def enrich_trip(trip, refresh=False, verbose=False):
    photos_by_date = load_photo_points(trip)
    actual_days = trip.get("actualDays") or {}
    output = []
    for day_key, day in trip.get("days", {}).items():
        date = iso_date_for_day(trip, day_key)
        actual_day = actual_days.get(day_key) or {}
        photo_points = photos_by_date.get(date, [])
        existing_stops = []
        if actual_day.get("source") != "planned":
            for stop in actual_day.get("timeline", []):
                lat = stop.get("lat")
                lng = stop.get("lng", stop.get("lon"))
                if lat is not None and lng is not None:
                    existing_stops.append((lat, lng, stop.get("photoCount", 0)))
        photo_clusters = cluster_points(photo_points)
        evidence = existing_stops + photo_clusters
        # 優先使用 GPS enrichment 已經辨識出的停留點；照片群組只作為沒有停留點時的 fallback。
        # 路線上的每張照片不應各自觸發一次 Overpass 查詢。
        centers = existing_stops or photo_clusters
        if not centers:
            continue
        try:
            elements = fetch_osm(trip["id"], day_key, centers, refresh)
        except OSMQueryError as exc:
            print(f"  ⚠ {exc}；改用 GPS 實際停留點完成此日", file=sys.stderr)
            elements = []
        attractions = osm_attractions(elements, centers, evidence)
        enriched = []
        planned = planned_points(day, trip, day_key)
        for attraction in attractions:
            evidence_point, distance = nearest_evidence((attraction["lat"], attraction["lng"]), evidence)
            _, planned_distance = nearest_evidence((attraction["lat"], attraction["lng"]), planned)
            if distance is not None and distance <= MATCH_RADIUS_M:
                status = "visited" if planned_distance is not None and planned_distance <= MATCH_RADIUS_M else "unplanned_visited"
                attraction.update({"status": status, "distanceMeters": round(distance), "photoCount": evidence_point[2]})
            else:
                attraction.update({"status": "nearby", "distanceMeters": round(distance) if distance is not None else None})
            enriched.append(attraction)
        for lat, lng, name in planned:
            _, distance = nearest_evidence((lat, lng), evidence)
            match = next((a for a in enriched if haversine_m((lat, lng), (a["lat"], a["lng"])) <= MATCH_RADIUS_M), None)
            status = "visited" if distance is not None and distance <= MATCH_RADIUS_M else "planned_not_visited"
            if match:
                match["status"] = status
                match["plannedName"] = name
                continue
            enriched.append({
                "id": f"planned-{day_key}-{len(enriched)}",
                "name": name,
                "lat": round(lat, 7),
                "lng": round(lng, 7),
                "category": "planned",
                "source": "planned",
                "status": status,
                "distanceMeters": round(distance) if distance is not None else None,
            })
        if not attractions and actual_day.get("source") != "planned":
            enriched.extend(gps_fallback_attractions(actual_day, evidence, day_key))
        if len(enriched) > MAX_ATTRACTIONS_PER_DAY:
            status_rank = {"planned_not_visited": 0, "visited": 1, "unplanned_visited": 2, "nearby": 3}
            enriched.sort(key=lambda item: (status_rank.get(item.get("status"), 4), item.get("distanceMeters") or 999999))
            enriched = enriched[:MAX_ATTRACTIONS_PER_DAY]
        if enriched:
            output.append((day_key, enriched))
            if verbose:
                print(f"  {day_key}: {len(enriched)} 個景點")
    return output


def validate_enrichment(enriched):
    """寫入前的保守檢查；失敗時由 main 中止，不碰行程 JSON。"""
    valid_statuses = {"visited", "planned_not_visited", "unplanned_visited", "nearby"}
    errors = []
    total = 0
    osm_count = 0
    evidence_count = 0
    for day_key, attractions in enriched:
        if not attractions:
            errors.append(f"{day_key}: 景點清單為空")
            continue
        if len(attractions) > MAX_ATTRACTIONS_PER_DAY:
            errors.append(f"{day_key}: 景點數量異常（{len(attractions)}）")
        for attraction in attractions:
            total += 1
            name = str(attraction.get("name", "")).strip()
            lat, lng = attraction.get("lat"), attraction.get("lng")
            status = attraction.get("status")
            if not name or re.fullmatch(r"[-\d., ]+", name):
                errors.append(f"{day_key}: 景點名稱無效：{name!r}")
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                errors.append(f"{day_key}: {name} 缺少有效座標")
            elif not (-90 <= lat <= 90 and -180 <= lng <= 180):
                errors.append(f"{day_key}: {name} 座標超出範圍")
            if status not in valid_statuses:
                errors.append(f"{day_key}: {name} 狀態無效：{status!r}")
            if attraction.get("source") == "osm":
                osm_count += 1
            if status in {"visited", "unplanned_visited"}:
                needs_photo_count = attraction.get("source") == "osm"
                if needs_photo_count and (not isinstance(attraction.get("photoCount"), (int, float)) or attraction.get("photoCount", 0) <= 0):
                    errors.append(f"{day_key}: {name} 被判定為已造訪但沒有照片證據")
                elif attraction.get("source") in {"osm", "gps"}:
                    evidence_count += 1
                if attraction.get("distanceMeters") is None or attraction["distanceMeters"] > MATCH_RADIUS_M:
                    errors.append(f"{day_key}: {name} 的造訪距離不合理")
    if total == 0:
        errors.append("沒有產生任何景點")
    if osm_count == 0 and total == 0:
        errors.append("沒有取得 OSM 景點，也沒有 GPS 停留點")
    if errors:
        return False, errors
    return True, [f"{len(enriched)} 天、{total} 個景點、{osm_count} 個 OSM 景點、{evidence_count} 個有照片證據的造訪"]


def main():
    parser = argparse.ArgumentParser(description="補上 OSM 景點與實際／規劃狀態")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--trip")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="忽略 OSM 快取重新查詢")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    ids = [args.trip] if args.trip else json.loads((TRIPS_DIR / "manifest.json").read_text())
    for trip_id in ids:
        path = TRIPS_DIR / f"{trip_id}.json"
        if not path.exists():
            print(f"⚠ 找不到 {path}", file=sys.stderr)
            continue
        trip = json.loads(path.read_text())
        print(f"📍 {trip_id}")
        trip_start = datetime.strptime(trip["dateStart"], "%Y-%m-%d").date()
        if trip_start > datetime.now().date():
            print(f"  ⏭ 尚未出發（{trip['dateStart']}），跳過，不查詢、不寫入 JSON")
            continue
        enriched = enrich_trip(trip, args.refresh, args.verbose)
        valid, validation_messages = validate_enrichment(enriched)
        for message in validation_messages:
            print(("  ✅ " if valid else "  ❌ ") + message)
        if not valid:
            print("  ⛔ 驗證失敗，未寫入 JSON", file=sys.stderr)
            continue
        if args.apply:
            for day_key, attractions in enriched:
                trip.setdefault("actualDays", {}).setdefault(day_key, {})["attractions"] = attractions
            path.write_text(json.dumps(trip, ensure_ascii=False, indent=2) + "\n")
            print(f"  ✅ 已寫入 {len(enriched)} 天")
        else:
            print(json.dumps({day: attractions for day, attractions in enriched}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
