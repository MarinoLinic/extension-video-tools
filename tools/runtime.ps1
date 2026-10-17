param([switch]$Update,[switch]$Offline)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if(-not [Environment]::Is64BitOperatingSystem){throw 'This bundle requires 64-bit Windows 10 or 11.'}
$projectRoot=Split-Path -Parent $PSScriptRoot
$runtimeRoot=Join-Path $projectRoot 'runtime'
$cacheRoot=Join-Path $projectRoot '.local\vendor-cache'
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime-manifest.json') -Raw | ConvertFrom-Json
$lockFile=Join-Path $projectRoot 'host\requirements.lock.txt'
$lockHash=(Get-FileHash -LiteralPath $lockFile -Algorithm SHA256).Hash
$marker=Join-Path $runtimeRoot 'ready.json'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
function Get-VendorArchive([string]$Name) {
    if($Offline){throw "Portable bundle is missing $Name. Run Setup.cmd with internet access to repair it."}
    New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
    $item=$manifest.$Name
    $archive=Join-Path $cacheRoot ($Name+'-'+$item.version+'.zip')
    if(-not (Test-Path -LiteralPath $archive) -or (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $item.sha256) {
        Write-Host "Downloading private $Name $($item.version)..."
        [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
        $client=New-Object Net.WebClient
        try{$client.DownloadFile($item.url,$archive)}finally{$client.Dispose()}
    }
    if((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $item.sha256){throw "$Name checksum did not match. No downloaded program was executed."}
    return $archive
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$pythonRoot=Join-Path $runtimeRoot 'python'
$python=Join-Path $pythonRoot 'python.exe'
if(-not (Test-Path -LiteralPath $python)) {
    $archive=Get-VendorArchive 'python'
    [IO.Compression.ZipFile]::ExtractToDirectory($archive,$pythonRoot)
}
# Relative paths make the embedded interpreter independent of the user's Python and this folder's location.
$pathConfig=Join-Path $pythonRoot 'python312._pth'
@('python312.zip','.','Lib/site-packages','../../host','import site') | Set-Content -LiteralPath $pathConfig -Encoding ascii
$packages=Join-Path $pythonRoot 'Lib\site-packages'
if(-not (Test-Path -LiteralPath (Join-Path $packages 'pip\__main__.py'))) {
    New-Item -ItemType Directory -Force -Path $packages | Out-Null
    [IO.Compression.ZipFile]::ExtractToDirectory((Get-VendorArchive 'pip'),$packages)
}
$nodeRoot=Join-Path $runtimeRoot 'node'
if(-not (Test-Path -LiteralPath (Join-Path $nodeRoot 'node.exe'))) {
    $archive=Get-VendorArchive 'node';$extract=Join-Path $cacheRoot ('node-extract-'+[Guid]::NewGuid().ToString('N'))
    [IO.Compression.ZipFile]::ExtractToDirectory($archive,$extract)
    $source=Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Force -Path $nodeRoot | Out-Null
    foreach($name in @('node.exe','LICENSE','README.md','CHANGELOG.md')) {
        $file=Join-Path $source.FullName $name
        if(Test-Path -LiteralPath $file){Copy-Item -LiteralPath $file -Destination $nodeRoot}
    }
}
$ffmpegRoot=Join-Path $runtimeRoot 'ffmpeg'
if(-not (Test-Path -LiteralPath (Join-Path $ffmpegRoot 'bin\ffmpeg.exe')) -or -not (Test-Path -LiteralPath (Join-Path $ffmpegRoot 'bin\ffprobe.exe'))) {
    $archive=Get-VendorArchive 'ffmpeg';$extract=Join-Path $cacheRoot ('ffmpeg-extract-'+[Guid]::NewGuid().ToString('N'))
    [IO.Compression.ZipFile]::ExtractToDirectory($archive,$extract)
    $source=Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Force -Path (Join-Path $ffmpegRoot 'bin') | Out-Null
    foreach($name in @('ffmpeg.exe','ffprobe.exe')){Copy-Item -LiteralPath (Join-Path $source.FullName "bin\$name") -Destination (Join-Path $ffmpegRoot 'bin')}
    foreach($name in @('LICENSE','README.txt','doc')) {
        $file=Join-Path $source.FullName $name
        if(Test-Path -LiteralPath $file){Copy-Item -LiteralPath $file -Destination $ffmpegRoot -Recurse}
    }
}
$ready=$null
if(Test-Path -LiteralPath $marker){$ready=Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json}
if($Update -or -not $ready -or $ready.dependencies -ne $lockHash) {
    if($Offline){throw 'Portable bundle dependencies are incomplete. Run Setup.cmd with internet access to repair them.'}
    $requirements=if($Update){Join-Path $projectRoot 'host\requirements.txt'}else{$lockFile}
    $pipArgs=@('-m','pip','install','--disable-pip-version-check','--no-cache-dir','--no-compile','--no-warn-script-location','--only-binary=:all:','-r',$requirements)
    if($Update){$pipArgs+='--upgrade'}
    & $python @pipArgs
    if($LASTEXITCODE -ne 0){throw 'Could not install the private download packages.'}
}
& $python -c "import yt_dlp,youtube_transcript_api,requests; print('Private download runtime is ready.')"
if($LASTEXITCODE -ne 0){throw 'Private runtime validation failed.'}
@{dependencies=$lockHash;python=$manifest.python.version;node=$manifest.node.version;ffmpeg=$manifest.ffmpeg.version} | ConvertTo-Json | Set-Content -LiteralPath $marker -Encoding ascii
