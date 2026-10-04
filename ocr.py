# -*- coding: utf-8 -*-
"""
ocr.py — las palabras de una hoja, aunque la hoja sea una foto o un escaneo.

Lo usan la hoja-guía (guia.palabras_de), el visor (elegir y resaltar texto) y
leer_devolucion.py. Todos piden las palabras por acá y no con get_text directo.

DECISIONES DE DISENO:

1. Por qué existe (2026-10-04): se marcó un PDF de imágenes escaneadas y la
   hoja-guía salió con las citas vacías, porque una foto no trae texto adentro.
   La IA que recibió la devolución no entendió a qué apuntaba cada marca.

2. Automático y sin pasos extra: el usuario NUNCA tiene que pasar el PDF por un
   OCR aparte ni instalar nada (regla del Diseñador: el programa es simple).
   El lector de texto (Tesseract) ya viene dentro de PyMuPDF; acá solo se le
   da la carpeta tessdata/ con el español y el inglés, que viaja con el
   programa (y dentro del .exe).

3. Solo se lee con OCR una hoja SIN texto propio y CON imágenes. Una hoja con
   texto real se lee como siempre: el texto original es exacto y el OCR no.

4. Lo leído se guarda en memoria por archivo y número de hoja: el visor lo pide
   al pasar el mouse y la guía al guardar, y no se lee dos veces.

5. Si algo falla (falta tessdata, imagen rara), devuelve lo que haya sin OCR:
   leer el PDF nunca se rompe por esto.
"""

import os
import sys

import pymupdf

# En el .exe (PyInstaller) los archivos del programa están en sys._MEIPASS.
_BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
TESSDATA = os.path.join(_BASE, "tessdata")
IDIOMAS = "spa+eng"
DPI = 300                # lo que recomienda Tesseract para escaneos
MIN_PALABRAS = 3         # menos que esto = hoja sin texto propio (ej. un número de página)
MIN_IMAGEN = 0.3         # las imágenes tienen que tapar al menos 30% de la hoja

_cache = {}


def _es_escaneo(pagina):
    """True si la hoja es, sobre todo, una imagen."""
    area = abs(pagina.rect) or 1.0
    tapado = 0.0
    try:
        for info in pagina.get_image_info():
            r = pymupdf.Rect(info["bbox"]) & pagina.rect
            if not r.is_empty:
                tapado += abs(r)
    except Exception:
        return False
    return tapado / area >= MIN_IMAGEN


def palabras(pagina):
    """Lo mismo que pagina.get_text("words"), con OCR si la hoja es un escaneo."""
    propias = pagina.get_text("words")
    if len(propias) >= MIN_PALABRAS or not os.path.isdir(TESSDATA):
        return propias
    # xref y no número de hoja: al sacar la hoja-guía las hojas se renumeran.
    clave = (pagina.parent.name, pagina.xref)
    if clave in _cache:
        return _cache[clave]
    leidas = propias
    try:
        if _es_escaneo(pagina):
            tp = pagina.get_textpage_ocr(language=IDIOMAS, dpi=DPI, full=True,
                                         tessdata=TESSDATA)
            leidas = pagina.get_text("words", textpage=tp) or propias
    except Exception:
        leidas = propias
    # Un documento nuevo sin nombre (en memoria) no se guarda: la clave no
    # lo distinguiría de otro.
    if pagina.parent.name:
        _cache[clave] = leidas
    return leidas
