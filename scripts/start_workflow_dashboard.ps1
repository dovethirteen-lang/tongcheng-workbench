$dashboardRoot = Join-Path $PSScriptRoot "..\\08_dashboard"
$dashboardRoot = (Resolve-Path $dashboardRoot).Path
$port = 4389
$url = "http://127.0.0.1:$port/workflow_overview.html"

Write-Host "Starting workflow dashboard at $url"

$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python launcher 'py' not found."
}

Start-Process -FilePath "py" -ArgumentList "-m", "http.server", "$port", "--bind", "127.0.0.1" -WorkingDirectory $dashboardRoot
Start-Sleep -Seconds 2
Start-Process $url
