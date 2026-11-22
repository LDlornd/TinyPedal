param(
    [ValidatePattern('^[0-9]{8}(-[a-z0-9]+)?$')]
    [string]$ReleaseTag = '20261122',
    [string]$TutorialDraft = 'docs/lfs-使用教程.xml'
)

$ErrorActionPreference = 'Stop'
$buildPython = Join-Path $PSScriptRoot '.venv310\Scripts\python.exe'
$nsisCompiler = Join-Path $PSScriptRoot '.build-tools\nsis-3.13\makensis.exe'
$releaseName = "dist-lfs-$ReleaseTag"
$releaseDirectory = Join-Path $PSScriptRoot $releaseName

foreach ($requiredPath in @($buildPython, $nsisCompiler, (Join-Path $PSScriptRoot $TutorialDraft))) {
    if (-not (Test-Path -LiteralPath $requiredPath)) { throw "缺少构建文件：$requiredPath" }
}
if (Test-Path -LiteralPath $releaseDirectory) { throw '分发目录已存在，请使用新的 ReleaseTag，避免覆盖已有分发文件。' }

$originalPythonPath = $env:PYTHONPATH
$originalQtPluginPath = $env:QT_PLUGIN_PATH
Push-Location $PSScriptRoot
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot '.build-tools\python'
    $env:QT_PLUGIN_PATH = Join-Path $PSScriptRoot '.venv310\Lib\site-packages\PySide2\plugins'
    & $buildPython build_win.py --output $releaseName
    if ($LASTEXITCODE -ne 0) { throw 'Windows 程序构建失败。' }
    & $buildPython packaging\prepare_lfs_release.py --release-dir $releaseName --release-tag $ReleaseTag --draft $TutorialDraft
    if ($LASTEXITCODE -ne 0) { throw '分发文件准备失败。' }
    & $nsisCompiler /INPUTCHARSET UTF8 "/DRELEASE_TAG=$ReleaseTag" "/DRELEASE_DIR=$releaseDirectory" packaging\lfs_installer.nsi
    if ($LASTEXITCODE -ne 0) { throw '安装程序编译失败。' }
    $portableZip = Join-Path $releaseDirectory "TinyPedal-LFS-$ReleaseTag-windows-x64-portable.zip"
    & $buildPython -m zipfile -c $portableZip (Join-Path $releaseDirectory 'TinyPedal')
    if ($LASTEXITCODE -ne 0) { throw '便携包压缩失败。' }
    $checksums = Get-ChildItem -LiteralPath $releaseDirectory -File |
        Where-Object { $_.Extension -in @('.exe', '.zip') } |
        ForEach-Object { "$( (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower() )  $($_.Name)" }
    $checksums | Set-Content -LiteralPath (Join-Path $releaseDirectory 'SHA256SUMS.txt') -Encoding utf8
    Write-Output "分发文件已生成：$releaseDirectory"
}
finally {
    Pop-Location
    $env:PYTHONPATH = $originalPythonPath
    $env:QT_PLUGIN_PATH = $originalQtPluginPath
}
