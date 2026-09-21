# -*- coding: utf-8 -*-
"""
anotaciones.py — guardar y leer las marcas de una devolucion dentro del PDF.

Modulo compartido por:
  - lector.pyw          (el programa que usa David para marcar)
  - leer_devolucion.py  (el que usa el agente para entender la devolucion)

DECISIONES DE DISENO (no cambiar sin leer esto):

1. Las marcas se guardan como ANOTACIONES PDF ESTANDAR (Ink para los trazos,
   FreeText para los textos), no como pixeles quemados sobre la pagina. Por eso
   el texto original del manual sigue siendo extraible intacto: ese es el
   "canal 1". Las anotaciones son el "canal 2". Un solo archivo, dos canales.

2. Toda anotacion escrita por este programa lleva autor (campo /T) = AUTOR.
   Sirve para dos cosas: reconocer "lo mio" al reabrir un PDF ya marcado, y no
   pisar anotaciones hechas con otros programas (Edge, Acrobat), que se dejan
   intactas.

3. Las coordenadas se manejan SIEMPRE en puntos PDF, con origen arriba-izquierda
   (el sistema de PyMuPDF), nunca en pixeles de pantalla. El zoom es solo una
   forma de mirar: no toca los datos. Asi una marca hecha con zoom 150% cae en
   el mismo lugar que una hecha al 80%.

4. Paginas rotadas: las anotaciones se insertan en el espacio SIN rotar de la
   pagina, que es lo que espera PyMuPDF. Se convierte con derotation_matrix
   (que es la identidad cuando la pagina no esta rotada, asi que el camino
   normal no paga nada). Los manuales de diseno no vienen rotados, pero un PDF
   bajado de cualquier lado si, y una marca desplazada 90 grados seria un dolor
   de cabeza dificil de entender.

5. El texto completo de cada nota va DOS veces: dibujado en la anotacion (para
   que se vea) y en el campo /Contents (para que se lea sin depender del
   dibujo). Si una nota es mas larga que su recuadro, el recuadro la recorta
   visualmente pero /Contents la conserva entera. Nunca se pierde una palabra.
"""

import os

import pymupdf

import idiomas

# Autor con el que se firman las anotaciones propias. Si esto cambia, los PDFs
# marcados con la version anterior dejan de reconocerse como propios.
AUTOR = "Devolucion"

# Marca en los metadatos del PDF: le dice al extractor "esto salio del lector".
MARCA_PRODUCTOR = "Lector PDF - devolucion de manual de diseno"

# Ancho MAXIMO del recuadro de una nota, en puntos PDF. El recuadro real se
# ajusta al texto (ver medir_nota): una nota de dos palabras no ocupa una caja
# de 250 pt con el fondo amarillo vacio al lado. Este es solo el tope: pasado
# este ancho el texto se parte en varias lineas en vez de seguir agrandando la
# caja. Es tambien el ancho con el que se escribe en pantalla (el editor).
ANCHO_NOTA = 250.0
# Ancho MINIMO: por debajo de esto la caja no se achica mas, para que una nota
# de una sola letra no quede como un cuadradito ilegible.
ANCHO_MIN_NOTA = 46.0
# Margen interno entre el texto y el borde de la caja, en puntos PDF.
PAD_NOTA = 6.0
# Tamano de letra de las notas, en puntos PDF.
CUERPO_NOTA = 11.0
# Alto de linea al maquetar una nota.
ALTO_LINEA = CUERPO_NOTA * 1.30
# (Historico) caracteres por linea estimados. Ya no se usa para medir: el ancho
# real de cada linea se calcula con la fuente de verdad en medir_nota.
CHARS_POR_LINEA = max(8, int(ANCHO_NOTA / (CUERPO_NOTA * 0.52)))

# Fondo de las notas de texto (amarillo papel) y su borde.
FONDO_NOTA = (1.0, 0.96, 0.70)

# Color del subrayado con el que se marca la frase a la que se ata una marca,
# y su opacidad. Tenue a proposito: tiene que senalar sin ensuciar la hoja ni
# competir con lo que David escribio.
COLOR_ANCLA = (0.85, 0.65, 0.0)
OPACIDAD_ANCLA = 0.2
# Con esto termina el nombre del resaltado, para poder emparejarlo con su nota.
SUFIJO_ANCLA = "-ancla"
# Con esto empieza el campo /Subj cuando la marca se refiere a otra marca.
PREFIJO_REF = "ref:"


class MarcasNoGuardadas(Exception):
    """El archivo se escribio pero alguna marca quedo afuera.

    Existe para que un fallo parcial nunca pase desapercibido: es peor mandar
    una devolucion a la que le falta una marca que no poder guardarla.
    """

    def __init__(self, fallos, ruta):
        self.fallos = fallos
        self.ruta = ruta
        super().__init__("No se pudieron escribir %d marca(s): %s"
                         % (len(fallos), "; ".join(fallos[:4])))


def limpiar_nombre(nombre):
    """(ver abajo)"""
    # Los nombres que empiezan con "fitz-" los inventa PyMuPDF sola cuando crea
    # una anotacion. No significan nada para nadie, asi que se descartan para
    # que en su lugar se genere uno legible ("dibujo-p02-1").
    if (nombre or "").startswith("fitz-"):
        return ""
    return _limpiar_nombre(nombre)


def _limpiar_nombre(nombre):
    """Deja el nombre en algo que se pueda escribir en el PDF sin romperlo.

    El nombre viaja dentro del archivo como texto plano entre parentesis, asi
    que los parentesis y las barras hay que sacarlos o el PDF queda mal formado.
    """
    limpio = "".join(c for c in (nombre or "")
                     if c.isalnum() or c in " -_.:#").strip()
    return limpio[:60]


def nombre_por_defecto(tipo, pagina, indice):
    """Nombre legible y estable: 'dibujo-p02-1', 'nota-p05-3'.

    Sirve para que David y el agente puedan hablar de una marca concreta
    ("lo que dice la nota-p05-3") sin tener el documento delante.
    """
    return "%s-p%02d-%d" % ("dibujo" if tipo == "lapiz" else "nota", pagina + 1, indice + 1)


def _ancho_texto(cadena):
    """Ancho en puntos PDF de una linea, en la fuente de las notas (Helvetica)."""
    try:
        return pymupdf.get_text_length(cadena, fontname="helv", fontsize=CUERPO_NOTA)
    except Exception:
        # Estimacion prudente si la medicion real no esta disponible.
        return len(cadena) * CUERPO_NOTA * 0.5


def _envolver(parrafo, ancho_util):
    """Parte un parrafo en lineas que no superen ancho_util, midiendo de verdad."""
    lineas, actual = [], ""
    for palabra in parrafo.split(" "):
        prueba = palabra if not actual else actual + " " + palabra
        if not actual or _ancho_texto(prueba) <= ancho_util:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def medir_nota(texto):
    """Ancho y alto del recuadro de una nota, ajustados a su texto (fit to size).

    La caja crece solo lo necesario: se estira con la linea mas larga hasta
    ANCHO_NOTA y ahi para, partiendo el texto en varias lineas. Asi el fondo
    amarillo no deja un hueco vacio al lado de una nota corta.
    """
    parrafos = (texto or "").split("\n")
    tope_util = ANCHO_NOTA - 2 * PAD_NOTA
    natural = max((_ancho_texto(p) for p in parrafos), default=0.0)
    ancho_util = max(ANCHO_MIN_NOTA - 2 * PAD_NOTA, min(tope_util, natural))
    lineas = 0
    for parrafo in parrafos:
        if not parrafo:
            lineas += 1
        else:
            lineas += len(_envolver(parrafo, ancho_util)) or 1
    ancho = ancho_util + 2 * PAD_NOTA
    alto = max(ALTO_LINEA + 2 * PAD_NOTA, lineas * ALTO_LINEA + 2 * PAD_NOTA)
    return ancho, alto


def alto_nota(texto):
    """Alto en puntos que necesita el recuadro de una nota para ese texto."""
    return medir_nota(texto)[1]


def rect_nota(x, y, texto):
    """Recuadro PDF de una nota, ajustado a su texto, esquina sup-izq en x,y."""
    ancho, alto = medir_nota(texto)
    return pymupdf.Rect(x, y, x + ancho, y + alto)


def bbox_trazo(trazos, grosor):
    """Recuadro que envuelve a un trazo de lapiz, con el margen del grosor."""
    xs = [p[0] for t in trazos for p in t]
    ys = [p[1] for t in trazos for p in t]
    if not xs:
        return pymupdf.Rect(0, 0, 0, 0)
    m = max(1.0, grosor)
    return pymupdf.Rect(min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)


# ---------------------------------------------------------------- guardar ----

def _poner_nombre(doc, annot, marca, numero, indice):
    """Graba el nombre de la marca en el campo /NM del PDF.

    PyMuPDF no deja escribirlo con set_info, hay que tocar el objeto directo.
    Es el identificador con el que David y el agente pueden referirse a una
    marca concreta sin tener el documento a la vista.
    """
    nombre = limpiar_nombre(marca.get("nombre")) or nombre_por_defecto(
        marca["tipo"], numero, indice)
    marca["nombre"] = nombre
    try:
        doc.xref_set_key(annot.xref, "NM", "(%s)" % nombre)
    except Exception:
        pass
    # Si la marca se refiere a OTRA marca (no a una frase), se guarda el nombre
    # de esa otra en el campo /Subj, que es texto libre del formato PDF.
    ref = limpiar_nombre(marca.get("ref"))
    if ref:
        try:
            annot.set_info(title=AUTOR, subject=PREFIJO_REF + ref)
            annot.update()
        except Exception:
            pass


def _poner_ancla(doc, pagina, matriz, marca, numero, indice):
    """Resaltado amarillo sobre la frase a la que esta atada la nota."""
    ancla = marca.get("ancla")
    if not ancla or not ancla.get("rects"):
        return
    try:
        quads = []
        for (x0, y0, x1, y1) in ancla["rects"]:
            quads.append((pymupdf.Rect(x0, y0, x1, y1) * matriz).normalize().quad)
        if not quads:
            return
        # Subrayado, no resaltado: el bloque de color encima de las palabras
        # ensucia la pagina y cuesta leer lo que esta marcado. Una linea abajo
        # dice lo mismo sin taparlo.
        annot = pagina.add_underline_annot(quads)
        annot.set_colors(stroke=COLOR_ANCLA)
        # En /Contents va la FRASE DEL MANUAL, no la nota: asi el resaltado se
        # explica solo aunque se lea con otro programa.
        annot.set_info(title=AUTOR, content=ancla.get("cita", "")[:2000])
        annot.update(opacity=OPACIDAD_ANCLA)
        nombre = limpiar_nombre(marca.get("nombre")) or nombre_por_defecto(
            "texto", numero, indice)
        doc.xref_set_key(annot.xref, "NM", "(%s%s)" % (nombre, SUFIJO_ANCLA))
    except Exception:
        # Que falle el resaltado no puede impedir que se guarde la nota.
        pass


def _limpiar_propias(pagina):
    """Borra de la pagina las anotaciones firmadas por este programa."""
    a_borrar = []
    for annot in pagina.annots():
        try:
            if (annot.info or {}).get("title", "") == AUTOR:
                a_borrar.append(annot)
        except Exception:
            continue
    for annot in a_borrar:
        try:
            pagina.delete_annot(annot)
        except Exception:
            pass


def guardar(ruta_origen, ruta_destino, marcas):
    """Escribe las marcas sobre una copia limpia del PDF de origen.

    marcas: dict {numero_de_pagina: [marca, ...]}, donde cada marca es
        {"tipo": "lapiz", "trazos": [[(x, y), ...], ...], "color": (r,g,b), "grosor": float}
        {"tipo": "texto", "x": float, "y": float, "texto": str, "color": (r,g,b)}

    Siempre se parte del PDF original en disco (no de la copia en memoria del
    visor) para que guardar varias veces no acumule capas ni degrade el archivo.
    Devuelve la ruta escrita.
    """
    mismo_archivo = os.path.abspath(ruta_origen) == os.path.abspath(ruta_destino)
    salida = ruta_destino + ".tmp-lector" if mismo_archivo else ruta_destino
    fallos = []   # marcas que no se pudieron escribir; se avisan, no se ocultan

    doc = pymupdf.open(ruta_origen)
    try:
        for numero, lista in sorted(marcas.items()):
            if numero < 0 or numero >= doc.page_count:
                continue
            pagina = doc[numero]
            _limpiar_propias(pagina)
            # Espacio sin rotar: identidad si la pagina no esta rotada.
            m = pagina.derotation_matrix
            for indice, marca in enumerate(lista):
                try:
                    if marca["tipo"] == "lapiz":
                        # OJO: add_ink_annot exige pares de float, NO objetos
                        # Point (tira ValueError). Se paso por esto una vez.
                        trazos = []
                        for trazo in marca["trazos"]:
                            if len(trazo) < 2:
                                continue
                            pts = []
                            for (x, y) in trazo:
                                q = pymupdf.Point(x, y) * m
                                pts.append((float(q.x), float(q.y)))
                            trazos.append(pts)
                        if not trazos:
                            continue
                        annot = pagina.add_ink_annot(trazos)
                        annot.set_colors(stroke=tuple(marca["color"]))
                        annot.set_border(width=float(marca.get("grosor", 2.5)))
                        annot.set_info(title=AUTOR)
                        annot.update()
                        _poner_nombre(doc, annot, marca, numero, indice)
                    elif marca["tipo"] == "texto":
                        texto = marca.get("texto", "")
                        if not texto.strip():
                            continue
                        # Si la nota esta anclada a una frase del manual, se
                        # escribe ademas un resaltado sobre esas palabras. Esa
                        # es la parte que le dice al agente A QUE se referia la
                        # nota, sin que tenga que deducirlo por la posicion.
                        _poner_ancla(doc, pagina, m, marca, numero, indice)
                        rect = (rect_nota(marca["x"], marca["y"], texto) * m).normalize()
                        annot = pagina.add_freetext_annot(
                            rect, texto,
                            fontsize=CUERPO_NOTA,
                            fontname="helv",
                            text_color=tuple(marca["color"]),
                            fill_color=FONDO_NOTA,
                            border_width=0.6,
                        )
                        # /Contents: el texto entero, pase lo que pase con el dibujo.
                        annot.set_info(title=AUTOR, content=texto)
                        annot.update()
                        _poner_nombre(doc, annot, marca, numero, indice)
                except Exception as e:
                    fallos.append("pagina %d, %s: %s" % (numero + 1, marca.get("tipo"), e))
                    continue

        meta = dict(doc.metadata or {})
        meta["producer"] = MARCA_PRODUCTOR
        try:
            doc.set_metadata(meta)
        except Exception:
            pass

        doc.save(salida, garbage=3, deflate=True)
    finally:
        doc.close()

    if mismo_archivo:
        # Windows no deja reemplazar un archivo que otro proceso tiene abierto.
        # Pasa cuando se guarda encima del PDF que se esta mirando: quien llama
        # tiene que cerrar su copia antes (el visor lo hace). Si igual falla, se
        # borra el temporal: nunca dejar un .tmp-lector tirado al lado del PDF.
        try:
            os.replace(salida, ruta_destino)
        except OSError:
            try:
                os.remove(salida)
            except OSError:
                pass
            raise
    if fallos:
        raise MarcasNoGuardadas(fallos, ruta_destino)
    return ruta_destino


def abrir_para_editar(ruta):
    """Devuelve (doc, marcas) listos para el visor.

    El doc que se devuelve NO tiene las marcas propias: el visor las dibuja por
    su cuenta a partir de la lista, asi que si tambien vinieran dibujadas en la
    pagina se verian dos veces (y al borrar una, la copia de abajo quedaria).
    Las anotaciones hechas con otros programas se dejan tal cual.
    """
    doc = pymupdf.open(ruta)
    if doc.needs_pass:
        # PyMuPDF diria "document closed or encrypted", que no le dice nada a
        # nadie. Mejor nombrar el problema con palabras.
        doc.close()
        raise ValueError(idiomas.t("pdf_con_contrasena"))
    marcas = cargar(doc)
    for numero in range(doc.page_count):
        _limpiar_propias(doc[numero])
    return doc, marcas


def doc_sin_marcas(ruta):
    """Abre el PDF y le quita las marcas propias, en memoria.

    Se usa para leer el texto original limpio: get_text() de PyMuPDF incluye
    tambien el texto dibujado por las anotaciones, asi que sin esto el "canal 1"
    (lo que decia el manual) saldria mezclado con el "canal 2" (lo que escribio
    David encima) y el agente leeria sus propias notas como parte del documento.
    """
    doc = pymupdf.open(ruta)
    for numero in range(doc.page_count):
        _limpiar_propias(doc[numero])
    return doc


# ----------------------------------------------------------------- cargar ----

def _leer_ref(info):
    """Nombre de la marca a la que se refiere esta, si se refiere a alguna."""
    subj = (info or {}).get("subject", "") or ""
    if subj.startswith(PREFIJO_REF):
        return limpiar_nombre(subj[len(PREFIJO_REF):])
    return ""


def _color_de_la_letra(doc, annot):
    """Color del TEXTO de una nota, leido de su /DA.

    annot.colors["stroke"] de un FreeText devuelve el color del recuadro (el
    amarillo del fondo), no el de la letra. Si se usara ese, al reabrir una
    devolucion las notas quedarian escritas en amarillo sobre fondo amarillo:
    invisibles. El color de la letra vive en /DA, con la forma
    "0.88 0.19 0.19 rg /Helv 11.0 Tf".
    """
    try:
        clase, valor = doc.xref_get_key(annot.xref, "DA")
        if clase == "string" and valor:
            partes = valor.split()
            for i, p in enumerate(partes):
                if p == "rg" and i >= 3:
                    return tuple(float(x) for x in partes[i - 3:i])
                if p == "g" and i >= 1:
                    gris = float(partes[i - 1])
                    return (gris, gris, gris)
                if p == "k" and i >= 4:
                    c, m, y, k = (float(x) for x in partes[i - 4:i])
                    return ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    except Exception:
        pass
    return (0.13, 0.15, 0.16)      # negro: siempre legible sobre el fondo claro


def cargar(doc):
    """Lee del documento las marcas propias y las devuelve en el formato de guardar().

    Se usa al abrir un PDF que ya fue marcado antes, para poder seguir
    editandolo en vez de empezar de nuevo.
    """
    marcas = {}
    for numero in range(doc.page_count):
        pagina = doc[numero]
        m = pagina.rotation_matrix  # vuelve del espacio sin rotar al visible

        # Primera pasada: juntar los resaltados de anclaje, para poder
        # engancharlos con su nota cuando aparezca mas abajo.
        anclas = {}
        for annot in pagina.annots():
            try:
                info = annot.info or {}
                if info.get("title", "") != AUTOR:
                    continue
                tipo = annot.type[1] if isinstance(annot.type, (list, tuple)) else ""
                nombre = info.get("id", "") or ""
                if tipo not in ("Underline", "Highlight") or not nombre.endswith(SUFIJO_ANCLA):
                    continue
                v = annot.vertices or []
                rects = []
                if len(v) >= 4 and len(v) % 4 == 0:
                    for i in range(0, len(v), 4):
                        r = (pymupdf.Quad(v[i:i + 4]).rect * m).normalize()
                        rects.append((r.x0, r.y0, r.x1, r.y1))
                if rects:
                    anclas[nombre[:-len(SUFIJO_ANCLA)]] = {
                        "rects": rects, "cita": info.get("content", "") or ""}
            except Exception:
                continue

        for annot in pagina.annots():
            try:
                info = annot.info or {}
                if info.get("title", "") != AUTOR:
                    continue
                tipo = annot.type[1] if isinstance(annot.type, (list, tuple)) else ""
                if tipo in ("Underline", "Highlight"):
                    continue      # ya se recogio arriba, va dentro de su nota
                color = (annot.colors or {}).get("stroke") or (0.88, 0.19, 0.19)
                if tipo == "Ink":
                    bruto = annot.vertices or []
                    # PyMuPDF devuelve [[p, p, ...], ...] o una lista plana
                    # segun la version; se normaliza a lista de trazos.
                    if bruto and isinstance(bruto[0], (list, tuple)) and bruto[0] \
                            and isinstance(bruto[0][0], (list, tuple)):
                        trazos_bruto = bruto
                    else:
                        trazos_bruto = [bruto]
                    trazos = []
                    for trazo in trazos_bruto:
                        pts = []
                        for p in trazo:
                            q = pymupdf.Point(p[0], p[1]) * m
                            pts.append((q.x, q.y))
                        if len(pts) >= 2:
                            trazos.append(pts)
                    if trazos:
                        marcas.setdefault(numero, []).append({
                            "tipo": "lapiz",
                            "trazos": trazos,
                            "color": tuple(color[:3]),
                            "grosor": float((annot.border or {}).get("width") or 2.5),
                            "nombre": limpiar_nombre(info.get("id", "")),
                            "ref": _leer_ref(info),
                        })
                elif tipo == "FreeText":
                    rect = (annot.rect * m).normalize()
                    marcas.setdefault(numero, []).append({
                        "tipo": "texto",
                        "x": rect.x0,
                        "y": rect.y0,
                        "texto": info.get("content", "") or "",
                        "color": _color_de_la_letra(doc, annot),
                        "nombre": limpiar_nombre(info.get("id", "")),
                        "ancla": anclas.get(info.get("id", "") or ""),
                        "ref": _leer_ref(info),
                    })
            except Exception:
                continue
    return marcas
