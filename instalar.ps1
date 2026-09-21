# instalar.ps1 — deja el Lector PDF instalado en C:\Program Files\Mios\LectorPDF
#
# Necesita permisos de administrador (Windows no deja escribir en Program Files
# sin ellos). Se ejecuta una sola vez; despues el programa se abre desde el
# acceso directo del escritorio como cualquier otro.
#
# QUE HACE, EN ORDEN:
#   1. Crea C:\Program Files\Mios\LectorPDF
#   2. Copia ahi el programa (sin los archivos de trabajo ni el __pycache__)
#   3. Le da permiso de escritura al usuario sobre esa carpeta  <-- ver nota
#   4. Rehace los accesos directos del escritorio apuntando a la ruta nueva
#   5. Deja el instructivo actualizado en el escritorio
#
# NOTA SOBRE EL PERMISO DE ESCRITURA (paso 3): por defecto Program Files es de
# solo lectura, y esta bien que lo sea. Se le da permiso al usuario sobre ESTA
# subcarpeta para que el programa se pueda seguir corrigiendo sin pedir
# administrador cada vez. Si se prefiere lo mas seguro, sacar el paso 3: el
# programa funciona igual, pero cada cambio va a necesitar elevacion.
# Los errores y ajustes NUNCA se escriben aca: van a la carpeta de datos del
# usuario, justamente porque Program Files no es lugar para eso.

param(
    # Por defecto, el origen es la carpeta donde esta este mismo script: asi
    # sirve tanto desde la carpeta de trabajo como desde la ya instalada (para
    # rehacer los accesos directos sin volver a copiar de ningun lado).
    [string]$Origen = $PSScriptRoot,
    [string]$Destino = "C:\Program Files\Mios\LectorPDF",
    [switch]$SinPermisos
)

$ErrorActionPreference = "Stop"

# El proceso corre elevado, en otra consola que se cierra sola: sin este
# registro no habria forma de ver que paso si algo falla.
$REGISTRO = Join-Path $env:TEMP "instalar_lectorpdf.log"
try { Start-Transcript -Path $REGISTRO -Force | Out-Null } catch {}
trap {
    Write-Host ("ERROR: " + $_.Exception.Message)
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

# Solo estos archivos son "el programa". El resto (ESTADO.md, autotest, los
# scripts de instalacion) es material de trabajo y no viaja.
$DEL_PROGRAMA = @("lector.pyw", "anotaciones.py", "errores.py", "ayuda.py",
                  "idiomas.py", "leer_devolucion.py", "lector.ico", "autotest.py",
                  "como_usar.txt")

Write-Host ""
Write-Host "=== Instalando el Lector PDF ==="
Write-Host "  desde : $Origen"
Write-Host "  hacia : $Destino"
Write-Host ""

foreach ($f in $DEL_PROGRAMA) {
    if (-not (Test-Path (Join-Path $Origen $f))) { throw "Falta el archivo $f en $Origen" }
}

New-Item -ItemType Directory -Force -Path $Destino | Out-Null
foreach ($f in $DEL_PROGRAMA) {
    Copy-Item (Join-Path $Origen $f) -Destination $Destino -Force
    Write-Host "  copiado  $f"
}

# El __pycache__ viejo puede tener modulos compilados de la version anterior.
$cache = Join-Path $Destino "__pycache__"
if (Test-Path $cache) { Remove-Item $cache -Recurse -Force }

if (-not $SinPermisos) {
    $usuario = "$env:USERDOMAIN\$env:USERNAME"
    $acl = Get-Acl $Destino
    $regla = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $usuario, "Modify",
        "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($regla)
    Set-Acl $Destino $acl
    Write-Host "  permiso de escritura dado a $usuario sobre la carpeta"
}

# --- accesos directos ---------------------------------------------------
$pw = "C:\Users\david\AppData\Local\Programs\Python\Python311\pythonw.exe"
if (-not (Test-Path $pw)) { throw "No se encontro pythonw.exe en $pw" }

$sh = New-Object -ComObject WScript.Shell
foreach ($d in @("C:\Users\david\Desktop", "C:\Users\david\OneDrive\Escritorio")) {
    if (Test-Path $d) {
        $lnk = $sh.CreateShortcut((Join-Path $d "Lector PDF.lnk"))
        $lnk.TargetPath       = $pw
        $lnk.Arguments        = '"' + (Join-Path $Destino "lector.pyw") + '"'
        $lnk.WorkingDirectory = $Destino
        $lnk.IconLocation     = (Join-Path $Destino "lector.ico") + ",0"
        $lnk.Description      = "Leer PDFs y marcarlos encima para devoluciones de manual de diseno"
        $lnk.WindowStyle      = 1
        $lnk.Save()
        Write-Host "  acceso directo actualizado en $d"
        # A proposito NO se deja el instructivo en el escritorio: esta en el
        # boton "?" del programa, que siempre esta al dia. Un .txt suelto es una
        # copia mas para mantener y una cosa mas que estorba en el escritorio.
        # Queda uno junto al programa, solo por si algun dia el programa no abre.
    }
}

Write-Host ""
Write-Host "Listo. El programa vive en $Destino"
Write-Host ""
try { Stop-Transcript | Out-Null } catch {}
