param([switch]$Stop, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = 'D:\AI\ComfyUI'
$python = "$root\.venv\Scripts\python.exe"
$main = "$root\main.py"
$pidFile = 'D:\AI\comfyui.pid'
$url = 'http://127.0.0.1:8188'
function Find-ComfyProcess {
    if (Test-Path -LiteralPath $pidFile) {
        $processId = [int](Get-Content -LiteralPath $pidFile -Raw)
        $p = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($p -and $p.CommandLine -like "*$main*") { return $p }
    }
    return $null
}
try {
    $existing = Find-ComfyProcess
    if ($Stop) {
        if ($existing) {
            # Windows venv python.exe can launch a runtime child; stop only this app's tree.
            $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($existing.ProcessId)" -ErrorAction SilentlyContinue
            foreach ($child in $children) {
                if ($child.CommandLine -like "*$main*" -and $child.ExecutablePath -like 'D:\AI\*') {
                    Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
                }
            }
            Stop-Process -Id $existing.ProcessId -ErrorAction SilentlyContinue
            Write-Output 'ComfyUI stopped.'
        }
        else { Write-Output 'ComfyUI is not running.' }
        if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile }
        exit 0
    }
    if (-not $existing) {
        if (Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue) {
            throw 'Port 8188 is occupied by another process. Please check before starting.'
        }
        $env:HF_HOME = 'D:\AI\cache\huggingface'
        $env:TORCH_HOME = 'D:\AI\cache\torch'
        $env:PIP_CACHE_DIR = 'D:\AI\cache\pip'
        $env:UV_CACHE_DIR = 'D:\AI\cache\uv'
        $env:TEMP = 'D:\AI\temp'
        $env:TMP = $env:TEMP
        $env:PYTHONUTF8 = '1'
        $env:OMP_NUM_THREADS = '6'
        $env:MKL_NUM_THREADS = '6'
        New-Item -ItemType Directory -Path 'D:\AI\logs' -Force | Out-Null
        $arguments = @($main,'--listen','127.0.0.1','--port','8188','--fp16-unet','--cpu-vae','--disable-pinned-memory','--reserve-vram','0.8','--disable-partner-nodes','--disable-auto-launch','--preview-method','none')
        $p = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput 'D:\AI\logs\comfyui.stdout.log' -RedirectStandardError 'D:\AI\logs\comfyui.stderr.log' -PassThru
        $p.Id | Set-Content -LiteralPath $pidFile -Encoding ASCII
        Write-Output "Starting ComfyUI (PID $($p.Id))..."
    }
    for ($i=0; $i -lt 150; $i++) {
        try {
            $null = Invoke-RestMethod "$url/system_stats" -TimeoutSec 2
            Write-Output "Ready: $url"
            if (-not $NoBrowser) { Start-Process $url }
            exit 0
        } catch { }
        if (-not (Find-ComfyProcess)) { throw 'ComfyUI exited. See D:\AI\logs\comfyui.stderr.log' }
        Start-Sleep -Seconds 2
    }
    throw 'Startup is taking longer than expected. See D:\AI\logs\comfyui.stderr.log'
} catch {
    Write-Error $_
    exit 1
}
