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
    "es": "Leer un manual de diseno y marcarlo encima para devolverselo al agente.",
    "en": "Read a design manual and mark it up to send it back to the agent.",
}

# ("seccion", texto) | ("parrafo", texto) | ("atajo", (tecla, que hace)) | ("nota", texto)
CONTENIDO = {
    "es": [
        ("seccion", "Para que es"),
        ("parrafo", "Vos ves un solo documento marcado. El agente recibe dos cosas separadas: "
                    "el texto original del manual y, aparte, cada marca tuya anclada al parrafo "
                    "sobre el que cae."),

        ("seccion", "Abrirlo"),
        ("parrafo", "Doble clic en el icono \u201cLector PDF\u201d del escritorio (una hoja con un "
                    "trazo rojo). Se abre mostrando los PDFs de Descargas, el mas nuevo arriba y "
                    "ya seleccionado. Doble clic o Enter sobre el que quieras."),
        ("nota", "Si el PDF esta en otra carpeta: boton \u201cOtra carpeta...\u201d, arriba a la derecha."),

        ("seccion", "Leer y marcar es la misma postura"),
        ("parrafo", "No hay que cambiar de modo para pasar de una cosa a la otra:"),
        ("atajo", ("Rueda del mouse", "Leer. Siempre, hagas lo que hagas. Al llegar al final de "
                                      "la hoja, el siguiente tiron pasa de pagina.")),
        ("atajo", ("Arrastrar", "Dibujar. Sin apretar ningun boton antes.")),

        ("seccion", "Las herramientas"),
        ("atajo", ("D  o  boton Dibujar", "Dibujar a mano alzada.")),
        ("atajo", ("T  o  boton Texto", "Escribir una nota: clic donde la querés, escribis, Esc.")),
        ("atajo", ("S  o  boton Seleccionar", "Agarrar lo ya hecho para moverlo o cambiarlo, y "
                                              "tambien seleccionar texto del PDF para copiarlo.")),
        ("atajo", ("B  o  boton Borrar", "Borrar una marca: clic encima de ella.")),

        ("seccion", "Modo Seleccionar, en detalle"),
        ("atajo", ("Clic sobre una marca", "La selecciona y abre el panel de la derecha.")),
        ("atajo", ("Arrastrar una marca", "La mueve de lugar.")),
        ("atajo", ("Ctrl + clic", "Sumar o sacar marcas de la seleccion.")),
        ("atajo", ("Arrastrar en un vacio", "Selecciona el texto del PDF que toques.")),
        ("atajo", ("Ctrl + C", "Copia el texto del PDF que hayas seleccionado.")),
        ("atajo", ("Doble clic en una nota", "Editar lo que dice.")),
        ("atajo", ("Comentar esta frase", "Con una frase del manual elegida: el programa pasa "
                                          "a modo Texto y esperas a hacer clic donde queres la "
                                          "nota. Esa nota queda ATADA a la frase.")),
        ("atajo", ("Dibujar sobre esta frase", "Lo mismo, pero lo que sigue es un dibujo.")),
        ("atajo", ("Referencia a...", "En el panel de cualquier marca: \u201cElegir\u201d y despues "
                                      "arrastras sobre una frase del manual, o haces clic en otra "
                                      "marca. \u201cQuitar\u201d la desata.")),
        ("atajo", ("Supr", "Borrar lo seleccionado.")),
        ("nota", "Con varios dibujos seleccionados aparece \u201cUnificar\u201d: los junta en un solo "
                 "dibujo, para que el agente los lea como una sola marca y no como tres sueltas."),
        ("nota", "Atar una marca a una frase es opcional: si no lo haces, todo funciona como "
                 "siempre. Atada, el agente sabe exactamente a que palabras te referis, sin "
                 "deducirlo por donde quedo pegada. Esc cancela si te arrepentis."),

        ("seccion", "Lo demas"),
        ("atajo", ("Ctrl + Z  /  Ctrl + Y", "Deshacer y rehacer.")),
        ("atajo", ("Colores y Grueso", "El color del trazo y de la letra. Rojo es el de entrada.")),
        ("atajo", ("Pagina / Ancho / + / -", "Ver la hoja entera o agrandada. El numero de pagina "
                                             "se puede escribir y apretar Enter.")),
        ("atajo", ("Flechas  o  Re/Av Pag", "Cambiar de pagina.")),

        ("seccion", "Guardar y pasarmelo"),
        ("parrafo", "Boton Guardar, o Ctrl+S. Elegis carpeta y nombre; te propone el del manual "
                    "con \u201c-devolucion\u201d al final. Al guardar, el programa copia solo al "
                    "portapapeles todo lo que el agente necesita: vas al chat y apretas Ctrl+V. "
                    "No hace falta explicar nada."),
        ("nota", "Podes guardar cuantas veces quieras. Si volves a abrir un PDF que ya marcaste, "
                 "tus marcas siguen ahi y podes agregarle mas."),

        ("seccion", "Cosas que conviene saber"),
        ("parrafo", "El manual original nunca se toca: siempre se guarda una copia nueva. Las "
                    "marcas quedan como anotaciones de PDF, no aplastadas contra la hoja, y por "
                    "eso se pueden seguir editando despues. Si cerras con marcas sin guardar, el "
                    "programa te avisa. Un clic suelto sin arrastrar no deja ninguna marca."),

        ("seccion", "Si algo no anda"),
        ("parrafo", "Si aparece un cartel de error, pasaselo al agente tal cual. El detalle de "
                    "TODOS los errores de la sesion queda guardado, y el boton \u201cVer errores\u201d "
                    "de esta ventana te dice donde."),
    ],
    "en": [
        ("seccion", "What it is for"),
        ("parrafo", "You see a single marked-up document. The agent receives two separate things: "
                    "the original text of the manual and, on the side, each of your marks anchored "
                    "to the paragraph it falls on."),

        ("seccion", "Opening it"),
        ("parrafo", "Double-click the \u201cLector PDF\u201d icon on the desktop (a sheet with a red "
                    "stroke). It opens showing the PDFs in Downloads, the newest at the top and "
                    "already selected. Double-click or Enter on the one you want."),
        ("nota", "If the PDF is in another folder: \u201cOther folder...\u201d button, top right."),

        ("seccion", "Reading and marking are the same posture"),
        ("parrafo", "You do not need to switch modes to go from one to the other:"),
        ("atajo", ("Mouse wheel", "Read. Always, whatever you are doing. When you reach the "
                                  "bottom of the sheet, the next nudge turns the page.")),
        ("atajo", ("Drag", "Draw. Without pressing any button first.")),

        ("seccion", "The tools"),
        ("atajo", ("D  or  Draw button", "Draw freehand.")),
        ("atajo", ("T  or  Text button", "Write a note: click where you want it, type, Esc.")),
        ("atajo", ("S  or  Select button", "Grab what you already made to move or change it, and "
                                           "also select text from the PDF to copy it.")),
        ("atajo", ("B  or  Erase button", "Erase a mark: click on top of it.")),

        ("seccion", "Select mode, in detail"),
        ("atajo", ("Click on a mark", "Selects it and opens the panel on the right.")),
        ("atajo", ("Drag a mark", "Moves it.")),
        ("atajo", ("Ctrl + click", "Add or remove marks from the selection.")),
        ("atajo", ("Drag on an empty area", "Selects the PDF text you touch.")),
        ("atajo", ("Ctrl + C", "Copies the PDF text you have selected.")),
        ("atajo", ("Double-click a note", "Edit what it says.")),
        ("atajo", ("Comment on this sentence", "With a sentence of the manual selected: the "
                                               "program switches to Text mode and waits for you "
                                               "to click where you want the note. That note "
                                               "stays TIED to the sentence.")),
        ("atajo", ("Draw over this sentence", "The same, but what follows is a drawing.")),
        ("atajo", ("Reference to...", "In any mark's panel: \u201cChoose\u201d and then drag over a "
                                      "sentence of the manual, or click another mark. "
                                      "\u201cRemove\u201d unties it.")),
        ("atajo", ("Del", "Delete what is selected.")),
        ("nota", "With several drawings selected, \u201cMerge\u201d appears: it joins them into a "
                 "single drawing, so the agent reads them as one mark and not as three loose ones."),
        ("nota", "Tying a mark to a sentence is optional: if you do not, everything works as "
                 "always. Tied, the agent knows exactly which words you mean, without deducing it "
                 "from where it ended up. Esc cancels if you change your mind."),

        ("seccion", "Everything else"),
        ("atajo", ("Ctrl + Z  /  Ctrl + Y", "Undo and redo.")),
        ("atajo", ("Colors and Thick", "The color of the stroke and the text. Red is the default.")),
        ("atajo", ("Page / Width / + / -", "See the whole sheet or enlarged. The page number can "
                                           "be typed and Enter pressed.")),
        ("atajo", ("Arrows  or  PgUp/PgDn", "Change page.")),

        ("seccion", "Save and send it to me"),
        ("parrafo", "Save button, or Ctrl+S. You choose a folder and name; it suggests the "
                    "manual's with \u201c-devolucion\u201d at the end. On saving, the program copies "
                    "to the clipboard by itself everything the agent needs: you go to the chat "
                    "and press Ctrl+V. No need to explain anything."),
        ("nota", "You can save as many times as you want. If you reopen a PDF you already marked, "
                 "your marks are still there and you can add more."),

        ("seccion", "Things worth knowing"),
        ("parrafo", "The original manual is never touched: a new copy is always saved. The marks "
                    "stay as PDF annotations, not flattened onto the sheet, and that is why they "
                    "can still be edited later. If you close with unsaved marks, the program "
                    "warns you. A single click without dragging leaves no mark."),

        ("seccion", "If something does not work"),
        ("parrafo", "If an error message appears, pass it to the agent as is. The detail of ALL "
                    "the errors of the session is saved, and the \u201cView errors\u201d button in "
                    "this window tells you where."),
    ],
}

# Textos de la ventana y del pie del .txt. Igual que el contenido: bilingue y en
# este mismo modulo, para que el instructivo entero se mantenga en un solo lugar.
CHROME = {
    "titulo_ventana": {"es": "Como usar el Lector PDF", "en": "How to use Lector PDF"},
    "ver_errores": {"es": "Ver errores de esta sesion", "en": "View this session's errors"},
    "cerrar": {"es": "Cerrar", "en": "Close"},
    "errores_titulo": {"es": "Errores de esta sesion", "en": "This session's errors"},
    "no_leer_registro": {"es": "No se pudo leer el registro: %s",
                         "en": "Could not read the log: %s"},
    "sin_errores": {"es": "No hubo ningun error en esta sesion.\n\n"
                          "Cuando haya alguno, queda anotado en:\n%s",
                    "en": "There were no errors in this session.\n\n"
                          "When there is one, it will be logged in:\n%s"},
    "pie_1": {"es": "El programa vive en C:\\Program Files\\Mios\\LectorPDF.",
              "en": "The program lives in C:\\Program Files\\Mios\\LectorPDF."},
    "pie_2": {"es": "Los errores quedan anotados en la carpeta LectorPDF de tus datos locales.",
              "en": "The errors are logged in the LectorPDF folder of your local data."},
    "pie_3": {"es": "Este mismo instructivo esta en el boton \u201c?\u201d del programa.",
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
            prefijo = "  %-26s " % tecla
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
        self.txt.tag_configure("que", lmargin1=0, lmargin2=196, spacing3=6)

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
                t.insert("end", "%-24s" % tecla, "tecla")
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
