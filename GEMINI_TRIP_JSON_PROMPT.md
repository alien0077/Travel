# Gemini Trip JSON Generator Prompt

## 用途
讓 Google Gemini 直接產出符合我們網站 schema 的完整行程 JSON 檔案。產出後直接存到 `trips/` 目錄即可自動匯入。

---

## Prompt 模板

```
你是一個日本旅行規劃助手。請根據我的行程資訊，產出一個完整符合我們網站 schema 的 JSON 檔案。

## 網站 JSON Schema

每個行程一個 JSON 檔，結構如下：

```json
{
  "id": "行程ID（也是檔名，如 2026-shikoku）",
  "type": "city 或 drive（自駕用 drive）",
  "title": "行程標題",
  "subtitle": "副標題",
  "badge": "英文徽章文字",
  "badgeIcon": "FontAwesome 圖示（如 fa-car-side）",
  "description": "簡短描述",
  "stats": ["統計標籤1", "統計標籤2"],
  "image": "圖片 CSS class 名稱",
  "prefectures": ["都道府縣代碼陣列"],
  "airports": ["機場 IATA 代碼"],
  "dateStart": "YYYY-MM-DD",
  "dateEnd": "YYYY-MM-DD",
  "countdownDate": "YYYY/MM/DD HH:MM:SS",
  "jpyToTwdRate": 0.22,
  "actionText": "頂部按鈕文字",
  "flights": {
    "outbound": "去程航班資訊",
    "inbound": "回程航班資訊"
  },
  "vjw": {
    "zip": "郵遞區號",
    "address": "地址",
    "name": "住宿名稱"
  },
  "sightsList": [
    { "id": "景點ID", "name": "景點名稱", "day": "day1" }
  ],
  "defaultExpenses": [
    { "id": "費用ID", "name": "項目名稱", "amount": 金額 }
  ],
  "days": {
    "day1": {
      "date": "M/D (曜日)",
      "title": "當天主題",
      "timeRange": "開始時間 - 結束時間",
      "route": [[x1,y1], [x2,y2], ...],
      "timeline": [
        {
          "type": "transport 或 act 或 drive",
          "time": "時間範圍",
          "title": "標題",
          "detail": "詳細說明",
          "mapUrl": "Google Maps 連結（可選）",
          "mapcode": "MAPCODE（可選）"
        }
      ],
      "food": [
        {
          "meal": "早餐/午餐/晚餐/宵夜",
          "name": "餐廳名稱",
          "detail": "詳細說明",
          "mapcode": "MAPCODE（可選）"
        }
      ],
      "parking": [
        {
          "name": "停車場名稱",
          "detail": "詳細說明",
          "mapcode": "MAPCODE（可選）"
        }
      ],
      "hotel": {
        "name": "飯店名稱",
        "detail": "詳細說明",
        "mapcode": "MAPCODE（可選）"
      },
      "details": "當天注意事項"
    }
  }
}
```

## 地圖座標系統

我們使用 SVG 地圖，座標系統如下（viewport 空間）：
- 地圖大小：1000 x 1000
- 北方在上，東方在右

### 四國都道府縣標籤位置
- 香川 (Kagawa): (416, 664)
- 徳島 (Tokushima): (431, 700)
- 愛媛 (Ehime): (328, 722)
- 高知 (Kochi): (369, 751)

### 其他參考點
- 大阪: (460, 618)
- 和歌山: (420, 650)
- 岡山: (430, 640)
- 広島: (400, 635)
- 福岡: (240, 670)

### 都道府縣代碼對照
香川=37, 徳島=36, 愛媛=38, 高知=39, 大阪=27, 兵庫=28, 岡山=33, 広島=34, 福岡=40

## Route 座標要求

1. **每個 route 必須是真實地理位置**，不能是隨機座標
2. **使用已知的標籤/地點座標**作為參考點
3. **在已知座標之間加入 3-5 個 waypoints**，讓路線更自然
4. **確保每天的起點接續前一天的終點**
5. **路線要符合實際道路走向**
6. **🚨 座標產出後必須用 SVG hit-test (`isPointInFill`) 驗證** — 標籤位置可能不在縣 polygon 內。詳見 SKILL.md。

### ⚠️ 重要：標籤位置 ≠ 地理邊界
都道府縣的 SVG 標籤是為可讀性擺放的，**不一定在實際 polygon 內部**！
例如高知標籤 (369,751) 經過踩點測試是 ❌ 島外。
所有 route 座標**必須**在瀏覽器用 hit-test 驗證後才能定案。

### 四國自駕路線走向
- 高松→徳島：往東南走（y↑）
- 徳島→松山：往西走（x↓）
- 松山→宇和島：往南走（y↑）
- 宇和島→四萬十：往東南走（x↑, y↑）
- 四萬十→高知：往東北走（x↑, y↓）
- 高知→徳島：往東北走（x↑, y↓，經鳴門）
- 徳島→高松：往北走（y↓）

### 已知有效座標參考（經 hit-test 驗證）
```
香川: x:384-449, y:637-685
徳島: x:390-472, y:666-729
愛媛: x:263-392, y:656-781（西南狹窄：僅 x:292-301,y:743）
高知: x:301-437, y:697-770（注意 y>770 幾乎全在海裡）
```

## 你的任務

請根據我提供的行程資訊，產出完整的 JSON 檔案內容。我會直接把這個 JSON 存到 trips/{id}.json。

## 我的行程資訊

[在這裡貼上你的行程，例如：]

目的地：四國
日期：2026/8/6 - 8/13（共8天7夜）
交通：自駕（高松進出）
航班：
- 去程：JX300 | 台中 11:20 → 14:20 高松
- 回程：JX301 | 高松 13:20 → 16:30 台中

住宿：
- Day 1-2: REF 松山市站
- Day 3: Nakamura Daiichi Hotel（四萬十川）
- Day 4-5: Dormy Inn Kochi + hotelLUANA（分流）
- Day 6: Guest House CYCLE&STAY（德島）
- Day 7-8: GRAND BASE Takamatsu

每日行程：
Day 1: 高松機場取車 → 丸龜城 → 高松市區
Day 2: 高松朝烏龍 → 德島脇町古街 → 松山城
Day 3: 下灘站 → 宇和島城 → 雲之上圖書館 → 四萬十川
Day 4: 高知日曜市 → 桂濱 → 夜來祭前夜祭
Day 5: 高知城 → 夜來祭本祭 → 分流
Day 6: 高知北上 → 鳴門大橋 → 德島
Day 7: AEON大採購 → 阿波舞本祭 → 回高松
Day 8: 栗林公園 → 還車 → 機場

請產出完整 JSON。
```

---

## 使用步驟

### 步驟 1：複製 Prompt
複製上面的完整 prompt（包含 schema 定義和座標系統）。

### 步驟 2：貼到 Google Gemini
把 prompt 貼到 Google Gemini。

### 步驟 3：修改行程資訊
修改「我的行程資訊」部分為你自己的行程內容。

### 步驟 4：取得 JSON
Gemini 會產出完整的 JSON 檔案內容。

### 步驟 5：存檔匯入
1. 把 JSON 內容存到 `trips/{行程ID}.json`
2. 把行程 ID 加入 `trips/manifest.json`
3. 重載首頁即可看到新卡片

### 步驟 6：視覺化驗證
在瀏覽器中載入 `viewer.html?trip={行程ID}`，檢查路線是否合理。

---

## 範例輸出

```json
{
  "id": "2026-shikoku",
  "type": "drive",
  "title": "四國夏祭典自駕",
  "subtitle": "8/6 - 8/13 現存天守 × MAPCODE × 停車死線",
  "badge": "Shikoku Road Trip",
  "badgeIcon": "fa-car-side",
  "description": "現存天守、MAPCODE、停車死線與祭典管制提醒，為八天自駕路線整理成一頁掌握。",
  "stats": ["8天7夜", "高松進出", "停車特化"],
  "image": "shikoku",
  "prefectures": ["37", "36", "38", "39"],
  "airports": ["TAK"],
  "dateStart": "2026-08-06",
  "dateEnd": "2026-08-13",
  "countdownDate": "2026/08/06 11:20:00",
  "jpyToTwdRate": 0.22,
  "actionText": "祭典資訊",
  "flights": {
    "outbound": "去程：JX300 | 台中 11:20 ➔ 14:20 高松",
    "inbound": "回程：JX301 | 高松 13:20 ➔ 16:30 台中"
  },
  "vjw": {
    "zip": "760-0011",
    "address": "香川県高松市浜ノ町 X-XX-X",
    "name": "GRAND BASE Takamatsu"
  },
  "days": {
    "day1": {
      "date": "8/6 (四)",
      "title": "啟航香川 ➔ 機場取車 ➔ 完攻丸龜城",
      "timeRange": "12:20pm - 07:00pm",
      "route": [[420,658], [415,656], [408,655], [400,655], [408,657], [416,661]],
      "timeline": [
        {
          "type": "act",
          "time": "12:20pm",
          "title": "降落高松機場",
          "detail": "🛬 星宇航空 JX300 降落高松機場。全家辦理出境。"
        }
      ],
      "food": [
        {
          "meal": "午餐",
          "name": "星宇航空精緻機上餐",
          "detail": "空中巴士 A321NEO 專屬美味餐食"
        }
      ],
      "parking": [],
      "hotel": {
        "name": "GRAND BASE Takamatsu",
        "detail": "無人自助 Check-in，附停車位。"
      },
      "details": "首日取車熟悉日本右駕。"
    }
  }
}
```

---

## 注意事項

1. **Gemini 可能會產出不完整的 JSON**，請手動檢查所有欄位
2. **Route 座標必須是數字陣列**，不能是字串
3. **確保 JSON 格式正確**（無 trailing comma、鍵名需雙引號）
4. **都道府縣代碼是字串**（如 "37" 不是 37）
5. **最終結果建議在瀏覽器中視覺化驗證**
