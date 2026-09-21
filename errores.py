# -*- coding: utf-8 -*-
"""
errores.py — registro de todo lo que salio mal en la sesion.

POR QUE ASI: antes se guardaba solo el ultimo error, y eso miente. Cuando algo
se rompe de verdad rara vez es una sola cosa: se cae una, eso deja el programa
en un estado raro, y se caen tres mas. Si solo se guarda la ultima, se ve el
sintoma y nunca la causa. Aca se guardan todas, en orden, con la hora y con el
detalle tecnico completo, y arriba de todo un resumen para leer de un vistazo.

El archivo se reescribe entero en cada anotacion, asi que siempre esta completo
aunque el programa se cierre de golpe.

DONDE VIVE: en la carpeta de datos del usuario, NO al lado del programa. El
programa vive en Program Files, donde Windows no deja escribir sin permisos de
administrador: si el registro se guardara ahi, el intento de anotar un error
fallaria tambien, y no quedaria rastro de nada.
"""

import os
import sys
import traceback

_NOMBRE_APP = "LectorPDF"


def carpeta_datos():
    """Carpeta propia del programa para cosas que se escriben (registro, ajustes)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    destino = os.path.join(base, _NOMBRE_APP)
    try:
        os.makedirs(destino, exist_ok=True)
    except OSError:
        destino = os.path.expanduser("~")
    return destino


ARCHIVO = os.path.join(carpeta_datos(), "errores_de_la_ultima_sesion.txt")
# El de la sesion anterior se guarda aparte al arrancar (ver limpiar).
ARCHIVO_ANTERIOR = os.path.join(carpeta_datos(), "errores_de_la_sesion_anterior.txt")

_sesion = []          # lista de (hora, titulo, detalle)


def _ahora():
    import time
    return time.strftime("%H:%M:%S")


def anotar(titulo, excepcion=None, detalle_extra=""):
    """Agrega un error al registro de la sesion y reescribe el archivo.

    titulo: en castellano, lo que estaba intentando hacer el programa.
    """
    detalle = ""
    if excepcion is not None:
        detalle = "".join(traceback.format_exception(
            type(excepcion), excepcion, excepcion.__traceback__))
    if detalle_extra:
        detalle = (detalle + "\n" + detalle_extra).strip()
    _sesion.append((_ahora(), titulo, detalle))
    _volcar()
    return len(_sesion)


def _volcar():
    try:
        with open(ARCHIVO, "w", encoding="utf-8") as f:
            f.write("ERRORES DE LA ULTIMA SESION DEL LECTOR PDF\n")
            f.write("=" * 66 + "\n")
            f.write("Programa : %s\n" % os.path.dirname(os.path.abspath(__file__)))
            f.write("Python   : %s\n" % sys.executable)
            f.write("Total    : %d error(es)\n\n" % len(_sesion))

            f.write("RESUMEN (para leer de un vistazo)\n")
            f.write("-" * 66 + "\n")
            for i, (hora, titulo, _) in enumerate(_sesion, 1):
                f.write("%2d. [%s] %s\n" % (i, hora, titulo))
            f.write("\n\nDETALLE COMPLETO (para pasarle al agente)\n")
            f.write("=" * 66 + "\n")
            for i, (hora, titulo, detalle) in enumerate(_sesion, 1):
                f.write("\n--- %d de %d --- [%s] %s\n" % (i, len(_sesion), hora, titulo))
                f.write(detalle if detalle else "(sin detalle tecnico)\n")
    except Exception:
        # Si ni siquiera se puede escribir el registro, no hay nada mas que
        # hacer: lo importante es no tumbar el programa por esto.
        pass


def limpiar():
    """Arranca una sesion nueva.

    El registro de la sesion anterior NO se borra: se renombra a
    ARCHIVO_ANTERIOR. Si el programa se colgo o se cerro mal, lo normal es
    volver a abrirlo para mandar el registro, y antes eso mismo lo borraba.
    """
    del _sesion[:]
    try:
        if os.path.exists(ARCHIVO):
            os.replace(ARCHIVO, ARCHIVO_ANTERIOR)
    except OSError:
        pass
