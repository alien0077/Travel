#!/bin/bash
# export-nas-gps.sh — 從 Synology NAS synofoto PostgreSQL 匯出 GPS 照片資料
#
# 用法:
#   bash scripts/export-nas-gps.sh
#
# 事前準備:
#   1. DSM 控制台 → 終端機與 SNMP → 啟用 SSH
#   2. 先執行一次以下指令建立 SSH 通道（輸入密碼後保持背景）:
#      ssh -M -S ~/.ssh/nas.control \
#        -o ControlPersist=2h \
#        -o StrictHostKeyChecking=accept-new \
#        alienchang@Alien_NAS
#
#   若用 IP:
#      ssh -M -S ~/.ssh/nas.control \
#        -o ControlPersist=2h \
#        alienchang@192.168.1.100
#
# 輸出: ~/Desktop/synology_photo_gps.csv
#
# 安全規則:
#   - 密碼僅存在記憶體變數中，不寫入檔案或聊天
#   - 全程唯讀 SELECT，不修改 NAS 任何資料
#   - 清理暫存 SQL 檔案

set -e

NAS_HOST="alienchang@192.168.1.100"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="$HOME/Desktop/synology_photo_gps.csv"
CONTROL_SOCKET="$HOME/.ssh/nas.control"

# 檢查 SSH ControlMaster 通道
if [ ! -S "$CONTROL_SOCKET" ]; then
    echo "SSH 通道不存在。請先執行："
    echo "  ssh -M -S $CONTROL_SOCKET -o ControlPersist=2h $NAS_HOST"
    exit 1
fi

# 檢查 NAS 是否可連
if ! ssh -S "$CONTROL_SOCKET" -o ConnectTimeout=5 "$NAS_HOST" "echo ok" > /dev/null 2>&1; then
    echo "NAS 連線失敗，請重新建立 SSH 通道"
    exit 1
fi

# 取得密碼（唯讀記憶體，不寫入檔案）
read -s -p "DSM Password: " P
echo ""

SSH_CMD="ssh -S $CONTROL_SOCKET $NAS_HOST"

SQL="\\copy (SELECT u.id AS photo_id, ui.name AS owner, u.filename, to_timestamp(u.takentime) AS taken_time, m.latitude, m.longitude, gi.country, gi.first_level, gi.second_level FROM unit u JOIN metadata m ON m.id_unit=u.id LEFT JOIN user_info ui ON ui.id=u.id_user LEFT JOIN geocoding g ON g.id=u.id_geocoding LEFT JOIN geocoding_info gi ON gi.id_geocoding=g.id AND gi.lang=0 WHERE m.latitude IS NOT NULL AND m.longitude IS NOT NULL ORDER BY u.takentime) TO '/tmp/synology_photo_gps.csv' WITH CSV HEADER;"

echo "寫入 SQL 至 NAS..."
{ printf '%s\n' "$P"; printf '%s\n' "$SQL"; } | $SSH_CMD "sudo -S tee /tmp/export_gps.sql > /dev/null" 2>/dev/null

echo "執行 GPS 匯出..."
printf '%s\n' "$P" | $SSH_CMD "sudo -S su - postgres -c 'psql -d synofoto -f /tmp/export_gps.sql'" 2>/dev/null

echo "複製 CSV 至本機..."
printf '%s\n' "$P" | $SSH_CMD "sudo -S cat /tmp/synology_photo_gps.csv" > "$OUTPUT" 2>/dev/null

echo "清理 NAS 暫存檔..."
printf '%s\n' "$P" | $SSH_CMD "sudo -S rm -f /tmp/export_gps.sql /tmp/synology_photo_gps.csv" 2>/dev/null

unset P

ROWS=$(wc -l < "$OUTPUT")
echo "完成！匯出 $((ROWS - 1)) 筆 GPS 資料"
echo "輸出: $OUTPUT"
