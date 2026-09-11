# -*- coding: utf-8 -*-
"""
leer_devolucion.py — convierte un PDF marcado en los dos canales que necesita el agente.

Uso:
    python leer_devolucion.py "C:\\ruta\\manual-devolucion.pdf"
    python leer_devolucion.py "...pdf" --solo-marcas     (sin el texto del manual)
    python leer_devolucion.py "...pdf" --png-dir CARPETA (donde dejar las imagenes)

Que imprime:
    CANAL 1 — el texto del manual tal como estaba, limpio de marcas.
    CANAL 2 — cada marca de David: que escribio o dibujo, en que pagina, y sobre
              que parte del texto original cae.
    Ademas deja un PNG de cada pagina marcada (pagina + marcas encima) para que
    el agente pueda VER los dibujos, que es lo que el texto no puede contar.

POR QUE ASI: una devolucion marcada a mano tiene dos mitades que se entienden
sola una junto a la otra: lo que decia el documento y lo que David le contesto.
Si llegan mezcladas, el agente lee las notas como si fueran parte del manual.
Por eso el canal 1 se extrae de una copia sin marcas (ver anotaciones.doc_sin_marcas)
y el canal 2 se reconstruye desde las anotaciones, cada una anclada al texto que
tiene debajo.
"""

import os
import sys
import tempfile

# La salida SIEMPRE en UTF-8: el manual trae acentos, comillas y guiones largos,
# y la consola de Windows arranca en cp850. Sin esto, el informe se corta con un
# UnicodeEncodeError en la primera tilde y el agente recibe un error en lugar de
# la devolucion.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
import anotaciones as A

DPI_PNG = 120
# Cuanto se estira hacia arriba el recuadro de un trazo para encontrar el texto:
# un subrayado se dibuja DEBAJO del renglon, asi que sin esto no encontraria nada.
ALTO_RENGLON = 14.0


def palabras(pagina):
    """Palabras del original con su recuadro: (rect, texto)."""
    salida = []
    for w in pagina.get_text("words"):
        salida.append((pymupdf.Rect(w[0], w[1], w[2], w[3]), w[4]))
    return salida


def texto_en(palabras_pagina, rect, ancho_pagina=None):
    """Texto del original que cae dentro del recuadro.

    Si no hay nada, se prueba con la banda horizontal completa a esa altura:
    una flecha al margen igual esta senalando ese renglon.
    """
    def juntar(r):
        """Arma el texto marcado sin inventar frases.

        Las palabras que caen en el recuadro pueden venir de bloques que en la
        hoja estan separados (un titulo y el pie de pagina, dos columnas). Si se
        pegan sin mas, sale una frase que en el manual no existe y el agente la
        cita como si estuviera escrita. Por eso los saltos se marcan: " / " entre
        renglones y " ... " cuando hay un hueco grande dentro del mismo renglon.
        """
        elegidas = [(wr, t) for wr, t in palabras_pagina
                    if (wr & r).get_area() > 0.25 * wr.get_area()]
        elegidas.sort(key=lambda p: (round(p[0].y0 / 4), p[0].x0))
        partes = []
        anterior = None
        for wr, t in elegidas:
            if anterior is not None:
                mismo_renglon = abs(wr.y0 - anterior.y0) < 4
                if not mismo_renglon:
                    partes.append("/")
                elif wr.x0 - anterior.x1 > 28:
                    partes.append("...")
            partes.append(t)
            anterior = wr
        return " ".join(partes).strip(" /.")

    r = pymupdf.Rect(rect.x0, rect.y0 - ALTO_RENGLON, rect.x1, rect.y1 + 3)
    t = juntar(r)
    if t:
        return t, "dentro de la marca"
    if ancho_pagina:
        banda = pymupdf.Rect(0, rect.y0 - ALTO_RENGLON, ancho_pagina, rect.y1 + 3)
        t = juntar(banda)
        if t:
            return t, "renglon a esa altura"
    return "", "sin texto cerca"


def contexto_nota(palabras_pagina, rect, ancho_pagina):
    """Que hay alrededor del lugar donde se pego una nota.

    Una nota no cae "sobre" un texto como un subrayado: se pega en un hueco, al
    margen o entre dos bloques. Adivinar a cual de los dos se refiere sale mal:
    una nota escrita en el blanco debajo de un parrafo termina atribuida al
    titulo de la seccion siguiente, y entonces el agente corrige el lugar
    equivocado del manual. Por eso no se elige: se muestran los tres vecinos
    (arriba, a la misma altura, abajo) y que decida quien lee, con todo a la vista.
    """
    # Renglones de la pagina, cada uno con su alto y su texto.
    filas = {}
    for wr, t in palabras_pagina:
        filas.setdefault(round(wr.y0 / 4.0), []).append((wr, t))
    renglones = []
    for _, ws in filas.items():
        ws.sort(key=lambda p: p[0].x0)
        renglones.append((min(w[0].y0 for w in ws), max(w[0].y1 for w in ws),
                          " ".join(t for _, t in ws).strip()))
    renglones.sort()

    def vecino(y_ref, hacia_arriba, cuantos=2, tope=260.0):
        """El texto mas cercano en esa direccion, con la distancia en puntos.

        Se busca el renglon mas proximo en vez de mirar una franja de alto fijo:
        el hueco donde se pega una nota puede ser de 20 puntos o de 200, y con
        una franja fija el vecino de un hueco grande no aparece nunca.
        """
        if hacia_arriba:
            cand = [r for r in renglones if r[1] <= y_ref + 1][-cuantos:]
            dist = (y_ref - cand[-1][1]) if cand else None
        else:
            cand = [r for r in renglones if r[0] >= y_ref - 1][:cuantos]
            dist = (cand[0][0] - y_ref) if cand else None
        if not cand or dist is None or dist > tope:
            return "", None
        return " ".join(r[2] for r in cand).strip(), dist

    a_la_altura = " ".join(r[2] for r in renglones
                           if r[1] > rect.y0 and r[0] < rect.y1).strip()
    return vecino(rect.y0, True), a_la_altura, vecino(rect.y1, False)


def figuras_en(pagina, rect):
    """Dice si la marca cae sobre una imagen o figura de la pagina.

    Sin esto, una flecha que senala un diagrama sale como "(nada)", que se lee
    como "no marco nada" cuando en realidad marco lo mas importante de la hoja.
    """
    try:
        for info in pagina.get_images(full=True):
            for r in pagina.get_image_rects(info[0]):
                if (r & rect).get_area() > 0.15 * min(r.get_area() or 1, rect.get_area() or 1):
                    return "una imagen o figura de la pagina (%.0f x %.0f pt)" % (r.width, r.height)
    except Exception:
        pass
    return ""


def cita(texto, tope=420):
    """Recorta una cita larga avisando que fue recortada.

    Sin el aviso, una cita cortada parece completa y el agente puede creer que
    la marca abarca menos texto del que abarca. Un parrafo de manual pasa el
    tope casi siempre.
    """
    texto = (texto or "").strip()
    if len(texto) <= tope:
        return '"%s"' % texto
    corte = texto.rfind(" ", 0, tope)
    if corte < tope * 0.6:
        corte = tope
    return '"%s..." (+%d caracteres mas hasta el final del bloque marcado)' % (
        texto[:corte].rstrip(), len(texto) - corte)


def informe(ruta, solo_marcas=False, png_dir=None):
    if not os.path.isfile(ruta):
        print("No existe el archivo: %s" % ruta)
        return 1

    doc_marcado = pymupdf.open(ruta)
    marcas = A.cargar(doc_marcado)
    limpio = A.doc_sin_marcas(ruta)

    producer = (doc_marcado.metadata or {}).get("producer") or ""
    total = sum(len(v) for v in marcas.values())
    paginas_con_marcas = sorted(marcas.keys())

    print("=" * 78)
    print("DEVOLUCION: %s" % os.path.basename(ruta))
    print("%d pagina(s) | %d marca(s) en la(s) pagina(s): %s"
          % (limpio.page_count, total,
             ", ".join(str(p + 1) for p in paginas_con_marcas) or "ninguna"))
    if A.MARCA_PRODUCTOR not in producer:
        print("AVISO: este PDF no fue marcado con el Lector PDF (producer=%r)." % producer)
        if total == 0:
            print("       Si esperabas marcas, puede que esten aplanadas como imagen,")
            print("       o hechas con otro programa (otro autor en las anotaciones).")
    print("=" * 78)

    if not solo_marcas:
        print("\n### CANAL 1 — EL MANUAL (texto original, sin las marcas)\n")
        for n in range(limpio.page_count):
            texto = limpio[n].get_text().strip()
            print("--- pagina %d ---" % (n + 1))
            print(texto if texto else "(pagina sin texto: probablemente una imagen o un diagrama)")
            print()

    print("\n### CANAL 2 — LA DEVOLUCION (lo que marco David)\n")
    print("Cada marca tiene un nombre propio. Sirve para contestarle a David hablando")
    print("de una marca concreta (\"lo de dibujo-p02-1\") sin que tenga que abrir el PDF.")
    print("Las que dicen NOTA SOBRE UNA FRASE estan atadas a esas palabras exactas:")
    print("ahi no hay nada que interpretar. Las que dicen NOTA ESCRITA son sueltas, y de")
    print("esas se muestran los vecinos para ubicarlas.")
    print("")
    if total == 0:
        print("No hay ninguna marca propia en este PDF.")
    for n in paginas_con_marcas:
        pg_limpia = limpio[n]
        palabras_pg = palabras(pg_limpia)
        ancho = pg_limpia.rect.width
        lista = marcas[n]

        # Orden de lectura: de arriba hacia abajo, y a igual altura de izq a der.
        def clave(mk):
            r = (A.bbox_trazo(mk["trazos"], mk.get("grosor", 2.0)) if mk["tipo"] == "lapiz"
                 else A.rect_nota(mk["x"], mk["y"], mk["texto"]))
            return (round(r.y0 / 10), r.x0)

        print("--- pagina %d (%d marca(s)) ---" % (n + 1, len(lista)))
        # Si la marca no trae nombre (viene de un PDF marcado con una version
        # vieja, o de otro programa), se le calcula el mismo que usaria el
        # visor, para poder nombrarla igual.
        for indice, mk in enumerate(lista):
            if not mk.get("nombre"):
                mk["nombre"] = A.nombre_por_defecto(mk["tipo"], n, indice)
        for mk in sorted(lista, key=clave):
            if mk["tipo"] == "texto":
                rect = A.rect_nota(mk["x"], mk["y"], mk["texto"])
                ancla = mk.get("ancla")
                if ancla and ancla.get("cita"):
                    # Nota ATADA a una frase: no hay nada que deducir. David
                    # eligio esas palabras y escribio sobre ellas.
                    print("\n  [NOTA SOBRE UNA FRASE]  pagina %d  ·  se llama \"%s\""
                          % (n + 1, mk.get("nombre") or "(sin nombre)"))
                    print("    Sobre esta frase del manual:")
                    print("      %s" % cita(ancla["cita"], 500))
                    if mk.get("ref"):
                        print("    Y ademas se refiere a la marca: %s" % mk["ref"])
                    print("    David escribio:")
                    for linea in mk["texto"].splitlines():
                        print("      > %s" % linea)
                    continue
                (arriba, d_arr), altura, (abajo, d_aba) = contexto_nota(
                    palabras_pg, rect, ancho)
                print("\n  [NOTA ESCRITA]  pagina %d  ·  se llama \"%s\""
                      % (n + 1, mk.get("nombre") or "(sin nombre)"))
                for linea in mk["texto"].splitlines():
                    print("    > %s" % linea)
                print("    Donde la pego (los tres vecinos, para no atribuirla mal):")
                print("      justo encima%s: %s"
                      % ((" (a %.0f pt)" % d_arr) if d_arr is not None else " ........",
                         cita(arriba, 300) if arriba else "(nada)"))
                print("      a esa altura ...: %s"
                      % (cita(altura, 300) if altura else "(hueco en blanco)"))
                print("      justo debajo%s: %s"
                      % ((" (a %.0f pt)" % d_aba) if d_aba is not None else " ........",
                         cita(abajo, 300) if abajo else "(nada)"))
            else:
                rect = A.bbox_trazo(mk["trazos"], mk.get("grosor", 2.0))
                ref, como = texto_en(palabras_pg, rect, ancho)
                puntos = sum(len(t) for t in mk["trazos"])
                print("\n  [DIBUJO A MANO]  %d trazo(s), %d puntos, color %s  ·  se llama \"%s\""
                      % (len(mk["trazos"]), puntos, nombre_color(mk["color"]),
                         mk.get("nombre") or "(sin nombre)"))
                print("    zona: %.0f x %.0f pt, esquina (%.0f, %.0f)"
                      % (rect.width, rect.height, rect.x0, rect.y0))
                if ref:
                    print("    encima de (%s): %s" % (como, cita(ref)))
                else:
                    fig = figuras_en(limpio[n], rect)
                    print("    encima de: %s" % (fig if fig else
                          "(ni texto ni figura: puede ser una marca al margen)"))
                if mk.get("ancla") and mk["ancla"].get("cita"):
                    print("    ATADO a esta frase del manual: %s"
                          % cita(mk["ancla"]["cita"], 400))
                if mk.get("ref"):
                    print("    Se refiere a la marca: %s" % mk["ref"])
                print("    -> mirar el PNG de la pagina %d para ver la forma del trazo." % (n + 1))
        print()

    # Imagenes: sin esto, un circulo y una flecha son el mismo dato.
    if paginas_con_marcas:
        destino = png_dir or os.path.join(tempfile.gettempdir(), "devolucion_png")
        os.makedirs(destino, exist_ok=True)
        print("\n### IMAGENES (pagina con las marcas encima)\n")
        z = DPI_PNG / 72.0
        for n in paginas_con_marcas:
            pix = doc_marcado[n].get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False, annots=True)
            archivo = os.path.normpath(os.path.join(destino, "pagina_%02d.png" % (n + 1)))
            pix.save(archivo)
            print("  %s" % archivo)
        print("\n  El agente tiene que ABRIR estas imagenes: el texto de arriba dice")
        print("  donde cae cada trazo, pero no si es un circulo, un tachado o una flecha.")

    limpio.close()
    doc_marcado.close()
    return 0


def nombre_color(c):
    refs = [("rojo", (0.88, 0.19, 0.19)), ("naranja", (0.96, 0.41, 0.03)),
            ("verde", (0.18, 0.62, 0.27)), ("azul", (0.10, 0.44, 0.76)),
            ("negro", (0.13, 0.15, 0.16))]
    mejor, dist = "?", 9.0
    for nombre, r in refs:
        d = sum((a - b) ** 2 for a, b in zip(c[:3], r))
        if d < dist:
            mejor, dist = nombre, d
    return mejor


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    solo = "--solo-marcas" in args
    png_dir = None
    if "--png-dir" in args:
        i = args.index("--png-dir")
        if i + 1 < len(args):
            png_dir = args[i + 1]
            del args[i:i + 2]
    rutas = [a for a in args if not a.startswith("--")]
    if not rutas:
        print("Falta la ruta del PDF.")
        return 2
    return informe(rutas[0], solo_marcas=solo, png_dir=png_dir)


if __name__ == "__main__":
    sys.exit(main())
