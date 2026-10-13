param([string]$Environment = 'D:\AI\environments\anima-cu130')
$ErrorActionPreference = 'Stop'
$baseline = 'D:\AI\ComfyUI\.venv\Scripts\python.exe'
$env:UV_CACHE_DIR = 'D:\AI\cache\uv'
$env:UV_LINK_MODE = 'hardlink'
$env:TEMP = 'D:\AI\temp'
$env:TMP = $env:TEMP
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$records = Join-Path $root 'generated\environment'
New-Item -ItemType Directory -Path $records -Force | Out-Null
$packages = @(uv pip freeze --python $baseline)
if ($LASTEXITCODE -ne 0) { throw 'Baseline package listing failed' }
$packages | Set-Content -LiteralPath (Join-Path $records 'requirements-cu126.txt') -Encoding UTF8
$other = $packages | Where-Object { $_ -notmatch '^(torch|torchvision)==' }
$other | Set-Content -LiteralPath (Join-Path $records 'requirements-shared.txt') -Encoding UTF8
$python = Join-Path $Environment 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    uv venv --python $baseline $Environment
    if ($LASTEXITCODE -ne 0) { throw 'Test venv creation failed' }
}
# Keep the same PyTorch/vision release; vary only the CUDA wheel build.
uv pip install --python $python 'torch==2.12.1+cu130' 'torchvision==0.27.1+cu130' --index-url https://download.pytorch.org/whl/cu130
if ($LASTEXITCODE -ne 0) { throw 'CUDA 13 wheels installation failed' }
uv pip install --python $python --no-deps -r (Join-Path $records 'requirements-shared.txt')
if ($LASTEXITCODE -ne 0) { throw 'Shared pinned packages installation failed' }
uv pip check --python $python
if ($LASTEXITCODE -ne 0) { throw 'Test environment dependency check failed' }
uv pip freeze --python $python | Set-Content -LiteralPath (Join-Path $records 'requirements-cu130.txt') -Encoding UTF8
Write-Output "Prepared isolated environment: $Environment"
