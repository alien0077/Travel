# AGENTS.md

此專案是為 Chang 家族設計的 **日本親子旅行入口網站** 與互動式行程手冊。為了讓未來的 AI 協作代理人（Agents）能快速上手並避免常規誤判，請遵循以下開發與維護指南：

## 🚀 專案本質與架構 (不看會猜錯的部分)

- **純靜態前端專案**：本專案**沒有** Node.js/npm 依賴（無 `package.json`），也沒有任何後端服務或編譯打包步驟。
- **進入點 (Entry Point)**：
  - `index.html`：**動態入口首頁**，自動讀取 `trips/*.json` 渲染行程卡片，依日期分類為進行中（大圖卡）與已結束（歷史書籤）。
  - `viewer.html`：**統一行程檢視器**，接收 `?trip=xxx` 參數載入對應 JSON 並呈現完整互動介面（分頁、時間軸、記帳、打卡等）。
  - `template.html`：移至 archive/（JSON 直接作為資料來源，不再需要範本網頁）
- **資料層**：
  - `trips/manifest.json`：所有行程 ID 列表（陣列）。
  - `trips/{id}.json`：每個行程的完整資料（時間軸、美食、住宿、航班、VJW 等）。
- **封存**：
  - `archive/`：舊的獨立 HTML 檔案移入此處保留，不再被首頁參考。
- **外部依賴 (CDN)**：全部使用 CDN 載入，包含：
  - Tailwind CSS (`https://cdn.tailwindcss.com`)
  - FontAwesome 圖標
- **狀態管理與持久化**：
  - 首頁 `index.html` 的動態卡片與地圖狀態皆透過 `localStorage` 持久化。
  - `viewer.html` 使用 `trip-{id}` 作為命名空間（如 `trip-2026-tokyo`）儲存分頁、打卡、記帳、筆記等狀態。
  - 記帳匯率從行程 JSON 中的 `jpyToTwdRate` 讀取。
- **部署平台**：以後本專案部署一律使用 GitHub Pages，不再使用 Netlify。
  - GitHub Pages workflow：`.github/workflows/deploy-pages.yml`
  - 觸發方式：push 到 `main` 後直接發布根目錄。
  - 無任何 build command；不要新增 Netlify 設定或執行 Netlify deploy。

---

## 🗺️ JSON 行程資料架構 (Trip JSON Schema)

每個行程一個 JSON 檔，置於 `trips/` 目錄下。完整規格如下：

### 中繼資料（供首頁與地圖使用）
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
  "dateEnd": "2026-07-08"
}
```

### 完整欄位說明
| 欄位 | 說明 |
|------|------|
| `id` | 唯一識別碼，也是檔名（`trips/{id}.json`） |
| `type` | `"city"`（市區）或 `"drive"`（自駕） |
| `title` / `subtitle` | 頁面標題與副標題 |
| `badge` / `badgeIcon` | 首頁卡片上的徽章文字與 FontAwesome 圖示 |
| `description` | 首頁卡片描述 |
| `stats` | 首頁卡片底部的統計標籤陣列 |
| `image` | 對應 CSS class 名稱，控制卡片背景圖片 |
| `prefectures` | 涵蓋的都道府縣代碼（二位數），供地圖自動標記 |
| `airports` | 進出機場 IATA 代碼，供地圖自動標記 |
| `dateStart` / `dateEnd` | ISO 日期（YYYY-MM-DD），首頁依此判斷進行中或已結束 |
| `flights` | `{ outbound, inbound }` 航班資訊字串 |
| `vjw` | `{ zip, address, name }` Visit Japan Web 填寫資料 |
| `sightsList` | `[{ id, name, day }]` 景點解鎖清單（僅 city 模式） |
| `defaultExpenses` | `[{ id, name, amount }]` 預設記帳項目（僅 city 模式） |
| `countdownDate` | 倒數計時目標時間 |
| `jpyToTwdRate` | 日幣匯率（city 模式記帳用） |
| `actionText` | 頂部按鈕文字 |
| `days` | 每日行程物件（見下方） |

### 每日行程 (`days.dayN`)
```json
{
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
      "meal": "晚餐",
      "name": "名代宇奈とと 鰻魚飯",
      "detail": "上野平價高 CP 值鰻魚飯。",
      "mapUrl": "...",
      "mapcode": "..."
    }
  ],
  "parking": [
    {
      "name": "上野中央地下停車場",
      "detail": "寬敞好停。",
      "mapUrl": "...",
      "mapcode": "..."
    }
  ],
  "hotel": {
    "name": "Ostay Ueno Hotel",
    "detail": "靠近上野站。",
    "mapUrl": "...",
    "mapcode": "..."
  },
  "details": "首日記得加值 Suica。"
}
```

### 未來代理人生成新行程的 Prompt 範本
當需要新增行程時，請使用以下流程，逐項與使用者確認後再產出：

```markdown
我將協助您建立新的旅遊行程 JSON。在開始之前，請先提供以下基本資訊：

## 步驟 1：確認行程基本資料
請告訴我：
- 📍 **目的地**：哪個城市/區域？
- 📅 **日期**：出發與回程日期？
- 👨‍👩‍👧‍👦 **同行成員**：有誰一起去？
- 🚗 **交通方式**：自駕（drive）還是大眾交通（city）？
- 🛫 **航班**：去回程航班資訊？
- 🏨 **住宿**：每天住哪？

## 步驟 2：逐日行程細節
請提供每天的：
- 主要目的地與活動
- 用餐地點（如有推薦）
- 自駕停車點（如有）
- 特別注意事項

## 步驟 3：產出 JSON
我會根據 `trips/*.json` 的格式，在 `trips/` 目錄下建立 `{id}.json`，包含：
1. 完整的中繼資料（`prefectures`、`airports`、`dateStart`、`dateEnd` 等）供首頁與地圖自動辨識
2. 每天的 `timeline`、`food`、`parking`、`hotel`、`details`
3. 所有景點、美食、飯店、停車場附上 `mapUrl`（Google Maps 連結）
4. 自駕行程每個景點/停車場/飯店加入 `mapcode`，每天加入 `route` 路線點
5. 將新的行程 ID 加入 `trips/manifest.json` 陣列中
```

---

## 🗂️ 首頁動態分類機制 (index.html Dynamic Layout)

`index.html` 完全由 JavaScript 驅動，執行流程：
1. 載入時 fetch `trips/manifest.json` → 取得所有行程 ID。
2. 逐一 fetch `trips/{id}.json`。
3. 比較 `dateEnd` 與當天日期：
   - `dateEnd >= 今天` → 顯示為大圖卡（`.trip-grid`）
   - `dateEnd < 今天` → 顯示為歷史書籤（`.archive-grid`）
4. 彙整所有進行中行程的 `prefectures` 與 `airports`，自動更新地圖的 `PLANNED_CODES`。
5. 頁面標題、統計區塊、topbar 年份皆自動跟隨最新行程更新。

若無任何進行中行程，則顯示「{明年} 年旅行規劃中 ✨」佔位卡。

---

## 🗺️ 日本制霸地圖 (Japan Prefecture Conquest Map)

首頁 `index.html` 下方內嵌了一個基於 Geolonia 向量路徑的**日本制霸地圖**，支援自動同步與手動修改狀態：
1. **自動規劃判定**：地圖的 `PLANNED_CODES` 與 `PLANNED_AIRPORTS` 由 JS 從進行中行程的 JSON 資料自動彙整，不需手動維護。
2. **手動點擊切換**：使用者可點擊地圖上的都道府縣來切換狀態（未訪 `#e2e8f0` -> 已去過 `#10b981` -> 想去 `#f59e0b` -> 未訪）。
3. **資料持久化**：使用者的手動狀態儲存於 `localStorage` 的 `japan-conquest-map-states` 中，並可透過「重設手動修改」按鈕清除重算。
4. **機場進出足跡 (Airports Visited)**：所有機場標示（含 35 座國內外主要機場）以圓點 + IATA 代碼形式直接標註在地圖上，點擊即可切換灰（未進出）/ 藍（規劃進出）/ 綠（已進出）狀態，資料儲存於 `localStorage` 的 `japan-conquest-airports` 中。
5. **都道府縣名稱**：地圖上每個都道府縣中心均標記有灰色日文漢字名稱，協助辨識地理位置。

---

## 📸 實際路線重建機制 (Actual GPS Route Enrichment)

完成一趟旅行後，可從 Synology NAS 的 HEIC/JPG 照片 GPS 資料重建實際行程路線：

### 運作方式
- **NAS 路徑**: `/Volumes/photo`
- **照片格式**: HEIC 和 JPG 都有 GPS（2019 年後的 iPhone 照片）
- **照片來源**: 掃描 `MobileBackup/iPhone/`、`MobileBackup/AlienChang/iPhone/`、`MobileBackup/nini/iPhone/`、`PhotoLibrary/` 四個目錄
- **批次萃取**: 用 `exiftool` + `-json` 批次萃取，不逐檔讀取

### 執行腳本
```bash
python3 ~/.config/opencode/skills/trip-gps-enrich/scripts/enrich_gps.py --trip <id>
python3 ~/.config/opencode/skills/trip-gps-enrich/scripts/enrich_gps.py --all
```

### 資料結構
行程 JSON 會增加 `actualDays` 區塊（保留原有 `days` 規劃不變）：
```json
{
  "routeColor": "#EF4444",
  "actualDays": {
    "day1": {
      "date": "2/8 (日)",
      "timeline": [
        {
          "type": "stop", "category": "sight",
          "actualTime": "10:18 - 11:45",
          "placeName": "神戸空港",
          "address": "神戸市中央区...",
          "lat": 34.6379, "lng": 135.2259,
          "photoCount": 3
        }
      ],
      "route": [[lat,lng], ...]
    }
  }
}
```

### 地圖渲染
- `index.html` 使用 Leaflet + OpenStreetMap 渲染路線
- 每趟不同顏色，含路線 polyline + 停留點 marker + Day 標籤
- Viewer 地圖每日切換，自動 zoom 至當天路線範圍

### 世界化地圖（World Map）
- **世界省/州邊界**: `trips/world-admin1.geojson`（38.8MB，4596 features，Natural Earth 10m）
- **世界城市邊界**: `trips/world-cities.geojson`（19.7MB，34472 features，geojson-world-cities）
- **全球機場資料**: `trips/ourairports.json`（4562 個大型+中型機場，OurAirports.com）
- **顯示邏輯**: zoom >= 3 顯示省/州虛線邊界，zoom >= 6 顯示城市虛線邊界
- **Canvas 渲染**: 使用 `L.canvas()` 提升大量 polygon 的繪製效能
- **插旗功能**: GPS 照片自動定位城市，以 🚩 標記visited cities（`visitedCitiesLayer`）
- **機場圖標**: 4562 個機場使用 ✈️ divIcon（`L.divIcon`），zoom < 7 只顯示大型機場，加入 viewport 篩選避免效能問題

### 航班時間窗口過濾
照片歸屬判定改用**航班時間**（不依賴 GPS bbox）：
- 從 `flights.outbound` 解析抵達時間（`➔` 後的 HH:MM）
- 從 `flights.inbound` 解析離境時間（`➔` 前的 HH:MM）
- 結合 `dateStart`/`dateEnd` 生成完整 datetime window
- 照片時間在 `[arrival_time, departure_time]` 區間內 → 屬於此行程
- 兩邊都是目的地當地時間，與 EXIF 當地時間一致，無需時區轉換

### 未來新增行程處理
完成新旅行後，用 `enrich_gps.py --trip <新行程ID>` 即可重建實際路線，無需修改 `index.html`。

### 🏞️ 實際景點與規劃落差 enrichment

已有 GPS 快取的行程可使用本地腳本補上 OpenStreetMap 景點：
```bash
python3 scripts/enrich-attractions.py --trip <id> --apply
python3 scripts/enrich-attractions.py --all --apply
```

- 腳本先讀取 `trips/gps-cache/`，再以每日照片停留群組查詢 Overpass；查詢結果快取在未納入版本控制的 `trips/osm-cache/`。
- 行程 JSON 的 `actualDays.dayN.attractions` 會保存 OSM 來源、座標、照片數量與 `visited`、`planned_not_visited`、`unplanned_visited` 狀態。
- `actualDays.dayN.source = "planned"` 不會被當成實際 GPS 證據；只有照片 GPS 或真實 enrichment 停留點能判定已造訪。
- 查詢前應確認照片 GPS 可送至外部 OSM 服務；若不允許外傳，先使用既有 OSM 快取或離線資料，不要在頁面即時查詢。

### NAS GPS 資料匯出
若有需要批次查詢 NAS 上所有照片的 GPS 資料，可使用：
```bash
# 1. 先建立 SSH 通道（輸入 DSM 密碼）
ssh -M -S ~/.ssh/nas.control -o ControlPersist=2h alienchang@192.168.1.100

# 2. 執行匯出腳本（再次輸入 DSM 密碼）
bash scripts/export-nas-gps.sh
```
匯出的 CSV 包含 72,263 筆照片的 GPS 座標、拍攝時間、地名與使用者資訊。

---

## 🛠️ 驗證與測試方式

- **無自動化測試**：專案不包含 Jest、Playwright 等預設測試框架。
- **本機預覽與調試**：
  1. 請勿嘗試執行 `npm run dev` 或 `npm install`。
  2. 使用簡單的靜態伺服器在本機啟動，例如：
     ```bash
     python3 -m http.server 8000
     ```
     或使用 `npx serve .`。
  3. 啟動後在瀏覽器開啟 `http://localhost:8000` 以進行 UI/UX 功能驗證。
- **UI/UX 修改準則**：請保持與現有 Tailwind 樣式及和風/商務配色的視覺一致性。

---

## ⚠️ 開發注意事項與限制

1. **修改 HTML 時**：由於是單一 HTML 檔案內含完整 CSS/JS，修改程式碼時請注意標籤閉合，避免語法錯誤導致整頁渲染失效。
2. **JSON 語法**：`trips/*.json` 使用嚴格 JSON 格式（無 trailing comma、鍵名需雙引號），否則 fetch 會解析失敗。
3. **新增行程流程**：建立 `trips/{id}.json` → 將 ID 加入 `trips/manifest.json` → 重載首頁即可看到新卡片（無需修改 `index.html`）。
4. **不要隨意引入打包工具**：除非使用者明確要求，否則請保持靜態檔案架構，不要新增 webpack, vite 等打包鏈。
