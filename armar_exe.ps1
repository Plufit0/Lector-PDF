# armar_exe.ps1 — arma dist\LectorPDF.exe, el archivo que se sube a GitHub Releases.
#
# Lo corre quien mantiene el programa, no quien lo usa. Necesita el Python que
# tiene pymupdf, pillow y pyinstaller (python -m pip install pyinstaller).
# La receta está en LectorPDF.spec. build\ y dist\ no se versionan.

param(
    [string]$Python = (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

& $Python -m PyInstaller --noconfirm --clean LectorPDF.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo (codigo $LASTEXITCODE)" }

$exe = Join-Path $PSScriptRoot "dist\LectorPDF.exe"
$mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host ""
Write-Host "Listo: $exe ($mb MB)"
Write-Host "Subirlo como archivo de una Release nueva en GitHub, con el nombre LectorPDF.exe."
