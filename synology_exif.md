# Synology Photos GPS EXIF 調查報告

**日期**: 2026-07-25  
**NAS**: Alien_NAS (192.168.1.100) | DS224+ | DSM 7.3.2  
**工具**: SSH ControlMaster、exiv2、PostgreSQL (synofoto)

---

## 背景

舊 iPhone（2018 年以前）拍攝的純 JPG 照片，經 Synology Photos 匯入後，原始檔案的 EXIF GPS 資料可能被清除（只剩地名，無經緯度座標）。此調查旨在確認：

1. 原始 JPG 檔案的 GPS EXIF 是否仍存在
2. Synology Photos 的 PostgreSQL 資料庫是否保留了 GPS 座標
3. 是否可從資料庫批次匯出 GPS 資料

---

## 測試照片

| 項目 | 值 |
|------|-----|
| 檔案 | `/volume1/photo/MobileBackup/iPhone/2018/09/IMG_4106.JPG` |
| 尺寸 | 2,405,155 bytes |
| 拍攝時間 | 2018-09-23 09:20:46 |
| 類型 | 純 JPG（無 HEIC 版本） |
| 所在目錄 | MobileBackup（原始備份，未匯入 Synology Photos） |

---

## 發現 1：原始 JPG 仍有完整 EXIF GPS

使用 `exiv2` 檢查 IMG_4106.JPG，結果顯示**所有 GPS 欄位完整**：

```
Exif.GPSInfo.GPSLatitudeRef       North
Exif.GPSInfo.GPSLatitude          25deg 6' 41"
Exif.GPSInfo.GPSLongitudeRef      East
Exif.GPSInfo.GPSLongitude         121deg 50' 54"
Exif.GPSInfo.GPSAltitudeRef       Above sea level
Exif.GPSInfo.GPSAltitude          325.5 m
Exif.GPSInfo.GPSTimeStamp         01:20:46.0
Exif.GPSInfo.GPSDateStamp         2018:09:23
Exif.GPSInfo.GPSHPositioningError 5 m
```

**結論**: MobileBackup 目錄下的原始 JPG 檔案，GPS 資料**沒有被清除**。

---

## 發現 2：synofoto 資料庫結構

`synofoto` PostgreSQL 資料庫存在 (Owner: SynologyPhotos)。

### GPS 座標存放位置

**`metadata` 表** — 實際 GPS 座標（double precision）：

| Column | Type | 說明 |
|--------|------|------|
| `id_unit` | integer | FK → `unit.id` |
| `latitude` | double precision | 緯度 |
| `longitude` | double precision | 經度 |
| `orientation`, `camera`, `focal_length` | ... | 其他 EXIF 資訊 |

**`unit` 表** — 照片索引（核心表）：

| Column | Type | 說明 |
|--------|------|------|
| `id` | integer | PK |
| `id_user` | integer | FK → `user_info.id` |
| `filename` | text | 檔名 |
| `id_folder` | integer | FK → `folder.id` |
| `id_geocoding` | integer | FK → `geocoding.id`（反向地理編碼） |
| `takentime` | bigint | 拍攝時間戳 |
| `filesize` | bigint | 檔案大小 |

### 反向地理編碼（地名）

- `geocoding` 表：`level_1` ~ `level_6` → `administrative` 表
- `geocoding_info` 表：`country`、`first_level`、`second_level`（可讀地名，含語系）

### 完整 JOIN 路徑

```sql
SELECT
  u.filename,
  f.name AS folder_name,
  ui.name AS owner,
  m.latitude,
  m.longitude,
  gi.country,
  gi.first_level,
  gi.second_level
FROM unit u
JOIN metadata m ON m.id_unit = u.id
LEFT JOIN folder f ON f.id = u.id_folder
LEFT JOIN user_info ui ON ui.id = u.id_user
LEFT JOIN geocoding g ON g.id = u.id_geocoding
LEFT JOIN geocoding_info gi ON gi.id_geocoding = g.id
```

---

## 發現 3：MobileBackup vs PhotoLibrary

| 路徑 | 類型 | 是否在 synofoto DB | GPS 來源 |
|------|------|-------------------|----------|
| `/volume1/photo/MobileBackup/` | 原始手機備份 | ❌ 未匯入 | 僅原始 EXIF |
| `/volume1/photo/PhotoLibrary/` | Synology Photos 管理 | ✅ 有索引 | DB metadata + 原始 EXIF |
| `/volume1/photo/Other_Picture/` | 手動上傳 | 不一定 | 依設定 |
| `/volume1/homes/*/Photos/` | 個人空間 | ✅ 有索引 | DB metadata + 原始 EXIF |

**關鍵**: 被 Synology Photos 匯入的照片，GPS 同時存在於：
1. 原始檔案 EXIF（可能被清除）
2. `synofoto.metadata` 表（`latitude` + `longitude`）

若 Synology Photos 清除了原始檔案的 EXIF GPS，**資料庫仍然保留座標**。

---

## 結論

1. **JPG 原始 GPS EXIF → 在 MobileBackup 中仍完好**，NAS 沒有主動刪除非索引路徑的 EXIF。
2. **synofoto DB 有完整 GPS → `metadata.latitude` / `longitude`** 即使原始檔 EXIF 被清除，座標仍在資料庫。
3. **可批次匯出** → 使用 SQL JOIN 即可產出含完整 GPS 的 CSV。
4. **MobileBackup 的照片**：GPS 只存在原始檔 EXIF，不在資料庫中。

---

---

## 實際路線補完結果

### enrich_gps.py 修改

修改 `enrich_gps.py` 支援 JPG（原僅 HEIC）：

| 修改項目 | 原內容 | 新內容 |
|---------|--------|--------|
| 副檔名過濾 | `.HEIC`, `.HEIF` | `.HEIC`, `.HEIF`, `.JPG`, `.JPEG` |
| 變數命名 | `heic_files` | `photo_files` |
| 提示文字 | *HEIC 照片* | *照片* |

### 各旅程補完狀態

| 旅程 | 日期 | 補完結果 |
|------|------|---------|
| **2018-kitakyushu** | 2018-06 | ✅ **8 天全覆蓋**：6 停留點、37 路線點（從 iphone6s 112-114APPLE Live Photo JPG 萃取） |
| **2019-fukuoka** | 2019-08 | ✅ **7 天全覆蓋**：18 停留點、131 路線點 |
| ~~**2024-minamikyushu**~~ | ~~2024-01~~ | ❌ 不存在旅程，已刪除（實為 2019-fukuoka） |

### CSV 匯出

- **來源**: `synofoto` PostgreSQL `metadata` 表（`latitude`、`longitude`）
- **筆數**: 72,263 張有 GPS 的照片
- **檔案**: `scripts/export-nas-gps.sh`（可重複使用的匯出腳本）
- **用法**: `bash scripts/export-nas-gps.sh`（需先建立 SSH 通道）
- **輸出**: `~/Desktop/synology_photo_gps.csv`
- **錯誤修正**: `takentime` 是 Unix seconds，不應除 1000

### 教訓

1. **舊 iPhone 純 JPG 照片**：如果經 Synology Photos 匯入，原始 EXIF GPS 可能被清除
2. **MobileBackup 原始備份**：未經 Synology Photos 處理的照片，GPS 仍完好
3. **資料庫備份**：`synofoto.metadata` 表保留 `latitude`/`longitude`，即使原始 EXIF 被清
4. **非 HEIC 無法復原**：一旦原始 EXIF 被清、DB 也無對應記錄，GPS 永久遺失
