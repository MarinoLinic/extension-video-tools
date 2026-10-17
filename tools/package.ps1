param([switch]$Portable)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$packageRoot=Join-Path $projectRoot '.local\packages'
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$kind=if($Portable){'windows-portable'}else{'browser'}
$stage=Join-Path $packageRoot ("stage-$kind-$stamp")
New-Item -ItemType Directory -Path $stage | Out-Null
function Copy-SourceTree([string]$Source,[string]$Destination) {
    $sourceItem=Get-Item -LiteralPath $Source
    if(-not $sourceItem.PSIsContainer){Copy-Item -LiteralPath $Source -Destination $Destination;return}
    $target=Join-Path $Destination $sourceItem.Name
    [IO.Directory]::CreateDirectory($target) | Out-Null
    foreach($file in Get-ChildItem -LiteralPath $Source -File -Recurse) {
        $relative=$file.FullName.Substring($sourceItem.FullName.Length+1)
        # Generated launchers may contain builder paths; the application uses python -m instead.
        if($relative -match '(^|\\)(__pycache__|Scripts)(\\|$)' -or $file.Extension -in @('.pyc','.pyo')){continue}
        $out=Join-Path $target $relative
        [IO.Directory]::CreateDirectory((Split-Path -Parent $out)) | Out-Null
        [IO.File]::Copy($file.FullName,$out)
    }
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'manifest.json') -Destination $stage
Copy-Item -LiteralPath (Join-Path $projectRoot 'extension') -Destination $stage -Recurse
if($Portable) {
    & (Join-Path $PSScriptRoot 'setup.ps1')
    foreach($name in @('host','tools','scripts','tests','runtime','README.md','AGENTS.md','VERIFICATION.md','THIRD_PARTY.md','Setup.cmd','Update Tools.cmd','Open Extension Folder.cmd','Build Portable.cmd','package.json')) {
        Copy-SourceTree (Join-Path $projectRoot $name) $stage
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot '.local\VideoToolsHost.exe') -Destination (Join-Path $stage 'host\VideoToolsHost.exe')
    $checksums=Get-ChildItem -LiteralPath $stage -File -Recurse | ForEach-Object {
        $relative=$_.FullName.Substring($stage.Length+1).Replace('\','/')
        ((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()+'  '+$relative)
    }
    $checksums | Set-Content -LiteralPath (Join-Path $stage 'PORTABLE-CHECKSUMS.sha256') -Encoding ascii
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$output=Join-Path $packageRoot ("video-tools-$kind-$stamp.zip")
[IO.Compression.ZipFile]::CreateFromDirectory($stage,$output,[IO.Compression.CompressionLevel]::Optimal,$false)
Write-Host $output
