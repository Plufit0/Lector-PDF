# -*- coding: utf-8 -*-
"""
ayuda.py — el instructivo del programa, en un solo lugar.

De aca salen las dos versiones: la ventana que abre el boton "?" y el archivo
"Como usar Lector PDF.txt" del escritorio. Estan escritas una sola vez a
proposito: si el instructivo viviera suelto en un .txt, cada cambio del programa
lo dejaria desactualizado sin que nadie se entere.

POR QUE EL TEXTO LARGO VIVE ACA Y NO EN idiomas.py: el resto del programa saca
sus carteles cortos de idiomas.py (el estandar del estudio). El instructivo es
la excepcion a proposito: es un texto largo y ESTRUCTURADO (secciones, atajos,
notas), no un puñado de cadenas sueltas, y su razon de ser es estar "en un solo
lugar". Por eso las dos versiones (es / en) viven aca, y este modulo solo le
pregunta a idiomas.py cual idioma mostrar.
"""

import tkinter as tk
from tkinter import ttk

import idiomas

# El nombre del programa es marca: no se traduce.
TITULO = "Lector PDF"

BAJADA = {
    "es": "Leé cualquier PDF y marcalo encima para devolvérselo a un agente.",
    "en": "Read any PDF and mark it up to hand it back to an agent.",
}

# ("seccion", texto) | ("parrafo", texto) | ("atajo", (tecla, que hace)) | ("nota", texto)
CONTENIDO = {
    "es": [
        ("seccion", "Para qué es"),
        ("parrafo", "Vos ves un solo documento marcado. El agente recibe dos cosas separadas: "
                    "el texto original del documento y, aparte, cada marca tuya con la parte "
                    "del texto sobre la que cae."),

        ("seccion", "Abrir un PDF"),
        ("parrafo", "Doble clic en el ícono \u201cLector PDF\u201d del escritorio. Se abre mostrando "
                    "los PDFs de Descargas, el más nuevo arriba y ya elegido. Doble clic o Enter "
                    "sobre el que quieras."),
        ("atajo", ("Filtrar", "Escribí parte del nombre y la lista muestra solo esos.")),
        ("atajo", ("Título de una columna", "Ordena por nombre, fecha o tamaño. Otro clic, al revés.")),
        ("atajo", ("Otra carpeta\u2026", "Ver los PDFs de otra carpeta.")),
        ("atajo", ("Abrir archivo\u2026  (Ctrl+O)", "Abrir un PDF de cualquier lado.")),

        ("seccion", "Moverse por el documento"),
        ("atajo", ("Rueda del mouse", "Leer. Siempre, tengas la herramienta que tengas. Al llegar "
                                      "al final de la hoja, el siguiente giro pasa de página.")),
        ("atajo", ("Ruedita apretada", "La \u201cmanito\u201d: apretala y mové el mouse para arrastrar "
                                       "la hoja.")),
        ("atajo", ("Ctrl + rueda", "Acercar o alejar hacia donde apunta el mouse.")),
        ("atajo", ("Shift + rueda", "Moverse de costado.")),
        ("atajo", ("Av Pág / Re Pág", "Página siguiente y anterior. También las flechas, si no "
                                      "hay nada elegido.")),
        ("atajo", ("Inicio / Fin", "Principio o final de la hoja.")),
        ("atajo", ("Ctrl + Inicio / Fin", "Primera o última página.")),
        ("atajo", ("Número de página", "Se puede escribir y apretar Enter.")),

        ("seccion", "Las herramientas"),
        ("atajo", ("S  o  Seleccionar", "La de siempre: elegir, mover y cambiar lo que ya marcaste, "
                                        "y elegir texto del PDF.")),
        ("atajo", ("D  o  Dibujar", "Dibujar a mano alzada. Queda puesta para hacer varios trazos "
                                    "seguidos.")),
        ("atajo", ("T  o  Texto", "Escribir una nota: clic donde la querés, escribís, Esc o clic "
                                  "afuera. Después vuelve sola a Seleccionar.")),
        ("atajo", ("B  o  Borrar", "Borrar la marca en la que hagas clic.")),
        ("nota", "Pasá el mouse por encima de cualquier botón para ver qué hace y su atajo."),

        ("seccion", "Seleccionar, en detalle"),
        ("atajo", ("Clic sobre una marca", "La elige y abre el panel de la derecha. En un dibujo "
                                           "hay que hacer clic sobre el trazo.")),
        ("atajo", ("Arrastrar una marca", "La mueve de lugar.")),
        ("atajo", ("Ctrl o Shift + clic", "Sumar o sacar marcas de la selección.")),
        ("atajo", ("Clic derecho y arrastrar", "Recuadro verde: elige los dibujos y notas que toca. "
                                               "Si no toca ninguna marca, elige el texto que "
                                               "queda adentro. Funciona con cualquier herramienta.")),
        ("atajo", ("Clic derecho", "Menú con lo que se puede hacer ahí: copiar, comentar, editar, "
                                   "borrar\u2026")),
        ("atajo", ("Arrastrar en un vacío", "Elige el texto del PDF que toques.")),
        ("atajo", ("Ctrl + A", "Elegir todas las marcas de la página.")),
        ("atajo", ("Flechas", "Con algo elegido, lo mueven de a poquito (con Shift, más).")),
        ("atajo", ("Supr o Retroceso", "Borrar lo elegido.")),
        ("atajo", ("Esc", "Soltar lo elegido o cancelar lo que estabas por hacer. Nunca cierra "
                          "el documento.")),
        ("atajo", ("Ctrl + C", "Copiar el texto del PDF que hayas elegido.")),
        ("nota", "Con varios dibujos elegidos aparece \u201cUnificar\u201d: los junta en uno solo, "
                 "para que el agente los lea como una sola marca y no como tres sueltas."),

        ("seccion", "Las notas"),
        ("atajo", ("Doble clic en una nota", "Editar lo que dice. En modo Texto alcanza con un clic.")),
        ("atajo", ("Manija del borde derecho", "Con la nota elegida, arrastrala para hacer la nota "
                                               "más ancha o más angosta, hasta un solo renglón del "
                                               "ancho de la hoja. El alto se acomoda solo.")),
        ("atajo", ("Ancho automático", "Botón del panel: la nota vuelve a su ancho de siempre.")),
        ("nota", "El recuadro amarillo siempre queda ajustado al texto, en pantalla y en el PDF "
                 "guardado."),

        ("seccion", "Atar una marca a una frase"),
        ("atajo", ("Comentar esta frase", "Con una frase del documento elegida: pasa a modo Texto "
                                          "y esperás a hacer clic donde querés la nota. Esa nota "
                                          "queda ATADA a la frase.")),
        ("atajo", ("Dibujar sobre esta frase", "Lo mismo, pero lo que sigue es un dibujo.")),
        ("atajo", ("Referencia a\u2026", "En el panel de cualquier marca: \u201cElegir\u201d y después "
                                         "arrastrás sobre una frase del documento o hacés clic en "
                                         "otra marca. \u201cQuitar\u201d la desata.")),
        ("nota", "Atar es opcional. Atada, el agente sabe exactamente a qué palabras te referís, sin "
                 "deducirlo por dónde quedó pegada. Al elegir una marca atada, una flecha naranja "
                 "apunta a su frase. Esc cancela si te arrepentís."),

        ("seccion", "Buscar"),
        ("atajo", ("Ctrl + F  o  Buscar", "Abre la barra de búsqueda.")),
        ("atajo", ("Enter  o  F3", "Siguiente resultado. Shift + Enter o Shift + F3, el anterior.")),
        ("atajo", ("Esc", "Cierra la búsqueda.")),
        ("nota", "Lo encontrado queda elegido como texto del documento: se lo puede comentar o "
                 "dibujar encima de una."),

        ("seccion", "Ver"),
        ("atajo", ("Página  (Ctrl+0)", "La hoja entera.")),
        ("atajo", ("Ancho  (Ctrl+2)", "La hoja al ancho de la ventana.")),
        ("atajo", ("Ctrl + 1", "Tamaño real. El porcentaje de al lado del \u201c+\u201d dice el zoom.")),
        ("atajo", ("+ / \u2212  (Ctrl + / Ctrl \u2212)", "Acercar y alejar.")),
        ("atajo", ("\U0001F441 Marcas (abajo)", "Oculta tus marcas para leer el documento limpio. "
                                               "Ocultas no se pueden tocar; vuelven al elegir "
                                               "Dibujar, Texto o Borrar.")),
        ("atajo", ("English / Español", "Cambia el idioma del programa en el momento, sin perder "
                                        "nada.")),

        ("seccion", "Lo demás"),
        ("atajo", ("Ctrl + Z  /  Ctrl + Y", "Deshacer y rehacer.")),
        ("atajo", ("Colores y Grueso", "El color del trazo y de la letra. Rojo es el de entrada.")),
        ("atajo", ("Ctrl + W  o  < Carpeta", "Volver a la lista de PDFs.")),
        ("atajo", ("F1  o  ?", "Este instructivo.")),

        ("seccion", "Guardar y pasárselo al agente"),
        ("parrafo", "Botón Guardar, o Ctrl+S. Elegís carpeta y nombre; te propone el del documento "
                    "con \u201c-devolucion\u201d al final, numerado si ya existe. Al guardar, el programa "
                    "copia solo al portapapeles todo lo que el agente necesita: vas al chat y "
                    "apretás Ctrl+V. No hace falta explicar nada."),
        ("nota", "Podés guardar cuantas veces quieras. Si volvés a abrir un PDF que ya marcaste, tus "
                 "marcas siguen ahí y podés agregarle más."),

        ("seccion", "Cosas que conviene saber"),
        ("parrafo", "El PDF original nunca se toca: siempre se guarda una copia nueva. Las marcas "
                    "quedan como anotaciones de PDF, no aplastadas contra la hoja: se ven en "
                    "cualquier otro lector de PDF y se pueden seguir editando después. Si cerrás "
                    "con cambios sin guardar, el programa te avisa. Un clic suelto sin arrastrar "
                    "no deja ninguna marca."),

        ("seccion", "Si algo no anda"),
        ("parrafo", "Si aparece un cartel de error, pasáselo al agente tal cual. El detalle de "
                    "TODOS los errores de la sesión queda guardado (y el de la sesión anterior "
                    "también), y el botón \u201cVer errores\u201d de esta ventana te dice dónde."),
    ],
    "en": [
        ("seccion", "What it is for"),
        ("parrafo", "You see a single marked-up document. The agent receives two separate things: "
                    "the original text of the document and, on the side, each of your marks with "
                    "the part of the text it falls on."),

        ("seccion", "Opening a PDF"),
        ("parrafo", "Double-click the \u201cLector PDF\u201d icon on the desktop. It opens showing the "
                    "PDFs in Downloads, the newest at the top and already selected. Double-click "
                    "or Enter on the one you want."),
        ("atajo", ("Filter", "Type part of the name and the list shows only those.")),
        ("atajo", ("Column title", "Sorts by name, date or size. Click again to reverse.")),
        ("atajo", ("Other folder\u2026", "See the PDFs of another folder.")),
        ("atajo", ("Open file\u2026  (Ctrl+O)", "Open a PDF from anywhere.")),

        ("seccion", "Moving around the document"),
        ("atajo", ("Mouse wheel", "Read. Always, whatever tool you have. At the bottom of the "
                                  "sheet, the next turn goes to the next page.")),
        ("atajo", ("Pressed wheel", "The \u201chand\u201d: press it and move the mouse to drag the "
                                    "sheet.")),
        ("atajo", ("Ctrl + wheel", "Zoom in or out toward the mouse pointer.")),
        ("atajo", ("Shift + wheel", "Move sideways.")),
        ("atajo", ("PgDn / PgUp", "Next and previous page. Also the arrows, if nothing is "
                                  "selected.")),
        ("atajo", ("Home / End", "Top or bottom of the sheet.")),
        ("atajo", ("Ctrl + Home / End", "First or last page.")),
        ("atajo", ("Page number", "Can be typed, then press Enter.")),

        ("seccion", "The tools"),
        ("atajo", ("S  or  Select", "The usual one: pick, move and change what you already marked, "
                                    "and select text from the PDF.")),
        ("atajo", ("D  or  Draw", "Draw freehand. It stays on so you can make several strokes.")),
        ("atajo", ("T  or  Text", "Write a note: click where you want it, type, Esc or click "
                                  "outside. Then it goes back to Select by itself.")),
        ("atajo", ("B  or  Erase", "Erase the mark you click on.")),
        ("nota", "Hover over any button to see what it does and its shortcut."),

        ("seccion", "Select, in detail"),
        ("atajo", ("Click on a mark", "Selects it and opens the panel on the right. On a drawing, "
                                      "click on the stroke itself.")),
        ("atajo", ("Drag a mark", "Moves it.")),
        ("atajo", ("Ctrl or Shift + click", "Add or remove marks from the selection.")),
        ("atajo", ("Right-click and drag", "Green box: selects the drawings and notes it touches. "
                                           "If it touches no mark, it selects the text inside. "
                                           "Works with any tool.")),
        ("atajo", ("Right-click", "Menu with what you can do there: copy, comment, edit, "
                                  "delete\u2026")),
        ("atajo", ("Drag on an empty area", "Selects the PDF text you touch.")),
        ("atajo", ("Ctrl + A", "Select all the marks on the page.")),
        ("atajo", ("Arrows", "With something selected, they nudge it (more with Shift).")),
        ("atajo", ("Del or Backspace", "Delete what is selected.")),
        ("atajo", ("Esc", "Clear the selection or cancel what you were about to do. It never "
                          "closes the document.")),
        ("atajo", ("Ctrl + C", "Copy the PDF text you selected.")),
        ("nota", "With several drawings selected, \u201cMerge\u201d appears: it joins them into one, so "
                 "the agent reads them as a single mark and not as three loose ones."),

        ("seccion", "Notes"),
        ("atajo", ("Double-click a note", "Edit what it says. In Text mode a single click is "
                                          "enough.")),
        ("atajo", ("Right-edge handle", "With the note selected, drag it to make the note wider or "
                                        "narrower, up to a single line as wide as the page. The "
                                        "height adjusts by itself.")),
        ("atajo", ("Automatic width", "Panel button: the note goes back to its usual width.")),
        ("nota", "The yellow box always fits the text, on screen and in the saved PDF."),

        ("seccion", "Tying a mark to a sentence"),
        ("atajo", ("Comment on this sentence", "With a sentence of the document selected: switches "
                                               "to Text mode and waits for you to click where you "
                                               "want the note. That note stays TIED to the "
                                               "sentence.")),
        ("atajo", ("Draw over this sentence", "The same, but what follows is a drawing.")),
        ("atajo", ("Reference to\u2026", "In any mark's panel: \u201cChoose\u201d and then drag over a "
                                         "sentence of the document or click another mark. "
                                         "\u201cRemove\u201d unties it.")),
        ("nota", "Tying is optional. Tied, the agent knows exactly which words you mean, without "
                 "deducing it from where it ended up. When you select a tied mark, an orange arrow "
                 "points to its sentence. Esc cancels if you change your mind."),

        ("seccion", "Find"),
        ("atajo", ("Ctrl + F  or  Find", "Opens the search bar.")),
        ("atajo", ("Enter  or  F3", "Next result. Shift + Enter or Shift + F3, the previous one.")),
        ("atajo", ("Esc", "Closes the search.")),
        ("nota", "What is found stays selected as document text: you can comment on it or draw "
                 "over it right away."),

        ("seccion", "View"),
        ("atajo", ("Page  (Ctrl+0)", "The whole sheet.")),
        ("atajo", ("Width  (Ctrl+2)", "The sheet as wide as the window.")),
        ("atajo", ("Ctrl + 1", "Actual size. The percentage next to \u201c+\u201d shows the zoom.")),
        ("atajo", ("+ / \u2212  (Ctrl + / Ctrl \u2212)", "Zoom in and out.")),
        ("atajo", ("\U0001F441 Marks (bottom)", "Hides your marks to read the clean document. "
                                               "Hidden marks cannot be touched; they come back "
                                               "when you choose Draw, Text or Erase.")),
        ("atajo", ("English / Español", "Changes the program's language on the spot, losing "
                                        "nothing.")),

        ("seccion", "Everything else"),
        ("atajo", ("Ctrl + Z  /  Ctrl + Y", "Undo and redo.")),
        ("atajo", ("Colors and Thick", "The color of the stroke and the text. Red is the default.")),
        ("atajo", ("Ctrl + W  or  < Folder", "Back to the list of PDFs.")),
        ("atajo", ("F1  or  ?", "This guide.")),

        ("seccion", "Save and hand it to the agent"),
        ("parrafo", "Save button, or Ctrl+S. You choose a folder and name; it suggests the "
                    "document's with \u201c-devolucion\u201d at the end, numbered if it already exists. "
                    "On saving, the program copies to the clipboard everything the agent needs: "
                    "go to the chat and press Ctrl+V. No need to explain anything."),
        ("nota", "You can save as many times as you want. If you reopen a PDF you already marked, "
                 "your marks are still there and you can add more."),

        ("seccion", "Things worth knowing"),
        ("parrafo", "The original PDF is never touched: a new copy is always saved. The marks stay "
                    "as PDF annotations, not flattened onto the sheet: they show up in any other "
                    "PDF reader and can still be edited later. If you close with unsaved changes, "
                    "the program warns you. A single click without dragging leaves no mark."),

        ("seccion", "If something does not work"),
        ("parrafo", "If an error message appears, pass it to the agent as is. The detail of ALL "
                    "the errors of the session is saved (and the previous session's too), and the "
                    "\u201cView errors\u201d button in this window tells you where."),
    ],
}

# Textos de la ventana y del pie del .txt. Igual que el contenido: bilingue y en
# este mismo modulo, para que el instructivo entero se mantenga en un solo lugar.
CHROME = {
    "titulo_ventana": {"es": "Cómo usar el Lector PDF", "en": "How to use Lector PDF"},
    "ver_errores": {"es": "Ver errores de esta sesión", "en": "View this session's errors"},
    "cerrar": {"es": "Cerrar", "en": "Close"},
    "errores_titulo": {"es": "Errores de esta sesión", "en": "This session's errors"},
    "no_leer_registro": {"es": "No se pudo leer el registro: %s",
                         "en": "Could not read the log: %s"},
    "sin_errores": {"es": "No hubo ningún error en esta sesión.\n\n"
                          "Cuando haya alguno, queda anotado en:\n%s",
                    "en": "There were no errors in this session.\n\n"
                          "When there is one, it will be logged in:\n%s"},
    "pie_1": {"es": "El programa vive en C:\\Program Files\\Mios\\LectorPDF.",
              "en": "The program lives in C:\\Program Files\\Mios\\LectorPDF."},
    "pie_2": {"es": "Los errores quedan anotados en la carpeta LectorPDF de tus datos locales.",
              "en": "The errors are logged in the LectorPDF folder of your local data."},
    "pie_3": {"es": "Este mismo instructivo está en el botón \u201c?\u201d del programa.",
              "en": "This same guide is in the program's \u201c?\u201d button."},
}


def _idioma():
    try:
        codigo = idiomas.idioma_actual()
    except Exception:
        codigo = "es"
    return codigo if codigo in ("es", "en") else "es"


def _bajada(idioma):
    return BAJADA.get(idioma) or BAJADA["es"]


def _contenido(idioma):
    return CONTENIDO.get(idioma) or CONTENIDO["es"]


def _chrome(clave, idioma):
    entrada = CHROME.get(clave, {})
    return entrada.get(idioma) or entrada.get("es", clave)


# ------------------------------------------------------------------ texto ----

def como_texto(idioma=None):
    """El instructivo en texto plano, para el archivo del escritorio.

    Se le puede pasar el idioma (\"es\" / \"en\") para generar el .txt en uno u
    otro; por defecto usa el idioma activo del programa.
    """
    import textwrap
    idioma = idioma if idioma in ("es", "en") else _idioma()
    lineas = [TITULO.upper(), "=" * len(TITULO), "", _bajada(idioma), ""]
    for clase, dato in _contenido(idioma):
        if clase == "seccion":
            lineas += ["", dato, "-" * len(dato)]
        elif clase == "parrafo":
            lineas += [textwrap.fill(dato, 78), ""]
        elif clase == "nota":
            lineas += [textwrap.fill(dato, 76, initial_indent="  * ",
                                     subsequent_indent="    "), ""]
        else:
            tecla, que = dato
            # La sangria de continuacion tiene que ser del ancho del prefijo
            # entero, o las lineas siguientes quedan escalonadas y no se lee.
            prefijo = "  %-30s " % tecla
            lineas.append(textwrap.fill(que, 78, initial_indent=prefijo,
                                        subsequent_indent=" " * len(prefijo)))
    lineas += ["", "", _chrome("pie_1", idioma), _chrome("pie_2", idioma),
               _chrome("pie_3", idioma)]
    return "\n".join(lineas)


# ---------------------------------------------------------------- ventana ----

FONDO = "#FFFFFF"
TINTA = "#1F2328"
AZUL = "#1B5E9E"
GRIS = "#5B6472"
CAJA = "#EEF4FA"


class Ventana(tk.Toplevel):
    """El mismo instructivo, pero para leer en pantalla."""

    def __init__(self, padre, ruta_errores=None):
        super().__init__(padre)
        self.idioma = _idioma()
        self.title(_chrome("titulo_ventana", self.idioma))
        self.geometry("760x720")
        self.minsize(560, 420)
        self.transient(padre)
        self.configure(bg=FONDO)

        cabecera = tk.Frame(self, bg=AZUL)
        cabecera.pack(fill="x")
        tk.Label(cabecera, text=TITULO, bg=AZUL, fg="white",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=20, pady=(15, 0))
        tk.Label(cabecera, text=_bajada(self.idioma), bg=AZUL, fg="#D7E6F5", wraplength=700,
                 justify="left", font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(2, 15))

        cuerpo = tk.Frame(self, bg=FONDO)
        cuerpo.pack(fill="both", expand=True)
        self.txt = tk.Text(cuerpo, wrap="word", bg=FONDO, fg=TINTA, relief="flat",
                           padx=22, pady=16, cursor="arrow",
                           font=("Segoe UI", 10), spacing1=1, spacing3=5)
        sb = ttk.Scrollbar(cuerpo, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.txt.tag_configure("seccion", font=("Segoe UI", 12, "bold"), foreground=AZUL,
                               spacing1=16, spacing3=7)
        self.txt.tag_configure("parrafo", spacing3=9, lmargin1=2, lmargin2=2)
        self.txt.tag_configure("nota", background=CAJA, foreground=GRIS, lmargin1=12,
                               lmargin2=12, rmargin=12, spacing1=6, spacing3=8,
                               font=("Segoe UI", 10))
        self.txt.tag_configure("tecla", font=("Consolas", 10, "bold"), foreground="#8A4B00")
        self.txt.tag_configure("que", lmargin1=0, lmargin2=226, spacing3=6)

        self._pintar()
        self.txt.config(state="disabled")

        pie = tk.Frame(self, bg="#F3F4F6")
        pie.pack(fill="x")
        if ruta_errores:
            ttk.Button(pie, text=_chrome("ver_errores", self.idioma),
                       command=lambda: self._mostrar_errores(ruta_errores)).pack(
                           side="left", padx=12, pady=10)
        ttk.Button(pie, text=_chrome("cerrar", self.idioma),
                   command=self.destroy).pack(side="right", padx=12, pady=10)

        self.bind("<Escape>", lambda e: self.destroy())
        self.txt.bind("<MouseWheel>", self._rueda)
        self.focus_set()

    def _rueda(self, e):
        self.txt.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    def _pintar(self):
        t = self.txt
        for clase, dato in _contenido(self.idioma):
            if clase == "seccion":
                t.insert("end", dato + "\n", "seccion")
            elif clase == "parrafo":
                t.insert("end", dato + "\n", "parrafo")
            elif clase == "nota":
                t.insert("end", " " + dato + " \n", "nota")
            else:
                tecla, que = dato
                t.insert("end", "%-28s" % tecla, "tecla")
                t.insert("end", que + "\n", "que")

    def _mostrar_errores(self, ruta):
        import os
        v = tk.Toplevel(self)
        v.title(_chrome("errores_titulo", self.idioma))
        v.geometry("820x520")
        caja = tk.Text(v, wrap="none", font=("Consolas", 9))
        caja.pack(fill="both", expand=True)
        if os.path.exists(ruta):
            try:
                caja.insert("1.0", open(ruta, encoding="utf-8").read())
            except Exception as err:
                caja.insert("1.0", _chrome("no_leer_registro", self.idioma) % err)
        else:
            caja.insert("1.0", _chrome("sin_errores", self.idioma) % ruta)
        caja.config(state="disabled")
        ttk.Button(v, text=_chrome("cerrar", self.idioma), command=v.destroy).pack(pady=8)
