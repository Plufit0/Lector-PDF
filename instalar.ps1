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
#   (El instructivo NO se deja en el escritorio: vive en el boton "?" del
#   programa, que siempre esta al dia. Queda una copia, como_usar.txt, junto al
#   programa, por si algun dia el programa no abre.)
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
    # El Python que tiene pymupdf y pillow. Por defecto, el Python 3.11 instalado
    # para este usuario (en esta maquina hay mas de un Python y solo ese tiene
    # las librerias). Si esta en otro lado, pasarlo con -Python "ruta\pythonw.exe".
    [string]$Python = (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\pythonw.exe"),
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

# Solo estos archivos son "el programa". El resto (notas del asistente, docs,
# README, los scripts de instalacion) es material de trabajo y no viaja. El
# autotest SI viaja a proposito: es la red de seguridad y se corre desde la
# carpeta instalada.
$DEL_PROGRAMA = @("lector.pyw", "anotaciones.py", "errores.py", "ayuda.py", "mano.cur",
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
$pw = $Python
if (-not (Test-Path $pw)) { throw "No se encontro pythonw.exe en $pw (pasar otro con -Python)" }

$sh = New-Object -ComObject WScript.Shell
# El escritorio real de este usuario (puede estar redirigido a OneDrive), y
# por las dudas tambien el de OneDrive si existe aparte. Sin rutas fijas.
$escritorios = @([Environment]::GetFolderPath("Desktop"))
if ($env:OneDrive) {
    foreach ($nombre in @("Escritorio", "Desktop")) {
        $escritorios += (Join-Path $env:OneDrive $nombre)
    }
}
foreach ($d in ($escritorios | Select-Object -Unique)) {
    if (Test-Path $d) {
        $lnk = $sh.CreateShortcut((Join-Path $d "Lector PDF.lnk"))
        $lnk.TargetPath       = $pw
        $lnk.Arguments        = '"' + (Join-Path $Destino "lector.pyw") + '"'
        $lnk.WorkingDirectory = $Destino
        $lnk.IconLocation     = (Join-Path $Destino "lector.ico") + ",0"
        $lnk.Description      = "Leer cualquier PDF y marcarlo encima para devolverselo a un agente"
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
