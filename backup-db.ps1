# Backs up data/comments.db to data/backups/, keeping the 14 most recent copies.
# Uses SQLite's online backup (via python) so a mid-write copy can't corrupt.
$dataDir = Join-Path $PSScriptRoot "data"
$backupDir = Join-Path $dataDir "backups"
$db = Join-Path $dataDir "comments.db"
if (-not (Test-Path $db)) { exit 0 }
New-Item -ItemType Directory -Force $backupDir | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd"
$dest = Join-Path $backupDir "comments-$stamp.db"
& "C:\Users\Kendall Eberly\miniconda3\python.exe" -c "import sqlite3; src = sqlite3.connect(r'$db'); dst = sqlite3.connect(r'$dest'); src.backup(dst); dst.close(); src.close(); print('backed up to', r'$dest')"

# prune old backups beyond the newest 14
Get-ChildItem $backupDir -Filter "comments-*.db" | Sort-Object Name -Descending | Select-Object -Skip 14 | Remove-Item -Force
