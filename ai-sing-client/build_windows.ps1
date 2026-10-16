$ErrorActionPreference = "Stop"



$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$AppName = "$([char]0x5999)$([char]0x5531)"

$Entry = Join-Path $Root "aising_client\main.py"

$Icon = Join-Path $Root "aising_client\resources\miaochang.ico"

$Resources = Join-Path $Root "aising_client\resources"



if (-not (Test-Path $Entry)) {

    throw "Cannot find client entry: $Entry"

}



if (-not (Test-Path $Icon)) {

    throw "Cannot find app icon: $Icon"

}



$DistDir = Join-Path $Root "dist"

$BuildDir = Join-Path $Root "build"

$OutputExe = Join-Path $Root "dist\$AppName\$AppName.exe"



Write-Host "Building $AppName..."

Write-Host "Entry: $Entry"

Write-Host "Icon: $Icon"



if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX "python.exe"))) {

    $PythonExe = Join-Path $env:CONDA_PREFIX "python.exe"

} else {

    $PythonExe = (Get-Command python -ErrorAction Stop).Source

}

Write-Host "Python: $PythonExe"



& $PythonExe -m PyInstaller --version

if ($LASTEXITCODE -ne 0) {

    throw "PyInstaller is not installed in this Python environment. Run: `"$PythonExe`" -m pip install pyinstaller"

}



& $PythonExe -m PyInstaller `

    --noconfirm `

    --clean `

    --windowed `

    --name $AppName `

    --icon $Icon `

    --paths $Root `

    --add-data "$Resources;aising_client/resources" `
    --add-data "$Root\aising_client\vendor;aising_client/vendor" `

    --distpath $DistDir `

    --workpath $BuildDir `

    --specpath $Root `

    $Entry



if ($LASTEXITCODE -ne 0) {

    throw "PyInstaller failed with exit code $LASTEXITCODE"

}



if (-not (Test-Path $OutputExe)) {

    throw "Build finished but executable was not found: $OutputExe"

}



Write-Host ""

Write-Host "Build complete: $OutputExe"


