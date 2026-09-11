# -*- coding: utf-8 -*-
"""
Lector PDF — leer un manual de diseno y marcarlo encima, sin cambiar de modo.

Flujo para el que fue hecho (no desviarse de esto sin pedirlo):
  acceso directo en el escritorio -> abre mostrando los PDFs de Descargas ->
  se abre uno -> se lee y se marca intercalando -> Guardar -> la ruta queda en
  el portapapeles para pegarla en el chat.

DECISIONES DE DISENO (leer antes de cambiar nada):

1. EL MODO POR DEFECTO ES "DIBUJAR", Y LA RUEDA SIEMPRE HACE SCROLL.
   Esa es la decision central del programa: leer y marcar son la misma postura,
   no dos modos entre los que hay que alternar. Arrastrar dibuja, la rueda lee,
   y nunca hay que tocar un boton para pasar de una cosa a la otra. Si alguna
   vez se agrega una herramienta, la rueda tiene que seguir leyendo.

2. Al terminar de escribir una nota, el programa vuelve solo a "Dibujar".
   Misma razon: el estado en reposo siempre es el mismo.

3. Las coordenadas de las marcas viven en puntos PDF, no en pixeles. El zoom
   solo cambia como se ve. Una marca hecha al 80% cae donde debe al 150%.

4. La pagina se renderiza SIN las marcas propias (ver anotaciones.abrir_para_editar):
   el visor las dibuja desde su lista. Si vinieran tambien en la imagen, se
   verian dobles y borrar una dejaria la de abajo.

5. Al guardar se parte siempre del PDF original en disco, no de lo que hay en
   memoria. Guardar dos veces no acumula capas ni agranda el archivo.

6. Si una marca no se puede escribir, el programa lo dice con nombre y pagina.
   Nunca se guarda en silencio una devolucion incompleta.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Las librerias que pueden faltar se importan aparte: si alguna no esta, el
# programa tiene que poder DECIRLO por pantalla. Sin esto, el doble clic en el
# escritorio no haria absolutamente nada y no habria forma de saber por que.
_ERROR_IMPORT = None
try:
    import pymupdf
    from PIL import Image, ImageTk

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import anotaciones as A
    import errores
    import ayuda
except Exception as _e:      # noqa: BLE001 - se reporta abajo, en main()
    _ERROR_IMPORT = _e

# Nitidez en pantallas con escalado de Windows. Sin esto el texto del PDF se ve
# borroso y el programa no sirve para leer, que es la mitad de su trabajo.
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def _carpeta_descargas():
    """La carpeta de Descargas real de este usuario.

    Se pregunta a Windows en vez de asumir "~/Downloads", porque puede estar
    redirigida (a OneDrive, a otro disco) y entonces el programa abriria una
    carpeta vacia y David no encontraria el manual que acaba de bajar.
    """
    try:
        import ctypes
        import ctypes.wintypes
        FOLDERID_Downloads = "{374DE290-123F-4565-9164-39C4925E467B}"
        buf = ctypes.c_wchar_p()
        guid = ctypes.create_string_buffer(16)
        if ctypes.windll.ole32.CLSIDFromString(FOLDERID_Downloads, guid) == 0:
            if ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None,
                                                          ctypes.byref(buf)) == 0:
                ruta = buf.value
                ctypes.windll.ole32.CoTaskMemFree(buf)
                if ruta and os.path.isdir(ruta):
                    return ruta
    except Exception:
        pass
    candidata = os.path.join(os.path.expanduser("~"), "Downloads")
    return candidata if os.path.isdir(candidata) else os.path.expanduser("~")


CARPETA_INICIAL = _carpeta_descargas()

COLORES = [
    ("Rojo",     (0.88, 0.19, 0.19)),
    ("Naranja",  (0.96, 0.41, 0.03)),
    ("Verde",    (0.18, 0.62, 0.27)),
    ("Azul",     (0.10, 0.44, 0.76)),
    ("Negro",    (0.13, 0.15, 0.16)),
]
GROSOR_FINO = 2.0
GROSOR_GRUESO = 6.0

FONDO_CANVAS = "#6E7378"
FONDO_BARRA = "#ECEDEE"
# Ancho del panel de propiedades. Va superpuesto sobre la hoja, no al costado.
ANCHO_PANEL = 258


def mezclar(color, alfa, fondo=(1.0, 1.0, 1.0)):
    """Simula transparencia mezclando con el fondo.

    El canvas de Tkinter no tiene opacidad: la unica forma de que una linea se
    vea tenue es calcular de antemano el color que daria esa transparencia.
    """
    return tuple(c * alfa + f * (1.0 - alfa) for c, f in zip(color, fondo))


def a_hex(color):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c * 255)))) for c in color)


def tamano_legible(bytes_):
    for unidad in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024 or unidad == "GB":
            return ("%.0f %s" % (bytes_, unidad)) if unidad == "B" else ("%.1f %s" % (bytes_, unidad))
        bytes_ /= 1024.0


def ruta_libre(carpeta, base):
    """Devuelve una ruta que no existe, numerando: -devolucion, -devolucion-2, ...

    Numerado, nunca "final" ni "corregido": la version mas alta es la ultima.
    """
    cand = os.path.join(carpeta, base + "-devolucion.pdf")
    n = 2
    while os.path.exists(cand):
        cand = os.path.join(carpeta, "%s-devolucion-%d.pdf" % (base, n))
        n += 1
    return cand


# =============================================================== biblioteca ==

class Biblioteca(ttk.Frame):
    """Pantalla inicial: los PDFs de una carpeta, el mas nuevo primero."""

    def __init__(self, app):
        super().__init__(app.contenedor)
        self.app = app
        self.carpeta = CARPETA_INICIAL
        self.archivos = []

        barra = ttk.Frame(self, padding=(12, 10))
        barra.pack(fill="x")
        self.lbl = ttk.Label(barra, text="", font=("Segoe UI", 14, "bold"))
        self.lbl.pack(side="left")
        ttk.Button(barra, text="Otra carpeta...", command=self.elegir_carpeta).pack(side="right")
        ttk.Button(barra, text="Actualizar", command=self.refrescar).pack(side="right", padx=6)

        cuerpo = ttk.Frame(self, padding=(12, 0, 12, 8))
        cuerpo.pack(fill="both", expand=True)
        cols = ("nombre", "fecha", "tamano")
        self.tabla = ttk.Treeview(cuerpo, columns=cols, show="headings", selectmode="browse")
        self.tabla.heading("nombre", text="Archivo")
        self.tabla.heading("fecha", text="Modificado")
        self.tabla.heading("tamano", text="Tamano")
        self.tabla.column("nombre", width=620, anchor="w")
        self.tabla.column("fecha", width=170, anchor="w")
        self.tabla.column("tamano", width=110, anchor="e")
        sb = ttk.Scrollbar(cuerpo, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tabla.bind("<Double-1>", lambda e: self.abrir_seleccion())
        self.tabla.bind("<Return>", lambda e: self.abrir_seleccion())

        pie = ttk.Frame(self, padding=(12, 0, 12, 12))
        pie.pack(fill="x")
        self.estado = ttk.Label(pie, text="", foreground="#555")
        self.estado.pack(side="left")
        ttk.Button(pie, text="Abrir", command=self.abrir_seleccion).pack(side="right")

        self.refrescar()

    def elegir_carpeta(self):
        c = filedialog.askdirectory(initialdir=self.carpeta, title="Elegir carpeta con PDFs")
        if c:
            self.carpeta = c
            self.refrescar()

    def refrescar(self):
        self.lbl.config(text="PDFs en %s" % os.path.basename(self.carpeta.rstrip("\\/")) or self.carpeta)
        for i in self.tabla.get_children():
            self.tabla.delete(i)
        self.archivos = []
        try:
            entradas = []
            with os.scandir(self.carpeta) as it:
                for e in it:
                    if e.is_file() and e.name.lower().endswith(".pdf"):
                        try:
                            st = e.stat()
                        except OSError:
                            continue
                        entradas.append((e.path, e.name, st.st_mtime, st.st_size))
            entradas.sort(key=lambda t: t[2], reverse=True)
        except OSError as err:
            self.estado.config(text="No se pudo leer la carpeta: %s" % err)
            return

        import datetime
        for ruta, nombre, mtime, size in entradas:
            fecha = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
            self.tabla.insert("", "end", values=(nombre, fecha, tamano_legible(size)))
            self.archivos.append(ruta)

        if self.archivos:
            primero = self.tabla.get_children()[0]
            self.tabla.selection_set(primero)
            self.tabla.focus(primero)
            self.tabla.focus_set()
            self.estado.config(text="%d PDF(s). Doble clic o Enter para abrir." % len(self.archivos))
        else:
            self.estado.config(text="No hay PDFs en esta carpeta.")

    def abrir_seleccion(self):
        sel = self.tabla.selection()
        if not sel:
            return
        idx = self.tabla.index(sel[0])
        if 0 <= idx < len(self.archivos):
            self.app.abrir_pdf(self.archivos[idx])


# ==================================================================== visor ==

class Visor(ttk.Frame):
    """Pantalla de lectura y marcado."""

    def __init__(self, app, ruta):
        super().__init__(app.contenedor)
        self.app = app
        self.ruta = ruta
        self.doc, self.marcas = A.abrir_para_editar(ruta)
        if self.doc.page_count < 1:
            self.doc.close()
            raise ValueError("El PDF no tiene ninguna pagina: puede estar danado.")
        self.pno = 0
        self.zoom = 1.0
        # Por defecto se ve la hoja ENTERA, no ajustada al ancho: en un monitor
        # ancho, "ajustar al ancho" agranda tanto la pagina que cada una ocupa
        # dos pantallas y media de scroll. Para revisar un manual de 14 paginas
        # conviene ver la hoja completa y pasar de pagina; el que quiera leer
        # letra grande tiene el boton "Ancho".
        self.modo_zoom = "pagina"          # "pagina" | "ancho" | "libre"
        self.ox = 0                 # corrimiento horizontal para centrar la hoja
        self.modo = "dibujar"
        self.color = COLORES[0][1]
        self.grosor = GROSOR_FINO
        # --- modo seleccionar -------------------------------------------
        self.seleccion = []        # indices de marcas elegidas en la pagina actual
        self.palabras_sel = []     # recuadros de texto del PDF seleccionado
        self._texto_sel = ""       # ese texto, listo para copiar
        self._arrastrando = None   # datos del movimiento en curso
        self._marco_sel = None     # rectangulo de seleccion por area
        self.ancla_pendiente = None  # frase a la que se va a atar lo proximo
        self.refiriendo = []         # marcas esperando que se elija su referencia
        self.rehacer_pila = []     # lo deshecho, para Ctrl+Y
        self.tkimg = None
        self.historial = []         # para deshacer
        self._trazo = None
        self._tmp = []
        self._editor = None
        self._editor_win = None
        self._editor_xy = None
        self._pan = None
        # Estado con el que quedo el archivo en disco: todo lo que difiera
        # de esto es un cambio sin guardar.
        self.firma_guardada = self._firma()

        self._armar_barra()

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        self.cuerpo = cuerpo
        # El panel de propiedades se arma ahora pero no se muestra: aparece solo
        # cuando hay algo seleccionado, para no comerle ancho a la hoja.
        self.panel = self._armar_panel(cuerpo)
        self.canvas = tk.Canvas(cuerpo, bg=FONDO_CANVAS, highlightthickness=0, cursor="pencil")
        self.vsb = ttk.Scrollbar(cuerpo, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.pie = ttk.Label(self, text="", padding=(10, 4), foreground="#333")
        self.pie.pack(fill="x")

        self.canvas.bind("<Configure>", self._al_redimensionar)
        self.canvas.bind("<ButtonPress-1>", self._click)
        self.canvas.bind("<B1-Motion>", self._arrastre)
        self.canvas.bind("<ButtonRelease-1>", self._soltar)
        self.canvas.bind("<Double-Button-1>", self._doble_click)
        self.canvas.bind("<MouseWheel>", self._rueda)
        self.canvas.bind("<Shift-MouseWheel>", self._rueda_horizontal)
        self.canvas.bind("<ButtonPress-2>", self._pan_inicio)
        self.canvas.bind("<B2-Motion>", self._pan_mover)
        self.canvas.bind("<ButtonRelease-2>", lambda e: setattr(self, "_pan", None))
        self.canvas.focus_set()

        self._actualizar_pie()

    # ------------------------------------------------------------- barra ----

    def _armar_barra(self):
        b = ttk.Frame(self, padding=(8, 6))
        b.pack(fill="x")

        ttk.Button(b, text="< Carpeta", width=10, command=self.app.volver_biblioteca).pack(side="left")
        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)

        self.btn_modo = {}
        for clave, etiqueta in (("dibujar", "Dibujar"), ("texto", "Texto"),
                                ("seleccionar", "Seleccionar"), ("borrar", "Borrar")):
            bt = tk.Button(b, text=etiqueta, width=11 if clave == "seleccionar" else 8,
                           relief="raised", command=lambda c=clave: self.set_modo(c))
            bt.pack(side="left", padx=2)
            self.btn_modo[clave] = bt

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        self.btn_color = []
        for nombre, col in COLORES:
            bt = tk.Button(b, width=3, bg=a_hex(col), activebackground=a_hex(col),
                           relief="raised", bd=2, command=lambda c=col: self.set_color(c))
            bt.pack(side="left", padx=1)
            self.btn_color.append((bt, col))

        self.btn_grosor = tk.Button(b, text="Grueso", width=7, command=self.toggle_grosor)
        self.btn_grosor.pack(side="left", padx=(8, 2))
        ttk.Button(b, text="Deshacer", width=9, command=self.deshacer).pack(side="left", padx=2)
        ttk.Button(b, text="Rehacer", width=9, command=self.rehacer).pack(side="left")

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(b, text="-", width=3, command=lambda: self.set_zoom(self.zoom / 1.2)).pack(side="left")
        self.btn_pagina = tk.Button(b, text="Pagina", width=7, command=self.zoom_pagina)
        self.btn_pagina.pack(side="left", padx=2)
        self.btn_ancho = tk.Button(b, text="Ancho", width=7, command=self.zoom_ancho)
        self.btn_ancho.pack(side="left")
        ttk.Button(b, text="+", width=3, command=lambda: self.set_zoom(self.zoom * 1.2)).pack(side="left", padx=2)

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(b, text="<", width=3, command=lambda: self.ir_pagina(self.pno - 1)).pack(side="left")
        # El numero de pagina se puede escribir: en un manual de 40 paginas,
        # llegar a la 27 a flechazos es una perdida de tiempo.
        self.entrada_pag = tk.Entry(b, width=4, justify="center", relief="flat",
                                    bg=FONDO_BARRA)
        self.entrada_pag.pack(side="left")
        self.entrada_pag.bind("<Return>", self._saltar_a_pagina)
        self.entrada_pag.bind("<FocusOut>", lambda e: self._actualizar_numero())
        self.lbl_total = ttk.Label(b, text="", width=6, anchor="w")
        self.lbl_total.pack(side="left")
        ttk.Button(b, text=">", width=3, command=lambda: self.ir_pagina(self.pno + 1)).pack(side="left")

        self.btn_guardar = tk.Button(b, text="Guardar", width=10, font=("Segoe UI", 9, "bold"),
                                     command=self.guardar)
        self.btn_guardar.pack(side="right")
        tk.Button(b, text="?", width=3, font=("Segoe UI", 10, "bold"),
                  command=self.mostrar_ayuda).pack(side="right", padx=6)

        self._pintar_botones()

    # ------------------------------------------------- panel de propiedades --

    def _armar_panel(self, padre):
        """Panel con lo que se puede hacer con lo que este elegido.

        Va superpuesto sobre la hoja (ver _mostrar_panel) y sin textos de ayuda
        al lado de cada boton: una vez que sabes lo que hace el boton, esos
        carteles son ruido.
        """
        p = tk.Frame(padre, bg="#F4F6F8", width=ANCHO_PANEL, bd=0,
                     highlightthickness=1, highlightbackground="#CDD3DA")
        p.pack_propagate(False)

        self.pnl_titulo = tk.Label(p, text="", bg="#F4F6F8", fg="#1F2328",
                                   font=("Segoe UI", 11, "bold"), anchor="w")
        self.pnl_titulo.pack(fill="x", padx=12, pady=(12, 2))
        self.pnl_datos = tk.Label(p, text="", bg="#F4F6F8", fg="#5B6472", anchor="w",
                                  justify="left", wraplength=230, font=("Segoe UI", 8))
        self.pnl_datos.pack(fill="x", padx=12, pady=(0, 10))

        # --- con texto del manual elegido -----------------------------------
        self.pnl_texto_pdf = tk.Frame(p, bg="#F4F6F8")
        tk.Button(self.pnl_texto_pdf, text="Comentar esta frase",
                  font=("Segoe UI", 9, "bold"),
                  command=self.comentar_seleccion).pack(fill="x", pady=(0, 3))
        tk.Button(self.pnl_texto_pdf, text="Dibujar sobre esta frase",
                  command=self.dibujar_sobre_seleccion).pack(fill="x")

        # --- nombre interno --------------------------------------------------
        self.pnl_nombre_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_nombre_bloque, text="NOMBRE INTERNO", bg="#F4F6F8",
                 fg="#7A828C", anchor="w",
                 font=("Segoe UI", 7, "bold")).pack(fill="x")
        fila_n = tk.Frame(self.pnl_nombre_bloque, bg="#F4F6F8")
        fila_n.pack(fill="x", pady=(1, 0))
        self.pnl_nombre = tk.Entry(fila_n, font=("Consolas", 9))
        self.pnl_nombre.pack(side="left", fill="x", expand=True)
        self.pnl_nombre.bind("<Return>", lambda e: self._renombrar())
        tk.Button(fila_n, text="OK", width=3,
                  command=self._renombrar).pack(side="left", padx=(4, 0))

        # --- referencia ------------------------------------------------------
        self.pnl_ref_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_ref_bloque, text="REFERENCIA A", bg="#F4F6F8", fg="#7A828C",
                 anchor="w", font=("Segoe UI", 7, "bold")).pack(fill="x")
        self.pnl_ref = tk.Entry(self.pnl_ref_bloque, font=("Segoe UI", 8),
                                state="readonly", readonlybackground="#ECEDEE")
        self.pnl_ref.pack(fill="x", pady=(1, 3))
        fila_r = tk.Frame(self.pnl_ref_bloque, bg="#F4F6F8")
        fila_r.pack(fill="x")
        self.btn_elegir_ref = tk.Button(fila_r, text="Elegir",
                                        command=self.elegir_referencia)
        self.btn_elegir_ref.pack(side="left", fill="x", expand=True)
        self.btn_quitar_ref = tk.Button(fila_r, text="Quitar",
                                        command=self.soltar_ancla)
        self.btn_quitar_ref.pack(side="left", fill="x", expand=True, padx=(3, 0))

        # --- color -----------------------------------------------------------
        self.pnl_color_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_color_bloque, text="COLOR", bg="#F4F6F8", fg="#7A828C",
                 anchor="w", font=("Segoe UI", 7, "bold")).pack(fill="x")
        fila_c = tk.Frame(self.pnl_color_bloque, bg="#F4F6F8")
        fila_c.pack(fill="x", pady=(2, 0))
        for _n, col in COLORES:
            tk.Button(fila_c, width=3, bg=a_hex(col), activebackground=a_hex(col),
                      relief="raised", bd=2,
                      command=lambda c=col: self._cambiar_color(c)).pack(side="left", padx=1)

        # --- grosor ----------------------------------------------------------
        self.pnl_grosor = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_grosor, text="GROSOR", bg="#F4F6F8", fg="#7A828C", anchor="w",
                 font=("Segoe UI", 7, "bold")).pack(fill="x")
        fila_g = tk.Frame(self.pnl_grosor, bg="#F4F6F8")
        fila_g.pack(fill="x", pady=(2, 0))
        for etiqueta, valor in (("Fino", GROSOR_FINO), ("Medio", 4.0),
                                ("Grueso", GROSOR_GRUESO)):
            tk.Button(fila_g, text=etiqueta, width=7,
                      command=lambda v=valor: self._cambiar_grosor(v)).pack(side="left", padx=1)

        # --- acciones ---------------------------------------------------------
        self.pnl_acciones = tk.Frame(p, bg="#F4F6F8")
        self.btn_editar_nota = tk.Button(self.pnl_acciones, text="Editar el texto",
                                         command=self._editar_nota_seleccionada)
        self.btn_unificar = tk.Button(self.pnl_acciones, text="Unificar en un solo dibujo",
                                      command=self._unificar)
        self.btn_borrar = tk.Button(self.pnl_acciones, text="Borrar",
                                    command=self._borrar_seleccion)
        self.btn_soltar = tk.Button(self.pnl_acciones, text="Soltar la seleccion",
                                    command=self._soltar_todo)
        return p

    def _soltar_todo(self):
        self._limpiar_seleccion()
        self.render(self.canvas.yview()[0])

    def _mostrar_panel(self, visible):
        """Muestra u oculta el panel SIN mover la hoja.

        Va superpuesto (place) y no empaquetado: si le quitara ancho al canvas,
        el zoom se recalcularia y la hoja saltaria de lugar cada vez que se
        elige algo, que es justo cuando uno esta mirando un punto concreto.
        """
        if visible and not self.panel.winfo_ismapped():
            self.panel.place(relx=1.0, y=0, anchor="ne", relheight=1.0, width=ANCHO_PANEL)
            self.panel.lift()
        elif not visible and self.panel.winfo_ismapped():
            self.panel.place_forget()

    def _texto_referencia(self, mk):
        """Lo que muestra el cuadro "Referencia a" para esa marca."""
        ancla = mk.get("ancla")
        if ancla and ancla.get("cita"):
            return "la frase: " + ancla["cita"][:70]
        if mk.get("ref"):
            return "la marca: " + mk["ref"]
        return ""

    def _refrescar_panel(self):
        """Vuelca en el panel lo que hay elegido ahora mismo."""
        for w in (self.pnl_texto_pdf, self.pnl_nombre_bloque, self.pnl_ref_bloque,
                  self.pnl_color_bloque, self.pnl_grosor, self.pnl_acciones):
            w.pack_forget()
        for b in (self.btn_editar_nota, self.btn_unificar, self.btn_borrar, self.btn_soltar):
            b.pack_forget()

        marcas = self._marcas_seleccionadas()
        if not marcas and not self._texto_sel:
            self._mostrar_panel(False)
            return
        self._mostrar_panel(True)

        # --- texto del manual elegido: todavia no es una marca ---------------
        if not marcas:
            self.pnl_titulo.config(text="Texto del manual")
            self.pnl_datos.config(text=u"%d caracteres\n\u201c%s\u201d"
                                  % (len(self._texto_sel), self._texto_sel[:150]))
            self.pnl_texto_pdf.pack(fill="x", padx=12, pady=(2, 0))
            return

        # --- una o varias marcas ---------------------------------------------
        uno = marcas[0] if len(marcas) == 1 else None
        if uno is not None:
            r = self._bbox(uno)
            if uno["tipo"] == "lapiz":
                self.pnl_titulo.config(text="Dibujo a mano")
                self.pnl_datos.config(
                    text=u"Pagina %d  \u00b7  %d trazo(s), %d puntos  \u00b7  %.0f \u00d7 %.0f pt"
                    % (self.pno + 1, len(uno["trazos"]),
                       sum(len(t) for t in uno["trazos"]), r.width, r.height))
            else:
                self.pnl_titulo.config(text="Nota escrita")
                self.pnl_datos.config(
                    text=u"Pagina %d  \u00b7  %d caracteres\n\u201c%s\u201d"
                    % (self.pno + 1, len(uno["texto"]), uno["texto"][:110]))
            lista = self.marcas.get(self.pno, [])
            nombre = uno.get("nombre") or A.nombre_por_defecto(
                uno["tipo"], self.pno, lista.index(uno))
            self.pnl_nombre.config(state="normal")
            self.pnl_nombre.delete(0, "end")
            self.pnl_nombre.insert(0, nombre)
            self.pnl_nombre_bloque.pack(fill="x", padx=12, pady=(0, 10))

            ref = self._texto_referencia(uno)
            self.pnl_ref.config(state="normal")
            self.pnl_ref.delete(0, "end")
            self.pnl_ref.insert(0, ref if ref else "(ninguna)")
            self.pnl_ref.config(state="readonly",
                                readonlybackground="#FFF6C9" if ref else "#ECEDEE")
            self.btn_quitar_ref.config(state="normal" if ref else "disabled")
            self.pnl_ref_bloque.pack(fill="x", padx=12, pady=(0, 10))
        else:
            dibujos = sum(1 for m in marcas if m["tipo"] == "lapiz")
            self.pnl_titulo.config(text="%d marcas elegidas" % len(marcas))
            self.pnl_datos.config(text=u"Pagina %d  \u00b7  %d dibujo(s), %d nota(s)"
                                  % (self.pno + 1, dibujos, len(marcas) - dibujos))

        self.pnl_color_bloque.pack(fill="x", padx=12, pady=(0, 10))
        if any(m["tipo"] == "lapiz" for m in marcas):
            self.pnl_grosor.pack(fill="x", padx=12, pady=(0, 10))

        self.pnl_acciones.pack(fill="x", padx=12, pady=(2, 0))
        if uno is not None and uno["tipo"] == "texto":
            self.btn_editar_nota.pack(fill="x", pady=(0, 3))
        if sum(1 for m in marcas if m["tipo"] == "lapiz") >= 2:
            self.btn_unificar.pack(fill="x", pady=(0, 3))
        self.btn_borrar.pack(fill="x", pady=(0, 3))
        self.btn_soltar.pack(fill="x")

    def _pintar_botones(self):
        for clave, bt in self.btn_modo.items():
            activo = (clave == self.modo)
            bt.config(relief="sunken" if activo else "raised",
                      bg="#C9D9EC" if activo else "SystemButtonFace")
        for bt, col in self.btn_color:
            bt.config(bd=4 if col == self.color else 2,
                      relief="sunken" if col == self.color else "raised")
        self.btn_grosor.config(relief="sunken" if self.grosor == GROSOR_GRUESO else "raised",
                               bg="#C9D9EC" if self.grosor == GROSOR_GRUESO else "SystemButtonFace")
        for bt, modo in ((getattr(self, "btn_pagina", None), "pagina"),
                         (getattr(self, "btn_ancho", None), "ancho")):
            if bt is not None:
                activo = (self.modo_zoom == modo)
                bt.config(relief="sunken" if activo else "raised",
                          bg="#C9D9EC" if activo else "SystemButtonFace")

    # ------------------------------------------------------ herramientas ----

    def set_modo(self, modo):
        if modo == "texto" and self.modo == "seleccionar" and self.comentar_seleccion():
            return          # habia una frase elegida: se comenta esa frase
        self._cerrar_editor(confirmar=True)
        self.modo = modo
        self.canvas.config(cursor={"dibujar": "pencil", "texto": "xterm",
                                   "seleccionar": "hand2", "borrar": "dotbox"}[modo])
        if modo != "seleccionar":
            self._limpiar_seleccion()
        self._pintar_botones()
        self._actualizar_pie()

    def set_color(self, col):
        self.color = col
        self._pintar_botones()

    def toggle_grosor(self):
        self.grosor = GROSOR_FINO if self.grosor == GROSOR_GRUESO else GROSOR_GRUESO
        self._pintar_botones()

    # ------------------------------------------------------------ render ----

    def _pagina(self):
        return self.doc[self.pno]

    def _al_redimensionar(self, _e=None):
        # Conservar la altura de lectura: si al agrandar la ventana o cambiar el
        # zoom la vista salta al principio de la hoja, hay que volver a buscar el
        # parrafo donde se estaba. Borrar y deshacer ya lo conservaban; el zoom no.
        donde = self.canvas.yview()[0]
        if self.modo_zoom != "libre":
            self._reajustar()
        self.render(donde)

    def _reajustar(self):
        """Recalcula el zoom segun el modo, sin redibujar."""
        rect = self._pagina().rect
        ancho = max(200, self.canvas.winfo_width() - 28)
        if self.modo_zoom == "ancho":
            z = ancho / rect.width
        elif self.modo_zoom == "pagina":
            alto = max(200, self.canvas.winfo_height() - 12)
            z = min(ancho / rect.width, alto / rect.height)
        else:
            return
        self.zoom = max(0.2, min(6.0, z))

    def zoom_ancho(self):
        donde = self.canvas.yview()[0]
        self.modo_zoom = "ancho"
        self._reajustar()
        self.render(donde)
        self._pintar_botones()

    def zoom_pagina(self):
        self.modo_zoom = "pagina"
        self._reajustar()
        self.render(0.0)     # la hoja entra entera: no hay donde volver
        self._pintar_botones()

    def set_zoom(self, z):
        donde = self.canvas.yview()[0]
        self.modo_zoom = "libre"
        self.zoom = max(0.2, min(6.0, z))
        self.render(donde)
        self._pintar_botones()

    def render(self, y_fraccion=0.0):
        self._cerrar_editor(confirmar=True)
        pagina = self._pagina()
        # Tope de seguridad: una hoja grande a zoom alto puede pedir cientos de
        # megas de memoria y dejar la ventana congelada. Antes de que eso pase,
        # se baja el zoom.
        rect = pagina.rect
        megapixeles = (rect.width * self.zoom) * (rect.height * self.zoom) / 1e6
        if megapixeles > 40:
            self.zoom = self.zoom * (40.0 / megapixeles) ** 0.5
        pix = pagina.get_pixmap(matrix=pymupdf.Matrix(self.zoom, self.zoom), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self.tkimg = ImageTk.PhotoImage(img)

        ancho_vista = max(1, self.canvas.winfo_width())
        self.ox = max(0, (ancho_vista - pix.width) // 2)

        self.canvas.delete("all")
        self.canvas.create_image(self.ox, 0, anchor="nw", image=self.tkimg)
        self.canvas.config(scrollregion=(0, 0, max(ancho_vista, pix.width + self.ox), pix.height))
        self._dibujar_marcas()
        self.canvas.yview_moveto(y_fraccion)
        self._actualizar_numero()
        self._actualizar_pie()

    def _actualizar_numero(self):
        self.entrada_pag.delete(0, "end")
        self.entrada_pag.insert(0, str(self.pno + 1))
        self.lbl_total.config(text="/ %d" % self.doc.page_count)

    def _saltar_a_pagina(self, _e=None):
        try:
            numero = int(self.entrada_pag.get().strip()) - 1
        except ValueError:
            self._actualizar_numero()
            return "break"
        self.ir_pagina(numero)
        self.canvas.focus_set()      # devolver el teclado al documento
        self._actualizar_numero()
        return "break"

    # coordenadas: pantalla <-> puntos PDF
    def _a_pdf(self, ex, ey):
        cx = self.canvas.canvasx(ex) - self.ox
        cy = self.canvas.canvasy(ey)
        return (cx / self.zoom, cy / self.zoom)

    def _a_canvas(self, px, py):
        return (px * self.zoom + self.ox, py * self.zoom)

    def _dibujar_marcas(self):
        # Primero el texto del manual resaltado, para que quede DEBAJO de las
        # marcas y no las tape.
        for r in self.palabras_sel:
            x0, y0 = self._a_canvas(r.x0, r.y0)
            x1, y1 = self._a_canvas(r.x1, r.y1)
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#A8C7F0", outline="",
                                         stipple="gray50", tags="seltexto")
        for i, marca in enumerate(self.marcas.get(self.pno, [])):
            self._dibujar_marca(marca, i)
        self._dibujar_seleccion()

    def _dibujar_subrayado(self, ancla, tag):
        """La linea tenue debajo de la frase a la que esta atada una marca."""
        color = a_hex(mezclar(A.COLOR_ANCLA, A.OPACIDAD_ANCLA))
        grosor = max(1, int(round(1.6 * self.zoom)))
        for (ax0, _ay0, ax1, ay1) in ancla.get("rects", []):
            px0, py = self._a_canvas(ax0, ay1)
            px1, _ = self._a_canvas(ax1, ay1)
            self.canvas.create_line(px0, py + grosor, px1, py + grosor,
                                    fill=color, width=grosor, tags=("marca", tag))

    def _dibujar_seleccion(self):
        """Recuadro punteado alrededor de lo elegido.

        Sin una senal clara de que esta agarrado, mover cosas es adivinar.
        """
        lista = self.marcas.get(self.pno, [])
        for i in self.seleccion:
            if not (0 <= i < len(lista)):
                continue
            r = self._bbox(lista[i])
            x0, y0 = self._a_canvas(r.x0, r.y0)
            x1, y1 = self._a_canvas(r.x1, r.y1)
            self.canvas.create_rectangle(x0 - 3, y0 - 3, x1 + 3, y1 + 3,
                                         outline="#1971C2", width=2, dash=(4, 3),
                                         tags="seleccion")
            for (ex, ey) in ((x0 - 3, y0 - 3), (x1 + 3, y0 - 3),
                             (x0 - 3, y1 + 3), (x1 + 3, y1 + 3)):
                self.canvas.create_rectangle(ex - 3, ey - 3, ex + 3, ey + 3,
                                             fill="#1971C2", outline="white",
                                             tags="seleccion")

    def _dibujar_marca(self, marca, i):
        tag = "marca%d" % i
        col = a_hex(marca["color"])
        ancla = marca.get("ancla")
        if ancla and marca["tipo"] == "lapiz":
            self._dibujar_subrayado(ancla, tag)
        if marca["tipo"] == "lapiz":
            w = max(1, int(round(marca.get("grosor", GROSOR_FINO) * self.zoom)))
            for trazo in marca["trazos"]:
                pts = []
                for (x, y) in trazo:
                    pts.extend(self._a_canvas(x, y))
                if len(pts) >= 4:
                    self.canvas.create_line(*pts, fill=col, width=w, capstyle="round",
                                            joinstyle="round", smooth=True, tags=("marca", tag))
        else:
            ancla = marca.get("ancla")
            if ancla:
                # El subrayado de la frase atada, y una linea fina desde la
                # frase hasta la nota para que se vea de que cuelga.
                self._dibujar_subrayado(ancla, tag)
                r0 = ancla["rects"][0] if ancla.get("rects") else None
                if r0:
                    lx, ly = self._a_canvas((r0[0] + r0[2]) / 2.0, r0[3])
                    nx, ny = self._a_canvas(marca["x"] + 8, marca["y"])
                    self.canvas.create_line(
                        lx, ly, nx, ny,
                        fill=a_hex(mezclar(A.COLOR_ANCLA, A.OPACIDAD_ANCLA)),
                        width=max(1, int(1.2 * self.zoom)), tags=("marca", tag))
            rect = A.rect_nota(marca["x"], marca["y"], marca["texto"])
            x0, y0 = self._a_canvas(rect.x0, rect.y0)
            x1, y1 = self._a_canvas(rect.x1, rect.y1)
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=a_hex(A.FONDO_NOTA),
                                         outline=col, width=1, tags=("marca", tag))
            self.canvas.create_text(
                x0 + 3, y0 + 2, text=marca["texto"], anchor="nw", fill=col,
                width=max(10, (x1 - x0) - 6),
                font=("Helvetica", max(6, int(round(A.CUERPO_NOTA * self.zoom)))),
                tags=("marca", tag))

    # -------------------------------------------------------------- mouse ----

    def _click(self, e):
        self.canvas.focus_set()
        if self._editor is not None:
            self._cerrar_editor(confirmar=True)
            return
        if self.modo == "dibujar":
            self._trazo = [self._a_pdf(e.x, e.y)]
            self._tmp = []
        elif self.modo == "texto":
            self._abrir_editor(self._a_pdf(e.x, e.y))
        elif self.modo == "seleccionar":
            self._click_seleccionar(e, sumando=bool(e.state & 0x0004))
        elif self.modo == "borrar":
            self._borrar_en(self._a_pdf(e.x, e.y))

    def _doble_click(self, e):
        """Doble clic en modo seleccionar: editar la nota que este debajo."""
        if self.modo != "seleccionar":
            return
        i = self._marca_en(self._a_pdf(e.x, e.y))
        if i is None:
            return
        self.seleccion = [i]
        if self.marcas[self.pno][i]["tipo"] == "texto":
            self._arrastrando = None
            self._editar_nota_seleccionada()

    def _arrastre(self, e):
        if self.modo == "seleccionar":
            self._arrastre_seleccionar(e)
            return
        if self.modo != "dibujar" or self._trazo is None:
            return
        p = self._a_pdf(e.x, e.y)
        ant = self._trazo[-1]
        # Filtrar puntos pegados: un trazo de 3000 puntos no se ve mejor y pesa.
        if abs(p[0] - ant[0]) * self.zoom < 1.2 and abs(p[1] - ant[1]) * self.zoom < 1.2:
            return
        self._trazo.append(p)
        a = self._a_canvas(*ant)
        b = self._a_canvas(*p)
        self._tmp.append(self.canvas.create_line(
            a[0], a[1], b[0], b[1], fill=a_hex(self.color),
            width=max(1, int(round(self.grosor * self.zoom))),
            capstyle="round", tags="temporal"))

    def _soltar(self, _e):
        if self.modo == "seleccionar":
            self._soltar_seleccionar(_e)
            return
        if self.modo != "dibujar" or self._trazo is None:
            return
        trazo, self._trazo = self._trazo, None
        for t in self._tmp:
            self.canvas.delete(t)
        self._tmp = []
        if len(trazo) < 2:
            return          # un clic suelto no deja nada
        # Un temblor de la mano al hacer clic tampoco: sin esto, un tiron de 3
        # pixeles queda como marca y viaja en la devolucion como si fuera algo.
        recorrido = sum(
            (abs(b[0] - a[0]) + abs(b[1] - a[1])) * self.zoom
            for a, b in zip(trazo, trazo[1:]))
        if recorrido < 9:
            return
        nueva = {"tipo": "lapiz", "trazos": [trazo],
                 "color": self.color, "grosor": self.grosor}
        if self.ancla_pendiente:
            # Venia de "Dibujar sobre esta frase": el trazo queda atado a ella.
            nueva["ancla"] = self.ancla_pendiente
            self.ancla_pendiente = None
        self._agregar(nueva)

    def _pan_inicio(self, e):
        self._pan = (e.x, e.y)
        self.canvas.config(cursor="fleur")

    def _pan_mover(self, e):
        if not self._pan:
            return
        dy = e.y - self._pan[1]
        self.canvas.yview_scroll(-1 if dy > 0 else 1, "units")
        self._pan = (e.x, e.y)

    def _rueda(self, e):
        if e.state & 0x0004:        # Ctrl: zoom
            self.set_zoom(self.zoom * (1.1 if e.delta > 0 else 1 / 1.1))
            return
        pasos = 1 if e.delta < 0 else -1
        prim, ult = self.canvas.yview()
        # Pasar de pagina solo si YA se estaba en el borde antes de este tiron.
        if pasos > 0 and ult >= 0.9999:
            self.ir_pagina(self.pno + 1, y=0.0)
            return
        if pasos < 0 and prim <= 0.0001:
            self.ir_pagina(self.pno - 1, y=1.0)
            return
        self.canvas.yview_scroll(pasos * 3, "units")

    def _rueda_horizontal(self, e):
        self.canvas.xview_scroll(1 if e.delta < 0 else -1, "units")

    # ------------------------------------------------------------- marcas ----

    def _instantanea(self):
        """Guarda como esta la pagina ANTES de cambiarla, para poder deshacer.

        Se guarda la pagina entera en vez de anotar que fue cada operacion: es
        una lista corta, y asi deshacer funciona igual para todo (agregar, mover,
        cambiar de color, unificar) sin un caso especial por cada cosa nueva.
        """
        import copy
        self.historial.append((self.pno, copy.deepcopy(self.marcas.get(self.pno, []))))
        if len(self.historial) > 100:
            self.historial.pop(0)
        del self.rehacer_pila[:]     # una accion nueva corta la rama de rehacer

    def _agregar(self, marca):
        self._instantanea()
        self.marcas.setdefault(self.pno, []).append(marca)
        self._dibujar_marca(marca, len(self.marcas[self.pno]) - 1)
        self._marcar_sucio()

    def _bbox(self, marca):
        if marca["tipo"] == "lapiz":
            return A.bbox_trazo(marca["trazos"], marca.get("grosor", GROSOR_FINO))
        return A.rect_nota(marca["x"], marca["y"], marca["texto"])

    def _borrar_en(self, punto):
        lista = self.marcas.get(self.pno, [])
        px, py = punto
        tol = 4.0 / max(0.2, self.zoom)     # margen generoso para trazos finos
        for i in range(len(lista) - 1, -1, -1):   # de arriba hacia abajo
            r = self._bbox(lista[i])
            if (r.x0 - tol) <= px <= (r.x1 + tol) and (r.y0 - tol) <= py <= (r.y1 + tol):
                self._instantanea()
                lista.pop(i)
                self._limpiar_seleccion()
                self.render(self.canvas.yview()[0])
                self._marcar_sucio()
                return

    def _volver_a(self, pila, otra):
        """Motor comun de deshacer y rehacer: saca de una pila y apila en la otra."""
        import copy
        if not pila:
            return
        pno, lista = pila.pop()
        otra.append((pno, copy.deepcopy(self.marcas.get(pno, []))))
        self.marcas[pno] = lista
        self._limpiar_seleccion()
        if pno != self.pno:
            self.pno = pno
            self._reajustar()
            self.render()
        else:
            self.render(self.canvas.yview()[0])
        self._marcar_sucio()

    def deshacer(self):
        # Si se esta escribiendo una nota, deshacer significa "cancelar esta
        # nota", no "borrar tambien la marca anterior".
        if self._editor is not None:
            self._cerrar_editor(confirmar=False)
            return
        self._volver_a(self.historial, self.rehacer_pila)

    def rehacer(self):
        """Ctrl+Y: devuelve lo ultimo que se deshizo."""
        self._cerrar_editor(confirmar=True)
        self._volver_a(self.rehacer_pila, self.historial)

    # ------------------------------------------------------- seleccionar ----

    def _marcas_seleccionadas(self):
        lista = self.marcas.get(self.pno, [])
        return [lista[i] for i in sorted(self.seleccion) if 0 <= i < len(lista)]

    def _limpiar_seleccion(self):
        self.seleccion = []
        self.palabras_sel = []
        self._texto_sel = ""
        self._mostrar_panel(False)

    def _marca_en(self, punto):
        """Indice de la marca que esta debajo del punto, o None.

        Se recorre de la ultima a la primera: si hay marcas encimadas, agarra la
        de arriba, que es la que el ojo ve.
        """
        px, py = punto
        lista = self.marcas.get(self.pno, [])
        tol = 4.0 / max(0.2, self.zoom)
        for i in range(len(lista) - 1, -1, -1):
            r = self._bbox(lista[i])
            if (r.x0 - tol) <= px <= (r.x1 + tol) and (r.y0 - tol) <= py <= (r.y1 + tol):
                return i
        return None

    def _click_seleccionar(self, e, sumando=False):
        punto = self._a_pdf(e.x, e.y)
        i = self._marca_en(punto)
        if self.refiriendo:
            # Se esta eligiendo a que se refiere una marca: un clic sobre otra
            # marca la toma como referencia; si no, se sigue de largo y lo que
            # se arrastre sobre el texto va a ser la referencia.
            if i is not None and i not in self.refiriendo:
                lista = self.marcas.get(self.pno, [])
                otra = lista[i]
                nombre = otra.get("nombre") or A.nombre_por_defecto(
                    otra["tipo"], self.pno, i)
                self._asignar_referencia(nombre=nombre)
                return
            if i is not None:
                return      # clic sobre si misma: se ignora
        if i is None:
            # En un vacio: empieza a seleccionar TEXTO del manual. Sin esto
            # habria que abrir el PDF en otro programa solo para copiar una
            # frase, que es exactamente lo que este programa venia a evitar.
            if not sumando:
                self._limpiar_seleccion()
            self._marco_sel = {"desde": punto, "hasta": punto}
            self.render(self.canvas.yview()[0])
            return
        if sumando:
            if i in self.seleccion:
                self.seleccion.remove(i)
            else:
                self.seleccion.append(i)
        elif i not in self.seleccion:
            self.seleccion = [i]
        self.palabras_sel = []
        self._texto_sel = ""
        # Preparar el movimiento: se anota desde donde se empezo a arrastrar.
        self._arrastrando = {"desde": punto, "movido": False}
        self.render(self.canvas.yview()[0])
        # El panel se abre al hacer clic, no al soltar: si esperara a que se
        # suelte, elegir algo y no moverlo no mostraria nada.
        self._refrescar_panel()

    def _arrastre_seleccionar(self, e):
        punto = self._a_pdf(e.x, e.y)
        if self._arrastrando is not None and self.seleccion:
            if not self._arrastrando["movido"]:
                self._instantanea()          # una sola instantanea por movimiento
                self._arrastrando["movido"] = True
            dx = punto[0] - self._arrastrando["desde"][0]
            dy = punto[1] - self._arrastrando["desde"][1]
            self._arrastrando["desde"] = punto
            self._mover_seleccion(dx, dy)
            self.render(self.canvas.yview()[0])
        elif self._marco_sel is not None:
            self._marco_sel["hasta"] = punto
            self._seleccionar_texto(self._marco_sel["desde"], punto)
            self.render(self.canvas.yview()[0])

    def _soltar_seleccionar(self, _e):
        if self.refiriendo and self._texto_sel and self.palabras_sel:
            self._marco_sel = None
            self._asignar_referencia(ancla={
                "rects": [(r.x0, r.y0, r.x1, r.y1) for r in self.palabras_sel],
                "cita": self._texto_sel})
            return
        if self._arrastrando is not None:
            if self._arrastrando["movido"]:
                self._marcar_sucio()
            self._arrastrando = None
        self._marco_sel = None
        self._refrescar_panel()

    def _mover_seleccion(self, dx, dy):
        rect = self._pagina().rect
        for mk in self._marcas_seleccionadas():
            if mk["tipo"] == "lapiz":
                mk["trazos"] = [[(x + dx, y + dy) for (x, y) in t] for t in mk["trazos"]]
            else:
                # Que no se vaya de la hoja: una nota fuera del papel llega
                # cortada en el PDF y el agente no la ve entera.
                mk["x"] = min(max(0.0, mk["x"] + dx), max(0.0, rect.width - A.ANCHO_NOTA))
                mk["y"] = min(max(0.0, mk["y"] + dy), max(0.0, rect.height - A.ALTO_LINEA))

    # --- texto del PDF original -------------------------------------------

    def _palabras_pagina(self):
        if getattr(self, "_cache_palabras_pno", None) != self.pno:
            self._cache_palabras = self._pagina().get_text("words")
            self._cache_palabras_pno = self.pno
        return self._cache_palabras

    def _seleccionar_texto(self, desde, hasta):
        """Selecciona el texto del manual entre dos puntos, en orden de lectura."""
        palabras = self._palabras_pagina()
        if not palabras:
            return
        a = self._indice_palabra(palabras, desde)
        b = self._indice_palabra(palabras, hasta)
        if a is None or b is None:
            return
        if a > b:
            a, b = b, a
        elegidas = palabras[a:b + 1]
        self.palabras_sel = [pymupdf.Rect(w[0], w[1], w[2], w[3]) for w in elegidas]
        self._texto_sel = " ".join(w[4] for w in elegidas)

    def _indice_palabra(self, palabras, punto):
        """La palabra mas cercana al punto (la de abajo del cursor, si la hay)."""
        px, py = punto
        mejor, dist = None, None
        for i, w in enumerate(palabras):
            if w[0] <= px <= w[2] and w[1] <= py <= w[3]:
                return i
            cx, cy = (w[0] + w[2]) / 2.0, (w[1] + w[3]) / 2.0
            # El eje vertical pesa mas: primero el renglon, despues la columna.
            d = (cx - px) ** 2 + ((cy - py) * 3.0) ** 2
            if dist is None or d < dist:
                mejor, dist = i, d
        return mejor

    def comentar_seleccion(self):
        """Dejar lista una nota que va a quedar atada a la frase elegida.

        No abre el cuadro de texto en un lugar elegido por el programa: pasa a
        modo Texto y espera a que David haga clic donde la quiere. La nota que
        escriba ahi queda atada a esta frase, se ponga donde se ponga.
        """
        if not self.palabras_sel or not self._texto_sel:
            return False
        self.ancla_pendiente = {
            "rects": [(r.x0, r.y0, r.x1, r.y1) for r in self.palabras_sel],
            "cita": self._texto_sel,
        }
        cita = self._texto_sel
        self._limpiar_seleccion()
        self.modo = "texto"
        self.canvas.config(cursor="xterm")
        self._pintar_botones()
        self.render(self.canvas.yview()[0])
        self.pie.config(text=("Hace clic donde quieras la nota. Va a quedar atada a: "
                              "\u201c%s\u201d   (Esc para cancelar)") % cita[:80])
        return True

    def dibujar_sobre_seleccion(self):
        """Igual que comentar, pero lo que sigue es un dibujo en vez de una nota."""
        if not self.palabras_sel or not self._texto_sel:
            return False
        self.ancla_pendiente = {
            "rects": [(r.x0, r.y0, r.x1, r.y1) for r in self.palabras_sel],
            "cita": self._texto_sel,
        }
        cita = self._texto_sel
        self._limpiar_seleccion()
        self.modo = "dibujar"
        self.canvas.config(cursor="pencil")
        self._pintar_botones()
        self.render(self.canvas.yview()[0])
        self.pie.config(text=("Dibuja donde quieras. El dibujo va a quedar atado a: "
                              "\u201c%s\u201d   (Esc para cancelar)") % cita[:80])
        return True

    def elegir_referencia(self):
        """Empezar a elegir a que se refiere la marca que esta seleccionada.

        Despues de tocar "Elegir", lo que se marque pasa a ser la referencia:
        una frase del manual (arrastrando sobre el texto) o una marca que ya
        exista (haciendole clic).
        """
        if not self.seleccion:
            return
        self.refiriendo = list(self.seleccion)
        self._limpiar_seleccion()
        self.modo = "seleccionar"
        self.canvas.config(cursor="hand2")
        self._pintar_botones()
        self.render(self.canvas.yview()[0])
        self.pie.config(text="Elegi la referencia: arrastra sobre una frase del manual, "
                             "o hace clic en otra marca.   (Esc para cancelar)")

    def _asignar_referencia(self, ancla=None, nombre=None):
        """Cierra el modo referencia, guardando lo elegido en las marcas que esperaban."""
        objetivo = self.refiriendo
        self.refiriendo = []
        lista = self.marcas.get(self.pno, [])
        if not objetivo:
            return
        self._instantanea()
        for i in objetivo:
            if not (0 <= i < len(lista)):
                continue
            mk = lista[i]
            mk.pop("ancla", None)
            mk.pop("ref", None)
            if ancla:
                mk["ancla"] = ancla
            elif nombre:
                mk["ref"] = nombre
        self.seleccion = [i for i in objetivo if 0 <= i < len(lista)]
        self.palabras_sel = []
        self._texto_sel = ""
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()
        self._refrescar_panel()
        self.pie.config(text="Referencia guardada.")

    def cancelar_pendientes(self):
        """Esc: abandonar lo que se estaba por atar, sin tocar nada."""
        algo = bool(self.ancla_pendiente or self.refiriendo)
        self.ancla_pendiente = None
        self.refiriendo = []
        if algo:
            self._actualizar_pie()
        return algo

    def soltar_ancla(self):
        """Sacarle la referencia a lo que este elegido."""
        marcas = [m for m in self._marcas_seleccionadas()
                  if m.get("ancla") or m.get("ref")]
        if not marcas:
            return
        self._instantanea()
        for mk in marcas:
            mk.pop("ancla", None)
            mk.pop("ref", None)
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()
        self._refrescar_panel()

    def copiar_texto(self):
        """Ctrl+C: manda al portapapeles el texto del manual seleccionado."""
        if not self._texto_sel:
            return
        self.app.clipboard_clear()
        self.app.clipboard_append(self._texto_sel)
        self.app.update()
        self.pie.config(text="Copiado: %d caracteres del manual." % len(self._texto_sel))

    # --- acciones del panel -----------------------------------------------

    def _renombrar(self):
        marcas = self._marcas_seleccionadas()
        if len(marcas) != 1:
            return
        nuevo = A.limpiar_nombre(self.pnl_nombre.get())
        if not nuevo:
            self._refrescar_panel()
            return
        self._instantanea()
        marcas[0]["nombre"] = nuevo
        self._marcar_sucio()
        self.pie.config(text="Ahora se llama “%s”." % nuevo)

    def _cambiar_color(self, col):
        marcas = self._marcas_seleccionadas()
        if not marcas:
            return
        self._instantanea()
        for mk in marcas:
            mk["color"] = col
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()

    def _cambiar_grosor(self, valor):
        marcas = [m for m in self._marcas_seleccionadas() if m["tipo"] == "lapiz"]
        if not marcas:
            return
        self._instantanea()
        for mk in marcas:
            mk["grosor"] = valor
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()

    def _unificar(self):
        """Junta varios dibujos en uno solo.

        Sirve para que una flecha hecha de tres trazos, o un circulo repasado,
        le lleguen al agente como UNA marca y no como tres sueltas: asi el
        informe dice "un dibujo de 3 trazos sobre este parrafo" en vez de tres
        garabatos sin relacion entre si.
        """
        indices = sorted(i for i in self.seleccion
                         if self.marcas[self.pno][i]["tipo"] == "lapiz")
        if len(indices) < 2:
            return
        self._instantanea()
        lista = self.marcas[self.pno]
        partes = [lista[i] for i in indices]
        unido = {
            "tipo": "lapiz",
            "trazos": [t for mk in partes for t in mk["trazos"]],
            "color": partes[0]["color"],
            "grosor": partes[0].get("grosor", GROSOR_FINO),
            "nombre": partes[0].get("nombre", ""),
        }
        for i in reversed(indices):
            lista.pop(i)
        lista.insert(indices[0], unido)
        self.seleccion = [indices[0]]
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()
        self._refrescar_panel()
        self.pie.config(text="%d dibujos unidos en uno solo (%d trazos)."
                             % (len(partes), len(unido["trazos"])))

    def _borrar_seleccion(self):
        if not self.seleccion:
            return
        self._instantanea()
        lista = self.marcas.get(self.pno, [])
        for i in sorted(self.seleccion, reverse=True):
            if 0 <= i < len(lista):
                lista.pop(i)
        self._limpiar_seleccion()
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()

    def _editar_nota_seleccionada(self):
        marcas = self._marcas_seleccionadas()
        if len(marcas) != 1 or marcas[0]["tipo"] != "texto":
            return
        mk = marcas[0]
        self._instantanea()
        self.marcas[self.pno].remove(mk)
        self._limpiar_seleccion()
        self.render(self.canvas.yview()[0])
        self.color = mk["color"]
        self._abrir_editor((mk["x"], mk["y"]), texto=mk.get("texto", ""),
                           nombre=mk.get("nombre", ""))

    def mostrar_ayuda(self):
        ayuda.Ventana(self.app, ruta_errores=errores.ARCHIVO)

    # ---------------------------------------------------- editor de texto ----

    def _abrir_editor(self, punto, texto="", nombre="", ancla=None):
        # Que la nota entre entera en la hoja. Si se hace clic cerca del borde
        # derecho, sin esto el cuadro de escribir se sale de la ventana (se
        # escribe a ciegas) y la nota queda con medio texto fuera de la pagina,
        # cortado en el PDF que recibe el agente. Se corre hacia adentro.
        rect = self._pagina().rect
        x = min(max(2.0, punto[0]), max(2.0, rect.width - A.ANCHO_NOTA - 2.0))
        y = min(max(2.0, punto[1]), max(2.0, rect.height - A.ALTO_LINEA - 6.0))
        punto = (x, y)
        self._editor_xy = punto
        self._editor_nombre = nombre
        self._editor_ancla = ancla
        cx, cy = self._a_canvas(*punto)
        ancho_px = A.ANCHO_NOTA * self.zoom
        cuerpo = max(7, int(round(A.CUERPO_NOTA * self.zoom)))
        self._editor = tk.Text(self.canvas, wrap="word", height=4, undo=True,
                               font=("Helvetica", cuerpo), bg=a_hex(A.FONDO_NOTA),
                               fg=a_hex(self.color), relief="solid", bd=1,
                               insertbackground=a_hex(self.color))
        self._editor_win = self.canvas.create_window(cx, cy, anchor="nw", window=self._editor,
                                                     width=ancho_px)
        if texto:
            self._editor.insert("1.0", texto)
        self._editor.focus_set()
        self._crecer_editor()
        self._editor.bind("<Escape>", lambda e: (self._cerrar_editor(confirmar=True), "break")[1])
        self._editor.bind("<Control-Return>", lambda e: (self._cerrar_editor(confirmar=True), "break")[1])
        self._editor.bind("<KeyRelease>", self._crecer_editor)
        self.pie.config(text="Escribiendo nota  —  Esc o clic afuera para confirmar")

    def _crecer_editor(self, _e=None):
        if self._editor is None:
            return
        lineas = int(self._editor.index("end-1c").split(".")[0])
        self._editor.config(height=max(4, min(16, lineas + 1)))

    def _cerrar_editor(self, confirmar=True):
        if self._editor is None:
            return
        texto = self._editor.get("1.0", "end-1c") if confirmar else ""
        ed, win, xy = self._editor, self._editor_win, self._editor_xy
        self._editor = self._editor_win = self._editor_xy = None
        try:
            self.canvas.delete(win)
            ed.destroy()
        except Exception:
            pass
        if texto.strip():
            nueva = {"tipo": "texto", "x": xy[0], "y": xy[1],
                     "texto": texto.rstrip(), "color": self.color,
                     "nombre": getattr(self, "_editor_nombre", "") or ""}
            ancla = getattr(self, "_editor_ancla", None) or self.ancla_pendiente
            self.ancla_pendiente = None
            if ancla:
                nueva["ancla"] = ancla
            self._agregar(nueva)
        self._editor_nombre = ""
        self._editor_ancla = None
        # Volver a Dibujar: el estado en reposo es siempre el mismo.
        if self.modo == "texto":
            self.modo = "dibujar"
            self.canvas.config(cursor="pencil")
            self._pintar_botones()
        self._actualizar_pie()

    # ------------------------------------------------------------ paginas ----

    def ir_pagina(self, numero, y=0.0):
        # Cerrar la nota ANTES de cambiar de pagina. Si se cierra despues (que es
        # lo que hace render), la nota a medio escribir se guarda en la pagina
        # nueva en vez de en la que se estaba mirando. Pasa al hacer clic en las
        # flechas < > mientras se escribe.
        self._cerrar_editor(confirmar=True)
        numero = max(0, min(self.doc.page_count - 1, numero))
        if numero == self.pno:
            return
        # Los indices de seleccion son de la pagina actual: al cambiar dejan de
        # significar nada y apuntarian a marcas equivocadas.
        self._limpiar_seleccion()
        self.pno = numero
        self._reajustar()      # paginas de distinto tamano dentro del mismo PDF
        self.render(y)

    # ------------------------------------------------------------- estado ----

    def _firma(self):
        """Resumen del estado de las marcas, para saber si hay cambios sin guardar.

        Se compara el estado con el que tenia el archivo la ultima vez que se
        guardo, en vez de encender un "sucio" que no se apaga nunca. Asi, si se
        deshace todo hasta dejarlo como estaba, el programa deja de pedir que se
        guarde algo que ya no cambio.
        """
        partes = []
        for pno in sorted(self.marcas):
            for mk in self.marcas[pno]:
                if mk["tipo"] == "lapiz":
                    partes.append("%d:l:%s:%.1f:%s" % (
                        pno, mk["color"], mk.get("grosor", 0),
                        ";".join("%.1f,%.1f" % (p[0], p[1])
                                 for t in mk["trazos"] for p in (t[0], t[-1]))))
                else:
                    partes.append("%d:t:%.1f:%.1f:%s" % (pno, mk["x"], mk["y"], mk["texto"]))
        return "|".join(partes)

    @property
    def sucio(self):
        return self._firma() != self.firma_guardada

    def _marcar_sucio(self):
        self.app.actualizar_titulo()
        self._actualizar_pie()

    def cuenta_marcas(self):
        return sum(len(v) for v in self.marcas.values())

    def _actualizar_pie(self):
        if self._editor is not None:
            return
        nombres = {"dibujar": "Dibujar", "texto": "Texto",
                   "seleccionar": "Seleccionar", "borrar": "Borrar"}
        if self.modo == "seleccionar":
            cola = ("clic: elegir  ·  arrastrar: mover  ·  Ctrl+clic: sumar  ·  "
                    "en un vacio: elegir texto  ·  Ctrl+C copiar  ·  Supr borrar")
        else:
            cola = ("rueda: leer  ·  arrastrar: dibujar  ·  D dibujar  T texto  "
                    "S seleccionar  B borrar  ·  Ctrl+Z/Ctrl+Y  ·  Ctrl+S guardar")
        self.pie.config(text="%s  |  %d marca(s)%s  |  %s"
                             % (nombres[self.modo], self.cuenta_marcas(),
                                "  ·  SIN GUARDAR" if self.sucio else "", cola))

    # ------------------------------------------------------------ guardar ----

    def guardar(self):
        self._cerrar_editor(confirmar=True)
        if self.cuenta_marcas() == 0:
            if not messagebox.askyesno("Sin marcas",
                                       "No hay ninguna marca todavia. Guardar igual?",
                                       parent=self):
                return
        carpeta = os.path.dirname(self.ruta)
        base = os.path.splitext(os.path.basename(self.ruta))[0]
        if base.endswith("-devolucion"):
            base = base[:-len("-devolucion")]
        sugerida = ruta_libre(carpeta, base)
        destino = filedialog.asksaveasfilename(
            parent=self, title="Guardar devolucion",
            initialdir=carpeta, initialfile=os.path.basename(sugerida),
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not destino:
            return

        # Guardar encima del PDF que se esta mirando: Windows no deja reemplazar
        # un archivo abierto, asi que hay que soltarlo y volver a tomarlo. Pasa
        # siempre que se reabre una devolucion para agregarle algo mas.
        mismo = os.path.abspath(destino) == os.path.abspath(self.ruta)
        y_actual = self.canvas.yview()[0]
        if mismo:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
        try:
            A.guardar(self.ruta, destino, self.marcas)
        except A.MarcasNoGuardadas as err:
            errores.anotar("Guardado incompleto en %s" % os.path.basename(destino), err)
            messagebox.showwarning(
                "Guardado incompleto",
                "El archivo se guardo en:\n%s\n\nPERO estas marcas quedaron afuera:\n\n%s"
                % (destino, "\n".join(err.fallos)), parent=self)
            return
        except Exception as err:
            errores.anotar("No se pudo guardar en %s" % destino, err)
            messagebox.showerror(
                "No se pudo guardar",
                "%s\n\nEl PDF anterior quedo intacto y tus marcas siguen en pantalla:\n"
                "proba con Guardar y otro nombre." % err, parent=self)
            return
        finally:
            if mismo:
                # Volver a tomar el archivo, se haya guardado bien o mal, para
                # que el programa nunca quede sin documento en pantalla.
                try:
                    self.doc, _ = A.abrir_para_editar(self.ruta)
                    self.pno = min(self.pno, self.doc.page_count - 1)
                    self.render(y_actual)
                except Exception:
                    pass

        self.firma_guardada = self._firma()
        self.app.actualizar_titulo()
        self._actualizar_pie()
        # Se copia el mensaje ENTERO, no solo la ruta: asi David pega una vez en
        # el chat y el agente ya sabe que es una devolucion y con que leerla, sin
        # tener que explicarle nada ni acordarse del comando.
        self.app.clipboard_clear()
        self.app.clipboard_append(mensaje_para_el_chat(destino))
        self.app.update()           # dejar el portapapeles firme en Windows
        DialogoGuardado(self.app, destino)


def mensaje_para_el_chat(destino):
    """El texto que se copia al guardar.

    ESTA ESCRITO PARA QUE LO LEA UN AGENTE, no David: es lo que David pega en el
    chat y con eso el otro lado tiene que entender, sin preguntar nada, que es
    esto, donde esta y como leerlo. Por eso arranca diciendo que es, en una
    linea, y sigue con el comando exacto.
    """
    extractor = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "leer_devolucion.py")
    return (
        "Te paso una devolucion mia marcada sobre un PDF.\n"
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
        "python \"%s\" \"%s\"\n"
    ) % (destino, extractor, destino)


class DialogoGuardado(tk.Toplevel):
    """Avisa donde quedo el archivo y deja todo listo para pegar en el chat."""

    def __init__(self, app, destino):
        super().__init__(app)
        self.title("Guardado")
        self.resizable(False, False)
        self.transient(app)
        marco = ttk.Frame(self, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Devolucion guardada", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(marco,
                  text="Esto ya esta copiado. Pegalo en el chat con Ctrl+V.\n"
                       "Es un mensaje escrito para el agente: le dice que es esto, donde\n"
                       "quedo el archivo y con que leerlo. No hace falta que agregues nada.",
                  foreground="#333", justify="left").pack(anchor="w", pady=(4, 10))
        caja = tk.Text(marco, width=92, height=13, wrap="word", relief="solid", bd=1,
                       font=("Consolas", 9), bg="#F7F7F7")
        caja.insert("1.0", mensaje_para_el_chat(destino))
        caja.config(state="disabled")
        caja.pack(fill="x")
        fila = ttk.Frame(marco)
        fila.pack(fill="x", pady=(14, 0))
        ttk.Button(fila, text="Abrir carpeta",
                   command=lambda: abrir_en_explorador(destino)).pack(side="left")
        ttk.Button(fila, text="Copiar de nuevo",
                   command=lambda: (app.clipboard_clear(),
                                    app.clipboard_append(mensaje_para_el_chat(destino)),
                                    app.update())).pack(side="left", padx=6)
        ttk.Button(fila, text="Copiar solo la ruta",
                   command=lambda: (app.clipboard_clear(), app.clipboard_append(destino),
                                    app.update())).pack(side="left")
        ttk.Button(fila, text="Listo", command=self.destroy).pack(side="right")
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + 160
        self.geometry("+%d+%d" % (max(0, x), max(0, y)))
        self.grab_set()
        self.focus_set()


def abrir_en_explorador(ruta):
    try:
        subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)])
    except Exception:
        pass


# ====================================================================== app ==

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Lector PDF")
        self.geometry("1280x860")
        try:
            self.state("zoomed")
        except Exception:
            pass
        icono = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lector.ico")
        if os.path.exists(icono):
            try:
                self.iconbitmap(icono)
            except Exception:
                pass
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass

        # Sesion nueva: el registro arranca vacio y va acumulando TODO lo que
        # falle, no solo lo ultimo. Cuando algo se rompe de verdad suelen fallar
        # varias cosas encadenadas, y con un solo error a la vista se ve el
        # sintoma y nunca la causa.
        errores.limpiar()
        self.report_callback_exception = self._fallo_no_previsto

        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(fill="both", expand=True)
        self.biblioteca = None
        self.visor = None
        self.mostrar_biblioteca()

        self.bind("<Key>", self._tecla)
        self.bind("<Control-s>", lambda e: self.visor and self.visor.guardar())
        # Ctrl+Z mientras se escribe una nota lo maneja el cuadro de texto
        # (deshace lo tipeado); si no, deshace la ultima marca.
        self.bind("<Control-z>",
                  lambda e: (self.visor and self.visor._editor is None
                             and self.visor.deshacer()))
        # Rehacer: Ctrl+Y es lo que se usa en Windows; Ctrl+Shift+Z tambien, que
        # es lo que espera el que viene de programas de diseno.
        for combo in ("<Control-y>", "<Control-Shift-Z>", "<Control-Shift-z>"):
            self.bind(combo, lambda e: (self.visor and self.visor._editor is None
                                        and self.visor.rehacer()))
        self.bind("<Control-c>", lambda e: self.visor and self.visor.copiar_texto())
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

    def _fallo_no_previsto(self, tipo, valor, traza):
        """Cualquier error que se escape de un boton o de un evento cae aca.

        Antes estos se perdian en el aire: el programa quedaba raro y no habia
        rastro de por que. Ahora se anotan todos y David puede pasarle el
        archivo entero al agente.
        """
        try:
            cuantos = errores.anotar("Fallo no previsto en la ventana", valor)
            self.after(50, lambda: messagebox.showerror(
                "Algo salio mal",
                "%s\n\nEs el error numero %d de esta sesion.\n"
                "Quedaron todos anotados en:\n%s"
                % (valor, cuantos, errores.ARCHIVO), parent=self))
        except Exception:
            pass

    # ------------------------------------------------------------ pantallas --

    def _soltar_visor(self):
        """Cierra el visor actual y suelta el PDF.

        Importante cerrar el documento: mientras este abierto, Windows no deja
        borrar ni mover ese PDF desde el explorador, y el usuario no tendria
        idea de por que.
        """
        if self.visor is None:
            return
        try:
            if self.visor.doc is not None:
                self.visor.doc.close()
        except Exception:
            pass
        self.visor.pack_forget()
        self.visor.destroy()
        self.visor = None

    def mostrar_biblioteca(self):
        self._soltar_visor()
        if self.biblioteca is None:
            self.biblioteca = Biblioteca(self)
        self.biblioteca.pack(fill="both", expand=True)
        self.biblioteca.refrescar()
        self.actualizar_titulo()

    def abrir_pdf(self, ruta):
        try:
            visor = Visor(self, ruta)
        except Exception as err:
            errores.anotar("No se pudo abrir %s" % os.path.basename(ruta), err)
            messagebox.showerror("No se pudo abrir", "%s\n\n%s" % (os.path.basename(ruta), err),
                                 parent=self)
            return
        self._soltar_visor()
        self.biblioteca.pack_forget()
        self.visor = visor
        self.visor.pack(fill="both", expand=True)
        self.actualizar_titulo()
        self.after(60, self.visor.zoom_pagina)

    def volver_biblioteca(self):
        if self.visor is not None and not self._confirmar_descartar():
            return
        self.mostrar_biblioteca()

    def _confirmar_descartar(self):
        if self.visor is None:
            return True
        # Una nota a medio escribir todavia no es una marca: sin esto, salir o
        # cerrar la tiraba sin preguntar nada, porque el programa se veia "limpio".
        self.visor._cerrar_editor(confirmar=True)
        if not self.visor.sucio:
            return True
        r = messagebox.askyesnocancel(
            "Hay marcas sin guardar",
            "Tenes %d marca(s) sin guardar.\n\nGuardar antes de salir?"
            % self.visor.cuenta_marcas(), parent=self)
        if r is None:
            return False
        if r:
            self.visor.guardar()
            return not self.visor.sucio
        return True

    def actualizar_titulo(self):
        if self.visor is None:
            self.title("Lector PDF  —  %s" % os.path.basename(CARPETA_INICIAL))
        else:
            self.title("%s%s  —  Lector PDF"
                       % ("* " if self.visor.sucio else "", os.path.basename(self.visor.ruta)))

    def cerrar(self):
        if self._confirmar_descartar():
            self.destroy()

    # --------------------------------------------------------------- teclas --

    def _tecla(self, e):
        v = self.visor
        if v is None or v._editor is not None:
            return              # mientras se escribe una nota, las letras son letras
        try:
            if isinstance(self.focus_get(), (tk.Entry, tk.Text)):
                return          # idem si el foco esta en el numero de pagina
        except Exception:
            pass
        k = e.keysym.lower()
        if k == "t" and v.modo == "seleccionar" and v.comentar_seleccion():
            return          # habia texto elegido: la nota quedo atada a esa frase
        if k in ("d", "t", "b", "s"):
            v.set_modo({"d": "dibujar", "t": "texto",
                        "s": "seleccionar", "b": "borrar"}[k])
        elif k == "delete":
            v._borrar_seleccion()
        elif k in ("next", "space"):
            v.ir_pagina(v.pno + 1)
        elif k == "prior":
            v.ir_pagina(v.pno - 1)
        elif k == "right":
            v.ir_pagina(v.pno + 1)
        elif k == "left":
            v.ir_pagina(v.pno - 1)
        elif k == "down":
            v.canvas.yview_scroll(3, "units")
        elif k == "up":
            v.canvas.yview_scroll(-3, "units")
        elif k == "home":
            v.canvas.yview_moveto(0)
        elif k == "end":
            v.canvas.yview_moveto(1)
        elif k == "escape":
            if not v.cancelar_pendientes():
                self.volver_biblioteca()
        elif k in ("plus", "equal", "kp_add"):
            v.set_zoom(v.zoom * 1.2)
        elif k in ("minus", "kp_subtract"):
            v.set_zoom(v.zoom / 1.2)


def main():
    if _ERROR_IMPORT is not None:
        # Ojo: en esta maquina hay mas de un Python instalado y solo uno tiene
        # las librerias. Por eso el mensaje dice CUAL se esta usando: casi
        # siempre el problema es que se arranco con el Python equivocado, no
        # que falte instalar algo.
        raise RuntimeError(
            "Falta una libreria que el programa necesita:\n\n    %s\n\n"
            "Se esta usando este Python:\n    %s\n\n"
            "Se arregla instalandola con:\n    \"%s\" -m pip install pymupdf pillow"
            % (_ERROR_IMPORT, sys.executable, sys.executable))
    app = App()
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.after(100, lambda: app.abrir_pdf(sys.argv[1]))
    app.mainloop()


def _morir_avisando(err):
    """Mostrar el error en pantalla en vez de no hacer nada.

    El programa arranca con pythonw.exe, que no tiene consola: si algo falla al
    iniciar (falta una libreria, se movio un archivo), sin esto David haria doble
    clic en el icono del escritorio y NO PASARIA NADA, sin ninguna pista de por
    que. Se muestra el error y ademas se deja escrito al lado del programa.
    """
    import traceback
    detalle = traceback.format_exc()

    # El registro se escribe en la carpeta de datos del usuario, NO al lado del
    # programa: el programa vive en Program Files, donde Windows no deja
    # escribir. Se hace a mano y no con errores.anotar porque este camino se usa
    # justamente cuando algun import fallo, y puede que errores.py no este.
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    archivo = os.path.join(base, "LectorPDF", "errores_de_la_ultima_sesion.txt")
    try:
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        with open(archivo, "w", encoding="utf-8") as f:
            f.write("ERRORES DE LA ULTIMA SESION DEL LECTOR PDF\n")
            f.write("=" * 66 + "\n")
            f.write("Python   : %s\n" % sys.executable)
            f.write("Total    : 1 error(es)\n\nRESUMEN\n")
            f.write("-" * 66 + "\n 1. El programa no pudo ni arrancar\n\n")
            f.write("DETALLE COMPLETO\n" + "=" * 66 + "\n")
            f.write(detalle)
    except Exception:
        archivo = "(no se pudo escribir el registro)"
    try:
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror(
            "El Lector PDF no pudo arrancar",
            "%s\n\nEl detalle quedo en:\n%s\n\nPasale este texto al agente y lo arregla."
            % (err, archivo))
        raiz.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as _err:
        _morir_avisando(_err)
        sys.exit(1)
