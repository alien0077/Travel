# JSON-based Trip Itinerary Architecture

## Problem

`index.html` currently has all content (trip cards, statistics, map planned codes) hard-coded as static HTML. Adding new trips requires manual edits to `index.html`. The homepage cannot automatically determine which trips are current/future vs. past, nor dynamically update its title, stats, or map data.

## Solution

Replace standalone trip HTML files with a unified JSON-driven system: each trip gets a JSON file under `trips/`, `index.html` fetches them dynamically for homepage rendering, and `viewer.html` renders a full interactive trip page from a `?trip=xxx` parameter.

## Directory Layout

```
/
├── index.html              # Dynamic: fetches trips/*.json, renders cards + archive
├── viewer.html             # Dynamic: ?trip=xxx fetches JSON, renders full interactive trip
├── template.html           # Static template for generating new trip JSONs
├── trips/
│   ├── manifest.json       # Manual list: array of trip IDs (one entry per trip)
│   ├── 2026-tokyo.json     # Tokyo trip data
│   └── 2026-shikoku.json   # Shikoku trip data
├── archive/                # Legacy standalone HTML files
│   ├── 2026_0705__0708東京快閃.html
│   └── 2026_0806__0813四國遊.html
├── .github/workflows/
│   └── deploy-pages.yml    # GitHub Pages deployment workflow
├── .nojekyll               # Publish files directly without Jekyll processing
├── AGENTS.md
└── .gitignore
```

## Trip JSON Schema

```json
{
  "id": "2026-tokyo",
  "type": "city",
  "title": "東京親子冒險",
  "subtitle": "7/5 - 7/8 親子交通導航・專屬手冊",
  "badge": "Tokyo City Sprint",
  "badgeIcon": "fa-train-subway",
  "description": "上野住宿、台場夜景、行前清單與每日分頁。",
  "stats": ["4天3夜", "成田進出", "互動記帳"],
  "image": "tokyo",
  "prefectures": ["12", "13"],
  "airports": ["NRT"],
  "dateStart": "2026-07-05",
  "dateEnd": "2026-07-08",
  "countdownDate": "2026/07/05 08:05:00",
  "jpyToTwdRate": 0.22,
  "actionText": "VJW / 工具",
  "flights": {
    "outbound": "去程：FD234 | 高雄 08:05 ➔ 12:55 成田",
    "inbound": "回程：FD235 | 成田 13:55 ➔ 17:05 高雄"
  },
  "vjw": {
    "zip": "110-0015",
    "address": "東京都台東区東上野 X-XX-X",
    "name": "Ostay Ueno Hotel"
  },
  "sightsList": [
    { "id": "sight1", "name": "🎮 Day 1: 台場一丁目商店街", "day": "day1" }
  ],
  "defaultExpenses": [
    { "id": 1, "name": "🏩 Ostay Ueno 四晚住宿預算", "amount": 98000 }
  ],
  "days": {
    "day1": {
      "date": "7/5 (日)",
      "title": "抵達東京與台場夜景",
      "timeRange": "12:55pm - 09:30pm",
      "timeline": [
        {
          "type": "transport",
          "time": "12:55pm - 14:30pm",
          "title": "成田機場 ➔ 上野京成電鐵",
          "detail": "搭乘 Skyliner 42 號。",
          "mapUrl": "https://maps.app.goo.gl/...",
          "mapcode": "12 345 678*90"
        }
      ],
      "food": [
        {
          "meal": "晚餐 (18:00)",
          "name": "名代宇奈とと 鰻魚飯",
          "detail": "上野高 CP 值鰻魚飯。",
          "mapUrl": "...",
          "mapcode": "12 345 678*90"
        }
      ],
      "parking": [
        {
          "name": "上野中央地下停車場",
          "detail": "寬敞好停。",
          "mapUrl": "...",
          "mapcode": "12 345 678*90"
        }
      ],
      "hotel": {
        "name": "Ostay Ueno Hotel",
        "detail": "靠近上野站。",
        "mapUrl": "...",
        "mapcode": "12 345 678*90"
      },
      "details": "首日記得加值 Suica。"
    }
  }
}
```

### Field Notes

- `type`: `"city"` or `"drive"` — controls which UI features activate (ledger + checklist for city, parking + mapcode for drive).
- `dateStart`/`dateEnd`: ISO 8601 dates (YYYY-MM-DD). Used by `index.html` to classify active vs. archive.
- `prefectures`: Array of 2-digit prefecture codes that the trip covers. Merged into the conquest map.
- `airports`: Array of IATA codes. Merged into the airport tracker.
- `days`: Object with `day1`, `day2`, ... keys. Unlike the current HTML template, `label` is not stored in JSON (it's computed as "Day N" from the key).

## index.html — Homepage Dynamic Behavior

### Fetch flow
1. Fetch `trips/manifest.json` — returns `["2026-tokyo", "2026-shikoku"]` (simple array of trip IDs).
2. Fetch each `trips/{id}.json`.
3. For each trip, compare `dateEnd` with `new Date()`:
   - `dateEnd >= today` → trip-grid card (large background card)
   - `dateEnd < today` → archive-grid card (compact bookmark)
4. Compute derived values:
   - **Title**: year from the latest active trip.
   - **Stats**: trip count, date range, airport list.
   - **Map planned codes**: union of all active trips' `prefectures`.
   - **Airport planned codes**: union of all active trips' `airports`.
5. If no active trips found → display placeholder card: "{next year} 年旅行規劃中 ✨".

### HTML attribute removal
- `data-year`, `data-end`, `data-prefectures` no longer needed on HTML elements. All data comes from JSON.

## viewer.html — Unified Trip Viewer

### URL parameter
- `?trip=2026-tokyo` → fetch `trips/2026-tokyo.json`.

### Rendering
- Duplicate the full interactive trip UI currently in the standalone HTML files: day tabs, timeline, food cards, parking, hotel, checklist, ledger, notes, VJW section.
- Uses `type` field to toggle city vs. drive features.
- localStorage namespace: `trip-{id}` (e.g., `trip-2026-tokyo`).

### States
| State | Display |
|-------|---------|
| No `trip` param | Redirect to `index.html` with a toast message |
| Invalid trip ID | Error message "行程不存在" |
| JSON loaded | Full interactive UI |
| JSON fetch failed | Retry button + error message |

## AGENTS.md Updates

The `tripConfig` documentation section must be updated to reflect the new JSON schema (the `template.html` example becomes the template for generating new `trips/*.json` files). The Prompt template for agents must be updated to reference the new workflow:
1. Create `trips/{id}.json` from the schema.
2. Add the trip ID to `trips/manifest.json`.
3. Optionally archive old standalone HTML if migrating.

## Migration Steps

1. Create `trips/manifest.json` containing `["2026-tokyo", "2026-shikoku"]`.
2. Create `trips/2026-tokyo.json` and `trips/2026-shikoku.json` from existing HTML data.
3. Create `archive/` directory, move standalone HTML files into it.
3. Rewrite `index.html` — add fetch logic, dynamic card rendering, dynamic map data.
4. Create `viewer.html` — parameter parsing, JSON fetch, interactive trip UI.
5. Update `AGENTS.md` with new workflow.
6. Verify: `viewer.html?trip=2026-tokyo` matches existing standalone HTML behavior.
7. Verify: `index.html` auto-classifies cards, updates title, stats, map.
