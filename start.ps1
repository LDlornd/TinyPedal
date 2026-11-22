$env:QT_PLUGIN_PATH = Join-Path $PSScriptRoot '.venv310\Lib\site-packages\PySide2\plugins'

& (Join-Path $PSScriptRoot '.venv310\Scripts\python.exe') `
  (Join-Path $PSScriptRoot 'run.py') @args