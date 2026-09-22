# -*- coding: utf-8 -*-
"""
Lector PDF — leer cualquier PDF y marcarlo encima para devolverselo a un agente.

Flujo para el que fue hecho (no desviarse de esto sin pedirlo):
  abre mostrando los PDFs de la ultima carpeta usada -> se abre uno -> se lee
  y se marca intercalando -> Guardar -> el mensaje para el chat queda en el
  portapapeles.

  Carpeta: decision del Disenador (sept-2026). Se recuerda la ultima carpeta
  elegida ("Cambiar carpeta..." o la de un PDF abierto con "Abrir archivo..."),
  entre sesiones, como pide la guia de Microsoft para los programas de
  Windows. Solo la primera vez (o si esa carpeta ya no existe) abre Descargas.
  Antes abria SIEMPRE Descargas, y quien guardaba sus PDFs en otro lado tenia
  que ir a buscarlos cada vez.

DECISIONES DE DISENO (leer antes de cambiar nada):

1. EL MODO POR DEFECTO ES "SELECCIONAR", Y LA RUEDA SIEMPRE HACE SCROLL.
   Decision del Disenador (cambiada a pedido, sept-2026): el estado en reposo es
   Seleccionar, como en los programas de edicion, para poder elegir, mover y
   tocar lo ya marcado sin apretar un boton antes. Para marcar se elige Dibujar
   o Texto. Texto vuelve solo a Seleccionar al terminar la nota; Dibujar queda
   puesta para poder hacer varios trazos seguidos. La rueda SIEMPRE
   lee (scroll), en cualquier modo: leer nunca depende de la herramienta activa.
   Si alguna vez se agrega una herramienta, la rueda tiene que seguir leyendo.

2. Al terminar de escribir una nota, el programa vuelve solo a "Seleccionar".
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

7. GUARDAR COMO EN LOS EDITORES (decision del Disenador, sept-2026). La primera
   vez, Guardar (Ctrl+S) pregunta el nombre de la copia ("-devolucion"). Despues
   guarda encima de esa misma copia sin preguntar. "Guardar como..."
   (Ctrl+Shift+S) pregunta siempre. Una devolucion reabierta se guarda encima de
   si misma. El PDF original nunca se toca.

8. LA BARRA ESPACIADORA NO HACE NADA (decision del Disenador, sept-2026): ni
   pasar de pagina ni arrastrar la hoja. Para eso estan Av Pag / Re Pag, la
   rueda y la ruedita apretada.

9. LA LETRA SUBRAYADA DE CADA HERRAMIENTA ES SU ATAJO (S, D, T, B; en ingles
   S, D, T, E). Anda la letra sola y tambien Alt + letra, como en Windows.
   Seleccionar va primero en la barra: es la de entrada.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

# El modulo de idiomas se importa aparte y ANTES del bloque de abajo: no depende
# de nada que pueda faltar (solo de 'os'), asi que hasta los carteles de "no pudo
# arrancar" pueden salir en el idioma elegido. Todo el texto que ve el usuario
# sale de aca: el programa nunca escribe un cartel a mano (ver idiomas.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idiomas
from idiomas import t

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
    carpeta vacia y no apareceria el PDF que se acaba de bajar.
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


# Carpeta con la que arranca la lista. main() la cambia por la ultima que se
# uso (ver carpeta_recordada); el autotest, que no pasa por main(), arranca
# siempre en Descargas y nunca pisa la carpeta que dejo elegida el usuario.
CARPETA_INICIAL = _carpeta_descargas()
# Solo main() lo pone en True: recien ahi se escribe la carpeta elegida.
RECORDAR_CARPETA = False


def _archivo_carpeta():
    """Donde se recuerda la ultima carpeta: al lado del idioma y del registro
    de errores, en la carpeta de datos del usuario (Program Files es de solo
    lectura)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "LectorPDF", "carpeta.txt")


def carpeta_recordada():
    """La ultima carpeta usada, o None si no hay o ya no existe (un pendrive
    que se saco, una carpeta borrada): en ese caso se vuelve a Descargas sin
    ningun cartel."""
    try:
        with open(_archivo_carpeta(), encoding="utf-8") as f:
            ruta = f.read().strip()
        return ruta if ruta and os.path.isdir(ruta) else None
    except OSError:
        return None


def recordar_carpeta(ruta):
    """Anota la carpeta elegida para abrir ahi la proxima vez."""
    if not RECORDAR_CARPETA:
        return
    try:
        os.makedirs(os.path.dirname(_archivo_carpeta()), exist_ok=True)
        with open(_archivo_carpeta(), "w", encoding="utf-8") as f:
            f.write(ruta)
    except OSError:
        pass

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
# Aire arriba y abajo de la hoja dentro del visor, en pixeles de pantalla. Sin
# esto la hoja queda pegada al borde y cuesta ver donde empieza y termina; un
# poco de colchon la despega y se lee mas comoda.
CUSHION_HOJA = 26
# Cursor de cada herramienta. Un solo lugar: antes estaba copiado en cuatro
# metodos y era facil que uno quedara distinto.
CURSORES = {"dibujar": "pencil", "texto": "xterm", "seleccionar": "arrow",
            "borrar": "dotbox"}
# La "manito" que agarra la hoja al arrastrarla con la ruedita apretada, como la
# mano cerrada de Acrobat. Windows no trae ese cursor, asi que viaja con el
# programa (mano.cur). Va entre llaves porque la ruta tiene espacios ("Program
# Files") y Tk la partiria. Si el archivo faltara, queda la cruz de mover.
_RUTA_MANO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mano.cur")
CURSOR_MANO = ("{@%s}" % _RUTA_MANO.replace("\\", "/")) if os.path.isfile(_RUTA_MANO) else "fleur"
# Herramientas en el orden de la barra: Seleccionar primero, que es la de
# entrada (Figma, tldraw, Excalidraw, Office). La letra subrayada del nombre es
# el atajo, asi que el atajo sale del texto del boton en el idioma activo.
HERRAMIENTAS = ("seleccionar", "dibujar", "texto", "borrar")
# Manijas de una nota elegida: 4 esquinas y 4 costados, como en cualquier
# editor. Todas cambian el TAMANO DE LA CAJA (nunca la letra: eso va en el
# panel). Mientras se arrastra, la caja mide exacto lo pedido; al soltar se
# ajusta al texto (decision del Disenador, sept-2026).
MANIJAS_ESQUINA = ("ai", "ad", "bi", "bd")      # arriba/abajo + izquierda/derecha
MANIJAS_COSTADO = ("izq", "der", "arr", "abj")


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


def _cerca_del_trazo(px, py, trazos, margen):
    """True si el punto (px, py) esta a menos de 'margen' de algun tramo del trazo.

    Es la prueba de "clic sobre un dibujo": se mide la distancia a la linea
    dibujada, no al recuadro que la envuelve.
    """
    m2 = margen * margen
    for trazo in trazos:
        if len(trazo) == 1:
            (x, y), = trazo
            if (px - x) ** 2 + (py - y) ** 2 <= m2:
                return True
        for (x0, y0), (x1, y1) in zip(trazo, trazo[1:]):
            dx, dy = x1 - x0, y1 - y0
            largo2 = dx * dx + dy * dy
            u = 0.0 if largo2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / largo2))
            cx, cy = x0 + u * dx, y0 + u * dy
            if (px - cx) ** 2 + (py - cy) ** 2 <= m2:
                return True
    return False


class Globito:
    """Cartel de ayuda que aparece al dejar el mouse quieto sobre un control.

    Dice que hace el boton y su atajo de teclado ("Dibujar (D)"). El texto se
    pide a idiomas.py en el momento de mostrarlo, asi sale en el idioma activo.
    Antes no habia ninguno: los cinco colores eran botones sin texto.
    """

    def __init__(self, widget, clave):
        self.widget, self.clave = widget, clave
        self._espera = None
        self._ventana = None
        widget.bind("<Enter>", self._programar, add="+")
        widget.bind("<Leave>", self._ocultar, add="+")
        widget.bind("<ButtonPress>", self._ocultar, add="+")

    def _programar(self, _e=None):
        self._cancelar()
        self._espera = self.widget.after(550, self._mostrar)

    def _cancelar(self):
        if self._espera is not None:
            try:
                self.widget.after_cancel(self._espera)
            except Exception:
                pass
            self._espera = None

    def _mostrar(self):
        self._espera = None
        try:
            x = self.widget.winfo_rootx() + 6
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self._ventana = tk.Toplevel(self.widget)
            self._ventana.wm_overrideredirect(True)
            self._ventana.wm_geometry("+%d+%d" % (x, y))
            tk.Label(self._ventana, text=t(self.clave), bg="#FFFFE6", fg="#1F2328",
                     relief="solid", bd=1, font=("Segoe UI", 9), padx=7, pady=3).pack()
        except Exception:
            self._ventana = None

    def _ocultar(self, _e=None):
        self._cancelar()
        if self._ventana is not None:
            try:
                self._ventana.destroy()
            except Exception:
                pass
            self._ventana = None


def atajo_de(modo):
    """La letra que elige una herramienta: la primera de su nombre, que es la
    que va subrayada en el boton ("Seleccionar" -> s; en ingles "Erase" -> e)."""
    return t("modo_" + modo)[:1].lower()


# Sufijos que puede traer el nombre de una devolucion (espanol e ingles): se
# sacan antes de proponer el nombre nuevo, asi no queda "-devolucion-feedback".
SUFIJOS_DEVOLUCION = ("-devolucion", "-feedback")


def ruta_libre(carpeta, base):
    """Devuelve una ruta que no existe, numerando: -devolucion, -devolucion-2, ...

    El sufijo va en el idioma de la interfaz (en ingles, -feedback).
    Numerado, nunca "final" ni "corregido": la version mas alta es la ultima.
    """
    sufijo = t("sufijo_devolucion")
    cand = os.path.join(carpeta, "%s-%s.pdf" % (base, sufijo))
    n = 2
    while os.path.exists(cand):
        cand = os.path.join(carpeta, "%s-%s-%d.pdf" % (base, sufijo, n))
        n += 1
    return cand


# =============================================================== biblioteca ==

class Biblioteca(ttk.Frame):
    """Pantalla inicial: los PDFs de una carpeta, el mas nuevo primero.

    Arranca en la ultima carpeta usada (la primera vez, Descargas). "Cambiar
    carpeta..." elige otra y queda recordada. Se puede filtrar escribiendo,
    ordenar tocando el titulo de una columna, o abrir un PDF de cualquier lado
    con "Abrir archivo...".
    """

    def __init__(self, app):
        super().__init__(app.contenedor)
        self.app = app
        self.carpeta = CARPETA_INICIAL
        self.archivos = []              # rutas, en el orden en que se ven
        self._entradas = []             # (ruta, nombre, fecha, tamano) de la carpeta
        self._orden = ("fecha", True)   # columna y si va de mayor a menor
        self._construir()
        self.refrescar()

    def _construir(self):
        """Arma los widgets. Aparte del __init__ para poder rehacerlos al cambiar
        de idioma sin perder la carpeta que se estaba mirando (ver retraducir)."""
        barra = ttk.Frame(self, padding=(12, 10))
        barra.pack(fill="x")
        self.lbl = ttk.Label(barra, text="", font=("Segoe UI", 14, "bold"))
        self.lbl.pack(side="left")
        # Boton para pasar de espanol a ingles y al reves.
        ttk.Button(barra, text=t("boton_idioma"),
                   command=self.app.cambiar_idioma).pack(side="right", padx=(6, 0))
        ttk.Button(barra, text=t("bib_abrir_archivo"),
                   command=self.app.abrir_archivo).pack(side="right")
        ttk.Button(barra, text=t("bib_otra_carpeta"),
                   command=self.elegir_carpeta).pack(side="right", padx=6)
        ttk.Button(barra, text=t("bib_actualizar"),
                   command=lambda: self.refrescar(self._ruta_elegida())).pack(side="right")

        # Filtro: se escribe y la lista muestra solo los nombres que lo tienen.
        fila = ttk.Frame(self, padding=(12, 0, 12, 6))
        fila.pack(fill="x")
        ttk.Label(fila, text=t("bib_filtrar")).pack(side="left")
        self.filtro = tk.StringVar()
        entrada = ttk.Entry(fila, textvariable=self.filtro, width=40)
        entrada.pack(side="left", padx=(6, 0))
        entrada.bind("<Down>", lambda e: (self.tabla.focus_set(), "break")[1])
        entrada.bind("<Return>", lambda e: self.abrir_seleccion())

        cuerpo = ttk.Frame(self, padding=(12, 0, 12, 8))
        cuerpo.pack(fill="both", expand=True)
        cols = ("nombre", "fecha", "tamano")
        self.tabla = ttk.Treeview(cuerpo, columns=cols, show="headings", selectmode="browse")
        for col in cols:
            self.tabla.heading(col, command=lambda c=col: self._ordenar_por(c))
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
        ttk.Button(pie, text=t("bib_abrir"), command=self.abrir_seleccion).pack(side="right")
        # El filtro se engancha al final, cuando la tabla ya existe.
        self.filtro.trace_add("write", lambda *_: self._poblar())

    def retraducir(self):
        """Rehace los widgets en el idioma nuevo, conservando carpeta, filtro y
        el archivo elegido."""
        carpeta, filtro, elegido = self.carpeta, self.filtro.get(), self._ruta_elegida()
        for w in list(self.winfo_children()):
            w.destroy()
        self._construir()
        self.carpeta = carpeta
        self.filtro.set(filtro)
        self.refrescar(seleccionar=elegido)

    def elegir_carpeta(self):
        c = filedialog.askdirectory(initialdir=self.carpeta, title=t("bib_elegir_carpeta_titulo"))
        if c:
            self.cambiar_carpeta(c)

    def cambiar_carpeta(self, carpeta, seleccionar=None):
        """Pasa a mostrar otra carpeta y la recuerda para la proxima vez."""
        self.carpeta = os.path.normpath(carpeta)
        recordar_carpeta(self.carpeta)
        self.refrescar(seleccionar=seleccionar)
        self.app.actualizar_titulo()

    def refrescar(self, seleccionar=None):
        # En la raiz de un disco ("D:\") el nombre de la carpeta queda vacio:
        # ahi se muestra la ruta entera (antes decia "PDFs en " y nada mas).
        nombre = os.path.basename(self.carpeta.rstrip("\\/")) or self.carpeta
        self.lbl.config(text=t("bib_pdfs_en") % nombre)
        entradas = []
        try:
            with os.scandir(self.carpeta) as it:
                for e in it:
                    if e.is_file() and e.name.lower().endswith(".pdf"):
                        try:
                            st = e.stat()
                        except OSError:
                            continue
                        entradas.append((e.path, e.name, st.st_mtime, st.st_size))
        except OSError as err:
            self._entradas = []
            self._poblar()
            self.estado.config(text=t("bib_no_leer_carpeta") % err)
            return
        self._entradas = entradas
        self._poblar(seleccionar)

    def _ordenar_por(self, col):
        """Clic en el titulo de una columna: ordena por ella; otro clic, al reves."""
        actual, desc = self._orden
        self._orden = (col, (not desc) if col == actual else col != "nombre")
        self._poblar(self._ruta_elegida())

    def _ruta_elegida(self):
        sel = self.tabla.selection()
        if not sel:
            return None
        idx = self.tabla.index(sel[0])
        return self.archivos[idx] if 0 <= idx < len(self.archivos) else None

    def _poblar(self, seleccionar=None):
        """Vuelca en la tabla las entradas que pasan el filtro, en el orden elegido."""
        import datetime
        for i in self.tabla.get_children():
            self.tabla.delete(i)
        filtro = self.filtro.get().strip().lower()
        filas = [e for e in self._entradas if filtro in e[1].lower()]
        col, desc = self._orden
        clave = {"nombre": lambda e: e[1].lower(), "fecha": lambda e: e[2],
                 "tamano": lambda e: e[3]}[col]
        filas.sort(key=clave, reverse=desc)
        flecha = " \u25BC" if desc else " \u25B2"
        for c, k in (("nombre", "col_archivo"), ("fecha", "col_modificado"),
                     ("tamano", "col_tamano")):
            self.tabla.heading(c, text=t(k) + (flecha if c == col else ""))
        self.archivos = []
        for ruta, nombre, mtime, size in filas:
            fecha = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
            self.tabla.insert("", "end", values=(nombre, fecha, tamano_legible(size)))
            self.archivos.append(ruta)

        if self.archivos:
            # Al volver de un PDF, queda elegido el que se estaba mirando.
            # misma_ruta: el dialogo de Windows devuelve la ruta con "/" y la
            # lista la tiene con "\": comparadas como texto no coincidian.
            idx = next((k for k, r in enumerate(self.archivos)
                        if seleccionar and A.misma_ruta(r, seleccionar)), 0)
            item = self.tabla.get_children()[idx]
            self.tabla.selection_set(item)
            self.tabla.focus(item)
            self.tabla.see(item)
            if not filtro:
                self.tabla.focus_set()
            if len(filas) < len(self._entradas):
                self.estado.config(text=t("bib_cuenta_filtrados")
                                   % (len(filas), len(self._entradas)))
            else:
                self.estado.config(text=t("bib_cuenta") % len(self.archivos))
        else:
            self.estado.config(text=t("bib_sin_pdfs") if not self._entradas
                               else t("bib_sin_coincidencias"))

    def abrir_seleccion(self):
        ruta = self._ruta_elegida()
        if ruta:
            self.app.abrir_pdf(ruta)


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
            raise ValueError(t("v_pdf_sin_paginas"))
        self.pno = 0
        self.zoom = 1.0
        # Por defecto se ve la hoja ENTERA, no ajustada al ancho: en un monitor
        # ancho, "ajustar al ancho" agranda tanto la pagina que cada una ocupa
        # dos pantallas y media de scroll. Para revisar un documento de 14 paginas
        # conviene ver la hoja completa y pasar de pagina; el que quiera leer
        # letra grande tiene el boton "Ancho".
        self.modo_zoom = "pagina"          # "pagina" | "ancho" | "libre"
        self.ox = 0                 # corrimiento horizontal para centrar la hoja
        self.oy = CUSHION_HOJA      # colchon vertical arriba de la hoja
        self.ver_marcas = True      # el "ojito": mostrar u ocultar las marcas propias
        self.modo = "seleccionar"
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
        self._rts = None            # recuadro de seleccion por area (boton derecho)
        self._redimensionando = None  # nota a la que se le mueve una manija
        self._cajas_notas = {}      # indice -> caja de cada nota tal como se dibujo
        self._nota_arrastre = None  # modo Texto: arrastre que elige el ancho de la nota
        self._borrando = None       # modo Borrar: pasada del borrador en curso
        # A donde guarda Ctrl+S sin preguntar (decision 7). Una devolucion
        # reabierta se guarda encima de si misma; un PDF original, nunca: la
        # primera vez se pregunta el nombre de la copia.
        self.ruta_guardado = ruta if A.es_devolucion(self.doc) else None
        # Letra de las notas nuevas: la de la ultima nota del PDF (asi se
        # recuerda al reabrir); si no hay, la de entrada.
        notas = [m for p in sorted(self.marcas) for m in self.marcas[p] if m["tipo"] == "texto"]
        self.cuerpo_nuevas = (notas[-1].get("cuerpo") if notas else None) or A.CUERPO_NOTA
        # Estado del cuadro de escribir y de otras cosas de paso. Se declaran
        # aca para que ninguna funcion dependa de que otra las haya creado antes.
        self._editor_nombre = ""
        self._editor_ancla = None
        self._editor_original = None
        self._editor_color = self.color
        self._editor_ancho = None
        self._editor_cuerpo = None
        self._editor_alto = None      # alto elegido arrastrando con Texto (puntos PDF)
        self._editor_fijo = False     # el ancho del cuadro lo eligio el usuario
        self._medidor = None        # cuadro escondido que mide los renglones de la nota
        self._editor_fuente = None
        self._cursor_actual = CURSORES[self.modo]
        self._ultimo_salto = (0, 0.0)   # (direccion, momento) del ultimo salto con la rueda
        self._region = (0, 0)           # tamano total del area desplazable
        self._clave_imagen = None
        self._tam_imagen = (0, 0)
        self._busqueda = {"q": None, "aciertos": [], "i": -1}
        self.dialogo_guardado = None
        # Estado con el que quedo el archivo en disco: todo lo que difiera
        # de esto es un cambio sin guardar.
        self.firma_guardada = self._firma()

        self._construir_widgets()
        self._actualizar_pie()

    def _construir_widgets(self):
        """Arma barra, panel, visor y pie. Aparte del __init__ para poder
        rehacerlos al cambiar de idioma sin cerrar el PDF ni perder las marcas
        (ver retraducir): las etiquetas de Tkinter se crean una sola vez, asi que
        cambiar de idioma es rehacer los widgets con el texto nuevo."""
        self._armar_barra()
        self._armar_busqueda()

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        self.cuerpo = cuerpo
        # El panel de propiedades se arma ahora pero no se muestra: aparece solo
        # cuando hay algo seleccionado, para no comerle ancho a la hoja.
        self.panel = self._armar_panel(cuerpo)
        self.canvas = tk.Canvas(cuerpo, bg=FONDO_CANVAS, highlightthickness=0, cursor="arrow")
        self.vsb = ttk.Scrollbar(cuerpo, orient="vertical", command=self.canvas.yview)
        # Barra horizontal: aparece sola cuando la hoja es mas ancha que la
        # ventana (antes solo se podia ir de costado con Shift+rueda).
        self.hsb = ttk.Scrollbar(cuerpo, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self._mover_hsb)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Barra de estado de abajo. En reposo queda VACIA (pedido del
        # Disenador: "Seleccionar / N marca(s)" era texto innecesario; lo que
        # falta guardar ya lo dice el asterisco del titulo, como en cualquier
        # programa). Solo habla cuando hay que seguir un paso ("Hace clic donde
        # quieras la nota...") o para confirmar algo ("Guardado en...").
        pie_barra = ttk.Frame(self)
        pie_barra.pack(fill="x")
        self.pie = ttk.Label(pie_barra, text="", padding=(10, 4), foreground="#333")
        self.pie.pack(side="left", fill="x")

        self.canvas.bind("<Configure>", self._al_redimensionar)
        self.canvas.bind("<ButtonPress-1>", self._click)
        self.canvas.bind("<B1-Motion>", self._arrastre)
        self.canvas.bind("<ButtonRelease-1>", self._soltar)
        self.canvas.bind("<Double-Button-1>", self._doble_click)
        self.canvas.bind("<Motion>", self._al_mover_mouse)
        self.canvas.bind("<MouseWheel>", self._rueda)
        self.canvas.bind("<Shift-MouseWheel>", self._rueda_horizontal)
        self.canvas.bind("<ButtonPress-2>", self._pan_inicio)
        self.canvas.bind("<B2-Motion>", self._pan_mover)
        self.canvas.bind("<ButtonRelease-2>", self._pan_fin)
        # Boton derecho: recuadro de seleccion por area (estilo RTS), en
        # cualquier modo, sin tener que pasar antes a Seleccionar.
        self.canvas.bind("<ButtonPress-3>", self._rts_inicio)
        self.canvas.bind("<B3-Motion>", self._rts_mover)
        self.canvas.bind("<ButtonRelease-3>", self._rts_soltar)
        self.canvas.focus_set()

    def _mover_hsb(self, primero, ultimo):
        """La barra horizontal se muestra solo si hace falta."""
        self.hsb.set(primero, ultimo)
        hace_falta = float(primero) > 0.0 or float(ultimo) < 1.0
        if hace_falta and not self.hsb.winfo_ismapped():
            self.hsb.pack(side="bottom", fill="x", before=self.canvas)
        elif not hace_falta and self.hsb.winfo_ismapped():
            self.hsb.pack_forget()

    def retraducir(self):
        """Rehace los widgets en el idioma nuevo sin cerrar el PDF ni tocar las
        marcas. Conserva la altura de lectura, el modo activo y la seleccion."""
        self._cerrar_editor(confirmar=True)
        y = self.canvas.yview()[0]
        modo = self.modo
        seleccion = list(self.seleccion)
        palabras_sel = self.palabras_sel
        texto_sel = self._texto_sel
        for w in list(self.winfo_children()):
            w.destroy()
        self._construir_widgets()
        self.modo = modo
        self._aplicar_cursor()
        self.seleccion = seleccion
        self.palabras_sel = palabras_sel
        self._texto_sel = texto_sel
        self._pintar_botones()
        self.render(y)
        self._refrescar_panel()

    # ------------------------------------------------------------- barra ----

    def _boton(self, padre, texto, comando, ancho=None, tip=None, **kw):
        """Boton de la barra. Todos del mismo tipo (antes se mezclaban dos
        estilos), ninguno toma el foco del teclado (si lo tomaba, Espacio o
        Enter lo volvian a apretar) y cada uno con su cartel."""
        bt = tk.Button(padre, text=texto, command=comando, takefocus=0, **kw)
        if ancho:
            bt.config(width=ancho)
        if tip:
            Globito(bt, tip)
        return bt

    def _armar_barra(self):
        b = ttk.Frame(self, padding=(8, 6))
        b.pack(fill="x")
        self.barra = b
        B = self._boton

        # Lo de la derecha se empaqueta PRIMERO: en una pantalla angosta, lo que
        # se corta es lo ultimo empaquetado, y Guardar no se puede perder.
        # Guardar es un boton partido, como en Office: el grande guarda, la
        # flechita al lado ofrece "Guardar como...".
        self.btn_guardar_mas = B(b, "▼", self._menu_guardar, 2, "tip_guardar_mas",
                                 font=("Segoe UI", 7))
        self.btn_guardar_mas.pack(side="right")
        self.btn_guardar = B(b, t("v_guardar"), self.guardar, 10, "tip_guardar",
                             font=("Segoe UI", 9, "bold"))
        self.btn_guardar.pack(side="right")
        B(b, "?", self.mostrar_ayuda, 3, "tip_ayuda",
          font=("Segoe UI", 10, "bold")).pack(side="right", padx=6)
        # Boton para pasar de espanol a ingles y al reves.
        B(b, t("boton_idioma"), self.app.cambiar_idioma, 8,
          "tip_idioma").pack(side="right", padx=(0, 6))

        B(b, t("v_carpeta"), self.app.volver_biblioteca, 10, "tip_carpeta").pack(side="left")
        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)

        # Herramientas: Seleccionar primero, y la primera letra subrayada, que
        # es su atajo (decision 9).
        self.btn_modo = {}
        for clave in HERRAMIENTAS:
            bt = B(b, t("modo_" + clave), lambda c=clave: self.set_modo(c),
                   11 if clave == "seleccionar" else 8, "tip_" + clave,
                   relief="raised", underline=0)
            bt.pack(side="left", padx=2)
            self.btn_modo[clave] = bt

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        self.btn_color = []
        for nombre, col in COLORES:
            bt = B(b, "", lambda c=col: self.set_color(c), 3, "color_" + nombre.lower(),
                   bg=a_hex(col), activebackground=a_hex(col), relief="raised", bd=2)
            bt.pack(side="left", padx=1)
            self.btn_color.append((bt, col))

        self.btn_grosor = B(b, t("v_grueso"), self.toggle_grosor, 7, "tip_grueso")
        self.btn_grosor.pack(side="left", padx=(8, 2))
        B(b, t("v_deshacer"), self.deshacer, 9, "tip_deshacer").pack(side="left", padx=2)
        B(b, t("v_rehacer"), self.rehacer, 9, "tip_rehacer").pack(side="left")

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        B(b, "-", lambda: self.set_zoom(self.zoom / 1.2), 3, "tip_alejar").pack(side="left")
        self.btn_pagina = B(b, t("v_pagina"), self.zoom_pagina, 7, "tip_pagina")
        self.btn_pagina.pack(side="left", padx=2)
        self.btn_ancho = B(b, t("v_ancho"), self.zoom_ancho, 7, "tip_ancho")
        self.btn_ancho.pack(side="left")
        B(b, "+", lambda: self.set_zoom(self.zoom * 1.2), 3, "tip_acercar").pack(side="left", padx=2)
        # Cuanto zoom hay (100% = tamano real). Antes no habia forma de saberlo.
        self.lbl_zoom = ttk.Label(b, text="", width=5, anchor="w")
        self.lbl_zoom.pack(side="left", padx=(2, 0))
        Globito(self.lbl_zoom, "tip_zoom")
        # Ocultar marcas: con lo demas de "ver", arriba (antes era un ojito en
        # la barra de abajo, donde ningun programa lo pone). El texto dice lo
        # que hace el boton; apretado queda hundido y de color, y pasa a decir
        # "Mostrar marcas" (ver _pintar_ojo). Ancho fijo: no mueve la barra.
        ancho_ojo = max(len(t("ojo_ocultar")), len(t("ojo_mostrar"))) + 2
        self.btn_ojo = B(b, t("ojo_ocultar"), self.toggle_ver_marcas, ancho_ojo, "tip_ojo")
        self.btn_ojo.pack(side="left", padx=(6, 0))

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        B(b, "<", lambda: self.ir_pagina(self.pno - 1), 3, "tip_anterior").pack(side="left")
        # El numero de pagina se puede escribir: en un documento de 40 paginas,
        # llegar a la 27 a flechazos es una perdida de tiempo.
        self.entrada_pag = tk.Entry(b, width=4, justify="center", relief="flat",
                                    bg=FONDO_BARRA)
        self.entrada_pag.pack(side="left")
        self.entrada_pag.bind("<Return>", self._saltar_a_pagina)
        self.entrada_pag.bind("<FocusOut>", lambda e: self._actualizar_numero())
        Globito(self.entrada_pag, "tip_num_pagina")
        self.lbl_total = ttk.Label(b, text="", width=6, anchor="w")
        self.lbl_total.pack(side="left")
        B(b, ">", lambda: self.ir_pagina(self.pno + 1), 3, "tip_siguiente").pack(side="left")

        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=8)
        B(b, t("v_buscar"), self.abrir_busqueda, 8, "tip_buscar").pack(side="left")

        self._pintar_botones()

    # ---------------------------------------------------------------- buscar --

    def _armar_busqueda(self):
        """Barra de buscar (Ctrl+F). Se arma escondida y aparece debajo de la
        barra de herramientas. Lo encontrado queda elegido como texto del
        documento, asi se lo puede comentar o dibujar encima de una."""
        f = ttk.Frame(self, padding=(8, 0, 8, 6))
        ttk.Label(f, text=t("buscar_etiqueta")).pack(side="left")
        self.entrada_buscar = ttk.Entry(f, width=36)
        self.entrada_buscar.pack(side="left", padx=6)
        self.entrada_buscar.bind("<Return>", lambda e: (self.buscar(1), "break")[1])
        self.entrada_buscar.bind("<Shift-Return>", lambda e: (self.buscar(-1), "break")[1])
        self.entrada_buscar.bind("<Escape>", lambda e: (self.cerrar_busqueda(), "break")[1])
        B = self._boton
        B(f, "\u25B2", lambda: self.buscar(-1), 3, "tip_buscar_anterior").pack(side="left")
        B(f, "\u25BC", lambda: self.buscar(1), 3, "tip_buscar_siguiente").pack(side="left", padx=(2, 0))
        self.lbl_buscar = ttk.Label(f, text="", foreground="#555")
        self.lbl_buscar.pack(side="left", padx=10)
        B(f, "\u2715", self.cerrar_busqueda, 3, "tip_buscar_cerrar").pack(side="right")
        self.barra_busqueda = f

    def abrir_busqueda(self):
        # winfo_manager y no winfo_ismapped: "esta abierta" no depende de que
        # la ventana ya se haya redibujado.
        if not self.barra_busqueda.winfo_manager():
            self.barra_busqueda.pack(fill="x", before=self.cuerpo)
        # Si hay una frase corta elegida, se propone buscarla.
        if self._texto_sel and len(self._texto_sel) <= 80:
            self.entrada_buscar.delete(0, "end")
            self.entrada_buscar.insert(0, self._texto_sel)
        self.entrada_buscar.focus_set()
        self.entrada_buscar.select_range(0, "end")

    def cerrar_busqueda(self):
        self.barra_busqueda.pack_forget()
        self.canvas.focus_set()

    def buscar(self, direccion=1):
        """Va a la siguiente (o anterior) aparicion del texto buscado."""
        q = self.entrada_buscar.get().strip() if self.barra_busqueda.winfo_manager() \
            else (self._busqueda["q"] or "")
        if not q:
            self.abrir_busqueda()
            return
        b = self._busqueda
        if q != b["q"]:
            aciertos = []
            for pno in range(self.doc.page_count):
                for r in self.doc[pno].search_for(q):
                    aciertos.append((pno, pymupdf.Rect(r)))
            b.update(q=q, aciertos=aciertos, i=-1)
            # Arranca desde la pagina que se esta mirando, no desde la primera.
            if aciertos and direccion > 0:
                desde = [k for k, (p, _r) in enumerate(aciertos) if p >= self.pno]
                b["i"] = (desde[0] if desde else 0) - 1
        aciertos = b["aciertos"]
        if not aciertos:
            self.lbl_buscar.config(text=t("buscar_sin_resultados"))
            return
        b["i"] = (b["i"] + direccion) % len(aciertos)
        pno, r = aciertos[b["i"]]
        if pno != self.pno:
            self.ir_pagina(pno)
        self.seleccion = []
        self.palabras_sel = [r]
        self._texto_sel = self._pagina().get_textbox(r).strip() or q
        # Que lo encontrado quede a un tercio de la altura de la ventana.
        _ancho, alto = self._region
        y = r.y0 * self.zoom + self.oy - self.canvas.winfo_height() / 3.0
        self.render(max(0.0, y) / alto if alto else 0.0)
        self._refrescar_panel()
        self.lbl_buscar.config(text=t("buscar_n_de_m") % (b["i"] + 1, len(aciertos)))

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
        # El subtexto (pagina, caracteres, cita) no se muestra: era ruido.

        # --- con texto del documento elegido -----------------------------------
        self.pnl_texto_pdf = tk.Frame(p, bg="#F4F6F8")
        tk.Button(self.pnl_texto_pdf, text=t("pnl_comentar"),
                  font=("Segoe UI", 9, "bold"),
                  command=self.comentar_seleccion).pack(fill="x", pady=(0, 3))
        tk.Button(self.pnl_texto_pdf, text=t("pnl_dibujar_sobre"),
                  command=self.dibujar_sobre_seleccion).pack(fill="x")

        # --- nombre interno --------------------------------------------------
        self.pnl_nombre_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_nombre_bloque, text=t("pnl_nombre_interno"), bg="#F4F6F8",
                 fg="#7A828C", anchor="w",
                 font=("Segoe UI", 7, "bold")).pack(fill="x")
        fila_n = tk.Frame(self.pnl_nombre_bloque, bg="#F4F6F8")
        fila_n.pack(fill="x", pady=(1, 0))
        self.pnl_nombre = tk.Entry(fila_n, font=("Consolas", 9))
        self.pnl_nombre.pack(side="left", fill="x", expand=True)
        self.pnl_nombre.bind("<Return>", lambda e: self._renombrar())
        tk.Button(fila_n, text=t("pnl_ok"), width=3,
                  command=self._renombrar).pack(side="left", padx=(4, 0))

        # --- referencia ------------------------------------------------------
        self.pnl_ref_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_ref_bloque, text=t("pnl_referencia_a"), bg="#F4F6F8", fg="#7A828C",
                 anchor="w", font=("Segoe UI", 7, "bold")).pack(fill="x")
        self.pnl_ref = tk.Entry(self.pnl_ref_bloque, font=("Segoe UI", 8),
                                state="readonly", readonlybackground="#ECEDEE")
        self.pnl_ref.pack(fill="x", pady=(1, 3))
        fila_r = tk.Frame(self.pnl_ref_bloque, bg="#F4F6F8")
        fila_r.pack(fill="x")
        self.btn_elegir_ref = tk.Button(fila_r, text=t("pnl_elegir"),
                                        command=self.elegir_referencia)
        self.btn_elegir_ref.pack(side="left", fill="x", expand=True)
        self.btn_quitar_ref = tk.Button(fila_r, text=t("pnl_quitar"),
                                        command=self.soltar_ancla)
        self.btn_quitar_ref.pack(side="left", fill="x", expand=True, padx=(3, 0))

        # --- color -----------------------------------------------------------
        self.pnl_color_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_color_bloque, text=t("pnl_color"), bg="#F4F6F8", fg="#7A828C",
                 anchor="w", font=("Segoe UI", 7, "bold")).pack(fill="x")
        fila_c = tk.Frame(self.pnl_color_bloque, bg="#F4F6F8")
        fila_c.pack(fill="x", pady=(2, 0))
        for _n, col in COLORES:
            tk.Button(fila_c, width=3, bg=a_hex(col), activebackground=a_hex(col),
                      relief="raised", bd=2,
                      command=lambda c=col: self._cambiar_color(c)).pack(side="left", padx=1)

        # --- tamano de letra (solo notas) ---------------------------------------
        self.pnl_letra_bloque = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_letra_bloque, text=t("pnl_letra_titulo"), bg="#F4F6F8",
                 fg="#7A828C", anchor="w", font=("Segoe UI", 7, "bold")).pack(fill="x")
        self.pnl_letra = ttk.Spinbox(self.pnl_letra_bloque, from_=A.CUERPO_MIN,
                                     to=A.CUERPO_MAX, increment=1, width=6,
                                     command=self._cambiar_letra)
        self.pnl_letra.pack(anchor="w", pady=(2, 0))
        self.pnl_letra.bind("<Return>", self._cambiar_letra)
        self.pnl_letra.bind("<FocusOut>", self._cambiar_letra)

        # --- grosor ----------------------------------------------------------
        self.pnl_grosor = tk.Frame(p, bg="#F4F6F8")
        tk.Label(self.pnl_grosor, text=t("pnl_grosor_titulo"), bg="#F4F6F8", fg="#7A828C", anchor="w",
                 font=("Segoe UI", 7, "bold")).pack(fill="x")
        fila_g = tk.Frame(self.pnl_grosor, bg="#F4F6F8")
        fila_g.pack(fill="x", pady=(2, 0))
        for etiqueta, valor in ((t("grosor_fino"), GROSOR_FINO), (t("grosor_medio"), 4.0),
                                (t("grosor_grueso"), GROSOR_GRUESO)):
            tk.Button(fila_g, text=etiqueta, width=7,
                      command=lambda v=valor: self._cambiar_grosor(v)).pack(side="left", padx=1)

        # --- acciones ---------------------------------------------------------
        self.pnl_acciones = tk.Frame(p, bg="#F4F6F8")
        self.btn_editar_nota = tk.Button(self.pnl_acciones, text=t("pnl_editar_texto"),
                                         command=self._editar_nota_seleccionada)
        self.btn_unificar = tk.Button(self.pnl_acciones, text=t("pnl_unificar"),
                                      command=self._unificar)
        self.btn_borrar = tk.Button(self.pnl_acciones, text=t("pnl_borrar"),
                                    command=self._borrar_seleccion)
        self.btn_soltar = tk.Button(self.pnl_acciones, text=t("pnl_soltar"),
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
            return t("ref_la_frase") % ancla["cita"][:70]
        if mk.get("ref"):
            return t("ref_la_marca") % mk["ref"]
        return ""

    def _refrescar_panel(self):
        """Vuelca en el panel lo que hay elegido ahora mismo."""
        for w in (self.pnl_texto_pdf, self.pnl_nombre_bloque, self.pnl_ref_bloque,
                  self.pnl_color_bloque, self.pnl_letra_bloque, self.pnl_grosor,
                  self.pnl_acciones):
            w.pack_forget()
        for b in (self.btn_editar_nota, self.btn_unificar, self.btn_borrar, self.btn_soltar):
            b.pack_forget()

        marcas = self._marcas_seleccionadas()
        if not marcas and not self._texto_sel:
            self._mostrar_panel(False)
            return
        self._mostrar_panel(True)

        # --- texto del documento elegido: todavia no es una marca ---------------
        if not marcas:
            self.pnl_titulo.config(text=t("pnl_texto_manual"))
            self.pnl_datos.config(text=t("pnl_caracteres_cita")
                                  % (len(self._texto_sel), self._texto_sel[:150]))
            self.pnl_texto_pdf.pack(fill="x", padx=12, pady=(2, 0))
            return

        # --- una o varias marcas ---------------------------------------------
        uno = marcas[0] if len(marcas) == 1 else None
        if uno is not None:
            r = self._bbox(uno)
            if uno["tipo"] == "lapiz":
                self.pnl_titulo.config(text=t("pnl_dibujo_mano"))
                self.pnl_datos.config(
                    text=t("pnl_datos_dibujo")
                    % (self.pno + 1, len(uno["trazos"]),
                       sum(len(tr) for tr in uno["trazos"]), r.width, r.height))
            else:
                self.pnl_titulo.config(text=t("pnl_nota_escrita"))
                self.pnl_datos.config(
                    text=t("pnl_datos_nota")
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
            self.pnl_ref.insert(0, ref if ref else t("pnl_ninguna"))
            self.pnl_ref.config(state="readonly",
                                readonlybackground="#FFF6C9" if ref else "#ECEDEE")
            self.btn_quitar_ref.config(state="normal" if ref else "disabled")
            self.pnl_ref_bloque.pack(fill="x", padx=12, pady=(0, 10))
        else:
            dibujos = sum(1 for m in marcas if m["tipo"] == "lapiz")
            self.pnl_titulo.config(text=t("pnl_n_marcas") % len(marcas))
            self.pnl_datos.config(text=t("pnl_datos_varias")
                                  % (self.pno + 1, dibujos, len(marcas) - dibujos))

        self.pnl_color_bloque.pack(fill="x", padx=12, pady=(0, 10))
        if uno is not None and uno["tipo"] == "texto":
            self.pnl_letra.set("%g" % (uno.get("cuerpo") or A.CUERPO_NOTA))
            self.pnl_letra_bloque.pack(fill="x", padx=12, pady=(0, 10))
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
        self._pintar_ojo()

    def _pintar_ojo(self):
        """El boton de ocultar marcas refleja el estado: suelto dice "Ocultar
        marcas"; apretado (marcas ocultas) queda hundido, de color, y dice
        "Mostrar marcas". Estado y accion se leen sin depender solo del color."""
        bt = getattr(self, "btn_ojo", None)
        if bt is None:
            return
        ocultas = not self.ver_marcas
        bt.config(text=t("ojo_mostrar") if ocultas else t("ojo_ocultar"),
                  relief="sunken" if ocultas else "raised",
                  bg="#C9D9EC" if ocultas else "SystemButtonFace")

    # ------------------------------------------------------ herramientas ----

    def set_modo(self, modo):
        if modo == "texto" and self.modo == "seleccionar" and self.comentar_seleccion():
            return          # habia una frase elegida: se comenta esa frase
        self._cerrar_editor(confirmar=True)
        # Cambiar de herramienta abandona lo que estaba "por atarse". Antes, una
        # frase elegida con "Comentar esta frase" y despues abandonada quedaba
        # viva sin verse y se pegaba sola a la marca siguiente.
        self.ancla_pendiente = None
        self.refiriendo = []
        self.modo = modo
        # Para marcar hay que ver lo que se marca: el ojito se vuelve a encender.
        if modo in ("dibujar", "texto", "borrar") and not self.ver_marcas:
            self.toggle_ver_marcas()
        if modo != "seleccionar":
            self._limpiar_seleccion()
        self._aplicar_cursor()
        self._pintar_botones()
        self._actualizar_pie()

    def _aplicar_cursor(self):
        """Pone el cursor que corresponde al estado actual. Un solo lugar: antes
        cada funcion ponia el suyo y alguno quedaba colgado (la mira de "elegir
        referencia" seguia puesta despues de elegirla)."""
        self._cursor_actual = "crosshair" if self.refiriendo else CURSORES[self.modo]
        self.canvas.config(cursor=self._cursor_actual)

    def set_color(self, col):
        self.color = col
        self._pintar_botones()

    def toggle_grosor(self):
        self.grosor = GROSOR_FINO if self.grosor == GROSOR_GRUESO else GROSOR_GRUESO
        self._pintar_botones()

    def toggle_ver_marcas(self):
        """El "ojito": muestra u oculta las marcas propias sobre la hoja.

        Sirve para leer el documento limpio un momento sin perder lo marcado: las
        marcas siguen ahi, solo se dejan de dibujar hasta volver a apretarlo.
        """
        self.ver_marcas = not self.ver_marcas
        if not self.ver_marcas:
            # Lo que no se ve no se toca: se suelta lo elegido y las marcas
            # dejan de responder a clics y recuadros hasta volver a mostrarlas.
            # Antes se podia agarrar y borrar un dibujo invisible.
            self.seleccion = []
            self._refrescar_panel()
        self._pintar_ojo()
        self.render(self.canvas.yview()[0])

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
            alto = max(200, self.canvas.winfo_height() - 12 - 2 * CUSHION_HOJA)
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
        # La imagen de la hoja se guarda y solo se vuelve a sacar del PDF cuando
        # cambia la pagina, el zoom o el documento. Antes se rasterizaba en CADA
        # movimiento del mouse al arrastrar una marca, y con zoom alto el
        # arrastre iba a los tirones.
        clave = (id(self.doc), self.pno, round(self.zoom, 5))
        if getattr(self, "_clave_imagen", None) != clave or self.tkimg is None:
            pix = pagina.get_pixmap(matrix=pymupdf.Matrix(self.zoom, self.zoom), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            self.tkimg = ImageTk.PhotoImage(img)
            self._tam_imagen = (pix.width, pix.height)
            self._clave_imagen = clave
        ancho_img, alto_img = self._tam_imagen

        ancho_vista = max(1, self.canvas.winfo_width())
        self.ox = max(0, (ancho_vista - ancho_img) // 2)
        self.oy = CUSHION_HOJA

        self.canvas.delete("all")
        self.canvas.create_image(self.ox, self.oy, anchor="nw", image=self.tkimg)
        self._region = (max(ancho_vista, ancho_img + self.ox), alto_img + 2 * CUSHION_HOJA)
        self.canvas.config(scrollregion=(0, 0) + self._region)
        self._dibujar_marcas()
        self.canvas.yview_moveto(y_fraccion)
        self.lbl_zoom.config(text="%d%%" % round(self.zoom * 72.0 / self._ppp() * 100))
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
        cy = self.canvas.canvasy(ey) - self.oy
        return (cx / self.zoom, cy / self.zoom)

    def _a_canvas(self, px, py):
        return (px * self.zoom + self.ox, py * self.zoom + self.oy)

    def _dibujar_marcas(self):
        # Primero el texto del documento resaltado, para que quede DEBAJO de las
        # marcas y no las tape.
        for r in self.palabras_sel:
            x0, y0 = self._a_canvas(r.x0, r.y0)
            x1, y1 = self._a_canvas(r.x1, r.y1)
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#A8C7F0", outline="",
                                         stipple="gray50", tags="seltexto")
        # El "ojito" apagado oculta las marcas propias, pero no la seleccion de
        # texto de arriba ni el recuadro de lo elegido: eso es la interaccion.
        self._cajas_notas = {}
        if self.ver_marcas:
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
            marca = lista[i]
            x0, y0, x1, y1 = self._caja_en_pantalla(marca, i)
            # Un halo azul DETRAS de la marca: hace que lo elegido salte a la
            # vista sin ensuciarlo (antes iba encima y tramaba el texto de la
            # nota). Queda arriba de la hoja y abajo de todas las marcas.
            halo = self.canvas.create_rectangle(x0 - 7, y0 - 7, x1 + 7, y1 + 7,
                                                fill="#9CC8F5", outline="",
                                                tags="seleccion")
            if self.canvas.find_withtag("marca"):
                self.canvas.tag_lower(halo, "marca")
            self.canvas.create_rectangle(x0 - 4, y0 - 4, x1 + 4, y1 + 4,
                                         outline="#1971C2", width=2, dash=(4, 3),
                                         tags="seleccion")
            # Manijas SOLO donde hacen algo: en una nota sola elegida. Antes
            # habia cuadraditos en las esquinas de todo lo elegido que parecian
            # manijas y no hacian nada. Un dibujo o varias marcas llevan solo el
            # recuadro: se mueven arrastrando, no se estiran.
            if marca["tipo"] == "texto" and len(self.seleccion) == 1:
                self._dibujar_manijas(i)
                guia = (self._redimensionando or {}).get("guia")
                if guia is not None:
                    # Mientras se arrastra un costado, una linea punteada marca
                    # el tope elegido; la caja se ajusta al texto (fit to size).
                    gx = self._a_canvas(guia, 0)[0]
                    self.canvas.create_line(gx, y0 - 10, gx, y1 + 10, fill="#1971C2",
                                            dash=(3, 3), tags="seleccion")
            # Si lo elegido esta atado a una frase, una flecha marcada apunta
            # desde la marca HACIA esa frase; si se refiere a otra marca, hacia
            # esa marca. Se ve de un vistazo a que se refiere sin leer el panel.
            puntos = self._conector(marca, marca.get("ancla")) if marca.get("ancla") else None
            if puntos is None and marca.get("ref"):
                otra = self._marca_por_nombre(marca["ref"])
                if otra is not None and otra is not marca:
                    puntos = self._conector(marca, {"rects": [tuple(self._bbox(otra))]})
            if puntos:
                self.canvas.create_line(
                    *puntos, fill="#E8A200",
                    width=max(2, int(round(2.4 * self.zoom))),
                    arrow="last", arrowshape=(12, 15, 5), tags="seleccion")

    def _caja_en_pantalla(self, marca, i):
        """Recuadro de una marca en el canvas: el de la nota tal como se dibujo,
        o el del dibujo convertido de puntos PDF."""
        if i in self._cajas_notas:
            return self._cajas_notas[i]
        r = self._bbox(marca)
        x0, y0 = self._a_canvas(r.x0, r.y0)
        x1, y1 = self._a_canvas(r.x1, r.y1)
        return x0, y0, x1, y1

    def _marca_por_nombre(self, nombre):
        """La marca de la pagina actual que se llama asi (o None)."""
        for mk in self.marcas.get(self.pno, []):
            if mk.get("nombre") == nombre:
                return mk
        return None

    def _manijas(self, i):
        """{nombre: (x, y)} de las 8 manijas de la nota i, en el canvas."""
        lista = self.marcas.get(self.pno, [])
        x0, y0, x1, y1 = self._caja_en_pantalla(lista[i], i)
        x0, y0, x1, y1 = x0 - 4, y0 - 4, x1 + 4, y1 + 4
        mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        return {"ai": (x0, y0), "ad": (x1, y0), "bi": (x0, y1), "bd": (x1, y1),
                "izq": (x0, my), "der": (x1, my), "arr": (mx, y0), "abj": (mx, y1)}

    def _dibujar_manijas(self, i):
        """Cuadraditos blancos con borde azul, como en cualquier editor."""
        for nombre, (mx, my) in self._manijas(i).items():
            if nombre in MANIJAS_ESQUINA:
                caja = (mx - 4, my - 4, mx + 4, my + 4)
            elif nombre in ("izq", "der"):
                caja = (mx - 3, my - 9, mx + 3, my + 9)
            else:
                caja = (mx - 9, my - 3, mx + 9, my + 3)
            self.canvas.create_rectangle(*caja, fill="white", outline="#1971C2",
                                         width=2, tags="seleccion")

    def _manija_en(self, e):
        """(indice, nombre) de la manija que esta bajo el mouse, o None.

        Solo hay manijas con una nota sola elegida, en modo Seleccionar.
        """
        if self.modo != "seleccionar" or len(self.seleccion) != 1 or self.refiriendo:
            return None
        lista = self.marcas.get(self.pno, [])
        i = self.seleccion[0]
        if not (0 <= i < len(lista)) or lista[i]["tipo"] != "texto" or not self.ver_marcas:
            return None
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        for nombre, (mx, my) in self._manijas(i).items():
            ax, ay = (7, 7) if nombre in MANIJAS_ESQUINA else \
                ((7, 12) if nombre in ("izq", "der") else (12, 7))
            if abs(cx - mx) <= ax and abs(cy - my) <= ay:
                return i, nombre
        return None

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
                puntos = self._conector(marca, ancla)
                if puntos:
                    self.canvas.create_line(
                        *puntos,
                        fill=a_hex(mezclar(A.COLOR_ANCLA, A.OPACIDAD_ANCLA)),
                        width=max(1, int(1.2 * self.zoom)), tags=("marca", tag))
            cuerpo = marca.get("cuerpo")
            f = A.escala_nota(cuerpo)
            rect = A.rect_de(marca)
            x0, y0 = self._a_canvas(rect.x0, rect.y0)
            _x1, y1 = self._a_canvas(rect.x1, rect.y1)
            # El texto va renglon por renglon, con el MISMO corte que usa el PDF
            # guardado (A.lineas_nota) y la letra en pixeles (tamano negativo en
            # Tk). Si se dejara que Tk corte solo y con tamano en puntos, Windows
            # agranda la letra y el segundo renglon se sale del recuadro.
            pad = A.PAD_NOTA * f * self.zoom
            fuente = ("Helvetica", -max(6, int(round(A.CUERPO_NOTA * f * self.zoom))))
            tag_txt = tag + "txt"
            for k, linea in enumerate(A.lineas_nota(marca["texto"], marca.get("ancho"), cuerpo)):
                self.canvas.create_text(
                    x0 + pad, y0 + A.tope_renglon(k, cuerpo) * self.zoom, text=linea,
                    anchor="nw", fill=col, font=fuente, tags=("marca", tag, tag_txt))
            # La caja se arma alrededor del texto YA DIBUJADO, no de la medida del
            # PDF: en pantalla la letra sale un poco mas angosta (Windows redondea
            # el tamano) y medida "de libro" quedaba un hueco vacio a la derecha.
            caja = self.canvas.bbox(tag_txt)
            x1 = max(x0 + A.ANCHO_MIN_NOTA * f * self.zoom, (caja[2] if caja else x0) + pad)
            # Mientras se arrastra una manija, el fondo mide exacto lo pedido
            # (el alto, como minimo: si el texto no entra, crece hacia abajo).
            arrastre = self._redimensionando
            if arrastre and arrastre.get("i") == i and arrastre.get("caja"):
                cx1, cy1 = self._a_canvas(arrastre["caja"][2], arrastre["caja"][3])
                x1, y1 = cx1, max(y1, cy1)
            fondo = self.canvas.create_rectangle(x0, y0, x1, y1, fill=a_hex(A.FONDO_NOTA),
                                                 outline=col, width=1, tags=("marca", tag))
            self.canvas.tag_lower(fondo, tag_txt)
            self._cajas_notas[i] = (x0, y0, x1, y1)

    def _al_mover_mouse(self, e):
        """Sin apretar nada, el cursor avisa que hay debajo (en Seleccionar).

        Flechas de estirar sobre las manijas de una nota (dobles horizontales
        en los costados, diagonales en las esquinas), cruz de mover sobre una
        marca, cursor de texto sobre el texto del documento. Asi se sabe que va
        a pasar antes de hacer clic, como en cualquier editor.
        """
        if self._pan or self._redimensionando is not None or self._rts:
            return
        cursor = "crosshair" if self.refiriendo else CURSORES[self.modo]
        if self.modo == "seleccionar" and not self.refiriendo:
            punto = self._a_pdf(e.x, e.y)
            manija = self._manija_en(e)
            if manija is not None:
                cursor = {"ai": "size_nw_se", "bd": "size_nw_se",
                          "ad": "size_ne_sw", "bi": "size_ne_sw",
                          "arr": "sb_v_double_arrow", "abj": "sb_v_double_arrow"}.get(
                              manija[1], "sb_h_double_arrow")
            elif self._marca_en(punto) is not None:
                cursor = "fleur"
            elif self._palabra_en(punto):
                cursor = "xterm"
        if cursor != self._cursor_actual:
            self._cursor_actual = cursor
            self.canvas.config(cursor=cursor)

    def _palabra_en(self, punto):
        """True si hay una palabra del documento justo debajo del punto."""
        px, py = punto
        return any(w[0] <= px <= w[2] and w[1] <= py <= w[3]
                   for w in self._palabras_pagina())

    def _conector(self, marca, ancla):
        """Puntos (x0, y0, x1, y1) de la linea que une una marca con su frase.

        Sale del BORDE de la marca que mira a la frase y llega al borde de la
        frase: asi la linea nunca atraviesa el texto de la nota.
        """
        rects = ancla.get("rects") or []
        if not rects:
            return None
        fx0 = min(r[0] for r in rects)
        fy0 = min(r[1] for r in rects)
        fx1 = max(r[2] for r in rects)
        fy1 = max(r[3] for r in rects)
        b = self._bbox(marca)
        cx, cy = (b.x0 + b.x1) / 2.0, (b.y0 + b.y1) / 2.0
        # Punto de la frase mas cercano a la marca, y punto de la marca mas
        # cercano a ese.
        ex, ey = min(max(cx, fx0), fx1), min(max(cy, fy0), fy1)
        sx, sy = min(max(ex, b.x0), b.x1), min(max(ey, b.y0), b.y1)
        if abs(sx - ex) < 0.5 and abs(sy - ey) < 0.5:
            return None         # la marca esta encima de la frase: no hace falta linea
        return self._a_canvas(sx, sy) + self._a_canvas(ex, ey)

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
            punto = self._a_pdf(e.x, e.y)
            i = self._marca_en(punto)
            if (i is not None and not self.ancla_pendiente
                    and self.marcas[self.pno][i]["tipo"] == "texto"):
                # Clic sobre una nota que ya existe: se edita esa, en vez de
                # abrir otra encima (como en cualquier editor).
                self.seleccion = [i]
                self._editar_nota_seleccionada()
                return
            self._abrir_editor(punto)
            # Si en vez de soltar se arrastra, el arrastre elige el ancho de la
            # nota, como el cuadro de texto de Acrobat o de Figma (ver
            # _arrastre_nota). Un clic suelto la deja con el ancho de entrada.
            if self._editor is not None:
                self._nota_arrastre = {"desde": punto, "movido": False}
        elif self.modo == "seleccionar":
            # Ctrl+clic o Shift+clic suman a la seleccion (Shift es lo de Windows).
            self._click_seleccionar(e, sumando=bool(e.state & 0x0005))
        elif self.modo == "borrar":
            # El borrador borra todo lo que toca mientras se arrastra, como el
            # de Office; toda la pasada se deshace con un solo Ctrl+Z.
            punto = self._a_pdf(e.x, e.y)
            self._borrando = {"ultimo": punto, "algo": False}
            self._borrar_en(punto)

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
        if self.modo == "texto" and self._nota_arrastre is not None:
            self._arrastre_nota(e)
            return
        if self.modo == "borrar" and self._borrando is not None:
            self._arrastre_borrar(e)
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
        if self.modo == "texto" and self._nota_arrastre is not None:
            self._soltar_nota(_e)
            return
        if self.modo == "borrar" and self._borrando is not None:
            borrando, self._borrando = self._borrando, None
            if borrando["algo"]:
                self._marcar_sucio()
            return
        if self.modo != "dibujar" or self._trazo is None:
            return
        trazo, self._trazo = self._trazo, None
        # Ojo: la variable NO puede llamarse "t", que es la funcion de idiomas.
        for linea_tmp in self._tmp:
            self.canvas.delete(linea_tmp)
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

    def _arrastre_nota(self, e):
        """Modo Texto, arrastrando despues del clic: el cuadro de la nota nueva
        va de donde se apreto hasta el mouse, en ancho Y alto. Mientras se
        escribe mide exacto eso; al terminar se ajusta al texto."""
        d = self._nota_arrastre
        if self._editor is None:
            self._nota_arrastre = None
            return
        px, py = self._a_pdf(e.x, e.y)
        x0, y0 = d["desde"]
        if not d["movido"] and max(abs(px - x0), abs(py - y0)) * self.zoom < 8:
            return          # un temblor del clic no cuenta como arrastre
        d["movido"] = True
        hoja = self._pagina().rect
        f = A.escala_nota(self._editor_cuerpo)
        izq, der = sorted((min(max(x0, 0.0), hoja.width), min(max(px, 0.0), hoja.width)))
        arr, abj = sorted((min(max(y0, 0.0), hoja.height), min(max(py, 0.0), hoja.height)))
        ancho = max(A.ANCHO_MIN_NOTA * f, der - izq)
        alto = max(A.medir_nota("", None, self._editor_cuerpo)[1], abj - arr)
        izq = max(0.0, min(izq, hoja.width - ancho))
        self._editor_ancho, self._editor_alto, self._editor_fijo = ancho, alto, True
        self._editor_xy = (izq, arr)
        self.canvas.coords(self._editor_win, *self._a_canvas(izq, arr))
        self._crecer_editor()

    def _soltar_nota(self, _e):
        """Fin del clic (o del arrastre) en modo Texto: el cuadro queda abierto
        para escribir; el recuadro punteado queda a la vista hasta cerrarlo."""
        self._nota_arrastre = None
        if self._editor is not None:
            self._editor.focus_set()

    def _arrastre_borrar(self, e):
        """Pasada del borrador: borra cada marca que toca el camino del mouse.

        Se revisan puntos intermedios del tramo: con un movimiento rapido el
        mouse salta varios pixeles entre evento y evento y, sin esto, un trazo
        fino que quedara en el medio se salvaba.
        """
        d = self._borrando
        p = self._a_pdf(e.x, e.y)
        x0, y0 = d["ultimo"]
        pasos = max(1, int(max(abs(p[0] - x0), abs(p[1] - y0)) * self.zoom / 3))
        for k in range(1, pasos + 1):
            self._borrar_en((x0 + (p[0] - x0) * k / pasos, y0 + (p[1] - y0) * k / pasos))
        d["ultimo"] = p

    def _pan_inicio(self, e):
        # La "manito": apretar la ruedita del mouse agarra la hoja y la arrastra,
        # como en Acrobat o los editores de imagen. Girar la ruedita sigue siendo
        # leer; apretarla y mover es mover el papel. Mientras se arrastra, el
        # cursor es una mano cerrada (antes era una cruz de flechas).
        self._pan = True
        try:
            self.canvas.config(cursor=CURSOR_MANO)
        except tk.TclError:
            self.canvas.config(cursor="fleur")
        self.canvas.scan_mark(e.x, e.y)

    def _pan_mover(self, e):
        if not self._pan:
            return
        # gain=1: la hoja sigue al mouse punto por punto, sin acelerar.
        self.canvas.scan_dragto(e.x, e.y, gain=1)

    def _pan_fin(self, _e):
        self._pan = None
        self._aplicar_cursor()

    def _menu_guardar(self):
        """La flechita al lado de Guardar: "Guardar como...", debajo del boton."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=t("menu_guardar_como"), accelerator="Ctrl+Shift+S",
                         command=lambda: self.guardar(como=True))
        # Copiar el mensaje para la IA de la ultima devolucion guardada.
        menu.add_command(label=t("menu_copiar_prompt"), command=self.copiar_prompt,
                         state="normal" if self.ruta_guardado else "disabled")
        bt = self.btn_guardar
        try:
            menu.tk_popup(bt.winfo_rootx(), bt.winfo_rooty() + bt.winfo_height())
        finally:
            menu.grab_release()

    # ----------------------------------------------- seleccion por area (RTS) --

    def _rts_inicio(self, e):
        """Boton derecho: empezar el recuadro verde de seleccion por area."""
        self._cerrar_editor(confirmar=True)
        self._rts = {"desde": (e.x, e.y), "id": None}

    def _rts_mover(self, e):
        if not self._rts:
            return
        x0 = self.canvas.canvasx(self._rts["desde"][0])
        y0 = self.canvas.canvasy(self._rts["desde"][1])
        x1 = self.canvas.canvasx(e.x)
        y1 = self.canvas.canvasy(e.y)
        if self._rts["id"] is not None:
            self.canvas.delete(self._rts["id"])
        # Recuadro verde translucido a lo RTS: se dibuja directo, sin re-render,
        # para que siga al mouse sin tironear.
        self._rts["id"] = self.canvas.create_rectangle(
            x0, y0, x1, y1, outline="#2FB344", width=2,
            fill="#2FB344", stipple="gray12", tags="rts")

    def _rts_soltar(self, e):
        datos = self._rts
        self._rts = None
        if not datos:
            return
        if datos["id"] is not None:
            self.canvas.delete(datos["id"])
        p0 = self._a_pdf(*datos["desde"])
        p1 = self._a_pdf(e.x, e.y)
        area = pymupdf.Rect(min(p0[0], p1[0]), min(p0[1], p1[1]),
                            max(p0[0], p1[0]), max(p0[1], p1[1]))
        if area.width < 2 and area.height < 2:
            # Clic derecho sin arrastrar: el menu de siempre, con lo que se
            # puede hacer con lo que hay debajo del mouse.
            self._menu_contextual(e, p1)
            return
        # Pasar a Seleccionar y agarrar todas las marcas que toque el area (las
        # ocultas por el ojito no cuentan: lo que no se ve no se toca).
        lista = self.marcas.get(self.pno, []) if self.ver_marcas else []
        elegidas = [i for i, mk in enumerate(lista) if self._bbox(mk).intersects(area)]
        self.ancla_pendiente = None
        self.refiriendo = []
        self.modo = "seleccionar"
        self._aplicar_cursor()
        self._pintar_botones()
        if elegidas:
            self.seleccion = elegidas
            self.palabras_sel = []
            self._texto_sel = ""
        else:
            # Ninguna marca en el area: se eligen las palabras del documento
            # que quedan DENTRO del recuadro (antes tomaba todo lo que habia
            # entre dos palabras en orden de lectura, y un recuadro en el
            # margen agarraba texto que no tocaba).
            self._limpiar_seleccion()
            self._elegir_palabras_en(area)
        self.render(self.canvas.yview()[0])
        self._refrescar_panel()

    def _elegir_palabras_en(self, area):
        """Elige las palabras del documento cuyo recuadro toca el area."""
        elegidas = [w for w in self._palabras_pagina()
                    if pymupdf.Rect(w[:4]).intersects(area)]
        self.palabras_sel = [pymupdf.Rect(w[:4]) for w in elegidas]
        self._texto_sel = " ".join(w[4] for w in elegidas)

    def _menu_contextual(self, e, punto):
        """Menu del clic derecho: acciones sobre lo que hay debajo del mouse."""
        menu = tk.Menu(self, tearoff=0)
        i = self._marca_en(punto)
        if i is not None:
            if i not in self.seleccion:
                self.modo = "seleccionar"
                self.seleccion = [i]
                self.palabras_sel = []
                self._texto_sel = ""
                self._aplicar_cursor()
                self._pintar_botones()
                self.render(self.canvas.yview()[0])
                self._refrescar_panel()
            if self.marcas[self.pno][i]["tipo"] == "texto" and len(self.seleccion) == 1:
                menu.add_command(label=t("pnl_editar_texto"), accelerator="Enter",
                                 command=self._editar_nota_seleccionada)
            menu.add_command(label=t("menu_copiar"), accelerator="Ctrl+C", command=self.copiar)
            menu.add_command(label=t("menu_cortar"), accelerator="Ctrl+X", command=self.cortar)
            menu.add_command(label=t("pnl_borrar"), accelerator=t("tecla_supr"),
                             command=self._borrar_seleccion)
            menu.add_separator()
            menu.add_command(label=t("pnl_soltar"), accelerator="Esc", command=self._soltar_todo)
        elif self._texto_sel:
            menu.add_command(label=t("menu_copiar"), accelerator="Ctrl+C",
                             command=self.copiar_texto)
            menu.add_command(label=t("pnl_comentar"), command=self.comentar_seleccion)
            menu.add_command(label=t("pnl_dibujar_sobre"),
                             command=self.dibujar_sobre_seleccion)
        else:
            menu.add_command(label=t("menu_nota_aca"),
                             command=lambda: self._abrir_editor(punto))
            if getattr(self.app, "marcas_copiadas", None):
                menu.add_command(label=t("menu_pegar"), accelerator="Ctrl+V",
                                 command=lambda: self.pegar(punto))
            if self.marcas.get(self.pno):
                menu.add_command(label=t("menu_seleccionar_todo"), accelerator="Ctrl+A",
                                 command=self.seleccionar_todo)
        try:
            menu.tk_popup(getattr(e, "x_root", 0), getattr(e, "y_root", 0))
        finally:
            menu.grab_release()

    def _rueda(self, e):
        if e.state & 0x0004:        # Ctrl: zoom hacia donde apunta el mouse
            self._zoom_hacia(e, 1.1 if e.delta > 0 else 1 / 1.1)
            return
        pasos = 1 if e.delta < 0 else -1
        prim, ult = self.canvas.yview()
        # Pasar de pagina solo si YA se estaba en el borde antes de este tiron.
        if pasos > 0 and ult >= 0.9999:
            if self._puede_saltar(1):
                self.ir_pagina(self.pno + 1, y=0.0)
            return
        if pasos < 0 and prim <= 0.0001:
            if self._puede_saltar(-1):
                self.ir_pagina(self.pno - 1, y=1.0)
            return
        self.canvas.yview_scroll(pasos * 3, "units")

    def _puede_saltar(self, direccion):
        """Un salto de pagina por vez con la rueda.

        Un touchpad o una rueda libre mandan muchos eventos seguidos: sin esto,
        un solo gesto saltaba varias paginas. Cambiar de direccion si se puede
        enseguida.
        """
        import time
        ahora = time.monotonic()
        antes_dir, antes_t = self._ultimo_salto
        if antes_dir == direccion and ahora - antes_t < 0.45:
            return False
        self._ultimo_salto = (direccion, ahora)
        return True

    def _zoom_hacia(self, e, factor):
        """Ctrl+rueda: acercar dejando quieto el punto del papel bajo el mouse,
        como en Acrobat o en un navegador (antes acercaba hacia la izquierda)."""
        px, py = self._a_pdf(e.x, e.y)
        self.set_zoom(self.zoom * factor)
        cx, cy = self._a_canvas(px, py)
        ancho, alto = self._region
        if ancho > 0:
            self.canvas.xview_moveto(max(0.0, cx - e.x) / ancho)
        if alto > 0:
            self.canvas.yview_moveto(max(0.0, cy - e.y) / alto)

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
        return A.rect_de(marca)

    def _borrar_en(self, punto):
        # Misma prueba que para elegir: se borra lo que esta bajo el mouse, y un
        # dibujo solo si el clic cae sobre su trazo.
        i = self._marca_en(punto)
        if i is None:
            return
        # Una sola instantanea por pasada del borrador: Ctrl+Z devuelve todo lo
        # que borro esa pasada junto, no de a una marca.
        pasada = self._borrando
        if pasada is None or not pasada["algo"]:
            self._instantanea()
            if pasada is not None:
                pasada["algo"] = True
        self.marcas[self.pno].pop(i)
        self._limpiar_seleccion()
        self.render(self.canvas.yview()[0])
        if pasada is None:
            self._marcar_sucio()

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
        if not self.ver_marcas:
            return None     # con el ojito apagado, lo que no se ve no se toca
        px, py = punto
        lista = self.marcas.get(self.pno, [])
        tol = 5.0 / max(0.2, self.zoom)
        for i in range(len(lista) - 1, -1, -1):
            mk = lista[i]
            r = self._bbox(mk)
            if not ((r.x0 - tol) <= px <= (r.x1 + tol) and (r.y0 - tol) <= py <= (r.y1 + tol)):
                continue
            if mk["tipo"] == "texto":
                return i
            # Un dibujo se toca por su TRAZO, no por el recuadro que lo
            # envuelve: si no, despues de encerrar un parrafo en un circulo no
            # habia forma de elegir el texto de adentro.
            if _cerca_del_trazo(px, py, mk["trazos"], tol + mk.get("grosor", GROSOR_FINO) / 2.0):
                return i
        return None

    def _click_seleccionar(self, e, sumando=False):
        punto = self._a_pdf(e.x, e.y)
        # Las manijas van primero: estan pegadas al borde de la nota y, si no,
        # el clic se tomaria como "agarrar la nota para moverla".
        manija = None if sumando else self._manija_en(e)
        if manija is not None:
            self._empezar_manija(*manija)
            return
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
                # El nombre queda FIJO en la otra marca: el nombre por defecto
                # depende del lugar en la lista, y si despues se borraba una
                # marca anterior la referencia pasaba a apuntar a otra.
                otra["nombre"] = self._nombre_libre(nombre, otra)
                self._asignar_referencia(nombre=otra["nombre"])
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
        if self._redimensionando is not None:
            self._redimensionar(punto)
            return
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
        if self._redimensionando is not None:
            datos = self._redimensionando
            self._redimensionando = None
            if datos["movido"]:
                lista = self.marcas.get(self.pno, [])
                if 0 <= datos["i"] < len(lista):
                    self._encajar_nota(lista[datos["i"]])   # que no quede fuera de la hoja
                self._marcar_sucio()
            self.render(self.canvas.yview()[0])
            self._refrescar_panel()
            return
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

    def _empezar_manija(self, i, cual):
        """Clic sobre una manija: se anota como estaba la nota al empezar.

        Todo el arrastre se calcula contra ese estado inicial (y no paso a
        paso), asi la nota no "deriva" por redondeos y volver el mouse al
        punto de partida la deja exactamente como estaba.
        """
        mk = self.marcas[self.pno][i]
        r = self._bbox(mk)
        self._redimensionando = {
            "i": i, "cual": cual, "movido": False, "guia": None,
            "ini": {"x": mk["x"], "y": mk["y"], "w": r.width, "h": r.height},
            "caja": None}

    def _redimensionar(self, punto):
        """Arrastrando una manija: la caja mide EXACTO lo que se marca.

        Mientras se arrastra, el fondo tiene el tamano pedido aunque el texto no
        lo llene, y el texto se parte a ese ancho. Al soltar, la caja se ajusta
        al texto (fit to size); el ancho elegido queda como ancho de los
        renglones. Si el texto no entra en el alto pedido, la caja crece hacia
        abajo. El lado (o la esquina) de enfrente queda quieto. Nunca se sale
        de la hoja.
        """
        datos = self._redimensionando
        lista = self.marcas.get(self.pno, [])
        if not (0 <= datos["i"] < len(lista)):
            return
        mk = lista[datos["i"]]
        ini, cual = datos["ini"], datos["cual"]
        hoja = self._pagina().rect
        minw = A.ANCHO_MIN_NOTA * A.escala_nota(mk.get("cuerpo"))
        minh = A.medir_nota("", None, mk.get("cuerpo"))[1]
        x0, y0 = ini["x"], ini["y"]
        x1, y1 = x0 + ini["w"], y0 + ini["h"]
        px = min(max(punto[0], 0.0), hoja.width)
        py = min(max(punto[1], 0.0), hoja.height)
        if cual in ("ai", "bi", "izq"):
            x0 = min(px, x1 - minw)
        if cual in ("ad", "bd", "der"):
            x1 = max(px, x0 + minw)
        if cual in ("ai", "ad", "arr"):
            y0 = min(py, y1 - minh)
        if cual in ("bi", "bd", "abj"):
            y1 = max(py, y0 + minh)
        nuevo = {"x": x0, "y": y0}
        if cual not in ("arr", "abj"):
            nuevo["ancho"] = x1 - x0
        datos["caja"] = (x0, y0, x1, y1)
        if not datos["movido"]:
            if all(abs((mk.get(k) or 0.0) - v) < 0.05 for k, v in nuevo.items()) \
                    and abs(y1 - (ini["y"] + ini["h"])) < 0.05:
                return
            self._instantanea()             # una sola instantanea por arrastre
            datos["movido"] = True
        mk.update(nuevo)
        self.render(self.canvas.yview()[0])

    def empujar_seleccion(self, dx, dy):
        """Flechas del teclado con algo elegido: moverlo de a poquito."""
        if not self.seleccion:
            return
        self._instantanea()
        self._mover_seleccion(dx, dy)
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()

    def seleccionar_todo(self):
        """Ctrl+A: elegir todas las marcas de la pagina."""
        lista = self.marcas.get(self.pno, [])
        if not lista:
            return
        if self.modo != "seleccionar":
            self.set_modo("seleccionar")
        self.seleccion = list(range(len(lista)))
        self.palabras_sel = []
        self._texto_sel = ""
        self.render(self.canvas.yview()[0])
        self._refrescar_panel()

    def zoom_real(self):
        """Ctrl+1: tamano real (una pulgada del papel = una pulgada de pantalla)."""
        self.set_zoom(self._ppp() / 72.0)

    def _ppp(self):
        """Puntos por pulgada de la pantalla (96 sin escalado de Windows)."""
        try:
            return float(self.winfo_fpixels("1i")) or 96.0
        except Exception:
            return 96.0

    def _cambiar_letra(self, _e=None):
        """Tamano de letra del panel: cambia la nota elegida y queda como el de
        las notas nuevas de este PDF (se recuerda: al reabrir, las notas nuevas
        usan el de la ultima nota)."""
        marcas = [m for m in self._marcas_seleccionadas() if m["tipo"] == "texto"]
        try:
            valor = float(str(self.pnl_letra.get()).replace(",", "."))
        except ValueError:
            self._refrescar_panel()
            return
        valor = max(A.CUERPO_MIN, min(A.CUERPO_MAX, round(valor)))
        self.cuerpo_nuevas = valor
        if len(marcas) != 1:
            return
        mk = marcas[0]
        if abs((mk.get("cuerpo") or A.CUERPO_NOTA) - valor) < 0.05:
            return
        self._instantanea()
        if abs(valor - A.CUERPO_NOTA) < 0.05:
            mk.pop("cuerpo", None)
        else:
            mk["cuerpo"] = valor
        self._encajar_nota(mk)
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()

    def _mover_seleccion(self, dx, dy):
        # Nada se va de la hoja: una marca fuera del papel llega cortada en el
        # PDF y el agente no la ve entera. Se usa el tamano REAL de cada marca
        # (antes una nota de varios renglones se podia sacar por abajo).
        # El limite solo impide salirse MAS: una marca que ya estaba afuera
        # (dibujada en el margen gris) se puede traer para adentro, pero no
        # salta de golpe al primer movimiento.
        hoja = self._pagina().rect
        for mk in self._marcas_seleccionadas():
            r = self._bbox(mk)
            mx = min(max(dx, min(0.0, -r.x0)), max(0.0, hoja.width - r.x1))
            my = min(max(dy, min(0.0, -r.y0)), max(0.0, hoja.height - r.y1))
            if mk["tipo"] == "lapiz":
                mk["trazos"] = [[(x + mx, y + my) for (x, y) in tr] for tr in mk["trazos"]]
            else:
                mk["x"] += mx
                mk["y"] += my

    def _encajar_nota(self, mk):
        """Corre una nota hacia adentro si con su tamano real se sale de la hoja."""
        hoja = self._pagina().rect
        r = self._bbox(mk)
        mk["x"] = max(0.0, min(mk["x"], hoja.width - r.width))
        mk["y"] = max(0.0, min(mk["y"], hoja.height - r.height))

    # --- texto del PDF original -------------------------------------------

    def _palabras_pagina(self):
        if getattr(self, "_cache_palabras_pno", None) != self.pno:
            self._cache_palabras = self._pagina().get_text("words")
            self._cache_palabras_pno = self.pno
        return self._cache_palabras

    def _seleccionar_texto(self, desde, hasta):
        """Selecciona el texto del documento entre dos puntos, en orden de lectura."""
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
        modo Texto y espera a que el usuario haga clic donde la quiere. La nota que
        escriba ahi queda atada a esta frase, se ponga donde se ponga.
        """
        return self._preparar_ancla("texto", "pie_comentar")

    def dibujar_sobre_seleccion(self):
        """Igual que comentar, pero lo que sigue es un dibujo en vez de una nota."""
        return self._preparar_ancla("dibujar", "pie_dibujar")

    def _preparar_ancla(self, modo, clave_pie):
        """Deja la frase elegida esperando a la proxima marca, y pasa a 'modo'."""
        if not self.palabras_sel or not self._texto_sel:
            return False
        self._cerrar_editor(confirmar=True)
        self.refiriendo = []
        self.ancla_pendiente = {
            "rects": [(r.x0, r.y0, r.x1, r.y1) for r in self.palabras_sel],
            "cita": self._texto_sel,
        }
        cita = self._texto_sel
        self._limpiar_seleccion()
        self.modo = modo
        if not self.ver_marcas:
            self.toggle_ver_marcas()
        self._aplicar_cursor()
        self._pintar_botones()
        self.render(self.canvas.yview()[0])
        self.pie.config(text=t(clave_pie) % cita[:80])
        return True

    def elegir_referencia(self):
        """Empezar a elegir a que se refiere la marca que esta seleccionada.

        Despues de tocar "Elegir", lo que se marque pasa a ser la referencia:
        una frase del documento (arrastrando sobre el texto) o una marca que ya
        exista (haciendole clic).
        """
        if not self.seleccion:
            return
        self.ancla_pendiente = None
        self.refiriendo = list(self.seleccion)
        self._limpiar_seleccion()
        self.modo = "seleccionar"
        # Mira (crosshair): "apunta a lo que queres referenciar". La manito
        # queda solo para arrastrar la hoja, asi no se confunden.
        self._aplicar_cursor()
        self._pintar_botones()
        self.render(self.canvas.yview()[0])
        self.pie.config(text=t("pie_elegir_ref"))

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
        self._aplicar_cursor()
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()
        self._refrescar_panel()
        self.pie.config(text=t("pie_ref_guardada"))

    def cancelar_pendientes(self):
        """Esc: abandonar lo que se estaba por atar, sin tocar nada."""
        algo = bool(self.ancla_pendiente or self.refiriendo)
        self.ancla_pendiente = None
        self.refiriendo = []
        if algo:
            self._aplicar_cursor()
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
        """Manda al portapapeles el texto del documento seleccionado."""
        if not self._texto_sel:
            return
        self.app.clipboard_clear()
        self.app.clipboard_append(self._texto_sel)
        self.app.update()
        # Lo ultimo que se copio es lo que se pega: si despues de copiar marcas
        # se copia texto, Ctrl+V ya no pega aquellas marcas.
        self.app.marcas_copiadas = None
        self.pie.config(text=t("pie_copiado") % len(self._texto_sel))

    # --- copiar, cortar y pegar marcas (Ctrl+C / Ctrl+X / Ctrl+V) ---------

    def copiar(self):
        """Ctrl+C: con marcas elegidas, las copia; si no, copia el texto del PDF
        elegido. Como en cualquier editor, copia lo que esta seleccionado."""
        import copy
        marcas = self._marcas_seleccionadas()
        if not marcas:
            self.copiar_texto()
            return False
        # Las marcas copiadas viven en el programa (no en el portapapeles de
        # Windows): sirven para pegarlas en otra pagina u otro PDF.
        self.app.marcas_copiadas = {"marcas": copy.deepcopy(marcas), "ruta": self.ruta,
                                    "pno": self.pno, "veces": 0}
        self.pie.config(text=t("pie_copiadas") % len(marcas))
        return True

    def cortar(self):
        """Ctrl+X: copiar las marcas elegidas y sacarlas de la hoja."""
        if self._marcas_seleccionadas() and self.copiar():
            self._borrar_seleccion()

    def pegar(self, punto=None):
        """Ctrl+V: pega las marcas copiadas y las deja elegidas.

        En la misma pagina, la copia cae corrida un poco (y cada pegado un poco
        mas), para que no quede escondida justo encima de la original. En otra
        pagina cae en el mismo lugar. Con 'punto' (menu del clic derecho,
        "Pegar aca"), cae donde se hizo el clic. Nunca queda fuera de la hoja.
        """
        import copy
        clip = getattr(self.app, "marcas_copiadas", None)
        if not clip or not clip["marcas"]:
            return
        self._cerrar_editor(confirmar=True)
        nuevas = copy.deepcopy(clip["marcas"])
        mismo_doc = A.misma_ruta(clip["ruta"], self.ruta)
        misma_pagina = mismo_doc and clip["pno"] == self.pno
        for mk in nuevas:
            mk.pop("nombre", None)          # la copia recibe su propio nombre al guardar
            if not misma_pagina:
                mk.pop("ancla", None)       # la frase atada es de la otra pagina
            if not mismo_doc:
                mk.pop("ref", None)         # y la marca referida, de otro PDF
        cajas = [self._bbox(mk) for mk in nuevas]
        x0, y0 = min(r.x0 for r in cajas), min(r.y0 for r in cajas)
        x1, y1 = max(r.x1 for r in cajas), max(r.y1 for r in cajas)
        if punto is not None:
            dx, dy = punto[0] - x0, punto[1] - y0
        elif misma_pagina:
            clip["veces"] += 1
            dx = dy = 12.0 * clip["veces"]
        else:
            dx = dy = 0.0
        hoja = self._pagina().rect
        dx = max(min(dx, hoja.width - x1), -x0)
        dy = max(min(dy, hoja.height - y1), -y0)
        for mk in nuevas:
            if mk["tipo"] == "lapiz":
                mk["trazos"] = [[(x + dx, y + dy) for (x, y) in tr] for tr in mk["trazos"]]
            else:
                mk["x"] += dx
                mk["y"] += dy
        if self.modo != "seleccionar":
            self.set_modo("seleccionar")
        self._instantanea()
        lista = self.marcas.setdefault(self.pno, [])
        inicio = len(lista)
        lista.extend(nuevas)
        self.seleccion = list(range(inicio, len(lista)))
        self.palabras_sel = []
        self._texto_sel = ""
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()
        self._refrescar_panel()
        self.pie.config(text=t("pie_pegadas") % len(nuevas))

    # --- acciones del panel -----------------------------------------------

    def _renombrar(self):
        marcas = self._marcas_seleccionadas()
        if len(marcas) != 1:
            return
        nuevo = A.limpiar_nombre(self.pnl_nombre.get())
        if not nuevo:
            self._refrescar_panel()
            return
        # Sin nombres repetidos: dos marcas con el mismo nombre se confundian
        # al reabrir (la frase de una terminaba en la otra).
        nuevo = self._nombre_libre(nuevo, marcas[0])
        self._instantanea()
        marcas[0]["nombre"] = nuevo
        self._refrescar_panel()
        self._marcar_sucio()
        self.pie.config(text=t("pie_renombrado") % nuevo)

    def _nombre_libre(self, nombre, propia):
        """'nombre' si ninguna otra marca lo usa; si no, 'nombre-2', '-3'..."""
        usados = {mk.get("nombre") for lista in self.marcas.values()
                  for mk in lista if mk is not propia}
        libre, n = nombre, 2
        while libre in usados:
            libre = "%s-%d" % (nombre, n)
            n += 1
        return libre

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
        # Si alguna parte estaba atada a una frase o a otra marca, el dibujo
        # unido lo hereda (antes se perdia al unificar).
        for clave in ("ancla", "ref"):
            valor = next((mk[clave] for mk in partes if mk.get(clave)), None)
            if valor:
                unido[clave] = valor
        for i in reversed(indices):
            lista.pop(i)
        lista.insert(indices[0], unido)
        self.seleccion = [indices[0]]
        self.render(self.canvas.yview()[0])
        self._marcar_sucio()
        self._refrescar_panel()
        self.pie.config(text=t("pie_unificados")
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
        lista = self.marcas[self.pno]
        indice = lista.index(mk)
        lista.pop(indice)
        self._limpiar_seleccion()
        self.render(self.canvas.yview()[0])
        # Se pasa TODO lo que la nota era (frase atada, referencia, color, lugar
        # en la lista): antes, editar una nota atada a una frase le borraba la
        # frase, y cancelar la edicion borraba la nota entera.
        self._abrir_editor((mk["x"], mk["y"]), texto=mk.get("texto", ""),
                           nombre=mk.get("nombre", ""), ancla=mk.get("ancla"),
                           original=(indice, mk))

    def mostrar_ayuda(self):
        ayuda.Ventana(self.app, ruta_errores=errores.ARCHIVO)

    # ---------------------------------------------------- editor de texto ----

    def _abrir_editor(self, punto, texto="", nombre="", ancla=None, original=None):
        # original = (indice, marca) cuando se edita una nota que ya existia:
        # sirve para devolverla tal cual si se cancela, y para conservar su
        # color, su referencia y su lugar en la lista al confirmar.
        self._editor_original = original
        self._editor_color = original[1]["color"] if original else self.color
        self._editor_ancho = original[1].get("ancho") if original else None
        self._editor_cuerpo = original[1].get("cuerpo") if original else (
            None if abs(self.cuerpo_nuevas - A.CUERPO_NOTA) < 0.05 else self.cuerpo_nuevas)
        # Una nota con ancho elegido se edita con ESE ancho (el que eligio el
        # usuario); una nueva hecha con un clic crece con el texto.
        self._editor_fijo = bool(self._editor_ancho)
        self._editor_alto = None
        f = A.escala_nota(self._editor_cuerpo)
        # La frase que estaba esperando (Comentar esta frase) se toma ACA, al
        # abrir el cuadro: si despues la nota queda vacia, la frase no queda
        # viva para pegarse a la marca siguiente.
        if ancla is None and original is None:
            ancla = self.ancla_pendiente
        self.ancla_pendiente = None
        # Que la nota entre entera en la hoja. Si se hace clic cerca del borde
        # derecho, sin esto el cuadro de escribir se sale de la ventana (se
        # escribe a ciegas) y la nota queda con medio texto fuera de la pagina,
        # cortado en el PDF que recibe el agente. Se corre hacia adentro. Una
        # nota que ya existe se mide con su tamano real (antes, editar una nota
        # corta pegada al borde la hacia saltar a la izquierda).
        rect = self._pagina().rect
        if original is not None:
            caja = self._bbox(original[1])
            ancho_caja, alto_caja = caja.width, caja.height
        else:
            ancho_caja, alto_caja = A.ANCHO_NOTA, A.ALTO_LINEA + 6.0
        x = min(max(2.0, punto[0]), max(2.0, rect.width - ancho_caja - 2.0))
        y = min(max(2.0, punto[1]), max(2.0, rect.height - alto_caja))
        punto = (x, y)
        self._editor_xy = punto
        self._editor_nombre = nombre
        self._editor_ancla = ancla
        cx, cy = self._a_canvas(*punto)
        # El cuadro de escribir se ve IGUAL que la nota terminada: misma letra
        # (en pixeles, tamano negativo), mismo margen interno y mismo alto de
        # renglon. Y es fit to size mientras se escribe (ver _crecer_editor).
        cuerpo = max(6, int(round(A.CUERPO_NOTA * f * self.zoom)))
        fuente = tkfont.Font(family="Helvetica", size=-cuerpo)
        self._editor_fuente = fuente
        pad = max(2, int(round(A.PAD_NOTA * f * self.zoom)))
        # Medio "aire" arriba y medio abajo de cada renglon: asi cada linea mide
        # ALTO_LINEA, igual que en A.tope_renglon.
        aire = max(0, int(round(A.ALTO_LINEA * f * self.zoom)) - fuente.metrics("linespace"))
        self._editor = tk.Text(self.canvas, wrap="word", height=1, undo=True,
                               font=fuente, bg=a_hex(A.FONDO_NOTA),
                               fg=a_hex(self._editor_color), relief="solid", bd=1,
                               highlightthickness=0, padx=pad, pady=pad,
                               spacing1=aire // 2, spacing3=aire - aire // 2,
                               insertbackground=a_hex(self._editor_color))
        # Cuadro auxiliar escondido para medir los renglones (ver _renglones_tk).
        self._medidor = tk.Text(self.canvas, wrap="word", font=fuente, padx=pad, pady=pad,
                                bd=1, relief="solid", highlightthickness=0,
                                spacing1=aire // 2, spacing3=aire - aire // 2)
        self._medidor.place(x=-20000, y=-20000, width=100, height=100)
        self._editor_win = self.canvas.create_window(cx, cy, anchor="nw", window=self._editor,
                                                     width=A.ANCHO_MIN_NOTA * f * self.zoom)
        if texto:
            self._editor.insert("1.0", texto)
        self._editor.focus_set()
        self._crecer_editor()
        self._editor.bind("<Escape>", lambda e: (self._cerrar_editor(confirmar=True), "break")[1])
        self._editor.bind("<Control-Return>", lambda e: (self._cerrar_editor(confirmar=True), "break")[1])
        # El cuadro se acomoda EN EL MOMENTO en que cambia el texto (evento
        # <<Modified>>), no al soltar la tecla: Tk mete la letra al apretar, y si el
        # cuadro se agrandaba recien al soltar, entre una cosa y otra el texto se
        # partia en un renglon que no entraba en el alto viejo y saltaba de lugar
        # (el parpadeo al llegar al borde derecho).
        self._editor.bind("<<Modified>>", self._al_modificar_editor)
        self.pie.config(text=t("pie_escribiendo"))

    def _al_modificar_editor(self, _e=None):
        """Cambio el texto del cuadro: acomodarlo antes de que se vuelva a dibujar."""
        ed = self._editor
        if ed is None or not ed.edit_modified():
            return
        ed.edit_modified(False)     # rearmar el aviso para el proximo cambio
        self._crecer_editor()

    def _renglones_tk(self, texto, ancho_px):
        """Cuantos renglones parte Tk de verdad un texto en un cuadro de ese ancho.

        Se mide en un cuadro auxiliar escondido (fuera del lienzo visible) con la
        misma letra, margenes y ancho que el de escribir. No se usa el conteo
        que trae Tk ("count -displaylines"): con datos atrasados o palabras muy
        largas contaba un renglon de menos. Preguntar renglon por renglon es
        exacto. Y como el auxiliar no se ve, el cuadro real recibe ancho y alto
        de una sola vez: sin estados intermedios que parpadeen.
        """
        m = self._medidor
        if m is None:
            return None
        try:
            m.place_configure(width=max(1, int(ancho_px)), height=4000)
            m.delete("1.0", "end")
            m.insert("1.0", texto)
            m.update_idletasks()
            n, i = 0, "1.0"
            while n < 800:
                if not m.dlineinfo(i):
                    break
                n += 1
                siguiente = m.index("%s + 1 display lines" % i)
                if siguiente == i:
                    break
                i = siguiente
            return max(1, n)
        except tk.TclError:
            return None

    def _crecer_editor(self, _e=None):
        """El cuadro de escribir: mientras se escribe manda el tamano elegido.

        Con ancho elegido (arrastrando con Texto, o una nota que ya lo tenia),
        el cuadro mide exacto eso, y de alto lo elegido; si el texto no entra,
        crece hacia abajo. Hecha con un clic, crece con el texto hasta el ancho
        de entrada. Al cerrar, la nota se ajusta al texto (fit to size).
        El alto sale de los renglones que Tk parte de verdad (_renglones_tk).
        """
        ed = self._editor
        if ed is None:
            return
        texto = ed.get("1.0", "end-1c")
        pad = int(ed.cget("padx"))
        f = A.escala_nota(self._editor_cuerpo)
        if self._editor_fijo and self._editor_ancho:
            ancho = self._editor_ancho * self.zoom
        else:
            lineas = A.lineas_nota(texto, self._editor_ancho, self._editor_cuerpo)
            # Ancho = el renglon mas ancho TAL COMO LO DIBUJA la pantalla (misma
            # razon que en _dibujar_marca), mas margenes, borde y el cursor.
            mas_ancho = max([self._editor_fuente.measure(l) for l in lineas] + [0])
            ancho = max(A.ANCHO_MIN_NOTA * f * self.zoom, mas_ancho + 2 * pad + 2 + 4)
        renglones = self._renglones_tk(texto, ancho) or 1
        if self._editor_alto:
            util = self._editor_alto - 2 * A.PAD_NOTA * f
            renglones = max(renglones, int(max(1, round(util / (A.ALTO_LINEA * f)))))
        # Ancho y alto juntos, en el mismo instante: nada intermedio se dibuja.
        self.canvas.itemconfigure(self._editor_win, width=ancho)
        ed.config(height=renglones)
        ed.yview_moveto(0)

    def _cerrar_editor(self, confirmar=True):
        if self._editor is None:
            return
        texto = self._editor.get("1.0", "end-1c") if confirmar else ""
        ed, win, xy = self._editor, self._editor_win, self._editor_xy
        self._editor = self._editor_win = self._editor_xy = None
        self._nota_arrastre = None
        try:
            self.canvas.delete(win)
            self.canvas.delete("guia_nota")
            ed.destroy()
            if self._medidor is not None:
                self._medidor.destroy()
        except Exception:
            pass
        self._medidor = None
        original = getattr(self, "_editor_original", None)
        color = getattr(self, "_editor_color", None) or self.color
        texto = texto.rstrip()
        if original is not None:
            # Se estaba EDITANDO una nota que ya existia.
            indice, previa = original
            lista = self.marcas.setdefault(self.pno, [])
            indice = min(indice, len(lista))
            if not confirmar or texto == previa.get("texto", ""):
                # Cancelada, o sin cambios: vuelve tal cual estaba, y se saca la
                # instantanea de deshacer que se tomo al empezar a editar.
                lista.insert(indice, previa)
                if self.historial:
                    self.historial.pop()
            elif texto.strip():
                editada = dict(previa)
                editada.update({"texto": texto, "x": xy[0], "y": xy[1], "color": color})
                self._encajar_nota(editada)
                lista.insert(indice, editada)
                self._marcar_sucio()
            else:
                self._marcar_sucio()        # se borro todo el texto: la nota se va
            self._editor_original = None
            self.render(self.canvas.yview()[0])
        elif texto.strip():
            nueva = {"tipo": "texto", "x": xy[0], "y": xy[1],
                     "texto": texto, "color": color,
                     "nombre": self._editor_nombre or ""}
            if self._editor_ancla:
                nueva["ancla"] = self._editor_ancla
            if self._editor_ancho:
                nueva["ancho"] = self._editor_ancho     # elegido arrastrando al crearla
            if self._editor_cuerpo:
                nueva["cuerpo"] = self._editor_cuerpo   # la letra elegida en el panel
            self._encajar_nota(nueva)
            self._agregar(nueva)
        self._editor_nombre = ""
        self._editor_ancla = None
        self._editor_original = None
        # Volver a Seleccionar: el estado en reposo es siempre el mismo.
        if self.modo == "texto":
            self.modo = "seleccionar"
            self._aplicar_cursor()
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
        # significar nada y apuntarian a marcas equivocadas. Por lo mismo se
        # abandona lo que estaba "por atarse": una referencia empezada en una
        # pagina se escribia en la marca con el mismo numero de la otra, y una
        # frase pendiente se ataba con las coordenadas de la pagina anterior.
        self._limpiar_seleccion()
        if self.ancla_pendiente or self.refiriendo:
            self.ancla_pendiente = None
            self.refiriendo = []
            self._aplicar_cursor()
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
        # El estado COMPLETO de cada marca (color, nombre, frase atada,
        # referencia, ancho...). Antes solo miraba la posicion y el texto: cambiar
        # el color de una nota o renombrar una marca no contaba como cambio, no
        # aparecia el asterisco y al cerrar se perdia sin avisar.
        import json
        return json.dumps({str(p): l for p, l in self.marcas.items() if l},
                          sort_keys=True, default=list, ensure_ascii=False)

    @property
    def sucio(self):
        return self._firma() != self.firma_guardada

    def _marcar_sucio(self):
        self.app.actualizar_titulo()
        self._actualizar_pie()

    def cuenta_marcas(self):
        return sum(len(v) for v in self.marcas.values())

    def _actualizar_pie(self):
        """La barra de abajo en reposo: vacia (ver _construir_widgets), salvo
        que haya un paso a medio hacer, que se sigue indicando aunque se
        cambie el zoom o la vista. Mientras se escribe una nota, conserva la
        indicacion de la nota."""
        if self._editor is not None:
            return
        if self.refiriendo:
            texto = t("pie_elegir_ref")
        elif self.ancla_pendiente:
            texto = t("pie_comentar" if self.modo == "texto" else "pie_dibujar") \
                % self.ancla_pendiente.get("cita", "")[:80]
        else:
            texto = ""
        self.pie.config(text=texto)

    # ------------------------------------------------------------ guardar ----

    def guardar(self, como=False):
        """Guardar (Ctrl+S) o, con como=True, "Guardar como..." (Ctrl+Shift+S).

        Como en los editores (decision 7): la primera vez pregunta el nombre de
        la copia; despues Guardar escribe encima de esa misma copia sin
        preguntar y solo avisa abajo. El cartel grande con el mensaje para el
        chat sale cuando se elige un nombre (la primera vez o con "Guardar
        como..."). El PDF original nunca se toca.
        """
        self.dialogo_guardado = None
        self._cerrar_editor(confirmar=True)
        if self.cuenta_marcas() == 0:
            if not messagebox.askyesno(t("dlg_sin_marcas_titulo"),
                                       t("dlg_sin_marcas_cuerpo"),
                                       parent=self):
                return
        preguntar = como or not self.ruta_guardado
        if preguntar:
            carpeta = os.path.dirname(self.ruta_guardado or self.ruta)
            base = os.path.splitext(os.path.basename(self.ruta))[0]
            for suf in SUFIJOS_DEVOLUCION:
                if base.endswith(suf):
                    base = base[:-len(suf)]
            sugerida = ruta_libre(carpeta, base)
            destino = filedialog.asksaveasfilename(
                parent=self, title=t("dlg_guardar_titulo"),
                initialdir=carpeta, initialfile=os.path.basename(sugerida),
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if not destino:
                return
        else:
            destino = self.ruta_guardado

        # Guardar encima del PDF que se esta mirando: Windows no deja reemplazar
        # un archivo abierto, asi que hay que soltarlo y volver a tomarlo. Pasa
        # siempre que se reabre una devolucion para agregarle algo mas.
        mismo = A.misma_ruta(destino, self.ruta)
        y_actual = self.canvas.yview()[0]
        if mismo:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
        self._ocupado(True)
        try:
            A.guardar(self.ruta, destino, self.marcas)
        except A.MarcasNoGuardadas as err:
            errores.anotar("Guardado incompleto en %s" % os.path.basename(destino), err)
            messagebox.showwarning(
                t("dlg_incompleto_titulo"),
                t("dlg_incompleto_cuerpo")
                % (destino, "\n".join(err.fallos)), parent=self)
            return
        except Exception as err:
            errores.anotar("No se pudo guardar en %s" % destino, err)
            messagebox.showerror(
                t("dlg_no_guardar_titulo"),
                t("dlg_no_guardar_cuerpo") % err, parent=self)
            return
        finally:
            self._ocupado(False)
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
        self.ruta_guardado = destino
        self.app.actualizar_titulo()
        # El mensaje para la IA NO se copia solo (pisaba el portapapeles sin
        # avisar): se copia con el boton "Copiar" del cartel, o con "Copiar
        # prompt" en la flechita de Guardar (decision del Disenador, sept-2026).
        if preguntar:
            self.dialogo_guardado = DialogoGuardado(self.app, destino)
        else:
            self.pie.config(text=t("pie_guardado") % os.path.basename(destino))

    def copiar_prompt(self):
        """Copia el mensaje para la IA de la devolucion guardada."""
        if not self.ruta_guardado:
            return
        self.app.clipboard_clear()
        self.app.clipboard_append(mensaje_para_el_chat(self.ruta_guardado))
        self.app.update()           # dejar el portapapeles firme en Windows
        self.pie.config(text=t("pie_prompt_copiado"))

    def _ocupado(self, si):
        """Cursor de espera mientras se guarda: un PDF grande tarda unos
        segundos y, sin aviso, la ventana parecia colgada."""
        try:
            self.app.config(cursor="watch" if si else "")
            if si:
                self.canvas.config(cursor="watch")
                self.pie.config(text=t("pie_guardando"))
                self.app.update_idletasks()
            else:
                self._aplicar_cursor()
                self._actualizar_pie()      # que no quede "Guardando..." colgado
        except Exception:
            pass


def mensaje_para_el_chat(destino):
    """El texto que se copia al guardar.

    ESTA ESCRITO PARA QUE LO LEA UN AGENTE, no el usuario: es lo que el usuario pega en el
    chat y con eso el otro lado tiene que entender, sin preguntar nada, que es
    esto, donde esta y como leerlo. Por eso arranca diciendo que es, en una
    linea, y sigue con el comando exacto.
    """
    extractor = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "leer_devolucion.py")
    return t("mensaje_chat") % (destino, _python_para_el_agente(), extractor, destino)


def _python_para_el_agente():
    """Ruta completa del Python que tiene las librerias.

    Con "python" a secas, el agente podia terminar usando otro Python de la
    maquina (hay mas de uno) y fallar por falta de pymupdf. Se da el python.exe
    que esta al lado del que corre el programa (no el pythonw, que no muestra
    nada en la consola).
    """
    carpeta = os.path.dirname(sys.executable)
    candidato = os.path.join(carpeta, "python.exe")
    if os.path.isfile(candidato):
        return candidato
    return sys.executable if not os.path.basename(sys.executable).lower().startswith("pythonw") \
        else "python"


class DialogoGuardado(tk.Toplevel):
    """Avisa donde quedo el archivo y deja todo listo para pegar en el chat."""

    def __init__(self, app, destino):
        super().__init__(app)
        self.title(t("dlg_guardado_titulo"))
        self.resizable(False, False)
        self.transient(app)
        marco = ttk.Frame(self, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text=t("dlg_devolucion_guardada"), font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(marco,
                  text=t("dlg_guardado_info"),
                  foreground="#333", justify="left").pack(anchor="w", pady=(4, 10))
        caja = tk.Text(marco, width=92, height=13, wrap="word", relief="solid", bd=1,
                       font=("Consolas", 9), bg="#F7F7F7")
        caja.insert("1.0", mensaje_para_el_chat(destino))
        caja.config(state="disabled")
        caja.pack(fill="x")
        fila = ttk.Frame(marco)
        fila.pack(fill="x", pady=(14, 0))
        # "Copiar" parpadea (Copiar / COPIAR) hasta que se toca: el mensaje no se
        # copia solo, y asi no se pasa por alto. Tocado, queda quieto.
        self.app_, self.destino = app, destino
        self.btn_copiar = tk.Button(fila, text=t("dlg_copiar"), width=10,
                                    font=("Segoe UI", 9, "bold"), command=self.copiar)
        self.btn_copiar.pack(side="left")
        self.copiado = False
        self._parpadeo = None
        self._parpadear(True)
        ttk.Button(fila, text=t("dlg_abrir_carpeta"),
                   command=lambda: abrir_en_explorador(destino)).pack(side="left", padx=6)
        ttk.Button(fila, text=t("dlg_copiar_ruta"),
                   command=lambda: (app.clipboard_clear(), app.clipboard_append(destino),
                                    app.update())).pack(side="left")
        ttk.Button(fila, text=t("dlg_listo"), command=self.destroy).pack(side="right")
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + 160
        self.geometry("+%d+%d" % (max(0, x), max(0, y)))
        self.grab_set()
        self.focus_set()

    def _parpadear(self, mayus):
        if self.copiado:
            return
        try:
            texto = t("dlg_copiar")
            self.btn_copiar.config(text=texto.upper() if mayus else texto)
            self._parpadeo = self.after(550, lambda: self._parpadear(not mayus))
        except tk.TclError:
            pass

    def copiar(self):
        self.copiado = True
        if self._parpadeo is not None:
            try:
                self.after_cancel(self._parpadeo)
            except tk.TclError:
                pass
        self.btn_copiar.config(text=t("dlg_copiar"))
        self.app_.clipboard_clear()
        self.app_.clipboard_append(mensaje_para_el_chat(self.destino))
        self.app_.update()


def abrir_en_explorador(ruta):
    try:
        subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)])
    except Exception:
        pass


# ====================================================================== app ==

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(t("app_titulo"))
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
        self._ultimo_cartel = -1e9
        self.report_callback_exception = self._fallo_no_previsto

        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(fill="both", expand=True)
        self.biblioteca = None
        self.visor = None
        self.mostrar_biblioteca()

        # Marcas copiadas con Ctrl+C, para pegarlas con Ctrl+V (en otra pagina o
        # en otro PDF). Viven en el programa y no en el portapapeles de Windows.
        self.marcas_copiadas = None

        self.bind("<Key>", self._tecla)
        # Ctrl+S guarda aunque se este escribiendo una nota (guardar la cierra
        # primero): es lo que se espera en cualquier programa. Ctrl+Shift+S es
        # "Guardar como..." (Tk ve la S mayuscula con Shift, y con Bloq Mayus la
        # ve mayuscula sin Shift: por eso los cuatro).
        for combo in ("<Control-s>", "<Control-S>"):
            self.bind(combo, lambda e: (self.visor and self.visor.guardar(), "break")[1])
        for combo in ("<Control-Shift-S>", "<Control-Shift-s>"):
            self.bind(combo, lambda e: (self.visor and self.visor.guardar(como=True),
                                        "break")[1])
        # F3 / Shift+F3: siguiente y anterior de la ultima busqueda.
        self.bind("<F3>", lambda e: (self.visor and self.visor.buscar(1), "break")[1])
        self.bind("<Shift-F3>", lambda e: (self.visor and self.visor.buscar(-1), "break")[1])
        # Los demas atajos con Ctrl NO se disparan mientras se escribe en un
        # cuadro de texto (el nombre de una marca, el numero de pagina, una
        # nota): ahi Ctrl+Z / Ctrl+C / Ctrl+A son del cuadro, no de las marcas.
        # Antes, Ctrl+C en el nombre de una marca pisaba el portapapeles con el
        # texto del PDF seleccionado.
        atajos = {
            "<Control-z>": lambda v: v.deshacer(),
            # Rehacer: Ctrl+Y es lo de Windows; Ctrl+Shift+Z, lo de los
            # programas de diseno.
            "<Control-y>": lambda v: v.rehacer(),
            "<Control-Shift-Z>": lambda v: v.rehacer(),
            "<Control-Shift-z>": lambda v: v.rehacer(),
            # Copiar, cortar y pegar: las marcas elegidas o, si no hay, el
            # texto del PDF elegido (Ctrl+C).
            "<Control-c>": lambda v: v.copiar(),
            "<Control-x>": lambda v: v.cortar(),
            "<Control-v>": lambda v: v.pegar(),
            "<Control-a>": lambda v: v.seleccionar_todo(),
            # Zoom con los atajos de Acrobat/Edge: Ctrl+0 hoja entera, Ctrl+1
            # tamano real, Ctrl+2 ancho, Ctrl+ +/- acercar y alejar.
            "<Control-Key-0>": lambda v: v.zoom_pagina(),
            "<Control-Key-1>": lambda v: v.zoom_real(),
            "<Control-Key-2>": lambda v: v.zoom_ancho(),
            "<Control-plus>": lambda v: v.set_zoom(v.zoom * 1.2),
            "<Control-equal>": lambda v: v.set_zoom(v.zoom * 1.2),
            "<Control-KP_Add>": lambda v: v.set_zoom(v.zoom * 1.2),
            "<Control-minus>": lambda v: v.set_zoom(v.zoom / 1.2),
            "<Control-KP_Subtract>": lambda v: v.set_zoom(v.zoom / 1.2),
            "<Control-Home>": lambda v: v.ir_pagina(0),
            "<Control-End>": lambda v: v.ir_pagina(v.doc.page_count - 1),
            "<Control-f>": lambda v: v.abrir_busqueda(),
            # Con Bloq Mayus activado Tk ve la letra en mayuscula: sin estas,
            # Ctrl+Z, Ctrl+C, etc. no hacian nada. (Ctrl+Shift+Z sigue siendo
            # rehacer: es una combinacion mas especifica y gana.)
            "<Control-Z>": lambda v: v.deshacer(),
            "<Control-Y>": lambda v: v.rehacer(),
            "<Control-C>": lambda v: v.copiar(),
            "<Control-X>": lambda v: v.cortar(),
            "<Control-V>": lambda v: v.pegar(),
            "<Control-A>": lambda v: v.seleccionar_todo(),
            "<Control-F>": lambda v: v.abrir_busqueda(),
        }
        for combo, accion in atajos.items():
            self.bind(combo, self._atajo_visor(accion))
        # Estos funcionan tambien en la pantalla de la carpeta.
        for combo in ("<Control-o>", "<Control-O>"):
            self.bind(combo, lambda e: (self.abrir_archivo(), "break")[1])
        for combo in ("<Control-w>", "<Control-W>"):
            self.bind(combo, lambda e: (self.volver_biblioteca(), "break")[1])
        self.bind("<F1>", lambda e: (self.mostrar_ayuda(), "break")[1])
        # F5: volver a leer la carpeta, como en el Explorador de Windows.
        self.bind("<F5>", lambda e: (self.visor is None and self.biblioteca is not None
                                     and self.biblioteca.refrescar(
                                         self.biblioteca._ruta_elegida()), "break")[1])
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

    def _escribiendo(self):
        """True si el teclado esta en un cuadro de texto (nota, nombre, pagina)."""
        try:
            return isinstance(self.focus_get(), (tk.Entry, tk.Text, ttk.Entry))
        except Exception:
            return False

    def _atajo_visor(self, accion):
        """Arma el manejador de un atajo con Ctrl que actua sobre el visor."""
        def manejador(_e):
            if self.visor is None or self._escribiendo():
                return None
            accion(self.visor)
            return "break"
        return manejador

    def abrir_archivo(self):
        """Ctrl+O: abrir un PDF de cualquier carpeta, sin pasar por la lista."""
        if self.visor is not None:
            carpeta = os.path.dirname(self.visor.ruta)
        elif self.biblioteca is not None:
            carpeta = self.biblioteca.carpeta
        else:
            carpeta = CARPETA_INICIAL
        ruta = filedialog.askopenfilename(parent=self, title=t("dlg_abrir_titulo"),
                                          initialdir=carpeta,
                                          filetypes=[("PDF", "*.pdf")])
        if not ruta:
            return
        if self.visor is not None and not self._confirmar_descartar():
            return
        # La carpeta de ese PDF pasa a ser la de la lista, y queda recordada:
        # "< Carpeta" vuelve ahi, y la proxima vez el programa abre ahi.
        if self.biblioteca is not None:
            self.biblioteca.cambiar_carpeta(os.path.dirname(ruta), seleccionar=ruta)
        self.abrir_pdf(ruta)

    def mostrar_ayuda(self):
        ayuda.Ventana(self, ruta_errores=errores.ARCHIVO)

    # ---------------------------------------------------------------- idioma --

    def cambiar_idioma(self):
        """El boton ES/EN: alterna el idioma, lo recuerda y rehace la interfaz.

        Se rehace con after_idle y no en el acto porque el boton que se acaba de
        apretar vive en la barra que estamos por destruir: primero se termina de
        atender el clic, despues se rehacen los widgets. No se pierde el PDF
        abierto ni las marcas: solo cambian los textos."""
        nuevo = "en" if idiomas.idioma_actual() == "es" else "es"
        idiomas.set_idioma(nuevo)
        self.after_idle(self._reconstruir_idioma)

    def _reconstruir_idioma(self):
        # Se rehacen las dos pantallas si existen: la que se ve ahora y la que
        # esta escondida, para que al volver ya este en el idioma nuevo.
        if self.visor is not None:
            self.visor.retraducir()
        if self.biblioteca is not None:
            self.biblioteca.retraducir()
        self.actualizar_titulo()

    def _fallo_no_previsto(self, tipo, valor, traza):
        """Cualquier error que se escape de un boton o de un evento cae aca.

        Antes estos se perdian en el aire: el programa quedaba raro y no habia
        rastro de por que. Ahora se anotan todos y el usuario puede pasarle el
        archivo entero al agente.
        """
        try:
            cuantos = errores.anotar("Fallo no previsto en la ventana", valor)
            # Un cartel cada tanto: si un error se repetia en cada movimiento del
            # mouse, salian decenas de carteles encimados. Los demas quedan igual
            # anotados en el registro.
            import time
            ahora = time.monotonic()
            if ahora - self._ultimo_cartel < 4.0:
                return
            self._ultimo_cartel = ahora
            self.after(50, lambda: messagebox.showerror(
                t("app_fallo_titulo"),
                t("app_fallo_cuerpo")
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

    def mostrar_biblioteca(self, seleccionar=None):
        self._soltar_visor()
        if self.biblioteca is None:
            self.biblioteca = Biblioteca(self)
        self.biblioteca.pack(fill="both", expand=True)
        self.biblioteca.refrescar(seleccionar=seleccionar)
        self.actualizar_titulo()

    def abrir_pdf(self, ruta):
        try:
            visor = Visor(self, ruta)
        except Exception as err:
            errores.anotar("No se pudo abrir %s" % os.path.basename(ruta), err)
            messagebox.showerror(t("app_no_abrir_titulo"),
                                 t("app_no_abrir_cuerpo") % (os.path.basename(ruta), err),
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
        # Al volver, queda elegido en la lista el PDF que se estaba mirando.
        self.mostrar_biblioteca(seleccionar=self.visor.ruta if self.visor else None)

    def _confirmar_descartar(self):
        if self.visor is None:
            return True
        # Una nota a medio escribir todavia no es una marca: sin esto, salir o
        # cerrar la tiraba sin preguntar nada, porque el programa se veia "limpio".
        self.visor._cerrar_editor(confirmar=True)
        if not self.visor.sucio:
            return True
        r = messagebox.askyesnocancel(
            t("app_sin_guardar_titulo"),
            t("app_sin_guardar_cuerpo")
            % self.visor.cuenta_marcas(), parent=self)
        if r is None:
            return False
        if r:
            self.visor.guardar()
            # Esperar a que se lea el cartel de "guardado" antes de cerrar: si
            # no, aparecia y desaparecia en el acto al salir con "Si, guardar".
            dialogo = self.visor.dialogo_guardado
            if dialogo is not None and dialogo.winfo_exists():
                self.wait_window(dialogo)
            return not self.visor.sucio
        return True

    def actualizar_titulo(self):
        if self.visor is None:
            carpeta = self.biblioteca.carpeta if self.biblioteca is not None else CARPETA_INICIAL
            self.title(t("app_titulo_carpeta")
                       % (os.path.basename(carpeta.rstrip("\\/")) or carpeta))
        else:
            self.title(t("app_titulo_doc")
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
        # La letra subrayada de cada herramienta la elige (decision 9): sola o
        # con Alt, como las letras subrayadas de Windows. Sale del nombre en el
        # idioma activo (en ingles, Erase = E).
        letras = {atajo_de(m): m for m in HERRAMIENTAS}
        # Las demas combinaciones con Ctrl o Alt tienen su propio atajo (o
        # ninguno): sin esto, Ctrl+D o Ctrl+T cambiaban de herramienta sin querer.
        if e.state & 0x0004:
            return
        if e.state & 0x20000:
            if k in letras:
                v.set_modo(letras[k])
                return "break"
            return
        if k == atajo_de("texto") and v.modo == "seleccionar" and v.comentar_seleccion():
            return          # habia texto elegido: la nota quedo atada a esa frase
        # Con marcas elegidas, las flechas las mueven (como en cualquier
        # editor); Shift las mueve de a 10 pt. Sin nada elegido, pasan de pagina.
        paso = 10.0 if e.state & 0x0001 else 1.0
        flechas = {"left": (-paso, 0), "right": (paso, 0), "up": (0, -paso), "down": (0, paso)}
        if k in flechas and v.seleccion:
            v.empujar_seleccion(*flechas[k])
            return
        if k in letras:
            v.set_modo(letras[k])
        elif k in ("return", "kp_enter"):
            # Enter con una nota elegida: editarla (como Figma o tldraw).
            v._editar_nota_seleccionada()
        elif k in ("delete", "backspace"):
            v._borrar_seleccion()
        # La barra espaciadora no hace nada (decision 8).
        elif k == "next":
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
            # Esc cancela o suelta, como en cualquier editor; nunca cierra el
            # documento (antes, sin nada pendiente, volvia a la carpeta y uno
            # perdia la hoja por querer deseleccionar). Salir: "< Carpeta" o Ctrl+W.
            if not v.cancelar_pendientes() and (v.seleccion or v._texto_sel):
                v._soltar_todo()
        elif k in ("plus", "equal", "kp_add"):
            v.set_zoom(v.zoom * 1.2)
        elif k in ("minus", "kp_subtract"):
            v.set_zoom(v.zoom / 1.2)


def main():
    # Recien aca (no al importar el modulo) se lee el idioma que dejo elegido
    # el usuario. Asi la red de seguridad (autotest.py), que crea la ventana sin pasar
    # por main(), corre siempre en espanol, que es lo que sus comprobaciones
    # esperan. Ver idiomas.py, decision 1.
    idiomas.cargar_idioma_guardado()
    # Igual con la carpeta: recien aca se lee la ultima que se uso y se
    # habilita recordar la proxima. El autotest no pasa por aca, asi que nunca
    # pisa la carpeta que dejo elegida el usuario.
    global CARPETA_INICIAL, RECORDAR_CARPETA
    CARPETA_INICIAL = carpeta_recordada() or CARPETA_INICIAL
    RECORDAR_CARPETA = True
    if _ERROR_IMPORT is not None:
        # Ojo: en esta maquina hay mas de un Python instalado y solo uno tiene
        # las librerias. Por eso el mensaje dice CUAL se esta usando: casi
        # siempre el problema es que se arranco con el Python equivocado, no
        # que falte instalar algo.
        raise RuntimeError(
            t("app_falta_libreria")
            % (_ERROR_IMPORT, sys.executable, sys.executable))
    app = App()
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.after(100, lambda: app.abrir_pdf(sys.argv[1]))
    app.mainloop()


def _morir_avisando(err):
    """Mostrar el error en pantalla en vez de no hacer nada.

    El programa arranca con pythonw.exe, que no tiene consola: si algo falla al
    iniciar (falta una libreria, se movio un archivo), sin esto el usuario haria doble
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
            t("app_no_arranco_titulo"),
            t("app_no_arranco_cuerpo") % (err, archivo))
        raiz.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as _err:
        _morir_avisando(_err)
        sys.exit(1)
