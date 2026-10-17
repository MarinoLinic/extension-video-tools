param([switch]$Update)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$localRoot = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $localRoot | Out-Null
$runtime = Join-Path $localRoot 'runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) {
    Write-Host 'Creating an isolated Python environment for Video Tools...'
    & py -3 -m venv (Join-Path $localRoot 'runtime')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required. Install Python and run Setup.cmd again.' }
}
$requirements = Join-Path $projectRoot 'host\requirements.lock.txt'
if ($Update -or -not (Test-Path -LiteralPath $requirements)) { $requirements = Join-Path $projectRoot 'host\requirements.txt' }
$pipArgs = @('-m', 'pip', 'install', '--disable-pip-version-check', '--no-cache-dir', '-r', $requirements)
if ($Update) { $pipArgs += '--upgrade' }
& $runtime @pipArgs
if ($LASTEXITCODE -ne 0) { throw 'Could not install the local download dependencies.' }
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '.NET Framework C# compiler was not found.' }
$executable = Join-Path $localRoot 'VideoToolsHost.exe'
& $compiler /nologo /target:winexe /optimize+ "/out:$executable" (Join-Path $projectRoot 'host\Launcher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Could not compile the native messaging launcher. Close Video Tools windows and retry.' }
$extensionManifest = Get-Content -LiteralPath (Join-Path $projectRoot 'extension\manifest.json') -Raw | ConvertFrom-Json
if (-not $extensionManifest.key) { throw 'The extension manifest is missing its stable public key.' }
$hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash([Convert]::FromBase64String($extensionManifest.key))
$alphabet = 'abcdefghijklmnop'
$extensionId = -join ($hash[0..15] | ForEach-Object { $alphabet[($_ -shr 4)] ; $alphabet[($_ -band 15)] })
$hostManifest = Join-Path $localRoot 'com.marin.video_tools.json'
@{name='com.marin.video_tools';description='Video Tools local download helper';path=$executable;type='stdio';allowed_origins=@("chrome-extension://$extensionId/")} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $hostManifest -Encoding UTF8
# These keys belong only to this application. No admin rights or browser policies are changed.
$registryPaths = @('HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.marin.video_tools',
                  'HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.marin.video_tools',
                  'HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.marin.video_tools')
foreach ($registryPath in $registryPaths) {
    New-Item -Path $registryPath -Force | Out-Null
    Set-Item -LiteralPath $registryPath -Value $hostManifest
}
& $runtime -m pip freeze | Set-Content -LiteralPath (Join-Path $localRoot 'installed-versions.txt') -Encoding UTF8
Write-Host ''
Write-Host 'Video Tools is ready.' -ForegroundColor Green
Write-Host "Extension ID: $extensionId"
Write-Host "Load unpacked folder: $(Join-Path $projectRoot 'extension')"
Write-Host 'Open brave://extensions, chrome://extensions or edge://extensions, enable Developer mode, and choose Load unpacked.'
Write-Host 'Pin Video Tools from the extensions menu. No helper server needs to stay open.'
