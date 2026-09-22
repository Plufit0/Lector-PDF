# -*- coding: utf-8 -*-
"""
ayuda.py — la ayuda del programa (boton "?" y F1), en un solo lugar.

De aca salen las dos versiones: la ventana de ayuda y el archivo de texto
"como_usar.txt" que queda junto al programa. Estan escritas una sola
vez a proposito: si la ayuda viviera suelta en un .txt, cada cambio del programa
la dejaria desactualizada sin que nadie se entere.

COMO ESTA ARMADA (decision del Disenador, sept-2026, siguiendo a NN/g y a
Microsoft: ayuda corta, pensada en tareas, con pasos concretos y una sola lista
de atajos):
  - "Como se usa": cinco pasos, uno por tarea. No explica como abrir el
    programa (ya esta abierto), no supone donde esta el icono ni en que carpeta
    estan los PDFs.
  - "Atajos": todas las teclas y gestos del mouse, agrupados, para buscar de un
    vistazo. Las teclas se dibujan como teclas.
Antes era un texto larguisimo de catorce secciones que arrancaba explicando
como abrir el programa.

POR QUE EL TEXTO VIVE ACA Y NO EN idiomas.py: el resto del programa saca sus
carteles cortos de idiomas.py. La ayuda es la excepcion a proposito: es un texto
ESTRUCTURADO (pasos, grupos de atajos), no un punado de cadenas sueltas. Las dos
versiones (es / en) viven aca, y este modulo solo le pregunta a idiomas.py cual
idioma mostrar.
"""

import tkinter as tk
from tkinter import ttk

import idiomas

# El nombre del programa es marca: no se traduce.
TITULO = "Lector PDF"

BAJADA = {
    "es": "Marcá cualquier PDF con dibujos y notas, y pasáselo a un agente.",
    "en": "Mark up any PDF with drawings and notes, and hand it to an agent.",
}

# Cinco pasos: (titulo, texto).
PASOS = {
    "es": [
        ("Abrí un PDF",
         "Doble clic en la lista. “Cambiar carpeta…” muestra otra carpeta y "
         "queda recordada para la próxima vez; “Abrir archivo…” abre un PDF "
         "de cualquier lado."),
        ("Marcá encima",
         "Dibujar (D) para trazar a mano. Texto (T) para escribir una nota: clic donde "
         "la querés, o arrastrá para elegir su tamaño."),
        ("Acomodá lo marcado",
         "Con Seleccionar (S), arrastrá una marca para moverla. En una nota elegida, "
         "las manijas cambian el tamaño del recuadro y el panel de la derecha, el "
         "tamaño de letra. Clic derecho y arrastrar elige varias marcas a la vez."),
        ("Señalá la frase exacta",
         "Arrastrá sobre el texto del PDF y tocá “Comentar esta frase”: la nota "
         "que escribas queda atada a esa frase, y el agente sabe a qué te referís."),
        ("Guardá y pegá en el chat",
         "Guardar (Ctrl+S) crea una copia del PDF con tus marcas; el original no se "
         "toca. Tocá Copiar y pegá el mensaje en el chat junto con el PDF (también "
         "está en la flechita de Guardar: Copiar prompt)."),
    ],
    "en": [
        ("Open a PDF",
         "Double-click it in the list. “Change folder…” shows another folder "
         "and remembers it for next time; “Open file…” opens a PDF from "
         "anywhere."),
        ("Mark it up",
         "Draw (D) to draw freehand. Text (T) to write a note: click where you want "
         "it, or drag to choose its size."),
        ("Arrange your marks",
         "With Select (S), drag a mark to move it. On a selected note, the handles "
         "change the size of the box and the right panel, the text size. Right-click "
         "and drag selects several marks at once."),
        ("Point at the exact sentence",
         "Drag over the PDF text and press “Comment on this sentence”: the note "
         "you write is tied to that sentence, and the agent knows what you mean."),
        ("Save and paste it in the chat",
         "Save (Ctrl+S) creates a copy of the PDF with your marks; the original is "
         "never touched. Press Copy and paste the message in the chat along with the "
         "PDF (it is also in the Save arrow: Copy prompt)."),
    ],
}

# Atajos por grupo: (grupo, [(teclas, que hace), ...]). "teclas" es una lista
# de alternativas; cada alternativa, una lista de teclas que se aprietan juntas.
_ES = [
    ("Herramientas", [
        ([["S"]], "Seleccionar: elegir, mover y editar marcas; en un lugar vacío, "
                  "elegir texto del PDF"),
        ([["D"]], "Dibujar a mano alzada (queda puesta para varios trazos)"),
        ([["T"]], "Texto: escribir una nota (después vuelve sola a Seleccionar)"),
        ([["B"]], "Borrar: clic en una marca, o arrastrar por encima de varias"),
    ]),
    ("Elegir y editar", [
        ([["Clic derecho", "arrastrar"]], "Recuadro para elegir varias marcas"),
        ([["Shift", "clic"], ["Ctrl", "clic"]], "Sumar o sacar una marca de la selección"),
        ([["Ctrl", "A"]], "Elegir todas las marcas de la página"),
        ([["Doble clic"], ["Enter"]], "Editar la nota elegida"),
        ([["Flechas"]], "Mover lo elegido (con Shift, de a 10)"),
        ([["Supr"]], "Borrar lo elegido"),
        ([["Ctrl", "C"]], "Copiar las marcas elegidas (o el texto del PDF elegido)"),
        ([["Ctrl", "X"]], "Cortar las marcas elegidas"),
        ([["Ctrl", "V"]], "Pegar las marcas copiadas"),
        ([["Ctrl", "Z"], ["Ctrl", "Y"]], "Deshacer y rehacer"),
        ([["Esc"]], "Soltar lo elegido o cancelar lo que estabas haciendo"),
        ([["Clic derecho"]], "Menú con lo que se puede hacer ahí"),
    ]),
    ("Ver y moverse", [
        ([["Rueda"]], "Leer; al final de la hoja pasa de página"),
        ([["Ruedita apretada"]], "Arrastrar la hoja con la mano"),
        ([["Ctrl", "rueda"]], "Acercar o alejar hacia el mouse"),
        ([["Shift", "rueda"]], "Moverse de costado"),
        ([["Ctrl", "0"]], "Ver la hoja entera"),
        ([["Ctrl", "1"]], "Tamaño real"),
        ([["Ctrl", "2"]], "Ancho de la ventana"),
        ([["Ctrl", "+"], ["Ctrl", "−"]], "Acercar y alejar"),
        ([["Av Pág"], ["Re Pág"]], "Página siguiente y anterior"),
        ([["Ctrl", "Inicio"], ["Ctrl", "Fin"]], "Primera y última página"),
        ([["Ctrl", "F"]], "Buscar (Enter o F3: el siguiente)"),
    ]),
    ("Archivo", [
        ([["Ctrl", "O"]], "Abrir un PDF de cualquier carpeta"),
        ([["Ctrl", "S"]], "Guardar (la primera vez pregunta el nombre)"),
        ([["Ctrl", "Shift", "S"]], "Guardar como…"),
        ([["Ctrl", "W"]], "Volver a la lista de PDFs"),
        ([["F5"]], "Actualizar la lista de PDFs"),
        ([["F1"]], "Esta ayuda"),
    ]),
]

_EN = [
    ("Tools", [
        ([["S"]], "Select: pick, move and edit marks; on an empty area, select PDF text"),
        ([["D"]], "Draw freehand (stays on for several strokes)"),
        ([["T"]], "Text: write a note (then goes back to Select by itself)"),
        ([["E"]], "Erase: click a mark, or drag over several"),
    ]),
    ("Select and edit", [
        ([["Right-click", "drag"]], "Box to select several marks"),
        ([["Shift", "click"], ["Ctrl", "click"]], "Add or remove a mark from the selection"),
        ([["Ctrl", "A"]], "Select all the marks on the page"),
        ([["Double-click"], ["Enter"]], "Edit the selected note"),
        ([["Arrows"]], "Move what is selected (with Shift, by 10)"),
        ([["Del"]], "Delete what is selected"),
        ([["Ctrl", "C"]], "Copy the selected marks (or the selected PDF text)"),
        ([["Ctrl", "X"]], "Cut the selected marks"),
        ([["Ctrl", "V"]], "Paste the copied marks"),
        ([["Ctrl", "Z"], ["Ctrl", "Y"]], "Undo and redo"),
        ([["Esc"]], "Clear the selection or cancel what you were doing"),
        ([["Right-click"]], "Menu with what you can do there"),
    ]),
    ("View and move around", [
        ([["Wheel"]], "Read; at the bottom of the sheet it goes to the next page"),
        ([["Pressed wheel"]], "Drag the sheet by hand"),
        ([["Ctrl", "wheel"]], "Zoom in or out toward the mouse"),
        ([["Shift", "wheel"]], "Move sideways"),
        ([["Ctrl", "0"]], "Fit the whole page"),
        ([["Ctrl", "1"]], "Actual size"),
        ([["Ctrl", "2"]], "Fit to window width"),
        ([["Ctrl", "+"], ["Ctrl", "−"]], "Zoom in and out"),
        ([["PgDn"], ["PgUp"]], "Next and previous page"),
        ([["Ctrl", "Home"], ["Ctrl", "End"]], "First and last page"),
        ([["Ctrl", "F"]], "Find (Enter or F3: the next one)"),
    ]),
    ("File", [
        ([["Ctrl", "O"]], "Open a PDF from any folder"),
        ([["Ctrl", "S"]], "Save (the first time it asks for the name)"),
        ([["Ctrl", "Shift", "S"]], "Save as…"),
        ([["Ctrl", "W"]], "Back to the list of PDFs"),
        ([["F5"]], "Refresh the list of PDFs"),
        ([["F1"]], "This help"),
    ]),
]

ATAJOS = {"es": _ES, "en": _EN}

# Textos de la ventana y del pie del .txt. Igual que el contenido: bilingue y en
# este mismo modulo, para que la ayuda entera se mantenga en un solo lugar.
CHROME = {
    "titulo_ventana": {"es": "Ayuda del Lector PDF", "en": "Lector PDF help"},
    "pestana_pasos": {"es": "Cómo se usa", "en": "How to use it"},
    "pestana_atajos": {"es": "Atajos", "en": "Shortcuts"},
    "consejo": {"es": "Pasá el mouse sobre cualquier botón para ver qué hace y su atajo.",
                "en": "Hover over any button to see what it does and its shortcut."},
    "ver_errores": {"es": "Ver errores de esta sesión", "en": "View this session's errors"},
    "cerrar": {"es": "Cerrar", "en": "Close"},
    "errores_titulo": {"es": "Errores de esta sesión", "en": "This session's errors"},
    "no_leer_registro": {"es": "No se pudo leer el registro: %s",
                         "en": "Could not read the log: %s"},
    "sin_errores": {"es": "No hubo ningún error en esta sesión.\n\n"
                          "Cuando haya alguno, queda anotado en:\n%s",
                    "en": "There were no errors in this session.\n\n"
                          "When there is one, it will be logged in:\n%s"},
    "pie_errores": {"es": "Si aparece un cartel de error, pasáselo al agente tal cual: el "
                          "detalle queda anotado en la carpeta LectorPDF de tus datos locales.",
                    "en": "If an error message appears, pass it to the agent as is: the "
                          "details are logged in the LectorPDF folder of your local data."},
    "pie_boton": {"es": "Esta misma ayuda está en el botón “?” del programa (F1).",
                  "en": "This same help is in the program's “?” button (F1)."},
}


def _idioma():
    try:
        codigo = idiomas.idioma_actual()
    except Exception:
        codigo = "es"
    return codigo if codigo in ("es", "en") else "es"


def _chrome(clave, idioma):
    entrada = CHROME.get(clave, {})
    return entrada.get(idioma) or entrada.get("es", clave)


def teclas_como_texto(teclas):
    """[["Ctrl", "Z"], ["Ctrl", "Y"]] -> "Ctrl+Z / Ctrl+Y"."""
    return " / ".join("+".join(combo) for combo in teclas)


# ------------------------------------------------------------------ texto ----

def como_texto(idioma=None):
    """La ayuda en texto plano (el como_usar.txt del escritorio).

    Se le puede pasar el idioma ("es" / "en"); por defecto usa el del programa.
    """
    import textwrap
    idioma = idioma if idioma in ("es", "en") else _idioma()
    lineas = [TITULO.upper(), "=" * len(TITULO), "", BAJADA[idioma], ""]
    titulo = _chrome("pestana_pasos", idioma)
    lineas += ["", titulo, "-" * len(titulo)]
    for n, (tit, texto) in enumerate(PASOS[idioma], 1):
        lineas.append(textwrap.fill("%d. %s. %s" % (n, tit, texto), 78,
                                    subsequent_indent="   "))
    lineas += ["", textwrap.fill(_chrome("consejo", idioma), 78)]
    titulo = _chrome("pestana_atajos", idioma)
    lineas += ["", "", titulo, "-" * len(titulo)]
    for grupo, filas in ATAJOS[idioma]:
        lineas += ["", grupo.upper()]
        for teclas, que in filas:
            # La sangria de continuacion es del ancho del prefijo entero, o las
            # lineas siguientes quedan escalonadas y no se lee.
            prefijo = "  %-26s " % teclas_como_texto(teclas)
            lineas.append(textwrap.fill(que, 78, initial_indent=prefijo,
                                        subsequent_indent=" " * len(prefijo)))
    lineas += ["", "", textwrap.fill(_chrome("pie_errores", idioma), 78),
               _chrome("pie_boton", idioma)]
    return "\n".join(lineas)


# ---------------------------------------------------------------- ventana ----

FONDO = "#FFFFFF"
TINTA = "#1F2328"
AZUL = "#1B5E9E"
GRIS = "#5B6472"
TECLA_FONDO = "#F1F3F5"
TECLA_BORDE = "#C4CAD1"


class Ventana(tk.Toplevel):
    """La ayuda para leer en pantalla: dos pestanas, pasos y atajos."""

    def __init__(self, padre, ruta_errores=None):
        super().__init__(padre)
        self.idioma = _idioma()
        self.title(_chrome("titulo_ventana", self.idioma))
        self.geometry("880x640")
        self.minsize(620, 440)
        self.transient(padre)
        self.configure(bg=FONDO)

        cabecera = tk.Frame(self, bg=AZUL)
        cabecera.pack(fill="x")
        tk.Label(cabecera, text=TITULO, bg=AZUL, fg="white",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(12, 0))
        tk.Label(cabecera, text=BAJADA[self.idioma], bg=AZUL, fg="#D7E6F5",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(0, 12))

        pie = tk.Frame(self, bg="#F3F4F6")
        pie.pack(side="bottom", fill="x")
        if ruta_errores:
            ttk.Button(pie, text=_chrome("ver_errores", self.idioma),
                       command=lambda: self._mostrar_errores(ruta_errores)).pack(
                           side="left", padx=12, pady=10)
        ttk.Button(pie, text=_chrome("cerrar", self.idioma),
                   command=self.destroy).pack(side="right", padx=12, pady=10)

        pestanas = ttk.Notebook(self)
        pestanas.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        pestanas.add(self._armar_pasos(pestanas), text="  %s  " % _chrome("pestana_pasos", self.idioma))
        pestanas.add(self._armar_atajos(pestanas), text="  %s  " % _chrome("pestana_atajos", self.idioma))
        self.pestanas = pestanas

        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

    # --- pestana 1: como se usa ---------------------------------------------

    def _armar_pasos(self, padre):
        marco = tk.Frame(padre, bg=FONDO)
        for n, (titulo, texto) in enumerate(PASOS[self.idioma], 1):
            fila = tk.Frame(marco, bg=FONDO)
            fila.pack(fill="x", padx=18, pady=(14 if n == 1 else 8, 0))
            tk.Label(fila, text=str(n), bg=AZUL, fg="white", width=2,
                     font=("Segoe UI", 12, "bold")).pack(side="left", anchor="n", padx=(0, 12))
            col = tk.Frame(fila, bg=FONDO)
            col.pack(side="left", fill="x", expand=True)
            tk.Label(col, text=titulo, bg=FONDO, fg=TINTA, anchor="w",
                     font=("Segoe UI", 11, "bold")).pack(fill="x")
            cuerpo = tk.Label(col, text=texto, bg=FONDO, fg=TINTA, anchor="w",
                              justify="left", font=("Segoe UI", 10))
            cuerpo.pack(fill="x")
            # El texto se acomoda al ancho de la ventana.
            col.bind("<Configure>", lambda e, c=cuerpo: c.config(wraplength=max(200, e.width - 4)))
        tk.Label(marco, text=_chrome("consejo", self.idioma), bg=FONDO, fg=GRIS,
                 anchor="w", font=("Segoe UI", 9, "italic")).pack(fill="x", padx=18, pady=(18, 8))
        return marco

    # --- pestana 2: atajos -----------------------------------------------------

    def _armar_atajos(self, padre):
        """Los grupos de atajos en dos columnas, con desplazamiento si no entran."""
        exterior = tk.Frame(padre, bg=FONDO)
        lienzo = tk.Canvas(exterior, bg=FONDO, highlightthickness=0)
        barra = ttk.Scrollbar(exterior, orient="vertical", command=lienzo.yview)
        lienzo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        lienzo.pack(side="left", fill="both", expand=True)
        interior = tk.Frame(lienzo, bg=FONDO)
        ventana = lienzo.create_window(0, 0, anchor="nw", window=interior)
        interior.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana, width=e.width))

        def rueda(e):
            lienzo.yview_scroll(-1 if e.delta > 0 else 1, "units")
            return "break"
        self.bind("<MouseWheel>", rueda)

        grupos = ATAJOS[self.idioma]
        mitad = (len(grupos) + 1) // 2
        interior.columnconfigure(0, weight=1, uniform="col")
        interior.columnconfigure(1, weight=1, uniform="col")
        for c, lote in enumerate((grupos[:mitad], grupos[mitad:])):
            col = tk.Frame(interior, bg=FONDO)
            col.grid(row=0, column=c, sticky="nwe", padx=(18, 10) if c == 0 else (10, 18), pady=8)
            # Tabla de dos columnas: las teclas a la izquierda, que hacen a la
            # derecha, en el mismo renglon (como la lista de atajos de Google
            # Docs): se busca la accion o la tecla de un vistazo.
            col.columnconfigure(0, minsize=170)
            col.columnconfigure(1, weight=1)
            filas_hechas = []
            fila = 0
            for grupo, filas in lote:
                tk.Label(col, text=grupo, bg=FONDO, fg=AZUL, anchor="w",
                         font=("Segoe UI", 11, "bold")).grid(
                             row=fila, column=0, columnspan=2, sticky="w", pady=(12, 4))
                fila += 1
                for teclas, que in filas:
                    filas_hechas.append(self._fila_atajo(col, fila, teclas, que))
                    fila += 1

            def acomodar(e, hechas=filas_hechas):
                # El texto usa lo que dejan las teclas mas anchas de la columna.
                teclas_max = max(max(f.winfo_reqwidth() for f, _t in hechas), 170)
                for _f, texto in hechas:
                    texto.config(wraplength=max(120, e.width - teclas_max - 16))
            col.bind("<Configure>", acomodar)
        return exterior

    def _fila_atajo(self, padre, fila, teclas, que):
        teclas_f = tk.Frame(padre, bg=FONDO)
        teclas_f.grid(row=fila, column=0, sticky="nw", pady=3)
        for k, combo in enumerate(teclas):
            if k:
                tk.Label(teclas_f, text="/", bg=FONDO, fg=GRIS,
                         font=("Segoe UI", 9)).pack(side="left", padx=3)
            for j, tecla in enumerate(combo):
                if j:
                    tk.Label(teclas_f, text="+", bg=FONDO, fg=GRIS,
                             font=("Segoe UI", 9)).pack(side="left", padx=1)
                # Cada tecla dibujada como una tecla: fondo claro y borde.
                tk.Label(teclas_f, text=tecla, bg=TECLA_FONDO, fg=TINTA,
                         font=("Segoe UI Semibold", 9), padx=6, pady=0,
                         highlightthickness=1, highlightbackground=TECLA_BORDE,
                         bd=0).pack(side="left")
        texto = tk.Label(padre, text=que, bg=FONDO, fg=TINTA, anchor="w", justify="left",
                         font=("Segoe UI", 9))
        texto.grid(row=fila, column=1, sticky="w", padx=(10, 0), pady=3)
        return teclas_f, texto

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
