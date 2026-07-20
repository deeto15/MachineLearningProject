# Opens a web UI for browsing data/comments.db at http://localhost:8001
# (Datasette, running natively on Windows - Docker port forwarding is broken
# under WSL mirrored networking mode on this machine). Ctrl+C to stop.
$db = Join-Path $PSScriptRoot "data\comments.db"
if (-not (Test-Path $db)) {
    Write-Host "No database yet at $db - start the stack first (docker compose up -d)"
    exit 1
}
Start-Process "http://localhost:8001/comments/comments?_sort_desc=processed_at"
& "C:\Users\Kendall Eberly\miniconda3\python.exe" -m datasette serve $db -p 8001 --setting sql_time_limit_ms 3000
