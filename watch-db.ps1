# Live view of data/comments.db - refreshes every 10 seconds. Ctrl+C to stop.
$docker = "docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
}

$query = @'
import sqlite3
c = sqlite3.connect("/data/comments.db")
total = c.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
trades = c.execute("SELECT COUNT(*) FROM comments WHERE prediction = 1").fetchone()[0]
print(f"{total} comments stored | {trades} predicted trades")
print()
print("=== latest 10 comments ===")
for r in c.execute("SELECT processed_at, id, stock, price, option_type, formatted_date, prediction, substr(replace(body, char(10), ' '), 1, 60) FROM comments ORDER BY processed_at DESC LIMIT 10"):
    print(r)
print()
print("=== latest 5 predicted trades ===")
for r in c.execute("SELECT processed_at, stock, price, option_type, formatted_date, substr(replace(body, char(10), ' '), 1, 60) FROM comments WHERE prediction = 1 ORDER BY processed_at DESC LIMIT 5"):
    print(r)
'@

while ($true) {
    $out = $query | & $docker compose exec -T comment-processor python -
    Clear-Host
    Write-Host "comments.db - $(Get-Date -Format 'HH:mm:ss') (refreshes every 10s, Ctrl+C to stop)" -ForegroundColor Cyan
    $out
    Start-Sleep -Seconds 10
}
