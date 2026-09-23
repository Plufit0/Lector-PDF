# -*- coding: utf-8 -*-
"""
guia.py — la hoja-guía que hace que una devolución se explique sola.

Lo usa anotaciones.guardar(): al guardar, el programa agrega al principio del
PDF una hoja en TEXTO real que dice qué es el archivo y describe cada marca
(qué es y sobre qué texto del documento cae), y pone junto a cada marca un
círculo violeta con su número.

DECISIONES DE DISENO:

1. Por qué existe (prueba con Gemini, sept-2026): una IA de chat recibió la
   devolución, vio las notas y los dibujos, pero no supo qué palabra estaba
   tachada ni que "Este color no me gusta" estaba atada a "Negro". Esa
   información la calculaba leer_devolucion.py, que solo corre en la PC. Ahora
   viaja DENTRO del PDF: cualquier IA (o persona) la lee sin programas, sin
   copiar ningún texto aparte y sin pasar por otra IA.

2. Todo sale de cuentas con las posiciones (qué palabras hay debajo de cada
   marca): NO se usa ninguna IA, no cuesta nada y funciona sin internet.

3. La hoja-guía va PRIMERO: quien lee (persona o IA) entiende qué es el archivo
   antes de ver el documento. Se reconoce por la clave /LectorGuia de la
   página, y los números y líneas por su nombre (/NM) con PREFIJO. Al reabrir,
   el programa los quita (anotaciones.quitar_guia / cargar) y se regeneran al
   guardar: la guía siempre coincide con las marcas.

4. El idioma de la guía es el de la interfaz, como el sufijo -devolucion /
   -feedback. Los textos viven acá (no en idiomas.py) porque son contenido del
   archivo, no de la interfaz.
"""

import io

import pymupdf

import idiomas

CLAVE_PAGINA = "LectorGuia"     # clave propia en el diccionario de la hoja-guía
PREFIJO = "guia-"               # /NM de los números y líneas: no son marcas
VIOLETA = (0.45, 0.18, 0.78)
ZW = "​"                   # espacio de ancho cero (lo traen los PDF de Google Docs)

TEXTOS = {
    "titulo": {"es": "Guía de lectura de esta devolución",
               "en": "How to read this feedback file"},
    "agregada": {"es": "Esta hoja la agregó el programa Lector PDF al guardar. No es parte del documento original.",
                 "en": "This page was added by Lector PDF when saving. It is not part of the original document."},
    "intro": {
        "es": "<b>Para la IA o persona que recibe este archivo:</b> alguien leyó el documento que sigue "
              "(desde la hoja %d de este PDF) y lo marcó encima con dibujos, notas y resaltados. "
              "Las marcas <b>no son "
              "parte del documento original</b>: son lo que esa persona comenta o contesta.",
        "en": "<b>For the AI or person receiving this file:</b> someone read the document that follows "
              "(from page %d of this PDF) and marked it up with drawings, notes and highlights. "
              "The marks <b>are not "
              "part of the original document</b>: they are that person's comments or answers."},
    "como": {
        "es": "Cada marca tiene al lado un <b>círculo violeta con un número</b>. Abajo está qué es cada una "
              "y sobre qué texto del documento cae, calculado por el programa a partir de la posición exacta "
              "de la marca. Usá esta lista para saber a qué texto se refiere cada marca, y la imagen de la "
              "hoja para ver la forma de los dibujos. El texto de las notas también aparece escrito dentro "
              "de las hojas: ese texto es de la persona, no del documento.",
        "en": "Each mark has a <b>purple circle with a number</b> next to it. Below is what each one is and "
              "which text of the document it falls on, computed by the program from the exact position of "
              "the mark. Use this list to know what text each mark refers to, and the image of the page to "
              "see the shape of the drawings. The text of the notes also appears written inside the pages: "
              "that text is the person's, not the document's."},
    "n_marcas": {"es": "Las %d marcas", "en": "The %d marks"},
    "una_marca": {"es": "La marca", "en": "The mark"},
    "marca": {"es": "Marca %d", "en": "Mark %d"},
    "hoja": {"es": "hoja %d del PDF (página %d del documento)",
             "en": "page %d of this PDF (page %d of the document)"},
    "dibujo": {"es": "<b>dibujo a mano</b>, %s, %d trazo%s.",
               "en": "<b>freehand drawing</b>, %s, %d stroke%s."},
    "raya": {"es": 'Es una raya casi horizontal que cruza %s: <b>"%s"</b>.',
             "en": 'It is a nearly horizontal line that crosses %s: <b>"%s"</b>.'},
    "medio": {"es": "por el medio (parece un tachado)", "en": "through the middle (looks like a strikethrough)"},
    "debajo": {"es": "por debajo (parece un subrayado)", "en": "underneath (looks like an underline)"},
    "arriba": {"es": "por arriba", "en": "above"},
    "circulo": {"es": 'Es un círculo (una línea que se cierra) que <b>encierra</b>: <b>"%s"</b>.',
                "en": 'It is a circle (a closed line) that <b>encloses</b>: <b>"%s"</b>.'},
    "circulo_vacio": {"es": "Es un círculo (una línea que se cierra) sin texto adentro. "
                            "La forma se ve en la hoja.",
                      "en": "It is a circle (a closed line) with no text inside. "
                            "The shape can be seen on the page."},
    "flecha": {"es": 'Parece una <b>flecha</b>: sale %s y <b>apunta a</b> <b>"%s"</b>.',
               "en": 'It looks like an <b>arrow</b>: it starts %s and <b>points at</b> <b>"%s"</b>.'},
    "de_la_nota": {"es": 'de la nota "%s"', "en": 'from the note "%s"'},
    "de_cerca": {"es": 'de cerca de "%s"', "en": 'near "%s"'},
    "vertical": {"es": 'Es una raya vertical al costado de estos renglones (los marca): "%s".',
                 "en": 'It is a vertical line beside these lines of text (it marks them): "%s".'},
    "tilde": {"es": 'Parece una <b>tilde de visto</b> (✓) junto a <b>"%s"</b>.',
              "en": 'It looks like a <b>check mark</b> (✓) next to <b>"%s"</b>.'},
    "resaltado": {"es": "<b>resaltado</b> %s.", "en": "<b>highlight</b>, %s."},
    "resaltado_det": {"es": 'La persona resaltó este texto del documento: <b>"%s"</b>.',
                      "en": 'The person highlighted this text of the document: <b>"%s"</b>.'},
    "amarillo": {"es": "amarillo", "en": "yellow"},
    "encima_de": {"es": 'Está dibujado encima de este texto: "%s". La forma se ve en la hoja.',
                  "en": 'It is drawn over this text: "%s". The shape can be seen on the page.'},
    "en_blanco": {"es": 'Está en un espacio en blanco, sin texto debajo. Texto justo encima: "%s"%s. '
                        'La forma del dibujo se ve en la hoja.',
                  "en": 'It is in a blank space, with no text under it. Text right above: "%s"%s. '
                        'The shape of the drawing can be seen on the page.'},
    "y_debajo": {"es": '; justo debajo: "%s"', "en": '; right below: "%s"'},
    "atado_dibujo": {"es": ' La persona lo ató a estas palabras: <b>"%s"</b>.',
                     "en": ' The person tied it to these words: <b>"%s"</b>.'},
    "nota_atada": {"es": "<b>nota atada a una frase</b>.", "en": "<b>note tied to a phrase</b>."},
    "nota_atada_det": {
        "es": 'La persona eligió estas palabras del documento: <b>"%s"</b> y sobre ellas escribió: '
              '<b>"%s"</b>. En la hoja, una línea punteada violeta une la nota con esas palabras.',
        "en": 'The person chose these words of the document: <b>"%s"</b> and wrote about them: '
              '<b>"%s"</b>. On the page, a dotted purple line joins the note to those words.'},
    "nota_suelta": {"es": "<b>nota suelta</b> (no atada a una frase).",
                    "en": "<b>loose note</b> (not tied to a phrase)."},
    "dice": {"es": 'Dice: <b>"%s"</b>. ', "en": 'It says: <b>"%s"</b>. '},
    "tapa": {"es": 'La nota está pegada encima del documento y <b>tapa este texto</b>: "%s". ',
             "en": 'The note sits on top of the document and <b>covers this text</b>: "%s". '},
    "ubicacion": {"es": 'Ubicación: justo encima, "%s"; a su misma altura, "%s"; justo debajo, "%s".',
                  "en": 'Location: right above, "%s"; at the same height, "%s"; right below, "%s".'},
    "nada": {"es": "(nada)", "en": "(nothing)"},
    "blanco": {"es": "(espacio en blanco)", "en": "(blank space)"},
    "rojo": {"es": "rojo", "en": "red"}, "naranja": {"es": "naranja", "en": "orange"},
    "verde": {"es": "verde", "en": "green"}, "azul": {"es": "azul", "en": "blue"},
    "negro": {"es": "negro", "en": "black"},
}


def _t(clave):
    return TEXTOS[clave].get(idiomas.idioma_actual(), TEXTOS[clave]["es"])


def _limpio(s):
    return " ".join((s or "").replace(ZW, " ").split())


def _corto(s, tope=350):
    """Cita larga recortada avisando (un párrafo entero no hace falta entero)."""
    s = s or ""
    return s if len(s) <= tope else s[:s.rfind(" ", 0, tope) if " " in s[:tope] else tope] + " […]"


def _esc(s):
    """Texto del usuario o del documento, seguro dentro del HTML de la guía."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _nombre_color(c):
    refs = [("rojo", (0.88, 0.19, 0.19)), ("naranja", (0.96, 0.41, 0.03)),
            ("amarillo", (1.0, 0.86, 0.12)),
            ("verde", (0.18, 0.62, 0.27)), ("azul", (0.10, 0.44, 0.76)),
            ("negro", (0.13, 0.15, 0.16))]
    mejor = min(refs, key=lambda r: sum((a - b) ** 2 for a, b in zip(c[:3], r[1])))
    return _t(mejor[0])


# ------------------------------------------------------ texto de la página ----

def palabras_de(pagina):
    """Palabras de la hoja (sin las marcas propias) con su recuadro."""
    salida = []
    for w in pagina.get_text("words"):
        t = _limpio(w[4])
        if t:
            salida.append((pymupdf.Rect(w[:4]), t))
    return salida


def _renglones(palabras):
    filas = {}
    for wr, t in palabras:
        filas.setdefault(round(wr.y0 / 4.0), []).append((wr, t))
    salida = []
    for ws in filas.values():
        ws.sort(key=lambda p: p[0].x0)
        salida.append((min(w[0].y0 for w in ws), max(w[0].y1 for w in ws),
                       " ".join(t for _, t in ws)))
    salida.sort()
    return salida


def _juntar(ws):
    """Palabras en orden de lectura; " / " marca el salto de renglón para no
    inventar una frase seguida que en el documento no existe."""
    ws = sorted(ws, key=lambda p: (round(p[0].y0 / 4), p[0].x0))
    partes, antes = [], None
    for wr, t in ws:
        if antes is not None and abs(wr.y0 - antes) >= 4:
            partes.append("/")
        partes.append(t)
        antes = wr.y0
    return " ".join(partes)


def _vecinos(renglones, rect):
    """Renglón justo encima, a la misma altura y justo debajo."""
    arriba = [r for r in renglones if r[1] <= rect.y0 + 1]
    abajo = [r for r in renglones if r[0] >= rect.y1 - 1]
    altura = [r for r in renglones if r[1] > rect.y0 + 1 and r[0] < rect.y1 - 1]
    return (arriba[-1][2] if arriba else "",
            " / ".join(r[2] for r in altura),
            abajo[0][2] if abajo else "")


def _debajo(palabras, rect, fraccion):
    return _juntar([(wr, t) for wr, t in palabras
                    if (wr & rect).get_area() > fraccion * wr.get_area()])


def _agrupar_dibujos(dibujos):
    """Trazos que se tocan (12 pt de margen) son UN dibujo: una cara hecha con
    siete trazos es una marca, no siete. dibujos: [(marca, rect)]."""
    grupos = [{"marcas": [mk], "rect": pymupdf.Rect(r)} for mk, r in dibujos]
    unidos = True
    while unidos:
        unidos = False
        for i in range(len(grupos)):
            for j in range(i + 1, len(grupos)):
                a = grupos[i]["rect"] + (-12, -12, 12, 12)
                if a.intersects(grupos[j]["rect"]):
                    grupos[i]["marcas"] += grupos[j]["marcas"]
                    grupos[i]["rect"] |= grupos[j]["rect"]
                    del grupos[j]
                    unidos = True
                    break
            if unidos:
                break
    return grupos


def _largo(trazo):
    return sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(trazo, trazo[1:]))


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _adentro(punto, poligono):
    """True si el punto cae dentro del camino cerrado (regla del rayo)."""
    x, y = punto
    dentro = False
    for (x0, y0), (x1, y1) in zip(poligono, poligono[1:] + poligono[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / ((y1 - y0) or 1e-9) + x0:
            dentro = not dentro
    return dentro


def _cerca_de(palabras, punto, tope=45.0, renglon=False):
    """La palabra más cercana a un punto (la punta de una flecha), o con
    renglon=True el renglón entero de esa palabra (para una tilde)."""
    if not palabras:
        return ""
    wr, t = min(palabras, key=lambda p: _dist(punto, ((p[0].x0 + p[0].x1) / 2, (p[0].y0 + p[0].y1) / 2)))
    centro = ((wr.x0 + wr.x1) / 2, (wr.y0 + wr.y1) / 2)
    if _dist(punto, centro) > tope + wr.width / 2:
        return ""
    if renglon:
        # Solo las palabras seguidas en ese renglón (no la otra columna).
        fila = sorted([p for p in palabras if abs(p[0].y0 - wr.y0) < 4], key=lambda p: p[0].x0)
        k = fila.index((wr, t))
        i, j = k, k
        while i > 0 and fila[i][0].x0 - fila[i - 1][0].x1 < 28:
            i -= 1
        while j < len(fila) - 1 and fila[j + 1][0].x0 - fila[j][0].x1 < 28:
            j += 1
        return " ".join(p[1] for p in fila[i:j + 1])
    return t


def _trazos(grupo):
    return [tr for mk in grupo["marcas"] for tr in mk["trazos"] if len(tr) >= 2]


def _circulo(grupo, palabras):
    """Un trazo que se cierra sobre sí mismo: dice qué palabras quedan adentro."""
    trs = _trazos(grupo)
    if len(trs) != 1:
        return None
    tr = trs[0]
    r = grupo["rect"]
    lado = max(r.width, r.height)
    if min(r.width, r.height) < 8 or _dist(tr[0], tr[-1]) > 0.3 * lado or _largo(tr) < 2.2 * lado:
        return None
    dentro = [(wr, t) for wr, t in palabras
              if _adentro(((wr.x0 + wr.x1) / 2, (wr.y0 + wr.y1) / 2), tr)]
    return _juntar(dentro) if dentro else ""


def _flecha(grupo, palabras):
    """Un trazo largo con trazos cortos pegados a una punta = flecha.
    Devuelve (de dónde sale, a qué apunta) o None."""
    trs = _trazos(grupo)
    if len(trs) < 2:
        return None
    largo = max(trs, key=_largo)
    L = _largo(largo)
    otros = [tr for tr in trs if tr is not largo]
    if L < 25 or any(_largo(tr) > 0.6 * L for tr in otros):
        return None
    a, b = largo[0], largo[-1]
    if _dist(a, b) < 0.6 * L:
        return None          # el cuerpo de una flecha es casi recto (una casa, no)
    punta = None
    for tr in otros:
        # La cabeza entera tiene que estar pegada a UNA punta del cuerpo.
        esta = a if sum(_dist(p, a) for p in tr) < sum(_dist(p, b) for p in tr) else b
        if max(_dist(p, esta) for p in tr) > 0.35 * L or (punta and esta is not punta):
            return None
        punta = esta
    return (b if punta is a else a), punta


def _vertical(grupo, renglones):
    """Raya vertical al costado de un párrafo: los renglones que abarca."""
    trs = _trazos(grupo)
    r = grupo["rect"]
    if len(trs) != 1 or r.height < 20 or r.height < 2.5 * r.width:
        return None
    return " / ".join(t for y0, y1, t in renglones if y1 > r.y0 and y0 < r.y1)


def _tilde(grupo, palabras):
    """Tilde de "listo" (✓): un trazo chico que baja y vuelve a subir."""
    trs = _trazos(grupo)
    r = grupo["rect"]
    if len(trs) != 1 or max(r.width, r.height) > 45 or max(r.width, r.height) < 6:
        return None
    tr = trs[0]
    k = max(range(len(tr)), key=lambda i: tr[i][1])        # el punto más bajo
    if not (0.15 * len(tr) <= k <= 0.7 * len(tr)):
        return None
    if tr[-1][1] > tr[0][1] - 0.2 * r.height or tr[-1][0] <= tr[k][0]:
        return None          # tiene que terminar arriba y a la derecha de la V
    return _cerca_de(palabras, ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2), 80.0, renglon=True)


def _raya(grupo, palabras):
    """Si el dibujo es una raya casi horizontal sobre palabras, devuelve
    (palabras, por dónde pasa). Si no, None."""
    r = grupo["rect"]
    if len(grupo["marcas"]) != 1 or r.width < 2 * r.height:
        return None
    pts = [p for t in grupo["marcas"][0]["trazos"] for p in t]
    if not pts:
        return None
    y_media = sum(p[1] for p in pts) / len(pts)
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    # Cada renglón que la raya toca de costado, con cómo lo toca. Una raya
    # debajo de un renglón cae casi pegada al de abajo (las cajas de las
    # palabras se tocan), así que se elige por prioridad: tachado, después
    # subrayado, después "por arriba". Sin esto, un subrayado se atribuía al
    # renglón siguiente.
    rangos = (("medio", 0.3, 0.85, 0), ("debajo", 0.85, 1.45, 1), ("arriba", -0.35, 0.3, 2))
    mejor = None
    for y0, _y1, _txt in _renglones(palabras):
        linea = [(wr, t) for wr, t in palabras if abs(wr.y0 - y0) < 4
                 and min(wr.x1, x1) - max(wr.x0, x0) > 0.5 * wr.width]
        if not linea:
            continue
        h = max(wr.height for wr, _ in linea) or 1
        rel = (y_media - min(wr.y0 for wr, _ in linea)) / h
        for como, desde, hasta, rango in rangos:
            if desde <= rel <= hasta:
                if mejor is None or rango < mejor[0]:
                    mejor = (rango, como, linea)
                break
    if mejor is None:
        return None
    return _juntar(mejor[2]), _t(mejor[1])


# ------------------------------------------------------------ la lista ----

def armar(marcas, palabras_por_pagina, rect_marca):
    """Lista ordenada de entradas de la guía.

    marcas: {pagina: [marca]} (formato de anotaciones.guardar)
    palabras_por_pagina: {pagina: [(Rect, texto)]} de la hoja SIN marcas
    rect_marca(marca) -> Rect visible de la marca (el mismo que se guarda)
    Devuelve [{"pagina", "rect", "cab", "det", "ancla_rect" | None}] en orden de lectura.
    """
    entradas = []
    for n, lista in sorted(marcas.items()):
        pal = palabras_por_pagina.get(n, [])
        ren = _renglones(pal)
        dibujos = [(mk, rect_marca(mk)) for mk in lista if mk["tipo"] == "lapiz"]
        for g in _agrupar_dibujos(dibujos):
            entradas.append({"pagina": n, "rect": g["rect"], "clase": "dibujo", "g": g,
                             "pal": pal, "ren": ren})
        for mk in lista:
            if mk["tipo"] == "texto" and (mk.get("texto") or "").strip():
                entradas.append({"pagina": n, "rect": rect_marca(mk), "clase": "nota", "mk": mk,
                                 "pal": pal, "ren": ren})
            elif mk["tipo"] == "resaltado" and mk.get("rects"):
                entradas.append({"pagina": n, "rect": rect_marca(mk), "clase": "resaltado",
                                 "mk": mk, "pal": pal, "ren": ren})
    entradas.sort(key=lambda e: (e["pagina"], round(e["rect"].y0 / 10), e["rect"].x0))
    lista_notas = {n: [mk for mk in lista if mk["tipo"] == "texto"] for n, lista in marcas.items()}

    for i, e in enumerate(entradas, 1):
        rect = e["rect"]
        cab = ""
        ancla = None
        if e["clase"] == "dibujo":
            g = e["g"]
            k = len(_trazos(g)) or len(g["marcas"])
            cab += _t("dibujo") % (_nombre_color(g["marcas"][0]["color"]), k, "" if k == 1 else "s")
            raya = _raya(g, e["pal"])
            circ = None if raya else _circulo(g, e["pal"])
            flecha = None if raya or circ is not None else _flecha(g, e["pal"])
            vert = None if raya or circ is not None or flecha else _vertical(g, e["ren"])
            tilde = None if raya or circ is not None or flecha or vert else _tilde(g, e["pal"])
            if raya:
                det = _t("raya") % (raya[1], _esc(raya[0]))
            elif circ:
                det = _t("circulo") % _esc(_corto(circ))
            elif circ == "":
                det = _t("circulo_vacio")
            elif flecha:
                cola, punta = flecha
                # Si sale de una nota, se dice de cuál: "sale de cerca de Córdoba"
                # confundía cuando la flecha arrancaba en la nota "Acá nací".
                nota = next((mk for mk in lista_notas.get(e["pagina"], [])
                             if (rect_marca(mk) + (-20, -20, 20, 20)).contains(pymupdf.Point(cola))),
                            None)
                desde = (_t("de_la_nota") % _esc(_limpio(nota["texto"]))) if nota else \
                    (_t("de_cerca") % (_esc(_cerca_de(e["pal"], cola)) or _t("nada")))
                det = _t("flecha") % (desde, _esc(_cerca_de(e["pal"], punta)) or _t("nada"))
            elif vert:
                det = _t("vertical") % _esc(_corto(vert))
            elif tilde:
                det = _t("tilde") % _esc(tilde)
            else:
                debajo = _debajo(e["pal"], rect + (0, -3, 0, 3), 0.25)
                if debajo:
                    det = _t("encima_de") % _esc(_corto(debajo))
                else:
                    arr, _alt, aba = _vecinos(e["ren"], rect)
                    det = _t("en_blanco") % (_esc(arr) or _t("nada"),
                                             (_t("y_debajo") % _esc(aba)) if aba else "")
            for mk in g["marcas"]:
                if (mk.get("ancla") or {}).get("cita"):
                    det += _t("atado_dibujo") % _esc(_limpio(mk["ancla"]["cita"]))
                    ancla = mk["ancla"]
                    break
        elif e["clase"] == "resaltado":
            mk = e["mk"]
            cab += _t("resaltado") % _nombre_color(mk["color"])
            det = _t("resaltado_det") % _esc(_corto(_limpio(mk.get("cita")) or
                                                    _debajo(e["pal"], rect, 0.5)))
        else:
            mk = e["mk"]
            texto = _limpio(mk["texto"])
            if (mk.get("ancla") or {}).get("cita"):
                ancla = mk["ancla"]
                cab += _t("nota_atada")
                det = _t("nota_atada_det") % (_esc(_limpio(ancla["cita"])), _esc(texto))
            else:
                cab += _t("nota_suelta")
                arr, alt, aba = _vecinos(e["ren"], rect)
                det = _t("dice") % _esc(texto)
                tapado = _debajo(e["pal"], rect, 0.5)
                if tapado:
                    det += _t("tapa") % _esc(tapado)
                det += _t("ubicacion") % (_esc(arr) or _t("nada"), _esc(alt) or _t("blanco"),
                                          _esc(aba) or _t("nada"))
        e["cab"], e["det"] = cab, det
        e["ancla_rect"] = (pymupdf.Rect(ancla["rects"][0])
                           if ancla and ancla.get("rects") else None)
    return entradas


# ------------------------------------------------- escribir en el PDF ----

def _circulo_pdf(cx, cy, r):
    """Círculo en operadores PDF (cuatro curvas de Bézier)."""
    k = 0.5523 * r
    return ("%.2f %.2f m " % (cx + r, cy)
            + "%.2f %.2f %.2f %.2f %.2f %.2f c " % (cx + r, cy + k, cx + k, cy + r, cx, cy + r)
            + "%.2f %.2f %.2f %.2f %.2f %.2f c " % (cx - k, cy + r, cx - r, cy + k, cx - r, cy)
            + "%.2f %.2f %.2f %.2f %.2f %.2f c " % (cx - r, cy - k, cx - k, cy - r, cx, cy - r)
            + "%.2f %.2f %.2f %.2f %.2f %.2f c h" % (cx + k, cy - r, cx + r, cy - k, cx + r, cy))


def lugar_numero(rect, palabras, ocupados, hoja):
    """Esquina superior izquierda del círculo con número: la posición alrededor
    de la marca que menos texto del documento tapa (antes iba siempre arriba a
    la izquierda y a veces tapaba una palabra). ocupados = recuadros ya usados
    (otros números y marcas) que tampoco conviene tapar."""
    d = 15.0
    cy = (rect.y0 + rect.y1) / 2 - d / 2
    candidatos = [(rect.x0 - d - 1, rect.y0 - d - 1), (rect.x1 + 1, rect.y0 - d - 1),
                  (rect.x0 - d - 2, cy), (rect.x1 + 2, cy),
                  (rect.x0 - d - 1, rect.y1 + 1), (rect.x1 + 1, rect.y1 + 1)]
    mejor = None
    for orden, (x, y) in enumerate(candidatos):
        x = max(1.0, min(x, hoja.width - d - 1))
        y = max(1.0, min(y, hoja.height - d - 1))
        c = pymupdf.Rect(x, y, x + d, y + d)
        tapa = sum((c & wr).get_area() for wr, _t in palabras if c.intersects(wr))
        tapa += 0.5 * sum((c & o).get_area() for o in ocupados if c.intersects(o))
        if mejor is None or tapa < mejor[0] - 0.01:
            mejor = (tapa, x, y)
    return mejor[1], mejor[2]


def poner_numero(doc, pagina, matriz, x, y, n, autor):
    """Círculo violeta con el número de la marca, como anotación propia.

    Es una FreeText (así trae la letra) con el dibujo reemplazado por un
    círculo. Si el reemplazo falla, o la hoja está rotada, queda el cuadrado
    de PyMuPDF con el número: se ve igual.
    """
    d = 15.0
    x = max(1.0, min(x, pagina.rect.width - d - 1))
    y = max(1.0, min(y, pagina.rect.height - d - 1))
    rect = (pymupdf.Rect(x, y, x + d, y + d) * matriz).normalize()
    annot = pagina.add_freetext_annot(rect, str(n), fontsize=8.5, fontname="helv",
                                      text_color=(1, 1, 1), fill_color=VIOLETA,
                                      border_width=0, align=pymupdf.TEXT_ALIGN_CENTER)
    annot.set_info(title=autor, content=str(n))
    annot.update()
    doc.xref_set_key(annot.xref, "NM", "(%snum-%d)" % (PREFIJO, n))
    if pagina.rotation:
        return
    try:
        clase, valor = doc.xref_get_key(annot.xref, "AP/N")
        if clase != "xref":
            return
        xref = int(valor.split()[0])
        bx0, by0, bx1, by1 = (float(v) for v in doc.xref_get_key(xref, "BBox")[1].strip("[]").split())
        cx, cy, r = (bx0 + bx1) / 2, (by0 + by1) / 2, (bx1 - bx0) / 2 - 0.6
        s = str(n)
        letra = 8.5 if n < 100 else 6.5
        ancho = pymupdf.get_text_length(s, fontname="helv", fontsize=letra)
        flujo = ("q 1 1 1 RG 1.2 w %.4f %.4f %.4f rg %s B "
                 "BT /Helv %.2f Tf 1 1 1 rg 1 0 0 1 %.2f %.2f Tm (%s) Tj ET Q"
                 % (VIOLETA + (_circulo_pdf(cx, cy, r), letra, cx - ancho / 2, cy - letra * 0.36, s)))
        doc.update_stream(xref, flujo.encode("latin-1"))
    except Exception:
        pass


def poner_lazo(doc, pagina, matriz, rect_nota, rect_ancla, n, autor):
    """Línea punteada de la marca a la frase atada: la atadura se ve en la hoja."""
    desde = pymupdf.Point((rect_nota.x0 + rect_nota.x1) / 2,
                          rect_nota.y0 if rect_nota.y0 > rect_ancla.y1 else rect_nota.y1)
    hasta = pymupdf.Point((rect_ancla.x0 + rect_ancla.x1) / 2,
                          rect_ancla.y1 + 1 if rect_nota.y0 > rect_ancla.y1 else rect_ancla.y0 - 1)
    annot = pagina.add_line_annot(desde * matriz, hasta * matriz)
    annot.set_colors(stroke=VIOLETA)
    annot.set_border(width=1.2, dashes=[3, 2])
    annot.set_info(title=autor)
    annot.update()
    doc.xref_set_key(annot.xref, "NM", "(%slazo-%d)" % (PREFIJO, n))


def _guia_pdf(entradas, guias, ancho, alto):
    """La guía como PDF aparte (en memoria). guias = cuántas hojas ocupa la
    guía, para numerar bien "hoja N del PDF"."""
    lista = "\n".join(
        "<p><b>%s</b> · %s · %s %s</p>" % (_t("marca") % i, _t("hoja") % (e["pagina"] + 1 + guias,
                                                                          e["pagina"] + 1),
                                           e["cab"], e["det"])
        for i, e in enumerate(entradas, 1))
    html = """
<div style="font-family: sans-serif; font-size: 10.5pt; line-height: 1.35; color: #222;">
<p style="font-size: 16pt; color: #5a2fbf;"><b>%s</b></p>
<p><i>%s</i></p>
<p>%s</p>
<p>%s</p>
<p style="font-size: 12.5pt; color: #5a2fbf;"><b>%s</b></p>
%s
</div>""" % (_t("titulo"), _t("agregada"), _t("intro") % (guias + 1), _t("como"),
             (_t("n_marcas") % len(entradas)) if len(entradas) != 1 else _t("una_marca"),
             lista)
    memoria = io.BytesIO()
    escritor = pymupdf.DocumentWriter(memoria)
    story = pymupdf.Story(html)
    caja = pymupdf.Rect(48, 48, ancho - 48, alto - 48)
    mas = True
    while mas:     # muchas marcas no entran en una hoja: se sigue en otra
        dev = escritor.begin_page(pymupdf.Rect(0, 0, ancho, alto))
        mas, _ = story.place(caja)
        story.draw(dev)
        escritor.end_page()
    escritor.close()
    return pymupdf.open("pdf", memoria.getvalue())


def poner_hoja(doc, entradas):
    """Inserta la hoja-guía (una o más) al principio del PDF."""
    ancho, alto = doc[0].rect.width, doc[0].rect.height
    guias = 1
    extra = _guia_pdf(entradas, guias, ancho, alto)
    if extra.page_count != guias:      # ocupó más: se rehace con la numeración justa
        guias = extra.page_count
        extra = _guia_pdf(entradas, guias, ancho, alto)
    doc.insert_pdf(extra, start_at=0)
    for k in range(extra.page_count):
        doc.xref_set_key(doc[k].xref, CLAVE_PAGINA, "true")
    return extra.page_count


def quitar_hojas(doc):
    """Quita las hojas-guía (en memoria). Devuelve cuántas quitó."""
    quitadas = 0
    for k in reversed(range(doc.page_count)):
        try:
            if doc.xref_get_key(doc[k].xref, CLAVE_PAGINA)[1] == "true":
                doc.delete_page(k)
                quitadas += 1
        except Exception:
            continue
    return quitadas
