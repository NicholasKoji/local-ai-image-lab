param(
    [string]$PackageDirectory = 'D:\AI\drivers\616.92\extracted',
    [string]$RecordDirectory = 'D:\AI\drivers\616.92\installation'
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $RecordDirectory -Force | Out-Null
$statusPath = Join-Path $RecordDirectory 'status.json'
$status = [ordered]@{ state='starting'; automaticRestart=$false }
try {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) { throw 'Run this driver installer with Windows administrator approval.' }
    $setup = Join-Path $PackageDirectory 'setup.exe'
    $signature = Get-AuthenticodeSignature -LiteralPath $setup
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'NVIDIA Corporation') {
        throw 'Driver installer signature is not a valid NVIDIA signature.'
    }
    $old = Get-CimInstance Win32_PnPSignedDriver -Filter "DeviceName='NVIDIA GeForce GTX 1660 Ti'"
    if (-not $old) { throw 'Expected GTX 1660 Ti device is not present.' }
    $status.oldDriver = $old.DriverVersion
    $status.oldInf = $old.InfName
    $backup = Join-Path $RecordDirectory 'previous-driver'
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    pnputil.exe /export-driver $old.InfName $backup | Out-File (Join-Path $RecordDirectory 'export-driver.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Previous driver export failed; installation not started.' }
    $status.previousDriverExport = $backup
    $status.state = 'installing'
    $status | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    # NVIDIA documented display-only silent install; -n suppresses reboot.
    # No clean-install switch: preserve user driver settings and omit NVIDIA App.
    $process = Start-Process -FilePath $setup -ArgumentList @('-s','-n','Display.Driver',"-log:$RecordDirectory",'-loglevel:6') -WorkingDirectory $PackageDirectory -WindowStyle Hidden -PassThru -Wait
    $status.exitCode = $process.ExitCode
    $status.state = if ($process.ExitCode -in @(0,1,3010)) { 'installed' } else { 'failed' }
    $status.rebootRequired = $process.ExitCode -in @(1,3010)
    $new = Get-CimInstance Win32_PnPSignedDriver -Filter "DeviceName='NVIDIA GeForce GTX 1660 Ti'"
    $status.newDriver = $new.DriverVersion
    $status | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    if ($status.state -ne 'installed') { exit 1 }
} catch {
    $status.state = 'failed'
    $status.error = $_.Exception.Message
    $status | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    throw
}
