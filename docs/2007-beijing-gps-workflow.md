# 2007 北京出差照片 GPS 建置紀錄

## 範圍

- 日期：2007-11-03 至 2007-11-13
- NAS 原稿：`/photo` 下三個來源父目錄
- 本機工作區：`/private/tmp/travel-beijing-2007-11-audit/local-copies`
- NAS 輸出：`/photo/GPS_enriched_2007-11/`

## 處理流程

1. 以 ExifTool 與目錄證據建立 736 張候選清單。
2. 先複製到本機，再在本機副本寫入 `GPSLatitude`、`GPSLongitude`、`GPSHPositioningError` 與人工辨識描述；NAS 原稿不直接修改。
3. 734 張成功寫入；CIMG3374、CIMG3434 為損壞 JPEG，保留未修改副本。
4. 將本機輸出複製到 NAS 新資料夾，確認 Synology DSM「控制台 → 索引服務 → 媒體索引」的 `photo` 已完成索引，並在 Synology Photos 地圖模式確認縮圖可見。
5. 地圖確認後，納入證據清單的 771 個原稿檔案移至 `/photo/北京出差原稿_待確認/`，保留完整相對路徑與 `quarantine-manifest.tsv`，未永久刪除；本機副本與雜湊清單保留。

## 證據分級

- 明確：照片文字、使用者確認（清華大學銀杏、胡同、全聚德）、景點目錄名稱。
- 推定：同一時間序列附近照片，GPS 誤差以 `GPSHPositioningError` 記錄。
- 例外：損壞 JPEG 不強行重建。
