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
   La red de seguridad (autotest.py) crea la ventana directamente (no pasa por
   main()), asi que nunca se llama a cargar_idioma_guardado(): la prueba corre
   SIEMPRE en espanol, sin importar que idioma haya quedado elegido. Si se
   cambia un texto en espanol que el autotest compara (por ejemplo el de "PDF
   con contrasena"), hay que actualizar tambien la comprobacion.

2. FALLBACK SIEMPRE AL ESPANOL. Si falta una clave, o falta el idioma pedido,
   se devuelve la version 'es'. Un cartel nunca queda vacio ni en blanco.

3. PERSISTENCIA EN LA CARPETA DE DATOS DEL USUARIO, no al lado del programa.
   El programa vive en Program Files (solo lectura): el idioma elegido se guarda
   en %LOCALAPPDATA%\\LectorPDF\\idioma.txt, igual que el registro de errores.

4. MODULO SIN DEPENDENCIAS (solo 'os'). Lo importan el programa, el extractor y
   anotaciones.py; no puede arrastrar a pymupdf ni a nada que pueda faltar.

5. ESPANOL ESCRITO BIEN: con tildes, enes y signos de apertura. La interfaz es
   lo que se ve: "Tamano" en vez de "Tamaño" cambia la palabra. (El codigo y
   sus comentarios siguen sin tildes, que es otra cosa.)
"""

import os

_NOMBRE_APP = "LectorPDF"

# Idioma activo. Arranca SIEMPRE en espanol (ver decision 1). main() lo cambia
# a lo que haya quedado guardado; el autotest lo deja como esta.
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

    Con persistir=False se fuerza un idioma sin tocar la eleccion guardada
    (sirve para pruebas).
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
# El diccionario.
# ===========================================================================

TEXTOS = {
    # --- boton para cambiar de idioma (dice el idioma AL QUE se pasa) --------
    "boton_idioma": {"es": "English", "en": "Español"},

    # ---------------------------------------------------------- biblioteca ---
    "bib_pdfs_en": {"es": "PDFs en %s", "en": "PDFs in %s"},
    "bib_otra_carpeta": {"es": "Otra carpeta…", "en": "Other folder…"},
    "bib_abrir_archivo": {"es": "Abrir archivo…", "en": "Open file…"},
    "bib_actualizar": {"es": "Actualizar", "en": "Refresh"},
    "bib_filtrar": {"es": "Filtrar:", "en": "Filter:"},
    "col_archivo": {"es": "Archivo", "en": "File"},
    "col_modificado": {"es": "Modificado", "en": "Modified"},
    "col_tamano": {"es": "Tamaño", "en": "Size"},
    "bib_elegir_carpeta_titulo": {"es": "Elegir carpeta con PDFs",
                                  "en": "Choose a folder with PDFs"},
    "bib_no_leer_carpeta": {"es": "No se pudo leer la carpeta: %s",
                            "en": "Could not read the folder: %s"},
    "bib_cuenta": {"es": "%d PDF(s). Doble clic o Enter para abrir.",
                   "en": "%d PDF(s). Double-click or Enter to open."},
    "bib_cuenta_filtrados": {"es": "%d de %d PDF(s). Doble clic o Enter para abrir.",
                             "en": "%d of %d PDF(s). Double-click or Enter to open."},
    "bib_sin_pdfs": {"es": "No hay PDFs en esta carpeta.",
                     "en": "There are no PDFs in this folder."},
    "bib_sin_coincidencias": {"es": "Ningún PDF coincide con el filtro.",
                              "en": "No PDF matches the filter."},
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
    "v_pagina": {"es": "Página", "en": "Page"},
    "v_ancho": {"es": "Ancho", "en": "Width"},
    "v_buscar": {"es": "Buscar", "en": "Find"},
    "v_guardar": {"es": "Guardar", "en": "Save"},

    # ------------------------------------- carteles de ayuda de los botones --
    "tip_carpeta": {"es": "Volver a la lista de PDFs (Ctrl+W)",
                    "en": "Back to the list of PDFs (Ctrl+W)"},
    "tip_dibujar": {"es": "Dibujar a mano alzada (D)", "en": "Draw freehand (D)"},
    "tip_texto": {"es": "Escribir una nota (T)", "en": "Write a note (T)"},
    "tip_seleccionar": {
        "es": "Elegir, mover y editar marcas. Arrastrar en un lugar vacío elige texto (S)",
        "en": "Pick, move and edit marks. Dragging on an empty area selects text (S)"},
    "tip_borrar": {"es": "Borrar la marca en la que hagas clic (B)",
                   "en": "Erase the mark you click on (B)"},
    "tip_grueso": {"es": "Trazo grueso o fino", "en": "Thick or thin stroke"},
    "tip_deshacer": {"es": "Deshacer (Ctrl+Z)", "en": "Undo (Ctrl+Z)"},
    "tip_rehacer": {"es": "Rehacer (Ctrl+Y)", "en": "Redo (Ctrl+Y)"},
    "tip_alejar": {"es": "Alejar (Ctrl+−)", "en": "Zoom out (Ctrl+−)"},
    "tip_acercar": {"es": "Acercar (Ctrl++)", "en": "Zoom in (Ctrl++)"},
    "tip_pagina": {"es": "Ver la hoja entera (Ctrl+0)", "en": "Fit the whole page (Ctrl+0)"},
    "tip_ancho": {"es": "Ajustar al ancho de la ventana (Ctrl+2)",
                  "en": "Fit to window width (Ctrl+2)"},
    "tip_zoom": {"es": "Zoom actual. 100% = tamaño real (Ctrl+1)",
                 "en": "Current zoom. 100% = actual size (Ctrl+1)"},
    "tip_anterior": {"es": "Página anterior (Re Pág)", "en": "Previous page (Page Up)"},
    "tip_siguiente": {"es": "Página siguiente (Av Pág)", "en": "Next page (Page Down)"},
    "tip_num_pagina": {"es": "Escribí un número y apretá Enter para ir a esa página",
                       "en": "Type a number and press Enter to go to that page"},
    "tip_buscar": {"es": "Buscar en el documento (Ctrl+F)", "en": "Find in the document (Ctrl+F)"},
    "tip_buscar_anterior": {"es": "Anterior (Shift+Enter)", "en": "Previous (Shift+Enter)"},
    "tip_buscar_siguiente": {"es": "Siguiente (Enter o F3)", "en": "Next (Enter or F3)"},
    "tip_buscar_cerrar": {"es": "Cerrar la búsqueda (Esc)", "en": "Close search (Esc)"},
    "tip_idioma": {"es": "Cambiar el idioma del programa", "en": "Change the program's language"},
    "tip_ayuda": {"es": "Cómo se usa (F1)", "en": "How to use it (F1)"},
    "tip_guardar": {"es": "Guardar la devolución y copiar el mensaje para el chat (Ctrl+S)",
                    "en": "Save the feedback and copy the message for the chat (Ctrl+S)"},
    "tip_ojo": {"es": "Mostrar u ocultar tus marcas para leer el documento limpio",
                "en": "Show or hide your marks to read the clean document"},
    "color_rojo": {"es": "Rojo", "en": "Red"},
    "color_naranja": {"es": "Naranja", "en": "Orange"},
    "color_verde": {"es": "Verde", "en": "Green"},
    "color_azul": {"es": "Azul", "en": "Blue"},
    "color_negro": {"es": "Negro", "en": "Black"},

    # ------------------------------------------------------ visor: buscar ----
    "buscar_etiqueta": {"es": "Buscar:", "en": "Find:"},
    "buscar_sin_resultados": {"es": "Sin resultados", "en": "No results"},
    "buscar_n_de_m": {"es": "%d de %d", "en": "%d of %d"},

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
    "pnl_ancho_auto": {"es": "Ancho automático", "en": "Automatic width"},
    "pnl_unificar": {"es": "Unificar en un solo dibujo",
                     "en": "Merge into a single drawing"},
    "pnl_borrar": {"es": "Borrar", "en": "Delete"},
    "pnl_soltar": {"es": "Soltar la selección", "en": "Clear the selection"},

    # ------------------------------------------- visor: panel (dinamico) ----
    "pnl_texto_manual": {"es": "Texto del documento", "en": "Document text"},
    "pnl_caracteres_cita": {"es": "%d caracteres\n“%s”",
                            "en": "%d characters\n“%s”"},
    "pnl_dibujo_mano": {"es": "Dibujo a mano", "en": "Freehand drawing"},
    "pnl_datos_dibujo": {
        "es": "Página %d  ·  %d trazo(s), %d puntos  ·  %.0f × %.0f pt",
        "en": "Page %d  ·  %d stroke(s), %d points  ·  %.0f × %.0f pt"},
    "pnl_nota_escrita": {"es": "Nota escrita", "en": "Written note"},
    "pnl_datos_nota": {"es": "Página %d  ·  %d caracteres\n“%s”",
                       "en": "Page %d  ·  %d characters\n“%s”"},
    "pnl_n_marcas": {"es": "%d marcas elegidas", "en": "%d marks selected"},
    "pnl_datos_varias": {"es": "Página %d  ·  %d dibujo(s), %d nota(s)",
                         "en": "Page %d  ·  %d drawing(s), %d note(s)"},
    "pnl_ninguna": {"es": "(ninguna)", "en": "(none)"},
    "ref_la_frase": {"es": "la frase: %s", "en": "the sentence: %s"},
    "ref_la_marca": {"es": "la marca: %s", "en": "the mark: %s"},

    # ------------------------------------------------- menu del clic derecho --
    "menu_copiar": {"es": "Copiar", "en": "Copy"},
    "menu_nota_aca": {"es": "Escribir una nota acá", "en": "Write a note here"},
    "menu_seleccionar_todo": {"es": "Seleccionar todas las marcas",
                              "en": "Select all marks"},

    # ----------------------------------------------- visor: pie (mensajes) ---
    "pie_comentar": {
        "es": "Hacé clic donde quieras la nota. Va a quedar atada a: "
              "“%s”   (Esc para cancelar)",
        "en": "Click where you want the note. It will be tied to: "
              "“%s”   (Esc to cancel)"},
    "pie_dibujar": {
        "es": "Dibujá donde quieras. El dibujo va a quedar atado a: "
              "“%s”   (Esc para cancelar)",
        "en": "Draw wherever you want. The drawing will be tied to: "
              "“%s”   (Esc to cancel)"},
    "pie_elegir_ref": {
        "es": "Elegí la referencia: arrastrá sobre una frase del documento "
              "o hacé clic en otra marca.   (Esc para cancelar)",
        "en": "Choose the reference: drag over a sentence of the document "
              "or click another mark.   (Esc to cancel)"},
    "pie_ref_guardada": {"es": "Referencia guardada.", "en": "Reference saved."},
    "pie_copiado": {"es": "Copiado: %d caracteres del documento.",
                    "en": "Copied: %d characters of the document."},
    "pie_renombrado": {"es": "Ahora se llama “%s”.",
                       "en": "Now it is called “%s”."},
    "pie_unificados": {"es": "%d dibujos unidos en uno solo (%d trazos).",
                       "en": "%d drawings merged into one (%d strokes)."},
    "pie_escribiendo": {
        "es": "Escribiendo una nota  —  Esc o clic afuera para confirmar",
        "en": "Writing a note  —  Esc or click outside to confirm"},
    "pie_guardando": {"es": "Guardando…", "en": "Saving…"},
    "pie_marcas": {"es": "%d marca(s)%s", "en": "%d mark(s)%s"},
    "pie_sin_guardar": {"es": "   ·   SIN GUARDAR", "en": "   ·   UNSAVED"},

    # ------------------------------------------------------- visor: errores --
    "v_pdf_sin_paginas": {
        "es": "El PDF no tiene ninguna página: puede estar dañado.",
        "en": "The PDF has no pages: it may be damaged."},

    # ----------------------------------------------------------- guardar -----
    "dlg_sin_marcas_titulo": {"es": "Sin marcas", "en": "No marks"},
    "dlg_sin_marcas_cuerpo": {
        "es": "Todavía no hay ninguna marca. ¿Guardar igual?",
        "en": "There are no marks yet. Save anyway?"},
    "dlg_guardar_titulo": {"es": "Guardar devolución", "en": "Save feedback"},
    "dlg_abrir_titulo": {"es": "Abrir un PDF", "en": "Open a PDF"},
    "dlg_incompleto_titulo": {"es": "Guardado incompleto", "en": "Incomplete save"},
    "dlg_incompleto_cuerpo": {
        "es": "El archivo se guardó en:\n%s\n\nPERO estas marcas quedaron afuera:\n\n%s",
        "en": "The file was saved to:\n%s\n\nBUT these marks were left out:\n\n%s"},
    "dlg_no_guardar_titulo": {"es": "No se pudo guardar", "en": "Could not save"},
    "dlg_no_guardar_cuerpo": {
        "es": "%s\n\nEl PDF anterior quedó intacto y tus marcas siguen en pantalla:\n"
              "probá con Guardar y otro nombre.",
        "en": "%s\n\nThe previous PDF is untouched and your marks are still on screen:\n"
              "try Save with a different name."},

    # ----------------------------------------------------- dialogo guardado --
    "dlg_guardado_titulo": {"es": "Guardado", "en": "Saved"},
    "dlg_devolucion_guardada": {"es": "Devolución guardada", "en": "Feedback saved"},
    "dlg_guardado_info": {
        "es": "Esto ya está copiado. Pegalo en el chat con Ctrl+V.\n"
              "Es un mensaje escrito para el agente: le dice qué es esto, dónde\n"
              "quedó el archivo y con qué leerlo. No hace falta que agregues nada.",
        "en": "This is already copied. Paste it into the chat with Ctrl+V.\n"
              "It is a message written for the agent: it tells it what this is, where\n"
              "the file ended up and what to read it with. You do not need to add anything."},
    "dlg_abrir_carpeta": {"es": "Abrir carpeta", "en": "Open folder"},
    "dlg_copiar_de_nuevo": {"es": "Copiar de nuevo", "en": "Copy again"},
    "dlg_copiar_ruta": {"es": "Copiar solo la ruta", "en": "Copy just the path"},
    "dlg_listo": {"es": "Listo", "en": "Done"},

    # ------------------------------------------- mensaje que se pega al chat --
    # Escrito para que lo lea un agente. Lleva 4 datos, en este orden:
    # %s = archivo, %s = Python con las librerias, %s = extractor, %s = archivo.
    # El Python va con su ruta completa: con "python" a secas el agente podia
    # terminar en otro Python de la maquina y fallar por falta de pymupdf.
    "mensaje_chat": {
        "es": "Te paso una devolución mía marcada sobre un PDF.\n"
              "\n"
              "QUÉ ES: leí el documento y lo marqué encima, a mano: dibujos y notas "
              "escritas. Algunas marcas están atadas a una frase concreta del "
              "documento y otras son sueltas.\n"
              "\n"
              "EL ARCHIVO:\n"
              "%s\n"
              "\n"
              "CÓMO LEERLO: no lo abras como un PDF común. Corré este comando, que te "
              "devuelve por separado el texto original del documento y cada marca mía "
              "con la parte del texto sobre la que cae, más una imagen de cada página "
              "marcada. Abrí esas imágenes: el texto te dice dónde cae cada trazo, "
              "pero no si es un círculo, un tachado o una flecha.\n"
              "\n"
              "\"%s\" \"%s\" \"%s\"\n",
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
              "\"%s\" \"%s\" \"%s\"\n"},

    # ------------------------------------------------------- app: titulo -----
    "app_titulo": {"es": "Lector PDF", "en": "Lector PDF"},
    "app_titulo_carpeta": {"es": "Lector PDF  —  %s", "en": "Lector PDF  —  %s"},
    "app_titulo_doc": {"es": "%s%s  —  Lector PDF", "en": "%s%s  —  Lector PDF"},

    # ------------------------------------------------------- app: errores ----
    "app_fallo_titulo": {"es": "Algo salió mal", "en": "Something went wrong"},
    "app_fallo_cuerpo": {
        "es": "%s\n\nEs el error número %d de esta sesión.\n"
              "Quedaron todos anotados en:\n%s",
        "en": "%s\n\nThis is error number %d of this session.\n"
              "They were all logged in:\n%s"},
    "app_no_abrir_titulo": {"es": "No se pudo abrir", "en": "Could not open"},
    "app_no_abrir_cuerpo": {"es": "%s\n\n%s", "en": "%s\n\n%s"},
    "app_sin_guardar_titulo": {"es": "Hay marcas sin guardar",
                               "en": "There are unsaved marks"},
    "app_sin_guardar_cuerpo": {
        "es": "Tenés cambios sin guardar (%d marca(s) en total).\n\n¿Guardar antes de salir?",
        "en": "You have unsaved changes (%d mark(s) in total).\n\nSave before leaving?"},

    # --------------------------------------- app: arranque fatal (bootstrap) -
    "app_falta_libreria": {
        "es": "Falta una librería que el programa necesita:\n\n    %s\n\n"
              "Se está usando este Python:\n    %s\n\n"
              "Se arregla instalándola con:\n    \"%s\" -m pip install pymupdf pillow",
        "en": "A library the program needs is missing:\n\n    %s\n\n"
              "This Python is being used:\n    %s\n\n"
              "Fix it by installing it with:\n    \"%s\" -m pip install pymupdf pillow"},
    "app_no_arranco_titulo": {"es": "El Lector PDF no pudo arrancar",
                              "en": "Lector PDF could not start"},
    "app_no_arranco_cuerpo": {
        "es": "%s\n\nEl detalle quedó en:\n%s\n\nPasale este texto al agente y lo arregla.",
        "en": "%s\n\nThe details are in:\n%s\n\nGive this text to the agent and it will fix it."},

    # ------------------------------------------------ anotaciones.py (visible) -
    "pdf_con_contrasena": {
        "es": "Este PDF está protegido con contraseña y no se puede marcar.\n"
              "Habría que abrirlo con la clave y guardar una copia sin protección.",
        "en": "This PDF is password-protected and cannot be marked up.\n"
              "You would need to open it with the password and save an unprotected copy."},
}
