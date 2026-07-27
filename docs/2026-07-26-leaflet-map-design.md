# Leaflet 互動地圖設計文件

## 目標
將 `index.html` 首頁的靜態 Geolonia SVG 地圖替換為 Leaflet 互動式地圖，使用 OpenStreetMap 底圖，支援缩放至市區町村層級。

## 範圍
- **替換**：首頁「日本制霸足跡地圖」區塊
- **保留**：所有現有功能（都道府縣著色、機場標記、旅行路線、制霸等級）
- **新增**：缩放時自動顯示市區町村邊界（虛線）

---

## 1. 技術架構

### 依賴（CDN）
- Leaflet 1.9.x（CSS + JS）
- 無其他框架依賴

### 檔案結構
```
index.html          ← 修改：替換 SVG 區塊為 Leaflet 容器
trips/
  japan-prefectures.geojson   ← 新增：47 都道府縣邊界
  japan-cities.geojson        ← 新增：市區町村邊界（可按需分割）
```

### HTML 結構
```html
<div id="map-section">
  <div id="japan-map"></div>
  <!-- Overlay: 制霸等級 -->
  <div class="map-overlay conquest-level">...</div>
  <!-- Overlay: 圖例 -->
  <div class="map-overlay map-legend">...</div>
  <!-- Overlay: 重設按鈕 -->
  <div class="map-controls">...</div>
</div>
```

---

## 2. 地圖初始化

```js
const map = L.map('japan-map', {
  center: [36.5, 138.0],  // 日本中心
  zoom: 5,
  minZoom: 4,
  maxZoom: 14,
  zoomControl: false
});

// 底圖
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors',
  maxZoom: 19
}).addTo(map);

// zoom control 放右上角
L.control.zoom({ position: 'topright' }).addTo(map);
```

---

## 3. 都道府縣圖層（主要功能）

### GeoJSON 載入
```js
fetch('trips/japan-prefectures.geojson')
  .then(r => r.json())
  .then(data => {
    prefectureLayer = L.geoJSON(data, {
      style: prefectureStyle,
      onEachFeature: prefectureInteraction
    }).addTo(map);
  });
```

### 著色邏輯（對應現有 localStorage）
- `japan-conquest-map-states`：存各縣狀態
- 狀態：`unvisited`（灰）、`visited`（紅）、`planned`（藍）、`want`（黃）

```js
function prefectureStyle(feature) {
  const code = feature.properties.code;  // 二位數都道府縣代碼
  const state = getPrefectureState(code);
  return {
    fillColor: STATE_COLORS[state],
    weight: 1,
    opacity: 1,
    color: '#666',
    fillOpacity: 0.6
  };
}
```

### 點擊互動
```js
function prefectureInteraction(feature, layer) {
  layer.on('click', () => {
    const code = feature.properties.code;
    cyclePrefectureState(code);  // unvisited → visited → want → unvisited
    prefectureLayer.resetStyle();  // 重繪所有縣
    updateConquestLevel();
  });
}
```

---

## 4. 市區町村圖層（zoom in 顯示）

### 觸發條件
- zoom level ≥ 8 時載入並顯示
- zoom level < 8 時隱藏
- 使用 `map.on('zoomend', ...)` 監聽

### GeoJSON 處理
市區町村 GeoJSON 檔案很大（全日本 ~1,800 區），方案：

**方案 A：全量載入（簡單）**
- 一次載入全部市區町村
- 用 `L.geoJSON` 的 `filter` 功能只顯示目前視窗范围内的
- 優點：簡單、不需要額外處理
- 缺點：初始載入慢（檔案可能 5-10MB）

**方案 B：按縣分割（推薦）**
- 將 GeoJSON 按都道府縣代碼分割成 47 個小檔
- 只在 zoom in 到某縣時載入該縣的市區町村
- 優點：按需載入、速度快
- 缺點：需要管理 47 個檔案或用 API 動態載入

**方案 C：用 TopoJSON 縮減**
- 將 GeoJSON 轉為 TopoJSON（消除重複邊界）
- 檔案大小可縮減 60-80%
- 優點：檔案小、保留精度
- 缺點：需要額外處理庫

### 樣式
```js
function cityStyle(feature) {
  return {
    weight: 1,
    opacity: 0.7,
    color: '#999',
    dashArray: '5, 5',  // 虛線
    fillOpacity: 0,
    className: 'city-boundary'
  };
}
```

---

## 5. 機場標記

### 實現
```js
const AIRPORT_GPS = {
  'CTS': [42.775, 141.692], 'HKD': [41.77, 140.817], ...
};

Object.entries(AIRPORT_GPS).forEach(([code, [lat, lng]]) => {
  const marker = L.marker([lat, lng], {
    icon: L.divIcon({
      className: 'airport-marker',
      html: `<span class="airport-code">${code}</span>`,
      iconSize: [30, 20]
    })
  }).addTo(map);
  
  marker.on('click', () => {
    cycleAirportState(code);  // 切換進出狀態
    updateAirportIcon(marker, code);
  });
});
```

### 狀態存儲
- `japan-conquest-airports`：存各機場狀態
- 狀態：`unvisited`（灰）、`planned`（藍）、`visited`（綠）

---

## 6. 實際旅行路線

### 實現
```js
function drawTripRoutes(trips) {
  trips.forEach(trip => {
    if (!trip.actualDays) return;
    const color = trip.routeColor || '#EF4444';
    
    Object.values(trip.actualDays).forEach(day => {
      if (!day.route) return;
      const latlngs = day.route.map(([lat, lng]) => [lat, lng]);
      
      L.polyline(latlngs, {
        color: color,
        weight: 3,
        opacity: 0.8
      }).addTo(map);
    });
  });
}
```

---

## 7. 制霸等級 Overlay

### HTML 結構（保留現有）
```html
<div class="map-overlay conquest-level">
  <h3>⛩ 制霸等級：<span id="conquest-title">制霸達人</span></h3>
  <p id="conquest-desc">幾乎全日本都去過</p>
  <div class="progress-bar">
    <div id="conquest-fill" style="width: 96.7%"></div>
  </div>
  <p id="conquest-count">29 / 30 都道府縣已制霸（下一等級：傳說冒險家）</p>
</div>
```

### 計算邏輯（不變）
- 從 `japan-conquest-map-states` 讀取各縣狀態
- 計算已去過/規劃中的數量
- 更新等級標題、描述、進度條

---

## 8. CSS 樣式

### 地圖容器
```css
#map-section {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: 12px;
  overflow: hidden;
}

#japan-map {
  width: 100%;
  height: 100%;
}

/* Leaflet 覆寫 */
.leaflet-container {
  background: #f8f9fa;
  font-family: inherit;
}
```

### Overlay 定位
```css
.map-overlay {
  position: absolute;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.conquest-level {
  top: 16px;
  right: 16px;
  max-width: 280px;
}

.map-legend {
  bottom: 16px;
  right: 16px;
}
```

### 機場標記
```css
.airport-marker {
  background: transparent;
  border: none;
}

.airport-code {
  display: inline-block;
  padding: 2px 4px;
  background: #1e293b;
  color: #fff;
  border-radius: 3px;
  font-size: 9px;
  font-weight: bold;
  white-space: nowrap;
  cursor: pointer;
}

.airport-code.major {
  font-size: 11px;
  padding: 3px 6px;
}
```

---

## 9. 資料流

```
初始化流程：
1. 載入 Leaflet CDN
2. 初始化地圖
3. fetch trips/manifest.json → 取得所有行程 ID
4. 逐一 fetch trips/{id}.json → 取得行程資料
5. 載入 japan-prefectures.geojson → 繪製都道府縣
6. 從 localStorage 讀取狀態 → 著色
7. 繪製機場標記
8. 繪製旅行路線
9. 計算並顯示制霸等級

互動流程：
- 點擊都道府縣 → cycle 狀態 → 重繪 → 更新等級
- 點擊機場 → cycle 狀態 → 更新圖標
- zoom in → 載入市區町村 GeoJSON → 顯示虛線
- zoom out → 隱藏市區町村
- 重設按鈕 → 清除 localStorage → 重繪
```

---

## 10. 效能考量

| 問題 | 解決方案 |
|------|---------|
| 市區町村 GeoJSON 太大 | 方案 B：按縣分割，按需載入 |
| 重繪時閃爍 | 使用 `requestAnimationFrame` 節流 |
| 路線太多時卡頓 | 限制同時顯示的路線數量 |
| 初始載入慢 | 先顯示底圖+都道府縣，路線延後載入 |

---

## 11. 還沒解決的問題

1. **市區町村 GeoJSON 來源**：需要找到可靠的47縣市區町村邊界資料
2. **GeoJSON 檔案大小**：全日本市區町村可能 5-10MB，需要評估是否可接受
3. **zoom level 閾值**：8 是否適合開始顯示市區町村？
4. **機場 marker 在高 zoom 時的顯示**：是否需要在 zoom in 時改用更大的圖標？
