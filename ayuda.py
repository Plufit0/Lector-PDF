# -*- coding: utf-8 -*-
"""
ayuda.py — el instructivo del programa, en un solo lugar.

De aca salen las dos versiones: la ventana que abre el boton "?" y el archivo
"Como usar Lector PDF.txt" del escritorio. Estan escritas una sola vez a
proposito: si el instructivo viviera suelto en un .txt, cada cambio del programa
lo dejaria desactualizado sin que nadie se entere.
"""

import tkinter as tk
from tkinter import ttk

TITULO = "Lector PDF"
BAJADA = "Leer un manual de diseno y marcarlo encima para devolverselo al agente."

# ("seccion", texto) | ("parrafo", texto) | ("atajo", (tecla, que hace)) | ("nota", texto)
CONTENIDO = [
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
]


# ------------------------------------------------------------------ texto ----

def como_texto():
    """El instructivo en texto plano, para el archivo del escritorio."""
    import textwrap
    lineas = [TITULO.upper(), "=" * len(TITULO), "", BAJADA, ""]
    for clase, dato in CONTENIDO:
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
    lineas += ["", "", "El programa vive en C:\\Program Files\\Mios\\LectorPDF.",
               "Los errores quedan anotados en la carpeta LectorPDF de tus datos locales.",
               "Este mismo instructivo esta en el boton \u201c?\u201d del programa."]
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
        self.title("Como usar el Lector PDF")
        self.geometry("760x720")
        self.minsize(560, 420)
        self.transient(padre)
        self.configure(bg=FONDO)

        cabecera = tk.Frame(self, bg=AZUL)
        cabecera.pack(fill="x")
        tk.Label(cabecera, text=TITULO, bg=AZUL, fg="white",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=20, pady=(15, 0))
        tk.Label(cabecera, text=BAJADA, bg=AZUL, fg="#D7E6F5", wraplength=700,
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
            ttk.Button(pie, text="Ver errores de esta sesion",
                       command=lambda: self._mostrar_errores(ruta_errores)).pack(
                           side="left", padx=12, pady=10)
        ttk.Button(pie, text="Cerrar", command=self.destroy).pack(side="right", padx=12, pady=10)

        self.bind("<Escape>", lambda e: self.destroy())
        self.txt.bind("<MouseWheel>", self._rueda)
        self.focus_set()

    def _rueda(self, e):
        self.txt.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    def _pintar(self):
        t = self.txt
        for clase, dato in CONTENIDO:
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
        v.title("Errores de esta sesion")
        v.geometry("820x520")
        caja = tk.Text(v, wrap="none", font=("Consolas", 9))
        caja.pack(fill="both", expand=True)
        if os.path.exists(ruta):
            try:
                caja.insert("1.0", open(ruta, encoding="utf-8").read())
            except Exception as err:
                caja.insert("1.0", "No se pudo leer el registro: %s" % err)
        else:
            caja.insert("1.0", "No hubo ningun error en esta sesion.\n\n"
                               "Cuando haya alguno, queda anotado en:\n%s" % ruta)
        caja.config(state="disabled")
        ttk.Button(v, text="Cerrar", command=v.destroy).pack(pady=8)
