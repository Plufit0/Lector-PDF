# -*- mode: python ; coding: utf-8 -*-
# LectorPDF.spec — receta de PyInstaller para armar LectorPDF.exe.
#
# Se usa con armar_exe.ps1 (no a mano). Sale UN solo .exe con todo adentro:
# Python, PyMuPDF, Pillow, Tk y el OCR (tessdata/ con español e inglés). Quien
# lo baja de GitHub hace doble clic y listo, sin instalar nada (decisión del
# Diseñador, 2026-10-04: el programa no le pide pasos extra a nadie).
#
# Los archivos de datos quedan en la raíz de sys._MEIPASS, que es donde los
# buscan lector.pyw (mano.cur, lector.ico) y ocr.py (tessdata/).

a = Analysis(
    ['lector.pyw'],
    pathex=[],
    binaries=[],
    datas=[
        ('mano.cur', '.'),
        ('lector.ico', '.'),
        ('tessdata/eng.traineddata', 'tessdata'),
        ('tessdata/spa.traineddata', 'tessdata'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Nada de esto lo usa el programa: sacarlo achica el .exe.
    excludes=['numpy', 'unittest', 'pydoc', 'test'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LectorPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # Sin UPX: comprimir el .exe hace que más antivirus lo marquen por error.
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon='lector.ico',
)
