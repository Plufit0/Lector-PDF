# -*- coding: utf-8 -*-
"""
anotaciones.py — guardar y leer las marcas de una devolucion dentro del PDF.

Modulo compartido por:
  - lector.pyw          (el programa con el que se marca)
  - leer_devolucion.py  (el que usa el agente para entender la devolucion)

DECISIONES DE DISENO (no cambiar sin leer esto):

1. Las marcas se guardan como ANOTACIONES PDF ESTANDAR (Ink para los trazos,
   FreeText para los textos), no como pixeles quemados sobre la pagina. Por eso
   el texto original del documento sigue siendo extraible intacto: ese es el
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
   normal no paga nada). La mayoria de los PDF no vienen rotados, pero algunos
   si, y una marca desplazada 90 grados seria un dolor de cabeza dificil de
   entender.

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
# El extractor busca solo "Lector PDF" (FIRMA_PRODUCTOR), asi reconoce tambien
# los PDF marcados con versiones viejas, que decian "...de manual de diseno".
MARCA_PRODUCTOR = "Lector PDF - devolucion"
FIRMA_PRODUCTOR = "Lector PDF"
# Grosor de un trazo cuando no dice cual tiene (el "Fino" del visor).
GROSOR_POR_DEFECTO = 2.0

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
# Tamano de letra de las notas, en puntos PDF. Es el de entrada: cada nota
# puede tener el suyo (clave "cuerpo"), que se cambia arrastrando una esquina de
# la nota (decision del Disenador, sept-2026: esquinas = tamano de letra,
# costados = ancho, como Canva, tldraw y Excalidraw).
CUERPO_NOTA = 11.0
# Limites del tamano de letra de una nota, en puntos PDF.
CUERPO_MIN = 6.0
CUERPO_MAX = 48.0
# Alto de linea al maquetar una nota.
ALTO_LINEA = CUERPO_NOTA * 1.30

# Fondo de las notas de texto (amarillo papel) y su borde.
FONDO_NOTA = (1.0, 0.96, 0.70)
# Grosor del borde de la nota, en puntos PDF. PyMuPDF agranda el Rect de la
# anotacion medio borde por lado: al reabrir hay que descontarlo (ver cargar).
BORDE_NOTA = 0.6
# Clave propia del PDF donde se guarda el ancho elegido de una nota. Los otros
# visores ignoran las claves que no conocen, asi que no molesta a nadie.
CLAVE_ANCHO = "LectorAncho"

# Color del subrayado con el que se marca la frase a la que se ata una marca,
# y su opacidad. Tenue a proposito: tiene que senalar sin ensuciar la hoja ni
# competir con lo que el usuario escribio.
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

    Sirve para que el usuario y el agente puedan hablar de una marca concreta
    ("lo que dice la nota-p05-3") sin tener el documento delante.
    """
    return "%s-p%02d-%d" % ("dibujo" if tipo == "lapiz" else "nota", pagina + 1, indice + 1)


_FUENTE_NOTA = None


def _ancho_texto(cadena):
    """Ancho en puntos PDF de una linea, en la fuente de las notas (Helvetica).

    Se mide con pymupdf.Font y NO con pymupdf.get_text_length: esta ultima
    pierde los espacios que siguen a una letra con tilde o una ene, y la caja
    quedaba mas corta que el texto (se cortaba el final de la nota).
    """
    global _FUENTE_NOTA
    try:
        if _FUENTE_NOTA is None:
            _FUENTE_NOTA = pymupdf.Font("helv")
        return _FUENTE_NOTA.text_length(cadena, fontsize=CUERPO_NOTA)
    except Exception:
        # Estimacion prudente si la medicion real no esta disponible.
        return len(cadena) * CUERPO_NOTA * 0.55


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


def escala_nota(cuerpo=None):
    """Cuanto mas grande (o chica) es una nota que la de entrada.

    Una nota con letra de 22 pt es la de 11 pt al doble: margen, alto de
    renglon, ancho minimo y ancho de entrada crecen en la misma proporcion.
    Como el ancho del texto crece exactamente con la letra, el corte de
    renglones no cambia: agrandar la letra agranda la nota entera, igual.
    """
    try:
        cuerpo = float(cuerpo or CUERPO_NOTA)
    except (TypeError, ValueError):
        cuerpo = CUERPO_NOTA
    return max(CUERPO_MIN, min(CUERPO_MAX, cuerpo)) / CUERPO_NOTA


def _maquetar_nota(texto, ancho=None, cuerpo=None):
    """(ancho_util, lineas): como queda partida una nota dentro de su caja.

    Es la UNICA fuente de verdad del corte de renglones: la usan la caja
    (medir_nota), el visor para dibujar linea por linea y el PDF guardado. Si
    cada uno cortara por su cuenta, el texto se saldria de la caja.

    ancho: el ancho que eligio el usuario arrastrando un costado de la nota
    (en puntos PDF, caja entera). Sin elegir, es ANCHO_NOTA (a escala). Es un
    TOPE: la caja nunca queda mas ancha que su renglon mas largo (fit to size),
    asi que agrandarlo "desenrolla" renglones hasta que el texto entra en uno.

    cuerpo: tamano de letra de la nota. Todo se calcula a la letra de entrada
    y despues se multiplica por la escala (ver escala_nota).
    """
    f = escala_nota(cuerpo)
    tope_util = max(ANCHO_MIN_NOTA, (ancho / f) if ancho else ANCHO_NOTA) - 2 * PAD_NOTA
    # Primero se parte al tope; despues la caja se ajusta al renglon mas ancho
    # que haya quedado. Si una sola palabra es mas ancha que el tope (no se
    # puede partir), la caja la envuelve entera en vez de dejarla saliendose.
    lineas = []
    for parrafo in (texto or "").split("\n"):
        lineas.extend(_envolver(parrafo, tope_util) if parrafo else [""])
    mas_ancha = max((_ancho_texto(l) for l in lineas), default=0.0)
    return max(ANCHO_MIN_NOTA - 2 * PAD_NOTA, mas_ancha) * f, lineas


def lineas_nota(texto, ancho=None, cuerpo=None):
    """Los renglones de una nota tal como entran en su caja."""
    return _maquetar_nota(texto, ancho, cuerpo)[1]


# Alto de la letra sobre la linea base, en "em" (Helvetica/Arial). Sirve para
# ubicar la linea base de cada renglon igual en pantalla y en el PDF.
ASCENSO = 0.905
# Alto de renglon "natural" de la letra (Tk lo llama linespace), en em.
RENGLON_NATURAL = 1.15


def tope_renglon(k, cuerpo=None):
    """Distancia desde el borde de arriba de la caja hasta el renglon k.

    La usan la pantalla (visor) y el PDF (_dibujar_nota_en_pdf): con la misma
    cuenta en los dos lados, la nota guardada se ve igual que en pantalla.
    """
    f = escala_nota(cuerpo)
    return f * (PAD_NOTA + (ALTO_LINEA - RENGLON_NATURAL * CUERPO_NOTA) / 2.0 + k * ALTO_LINEA)


def _entra_en_la_letra(texto):
    """True si todos los caracteres existen en la letra de las notas (WinAnsi)."""
    try:
        texto.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def _texto_pdf(cadena):
    """Una linea lista para escribir en el PDF: WinAnsi y con escapes."""
    salida = []
    for c in cadena.encode("cp1252", "replace"):
        if c in (0x28, 0x29, 0x5C):             # ( ) \  van escapados
            salida.append("\\" + chr(c))
        elif 32 <= c < 127:
            salida.append(chr(c))
        else:                                     # acentos, enes: en octal
            salida.append("\\%03o" % c)
    return "".join(salida)


def _dibujar_nota_en_pdf(doc, annot, texto, color, borde, ancho=None, cuerpo=None):
    """Redibuja la nota dentro del PDF igual que en pantalla.

    PyMuPDF dibuja el texto de un FreeText casi pegado al borde (1,2 pt), asi que
    la caja quedaba con aire solo a la derecha y abajo. Aca se reemplaza ese
    dibujo por uno propio: mismo margen interno, mismo alto de renglon y mismo
    corte de lineas que el visor. El texto completo sigue en /Contents.

    Solo en paginas sin rotar: en una rotada se deja el dibujo de PyMuPDF, que
    sabe acomodar la rotacion. Tampoco si el texto trae simbolos que la letra
    de las notas no tiene (flechas, tildes de "check", alfabetos no latinos):
    esos saldrian como "?", y PyMuPDF si sabe buscarles otra letra.
    Si algo falla, tambien queda el de PyMuPDF.
    """
    if not _entra_en_la_letra(texto):
        return
    try:
        clase, valor = doc.xref_get_key(annot.xref, "AP/N")
        if clase != "xref":
            return
        xref = int(valor.split()[0])
        clase, caja = doc.xref_get_key(xref, "BBox")
        bx0, by0, bx1, by1 = (float(v) for v in caja.strip("[]").split())
        # El Rect de la anotacion viene agrandado medio borde por lado.
        m = borde / 2.0
        x0, y0, x1, y1 = bx0 + m, by0 + m, bx1 - m, by1 - m
        f = escala_nota(cuerpo)
        letra = CUERPO_NOTA * f
        partes = [
            "q",
            "%.4f %.4f %.4f rg" % tuple(FONDO_NOTA),
            "%.4f %.4f %.4f RG" % tuple(color),
            "%.2f w" % borde,
            "%.3f %.3f %.3f %.3f re B" % (x0, y0, x1 - x0, y1 - y0),
            "BT",
            "/Helv %.2f Tf" % letra,
            "%.4f %.4f %.4f rg" % tuple(color),
        ]
        for k, linea in enumerate(lineas_nota(texto, ancho, cuerpo)):
            base = y1 - tope_renglon(k, cuerpo) - ASCENSO * letra
            partes.append("1 0 0 1 %.3f %.3f Tm (%s) Tj"
                          % (x0 + PAD_NOTA * f, base, _texto_pdf(linea)))
        partes += ["ET", "Q"]
        doc.update_stream(xref, "\n".join(partes).encode("latin-1"))
    except Exception:
        pass


def medir_nota(texto, ancho=None, cuerpo=None):
    """Ancho y alto del recuadro de una nota, ajustados a su texto (fit to size).

    La caja crece solo lo necesario: se estira con la linea mas larga hasta el
    tope (ANCHO_NOTA, o el ancho que eligio el usuario) y ahi para, partiendo el
    texto en varias lineas. Asi el fondo nunca deja un hueco vacio al costado.
    """
    f = escala_nota(cuerpo)
    ancho_util, lineas = _maquetar_nota(texto, ancho, cuerpo)
    ancho = ancho_util + 2 * PAD_NOTA * f
    alto = f * (max(1, len(lineas)) * ALTO_LINEA + 2 * PAD_NOTA)
    return ancho, alto


def rect_nota(x, y, texto, ancho=None, cuerpo=None):
    """Recuadro PDF de una nota, ajustado a su texto, esquina sup-izq en x,y."""
    w, h = medir_nota(texto, ancho, cuerpo)
    return pymupdf.Rect(x, y, x + w, y + h)


def rect_de(marca):
    """Recuadro PDF de una nota a partir de la marca entera (atajo de rect_nota)."""
    return rect_nota(marca["x"], marca["y"], marca.get("texto", ""),
                     marca.get("ancho"), marca.get("cuerpo"))


def bbox_trazo(trazos, grosor):
    """Recuadro que envuelve a un trazo de lapiz, con el margen del grosor."""
    xs = [p[0] for t in trazos for p in t]
    ys = [p[1] for t in trazos for p in t]
    if not xs:
        return pymupdf.Rect(0, 0, 0, 0)
    m = max(1.0, grosor)
    return pymupdf.Rect(min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)


# ---------------------------------------------------------------- guardar ----

def _poner_nombre(doc, annot, marca):
    """Graba el nombre de la marca en el campo /NM del PDF.

    PyMuPDF no deja escribirlo con set_info, hay que tocar el objeto directo.
    Es el identificador con el que la persona y el agente pueden referirse a
    una marca concreta sin tener el documento a la vista. Si falla, se avisa
    (decision 6 del visor: nunca guardar en silencio algo incompleto).
    """
    doc.xref_set_key(annot.xref, "NM", "(%s)" % marca["nombre"])
    # Si la marca se refiere a OTRA marca (no a una frase), se guarda el nombre
    # de esa otra en el campo /Subj, que es texto libre del formato PDF.
    ref = limpiar_nombre(marca.get("ref"))
    if ref:
        annot.set_info(title=AUTOR, subject=PREFIJO_REF + ref)
        annot.update()


def _poner_ancla(doc, pagina, matriz, marca):
    """Subrayado tenue sobre la frase a la que esta atada la marca.

    Sirve igual para notas y para dibujos: antes solo las notas guardaban su
    frase, y un dibujo hecho con "Dibujar sobre esta frase" perdia la atadura
    al guardar.
    """
    ancla = marca.get("ancla")
    if not ancla or not ancla.get("rects"):
        return
    quads = [(pymupdf.Rect(x0, y0, x1, y1) * matriz).normalize().quad
             for (x0, y0, x1, y1) in ancla["rects"]]
    # Subrayado, no resaltado: el bloque de color encima de las palabras
    # ensucia la pagina y cuesta leer lo que esta marcado. Una linea abajo
    # dice lo mismo sin taparlo.
    annot = pagina.add_underline_annot(quads)
    annot.set_colors(stroke=COLOR_ANCLA)
    # En /Contents va la FRASE DEL DOCUMENTO, no la nota: asi el subrayado se
    # explica solo aunque se lea con otro programa.
    annot.set_info(title=AUTOR, content=ancla.get("cita", "")[:2000])
    annot.update(opacity=OPACIDAD_ANCLA)
    doc.xref_set_key(annot.xref, "NM", "(%s%s)" % (marca["nombre"], SUFIJO_ANCLA))


def _nombres_unicos(marcas):
    """Le da a cada marca un nombre propio y sin repetir, y lo deja puesto.

    Dos marcas con el mismo nombre se confundian al reabrir (la frase de una
    terminaba en la otra). Y los nombres por defecto dependian del lugar en la
    lista ("dibujo-p01-2"): al borrar la primera, una referencia a la segunda
    pasaba a apuntar a otra. Ahora el nombre se fija la primera vez que se
    guarda y queda en la marca para siempre.
    """
    usados = set()
    for numero, lista in sorted(marcas.items()):
        for indice, marca in enumerate(lista):
            base = limpiar_nombre(marca.get("nombre")) or nombre_por_defecto(
                marca["tipo"], numero, indice)
            nombre, n = base, 2
            while nombre in usados:
                nombre = "%s-%d" % (base, n)
                n += 1
            usados.add(nombre)
            marca["nombre"] = nombre


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


def misma_ruta(a, b):
    """True si dos rutas son el mismo archivo (Windows no distingue mayusculas)."""
    return (os.path.normcase(os.path.abspath(a))
            == os.path.normcase(os.path.abspath(b)))


def guardar(ruta_origen, ruta_destino, marcas):
    """Escribe las marcas sobre una copia limpia del PDF de origen.

    marcas: dict {numero_de_pagina: [marca, ...]}, donde cada marca es
        {"tipo": "lapiz", "trazos": [[(x, y), ...], ...], "color": (r,g,b), "grosor": float}
        {"tipo": "texto", "x": float, "y": float, "texto": str, "color": (r,g,b)}
    (mas "nombre", "ancla", "ref" y, en las notas, "ancho" y "cuerpo", todas
    opcionales).

    Siempre se parte del PDF original en disco (no de la copia en memoria del
    visor) para que guardar varias veces no acumule capas ni degrade el archivo.
    Devuelve la ruta escrita.
    """
    mismo_archivo = misma_ruta(ruta_origen, ruta_destino)
    salida = ruta_destino + ".tmp-lector" if mismo_archivo else ruta_destino
    fallos = []   # marcas que no se pudieron escribir; se avisan, no se ocultan
    _nombres_unicos(marcas)

    doc = pymupdf.open(ruta_origen)
    try:
        # Se limpian TODAS las paginas, no solo las que tienen marcas: si no,
        # una marca vieja de una pagina que ahora quedo vacia sobrevivia en el
        # archivo sin que el visor la mostrara.
        for pagina in doc:
            _limpiar_propias(pagina)
        for numero, lista in sorted(marcas.items()):
            if numero < 0 or numero >= doc.page_count:
                continue
            pagina = doc[numero]
            # Espacio sin rotar: identidad si la pagina no esta rotada.
            m = pagina.derotation_matrix
            for marca in lista:
                que = "pagina %d, %s" % (numero + 1, marca["nombre"])
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
                        annot.set_border(width=float(marca.get("grosor", GROSOR_POR_DEFECTO)))
                        annot.set_info(title=AUTOR)
                        annot.update()
                    elif marca["tipo"] == "texto":
                        texto = marca.get("texto", "")
                        if not texto.strip():
                            continue
                        ancho = marca.get("ancho")
                        cuerpo = marca.get("cuerpo")
                        rect = (rect_nota(marca["x"], marca["y"], texto, ancho, cuerpo)
                                * m).normalize()
                        # El tamano de letra va en el lugar estandar del PDF
                        # (/DA de la FreeText): cualquier otro visor lo respeta.
                        annot = pagina.add_freetext_annot(
                            rect, texto,
                            fontsize=CUERPO_NOTA * escala_nota(cuerpo),
                            fontname="helv",
                            text_color=tuple(marca["color"]),
                            fill_color=FONDO_NOTA,
                            border_width=BORDE_NOTA,
                        )
                        # /Contents: el texto entero, pase lo que pase con el dibujo.
                        annot.set_info(title=AUTOR, content=texto)
                        annot.update()
                    else:
                        continue
                except Exception as e:
                    fallos.append("%s: %s" % (que, e))
                    continue

                # Lo que acompana a la marca. Si algo de esto falla, la marca
                # queda guardada igual, pero se avisa que llego incompleta.
                try:
                    _poner_nombre(doc, annot, marca)
                except Exception as e:
                    fallos.append("%s (nombre o referencia): %s" % (que, e))
                try:
                    # Si la marca esta atada a una frase, se escribe ademas un
                    # subrayado sobre esas palabras: es lo que le dice al agente
                    # A QUE se referia, sin deducirlo por la posicion.
                    _poner_ancla(doc, pagina, m, marca)
                except Exception as e:
                    fallos.append("%s (frase atada): %s" % (que, e))
                if marca["tipo"] == "texto":
                    # Al final, despues de todo update(): cualquier update
                    # posterior volveria a poner el dibujo de PyMuPDF.
                    if pagina.rotation == 0:
                        _dibujar_nota_en_pdf(doc, annot, texto,
                                             tuple(marca["color"]), BORDE_NOTA, ancho, cuerpo)
                    # El ancho que eligio el usuario (arrastrando el borde) va
                    # en una clave propia: los otros visores la ignoran, y al
                    # reabrir la nota se parte igual que antes.
                    if ancho:
                        doc.xref_set_key(annot.xref, CLAVE_ANCHO, "%.2f" % float(ancho))

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
    (lo que decia el documento) saldria mezclado con el "canal 2" (lo que escribio
    el usuario encima) y el agente leeria sus propias notas como parte del documento.
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


def _cuerpo_de_la_letra(doc, annot):
    """Tamano de letra de una nota, leido de su /DA ("... /Helv 16 Tf").

    Devuelve None si es el de entrada (o no se puede leer): asi una nota comun
    vuelve igual que como se hizo, sin una clave de mas.
    """
    try:
        clase, valor = doc.xref_get_key(annot.xref, "DA")
        if clase == "string" and valor:
            partes = valor.split()
            for i, p in enumerate(partes):
                if p == "Tf" and i >= 1:
                    cuerpo = float(partes[i - 1])
                    if cuerpo > 0 and abs(cuerpo - CUERPO_NOTA) > 0.05:
                        return max(CUERPO_MIN, min(CUERPO_MAX, cuerpo))
                    return None
    except Exception:
        pass
    return None


def es_devolucion(doc):
    """True si el PDF lo escribio este programa (una devolucion ya guardada).

    Sirve para Guardar (Ctrl+S): una devolucion reabierta se guarda encima de
    si misma, como en cualquier editor; un PDF original nunca se toca, asi que
    la primera vez se pregunta el nombre de la copia.
    """
    try:
        return FIRMA_PRODUCTOR in ((doc.metadata or {}).get("producer") or "")
    except Exception:
        return False


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
                            "grosor": float((annot.border or {}).get("width") or GROSOR_POR_DEFECTO),
                            "nombre": limpiar_nombre(info.get("id", "")),
                            "ancla": anclas.get(info.get("id", "") or ""),
                            "ref": _leer_ref(info),
                        })
                elif tipo == "FreeText":
                    rect = (annot.rect * m).normalize()
                    # PyMuPDF agranda el Rect medio borde por lado. Sin
                    # descontarlo, cada guardar+reabrir corria la nota 0,3 pt
                    # hacia arriba a la izquierda, y el corrimiento se acumulaba.
                    medio = float((annot.border or {}).get("width") or 0) / 2.0
                    nota = {
                        "tipo": "texto",
                        "x": rect.x0 + medio,
                        "y": rect.y0 + medio,
                        "texto": info.get("content", "") or "",
                        "color": _color_de_la_letra(doc, annot),
                        "nombre": limpiar_nombre(info.get("id", "")),
                        "ancla": anclas.get(info.get("id", "") or ""),
                        "ref": _leer_ref(info),
                    }
                    try:
                        clase, valor = doc.xref_get_key(annot.xref, CLAVE_ANCHO)
                        if clase in ("real", "int") and float(valor) > 0:
                            nota["ancho"] = float(valor)
                    except Exception:
                        pass
                    cuerpo = _cuerpo_de_la_letra(doc, annot)
                    if cuerpo:
                        nota["cuerpo"] = cuerpo
                    marcas.setdefault(numero, []).append(nota)
            except Exception:
                continue
    return marcas
