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
- **部署平台**：使用 GitHub Pages 部署，透過 `.github/workflows/deploy-pages.yml` 在 `main` push 後直接發布根目錄，無任何 build command。

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
