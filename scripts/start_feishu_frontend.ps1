$projectRoot = Join-Path $PSScriptRoot ".."
$projectRoot = (Resolve-Path $projectRoot).Path
$port = 4390
$url = "http://127.0.0.1:$port"

Write-Host "Rendering Feishu frontend data..."
py (Join-Path $PSScriptRoot "render_feishu_frontend.py")

Write-Host "Building Feishu frontend release..."
py (Join-Path $PSScriptRoot "build_feishu_frontend_release.py")

Write-Host "Starting local workbench server at $url"
Start-Process -FilePath "py" -ArgumentList (Join-Path $PSScriptRoot "run_workbench_server.py"), "--host", "127.0.0.1", "--port", "$port" -WorkingDirectory $projectRoot
Start-Sleep -Seconds 2
Start-Process $url
