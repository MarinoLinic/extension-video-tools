$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$packageRoot=Join-Path $projectRoot '.local\packages'
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
$output=Join-Path $packageRoot ('video-tools-extension-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.zip')
# The extension folder is an explicit public-source allowlist; no host config, jobs or cookies.
Compress-Archive -Path (Join-Path $projectRoot 'extension\*') -DestinationPath $output
Write-Host $output
