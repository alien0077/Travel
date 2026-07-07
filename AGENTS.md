# AGENTS.md

此專案是為 Chang 家族設計的 **2026 日本親子旅行入口網站** 與互動式行程手冊。為了讓未來的 AI 協作代理人（Agents）能快速上手並避免常規誤判，請遵循以下開發與維護指南：

## 🚀 專案本質與架構 (不看會猜錯的部分)

- **純靜態前端專案**：本專案**沒有** Node.js/npm 依賴（無 `package.json`），也沒有任何後端服務或編譯打包步驟。
- **進入點 (Entry Point)**：
  - `index.html`：整合兩段行程的入口首頁。
  - `2026_0705__0708東京快閃.html`：東京 4 天 3 夜親子冒險互動手冊。
  - `2026_0806__0813四國遊.html`：四國 8 天 7 夜自駕與祭典特化手冊。
  - `template.html`：**通用旅遊行程範本網頁**，支援自駕/非自駕模式切換。
- **外部依賴 (CDN)**：全部使用 CDN 載入，包含：
  - Tailwind CSS (`https://cdn.tailwindcss.com`)
  - FontAwesome 圖標
  - Chart.js (`https://cdn.jsdelivr.net/npm/chart.js`，僅四國遊頁面使用)
- **狀態管理與持久化**：
  - 頁面上的互動狀態（分頁、景點打卡、隨手筆記、記帳明細）皆透過瀏覽器 `localStorage` 進行讀寫與持久化（東京頁面命名空間為 `tokyo-2026-guide`，範本頁面則由 `tripConfig.appId` 動態指定）。
  - 東京頁面的記帳功能含有硬編碼的日幣換台幣匯率 `JPY_TO_TWD = 0.22`。
- **部署平台**：使用 Netlify 部署，`netlify.toml` 設定為發布根目錄 (`publish = "."`)，無 any build command。

---

## 🗺️ 範本樣式框架 (Travel Template Framework)

專案中包含一個通用範本網頁 `template.html`。此範本為**資料驅動 (Data-Driven)** 架構，所有行程資訊均由檔案底部的 `tripConfig` 物件所控制。

### JSON 設定結構 (`tripConfig` 規格)
當需要新增旅遊行程表時，未來的代理人只需複製 `template.html`，並用新的行程資訊替換 `tripConfig` 物件。規格如下：

```javascript
const tripConfig = {
    appId: 'travel-template-2026',        // LocalStorage 儲存命名空間 (每個行程需唯一)
    tripType: 'city',                     // 模式：'city' (市區/記帳/打卡) 或 'drive' (自駕/MAPCODE/隱藏記帳)
    jpyToTwdRate: 0.22,                   // 日幣兌台幣匯率 (非自駕模式下記帳用)
    countdownDate: '2026/07/05 08:05:00', // 倒數計時目標時間
    title: 'TRAVEL NAVI 2026',            // 頁面主標題
    subtitle: '日式親子旅行互動手冊',      // 頁面副標題
    actionText: 'VJW / 工具',             // 頂部按鈕名稱
    
    // 航班資訊
    flights: {
        outbound: '去程：FD234 | 高雄 08:05 ➔ 12:55 成田',
        inbound: '回程：FD235 | 成田 13:55 ➔ 17:05 高雄'
    },
    
    // Visit Japan Web 填寫對照資料
    vjw: {
        zip: '110-0015',
        address: '東京都台東区東上野 X-XX-X',
        name: 'Ostay Ueno Hotel'
    },
    
    // 景點解鎖清單 (僅市區模式或有設定時顯示)
    sightsList: [
        { id: 'sight1', name: '🎮 Day 1: 台場一丁目商店街', day: 'day1' }
    ],
    
    // 預設記帳項目 (選填)
    defaultExpenses: [
        { id: 1, name: '🏩 預留住宿費用', amount: 98000 }
    ],
    
    // 每日詳細行程資料
    days: {
        day1: {
            label: 'Day 1',
            date: '7/5 (日)',
            title: '抵達東京與台場夜景',
            timeRange: '12:55pm - 09:30pm',
            
            // 每日時間軸事件
            timeline: [
                {
                    type: 'transport', // 類型：'transport' (非自駕大眾交通) 或 'act' (景點/活動)
                    time: '12:55pm - 14:30pm',
                    title: '成田機場 ➔ 上野京成電鐵 (大眾交通)',
                    detail: '搭乘 Skyliner 42 號直達日暮里/上野。請先在櫃檯購票。',
                    mapUrl: 'https://maps.app.goo.gl/...', // Google Map 連結 (選填)
                    mapcode: '12 345 678*90'               // Mapcode (自駕模式選填)
                }
            ],
            
            // 每日美食補給
            food: [
                {
                    meal: '晚餐 (18:00)',
                    name: '名代宇奈とと 鰻魚飯',
                    detail: '上野平價高 CP 值鰻魚飯。',
                    mapUrl: 'https://maps.app.goo.gl/...',
                    mapcode: '12 345 678*90'
                }
            ],
            
            // 建議停車場 (自駕模式選填，非自駕模式不渲染)
            parking: [
                {
                    name: '上野中央地下停車場',
                    detail: '寬敞好停。',
                    mapUrl: 'https://maps.app.goo.gl/...',
                    mapcode: '12 345 678*90'
                }
            ],
            
            // 每日住宿飯店
            hotel: {
                name: 'Ostay Ueno Hotel',
                detail: '靠近上野站，出入非常方便。',
                mapUrl: 'https://maps.app.goo.gl/...',
                mapcode: '12 345 678*90' // 飯店 Mapcode (自駕與非自駕皆選填)
            },
            
            details: '首日抵達請先在京成電鐵櫃檯加值 Suica 卡。' // 備註警告欄位 (選填)
        }
    }
};
```

### 未來代理人生成新行程表的 Prompt 範本
當需要新增行程表網頁時，可以直接使用以下 Prompt 指令：
```markdown
請根據專案中的 `template.html` 做為範本，為我新增一個名為 `2026_XXXX__XXXX_OO遊.html` 的旅遊手冊網頁。
讀取我提供的旅遊資訊後：
1. 將行程資訊（時間軸、美食、停車場、飯店、VJW 資訊、航班等）正確地對照並填入 `tripConfig` 中。
2. 確保每個景點、美食餐廳、飯店以及停車場都附上對應的 `mapUrl` (Google Maps 連結)。
3. 如果是自駕行程（請將 `tripType` 設為 `'drive'`），請務必在飯店、景點及停車場加入 `mapcode`；如果是大眾交通，請將 `tripType` 設為 `'city'`，並於時間軸 of 交通事件中將 `type` 設為 `'transport'` 以標明大眾交通工具。
4. 在入口網頁 `index.html` 的 `trip-grid` 行程卡清單中，為這個新行程加上專屬的入口卡片，維持樣式一致。
```

---

## 🗂️ 首頁行程分類指引 (index.html Layout Rules)

為防止首頁（`index.html`）隨著年份與行程增加而過度拉長，首頁採用**最新行程大圖卡 + 歷史行程收納區**的劃分規則：
1. **最新/當年度行程**：使用大型背景圖卡（類別為 `.trip-card`，放置於 `.trip-grid` 內），享有最主要的視覺焦點。
2. **過往/歷史行程**：使用簡潔的橫向歷史書籤卡片（類別為 `.archive-card`，放置於 `.archive-grid` 內），收納在「歷年足跡回顧」區塊，只呈現年份、名稱與天數，不加背景圖，以避免佔用過多頁面空間。

---

## 🗺️ 日本制霸地圖 (Japan Prefecture Conquest Map)

首頁 `index.html` 下方內嵌了一個基於 Geolonia 向量路徑的**日本制霸地圖**，支援自動同步與手動修改狀態：
1. **自動規劃判定**：JS 中的 `PLANNED_CODES` 陣列包含當前所有規劃行程涉及的都道府縣代碼（例如千葉、東京、香川、德島、愛媛、高知）。這些地區預設會標記為「規劃中」（藍色）。
2. **手動點擊切換**：使用者可點擊地圖上的都道府縣來切換狀態（未訪 `#e2e8f0` -> 已去過 `#10b981` -> 想去 `#f59e0b` -> 未訪）。
3. **資料持久化**：使用者的手動狀態儲存於 `localStorage` 的 `japan-conquest-map-states` 中，並可透過「重設手動修改」按鈕清除重算。
4. **機場進出足跡 (Airports Visited)**：地圖控制面板下方設有主要機場進出狀態標籤。根據行程航班，成田機場 (NRT) 與高松機場 (TAK) 會自動標記為藍色「規劃進出」狀態；其餘機場（如羽田、關西、福岡、新千歲等）允許點擊手動切換為綠色「已進出」狀態，資料儲存於 `localStorage` 的 `japan-conquest-airports` 中。所有機場標示（含 35 座國內外主要機場）以圓點 + IATA 代碼形式直接標註在地圖上，點擊即可切換灰（未進出）/ 藍（規劃進出）/ 綠（已進出）狀態。
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

1. **修改 HTML 時**：由於是單一 HTML 檔案內含完整 CSS/JS，修改程式碼時請注意標籤閉合，尤其是大段的 `tripData` JSON 物件，避免語法錯誤導致整頁渲染失效。
2. **匯率與時間**：倒數計時器及記帳匯率皆為靜態設定。若有調整需求需直接修改 JS 常數。
3. **不要隨意引入打包工具**：除非使用者明確要求，否則請保持單一 HTML 靜態架喚，不要新增 webpack, vite 等繁雜的打包鏈。
