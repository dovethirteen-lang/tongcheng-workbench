$frontendRoot = Join-Path $PSScriptRoot "..\\09_feishu_frontend"
$frontendRoot = (Resolve-Path $frontendRoot).Path
$port = 4390
$url = "http://127.0.0.1:$port"

Write-Host "Rendering Feishu frontend data..."
py (Join-Path $PSScriptRoot "render_feishu_frontend.py")

Write-Host "Starting Feishu frontend at $url"
Start-Process -FilePath "py" -ArgumentList "-m", "http.server", "$port", "--bind", "127.0.0.1" -WorkingDirectory $frontendRoot
Start-Sleep -Seconds 2
Start-Process $url
