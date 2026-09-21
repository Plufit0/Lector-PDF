# -*- coding: utf-8 -*-
"""
idiomas.py — todo el texto que ve el usuario, en un solo lugar y en dos idiomas.

POR QUE ASI (estandar tomado del proyecto Chispita del mismo autor):
El programa se maneja en espanol y en ingles. En vez de tener las cadenas
sueltas por todo el codigo, viven aca en un diccionario {clave: {'es':.., 'en':..}}.
El resto del programa nunca escribe un cartel a mano: pide t("clave") y este
modulo devuelve la version en el idioma activo.

DECISIONES DE DISENO (leer antes de tocar):

1. EL IDIOMA POR DEFECTO ES 'es', Y NO SE LEE EL ARCHIVO AL IMPORTAR.
   La red de seguridad (autotest.py) compara textos EXACTOS en espanol. Como el
   autotest crea la ventana directamente (no pasa por main()), nunca se llama a
   cargar_idioma_guardado(): asi la prueba corre SIEMPRE en espanol, sin importar
   que idioma haya dejado elegido David. Por eso las cadenas 'es' tienen que ser
   identicas, caracter por caracter, a las que habia antes (incluida la falta de
   tildes donde hoy no las hay).

2. FALLBACK SIEMPRE AL ESPANOL. Si falta una clave, o falta el idioma pedido,
   se devuelve la version 'es'. Un cartel nunca queda vacio ni en blanco.

3. PERSISTENCIA EN LA CARPETA DE DATOS DEL USUARIO, no al lado del programa.
   El programa vive en Program Files (solo lectura): el idioma elegido se guarda
   en %LOCALAPPDATA%\\LectorPDF\\idioma.txt, igual que el registro de errores.

4. MODULO SIN DEPENDENCIAS (solo 'os'). Lo importan el programa, el extractor y
   anotaciones.py; no puede arrastrar a pymupdf ni a nada que pueda faltar.
"""

import os

_NOMBRE_APP = "LectorPDF"

# Idioma activo. Arranca SIEMPRE en espanol (ver decision 1). main() lo cambia
# a lo que haya guardado David; el autotest lo deja como esta.
_idioma = "es"

IDIOMAS_VALIDOS = ("es", "en")


def _archivo_idioma():
    """Ruta del archivito donde se recuerda el idioma elegido."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    carpeta = os.path.join(base, _NOMBRE_APP)
    try:
        os.makedirs(carpeta, exist_ok=True)
    except OSError:
        carpeta = os.path.expanduser("~")
    return os.path.join(carpeta, "idioma.txt")


def idioma_actual():
    return _idioma


def set_idioma(codigo, persistir=True):
    """Cambia el idioma activo. Si persistir, lo recuerda para la proxima vez.

    El autotest llama a esto con persistir=False para forzar un idioma sin
    tocar la eleccion de David.
    """
    global _idioma
    if codigo not in IDIOMAS_VALIDOS:
        codigo = "es"
    _idioma = codigo
    if persistir:
        try:
            with open(_archivo_idioma(), "w", encoding="utf-8") as f:
                f.write(codigo)
        except OSError:
            pass
    return _idioma


def cargar_idioma_guardado():
    """Lee el idioma recordado de la sesion anterior. Si no hay, deja espanol.

    Se llama al arrancar el programa de verdad (main()), NO al importar el
    modulo: por eso el autotest, que no pasa por main(), corre siempre en 'es'.
    """
    global _idioma
    try:
        with open(_archivo_idioma(), encoding="utf-8") as f:
            guardado = f.read().strip().lower()
        if guardado in IDIOMAS_VALIDOS:
            _idioma = guardado
    except OSError:
        pass
    return _idioma


def t(clave, **fmt):
    """Devuelve la cadena de 'clave' en el idioma activo.

    Con datos que van adentro del texto, hay dos formas de usarlo:
      - t("clave") % (a, b)        cuando la plantilla trae %s / %d (el estilo
                                   que ya usaba el programa).
      - t("clave", nombre=x)       cuando la plantilla trae {nombre} (se aplica
                                   .format(**fmt)).
    Si falta la clave o el idioma, cae al espanol; si igual falta, devuelve la
    clave cruda para que se note que falto traducir, en vez de un texto vacio.
    """
    entrada = TEXTOS.get(clave)
    if entrada is None:
        return clave
    cadena = entrada.get(_idioma)
    if cadena is None:
        cadena = entrada.get("es", clave)
    if fmt:
        try:
            cadena = cadena.format(**fmt)
        except Exception:
            pass
    return cadena


# ===========================================================================
# El diccionario. 'es' identico a lo que habia antes (lo chequea el autotest).
# ===========================================================================

TEXTOS = {
    # --- boton para cambiar de idioma (dice el idioma AL QUE se pasa) --------
    "boton_idioma": {"es": "English", "en": "Espanol"},

    # ---------------------------------------------------------- biblioteca ---
    "bib_pdfs_en": {"es": "PDFs en %s", "en": "PDFs in %s"},
    "bib_otra_carpeta": {"es": "Otra carpeta...", "en": "Other folder..."},
    "bib_actualizar": {"es": "Actualizar", "en": "Refresh"},
    "col_archivo": {"es": "Archivo", "en": "File"},
    "col_modificado": {"es": "Modificado", "en": "Modified"},
    "col_tamano": {"es": "Tamano", "en": "Size"},
    "bib_elegir_carpeta_titulo": {"es": "Elegir carpeta con PDFs",
                                  "en": "Choose a folder with PDFs"},
    "bib_no_leer_carpeta": {"es": "No se pudo leer la carpeta: %s",
                            "en": "Could not read the folder: %s"},
    "bib_cuenta": {"es": "%d PDF(s). Doble clic o Enter para abrir.",
                   "en": "%d PDF(s). Double-click or Enter to open."},
    "bib_sin_pdfs": {"es": "No hay PDFs en esta carpeta.",
                     "en": "There are no PDFs in this folder."},
    "bib_abrir": {"es": "Abrir", "en": "Open"},

    # ------------------------------------------------------- visor: barra ----
    "v_carpeta": {"es": "< Carpeta", "en": "< Folder"},
    "modo_dibujar": {"es": "Dibujar", "en": "Draw"},
    "modo_texto": {"es": "Texto", "en": "Text"},
    "modo_seleccionar": {"es": "Seleccionar", "en": "Select"},
    "modo_borrar": {"es": "Borrar", "en": "Erase"},
    "v_grueso": {"es": "Grueso", "en": "Thick"},
    "v_deshacer": {"es": "Deshacer", "en": "Undo"},
    "v_rehacer": {"es": "Rehacer", "en": "Redo"},
    "v_pagina": {"es": "Pagina", "en": "Page"},
    "v_ancho": {"es": "Ancho", "en": "Width"},
    "v_guardar": {"es": "Guardar", "en": "Save"},

    # ------------------------------------------------------- visor: ojito ----
    "ojo_marcas": {"es": "\U0001F441  Marcas", "en": "\U0001F441  Marks"},
    "ojo_ocultas": {"es": "\U0001F441  (ocultas)", "en": "\U0001F441  (hidden)"},

    # ------------------------------------------------------- visor: panel ----
    "pnl_comentar": {"es": "Comentar esta frase", "en": "Comment on this sentence"},
    "pnl_dibujar_sobre": {"es": "Dibujar sobre esta frase",
                          "en": "Draw over this sentence"},
    "pnl_nombre_interno": {"es": "NOMBRE INTERNO", "en": "INTERNAL NAME"},
    "pnl_ok": {"es": "OK", "en": "OK"},
    "pnl_referencia_a": {"es": "REFERENCIA A", "en": "REFERENCE TO"},
    "pnl_elegir": {"es": "Elegir", "en": "Choose"},
    "pnl_quitar": {"es": "Quitar", "en": "Remove"},
    "pnl_color": {"es": "COLOR", "en": "COLOR"},
    "pnl_grosor_titulo": {"es": "GROSOR", "en": "THICKNESS"},
    "grosor_fino": {"es": "Fino", "en": "Thin"},
    "grosor_medio": {"es": "Medio", "en": "Medium"},
    "grosor_grueso": {"es": "Grueso", "en": "Thick"},
    "pnl_editar_texto": {"es": "Editar el texto", "en": "Edit the text"},
    "pnl_unificar": {"es": "Unificar en un solo dibujo",
                     "en": "Merge into a single drawing"},
    "pnl_borrar": {"es": "Borrar", "en": "Delete"},
    "pnl_soltar": {"es": "Soltar la seleccion", "en": "Clear the selection"},

    # ------------------------------------------- visor: panel (dinamico) ----
    "pnl_texto_manual": {"es": "Texto del manual", "en": "Manual text"},
    "pnl_caracteres_cita": {"es": "%d caracteres\n“%s”",
                            "en": "%d characters\n“%s”"},
    "pnl_dibujo_mano": {"es": "Dibujo a mano", "en": "Freehand drawing"},
    "pnl_datos_dibujo": {
        "es": "Pagina %d  ·  %d trazo(s), %d puntos  ·  %.0f × %.0f pt",
        "en": "Page %d  ·  %d stroke(s), %d points  ·  %.0f × %.0f pt"},
    "pnl_nota_escrita": {"es": "Nota escrita", "en": "Written note"},
    "pnl_datos_nota": {"es": "Pagina %d  ·  %d caracteres\n“%s”",
                       "en": "Page %d  ·  %d characters\n“%s”"},
    "pnl_n_marcas": {"es": "%d marcas elegidas", "en": "%d marks selected"},
    "pnl_datos_varias": {"es": "Pagina %d  ·  %d dibujo(s), %d nota(s)",
                         "en": "Page %d  ·  %d drawing(s), %d note(s)"},
    "pnl_ninguna": {"es": "(ninguna)", "en": "(none)"},
    "ref_la_frase": {"es": "la frase: %s", "en": "the sentence: %s"},
    "ref_la_marca": {"es": "la marca: %s", "en": "the mark: %s"},

    # ----------------------------------------------- visor: pie (mensajes) ---
    "pie_comentar": {
        "es": "Hace clic donde quieras la nota. Va a quedar atada a: "
              "“%s”   (Esc para cancelar)",
        "en": "Click where you want the note. It will be tied to: "
              "“%s”   (Esc to cancel)"},
    "pie_dibujar": {
        "es": "Dibuja donde quieras. El dibujo va a quedar atado a: "
              "“%s”   (Esc para cancelar)",
        "en": "Draw wherever you want. The drawing will be tied to: "
              "“%s”   (Esc to cancel)"},
    "pie_elegir_ref": {
        "es": "Elegi la referencia: arrastra sobre una frase del manual, "
              "o hace clic en otra marca.   (Esc para cancelar)",
        "en": "Choose the reference: drag over a sentence of the manual, "
              "or click another mark.   (Esc to cancel)"},
    "pie_ref_guardada": {"es": "Referencia guardada.", "en": "Reference saved."},
    "pie_copiado": {"es": "Copiado: %d caracteres del manual.",
                    "en": "Copied: %d characters of the manual."},
    "pie_renombrado": {"es": "Ahora se llama “%s”.",
                       "en": "Now it is called “%s”."},
    "pie_unificados": {"es": "%d dibujos unidos en uno solo (%d trazos).",
                       "en": "%d drawings merged into one (%d strokes)."},
    "pie_escribiendo": {
        "es": "Escribiendo nota  —  Esc o clic afuera para confirmar",
        "en": "Writing note  —  Esc or click outside to confirm"},
    "pie_marcas": {"es": "%d marca(s)%s", "en": "%d mark(s)%s"},
    "pie_sin_guardar": {"es": "   ·   SIN GUARDAR", "en": "   ·   UNSAVED"},

    # ------------------------------------------------------- visor: errores --
    "v_pdf_sin_paginas": {
        "es": "El PDF no tiene ninguna pagina: puede estar danado.",
        "en": "The PDF has no pages: it may be damaged."},

    # ----------------------------------------------------------- guardar -----
    "dlg_sin_marcas_titulo": {"es": "Sin marcas", "en": "No marks"},
    "dlg_sin_marcas_cuerpo": {
        "es": "No hay ninguna marca todavia. Guardar igual?",
        "en": "There are no marks yet. Save anyway?"},
    "dlg_guardar_titulo": {"es": "Guardar devolucion", "en": "Save feedback"},
    "dlg_incompleto_titulo": {"es": "Guardado incompleto", "en": "Incomplete save"},
    "dlg_incompleto_cuerpo": {
        "es": "El archivo se guardo en:\n%s\n\nPERO estas marcas quedaron afuera:\n\n%s",
        "en": "The file was saved to:\n%s\n\nBUT these marks were left out:\n\n%s"},
    "dlg_no_guardar_titulo": {"es": "No se pudo guardar", "en": "Could not save"},
    "dlg_no_guardar_cuerpo": {
        "es": "%s\n\nEl PDF anterior quedo intacto y tus marcas siguen en pantalla:\n"
              "proba con Guardar y otro nombre.",
        "en": "%s\n\nThe previous PDF is untouched and your marks are still on screen:\n"
              "try Save with a different name."},

    # ----------------------------------------------------- dialogo guardado --
    "dlg_guardado_titulo": {"es": "Guardado", "en": "Saved"},
    "dlg_devolucion_guardada": {"es": "Devolucion guardada", "en": "Feedback saved"},
    "dlg_guardado_info": {
        "es": "Esto ya esta copiado. Pegalo en el chat con Ctrl+V.\n"
              "Es un mensaje escrito para el agente: le dice que es esto, donde\n"
              "quedo el archivo y con que leerlo. No hace falta que agregues nada.",
        "en": "This is already copied. Paste it into the chat with Ctrl+V.\n"
              "It is a message written for the agent: it tells it what this is, where\n"
              "the file ended up and what to read it with. You do not need to add anything."},
    "dlg_abrir_carpeta": {"es": "Abrir carpeta", "en": "Open folder"},
    "dlg_copiar_de_nuevo": {"es": "Copiar de nuevo", "en": "Copy again"},
    "dlg_copiar_ruta": {"es": "Copiar solo la ruta", "en": "Copy just the path"},
    "dlg_listo": {"es": "Listo", "en": "Done"},

    # ------------------------------------------- mensaje que se pega al chat --
    # Escrito para que lo lea un agente. Lleva 3 datos: %s = archivo,
    # %s = extractor, %s = archivo (en ese orden).
    "mensaje_chat": {
        "es": "Te paso una devolucion mia marcada sobre un PDF.\n"
              "\n"
              "QUE ES: lei el documento y lo marque encima, a mano: dibujos y notas "
              "escritas. Algunas marcas estan atadas a una frase concreta del "
              "documento y otras son sueltas.\n"
              "\n"
              "EL ARCHIVO:\n"
              "%s\n"
              "\n"
              "COMO LEERLO: no lo abras como un PDF comun. Corre este comando, que te "
              "devuelve por separado el texto original del documento y cada marca mia "
              "con la parte del texto sobre la que cae, mas una imagen de cada pagina "
              "marcada. Abri esas imagenes: el texto te dice donde cae cada trazo, "
              "pero no si es un circulo, un tachado o una flecha.\n"
              "\n"
              "python \"%s\" \"%s\"\n",
        "en": "Here is feedback of mine marked up on a PDF.\n"
              "\n"
              "WHAT IT IS: I read the document and marked it up by hand: drawings and "
              "written notes. Some marks are tied to a specific sentence of the "
              "document and others are loose.\n"
              "\n"
              "THE FILE:\n"
              "%s\n"
              "\n"
              "HOW TO READ IT: do not open it as a normal PDF. Run this command, which "
              "returns separately the original text of the document and each of my "
              "marks with the part of the text it falls on, plus an image of each "
              "marked page. Open those images: the text tells you where each stroke "
              "falls, but not whether it is a circle, a strikethrough or an arrow.\n"
              "\n"
              "python \"%s\" \"%s\"\n"},

    # ------------------------------------------------------- app: titulo -----
    "app_titulo": {"es": "Lector PDF", "en": "Lector PDF"},
    "app_titulo_carpeta": {"es": "Lector PDF  —  %s", "en": "Lector PDF  —  %s"},
    "app_titulo_doc": {"es": "%s%s  —  Lector PDF", "en": "%s%s  —  Lector PDF"},

    # ------------------------------------------------------- app: errores ----
    "app_fallo_titulo": {"es": "Algo salio mal", "en": "Something went wrong"},
    "app_fallo_cuerpo": {
        "es": "%s\n\nEs el error numero %d de esta sesion.\n"
              "Quedaron todos anotados en:\n%s",
        "en": "%s\n\nThis is error number %d of this session.\n"
              "They were all logged in:\n%s"},
    "app_no_abrir_titulo": {"es": "No se pudo abrir", "en": "Could not open"},
    "app_no_abrir_cuerpo": {"es": "%s\n\n%s", "en": "%s\n\n%s"},
    "app_sin_guardar_titulo": {"es": "Hay marcas sin guardar",
                               "en": "There are unsaved marks"},
    "app_sin_guardar_cuerpo": {
        "es": "Tenes %d marca(s) sin guardar.\n\nGuardar antes de salir?",
        "en": "You have %d unsaved mark(s).\n\nSave before leaving?"},

    # --------------------------------------- app: arranque fatal (bootstrap) -
    "app_falta_libreria": {
        "es": "Falta una libreria que el programa necesita:\n\n    %s\n\n"
              "Se esta usando este Python:\n    %s\n\n"
              "Se arregla instalandola con:\n    \"%s\" -m pip install pymupdf pillow",
        "en": "A library the program needs is missing:\n\n    %s\n\n"
              "This Python is being used:\n    %s\n\n"
              "Fix it by installing it with:\n    \"%s\" -m pip install pymupdf pillow"},
    "app_no_arranco_titulo": {"es": "El Lector PDF no pudo arrancar",
                              "en": "Lector PDF could not start"},
    "app_no_arranco_cuerpo": {
        "es": "%s\n\nEl detalle quedo en:\n%s\n\nPasale este texto al agente y lo arregla.",
        "en": "%s\n\nThe details are in:\n%s\n\nGive this text to the agent and it will fix it."},

    # ------------------------------------------------ anotaciones.py (visible) -
    "pdf_con_contrasena": {
        "es": "Este PDF esta protegido con contrasena y no se puede marcar.\n"
              "Habria que abrirlo con la clave y guardar una copia sin proteccion.",
        "en": "This PDF is password-protected and cannot be marked up.\n"
              "You would need to open it with the password and save an unprotected copy."},
}
