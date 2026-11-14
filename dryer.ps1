#requires -Version 7.3

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$PSNativeCommandArgumentPassing = 'Standard'
$toolPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'

if (-not (Test-Path -LiteralPath $toolPython -PathType Leaf)) {
    $venv = Join-Path $PSScriptRoot '.venv'
    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        & $launcher.Source -3 -m venv $venv
    } else {
        & python -m venv $venv
    }
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { exit $exitCode }
}

$installed = Join-Path $PSScriptRoot '.venv/Scripts/dryer.exe'
if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) {
    & $toolPython -m pip install -e $PSScriptRoot |
        ForEach-Object { [Console]::Error.WriteLine($_) }
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { exit $exitCode }
}

& $toolPython -m dryer @args
$exitCode = $LASTEXITCODE
exit $exitCode
