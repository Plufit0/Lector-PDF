# -*- coding: utf-8 -*-
"""
autotest.py — prueba el programa entero sin que nadie tenga que hacer clic.

Abre la ventana de verdad, simula trazos y notas sobre un PDF de prueba,
guarda, vuelve a abrir lo guardado y comprueba que todo cayo donde debia.
Es la red de seguridad del programa: si algo de esto falla, la devolucion que
se mande va a llegar incompleta o corrida de lugar.

    python autotest.py
"""

import os
import subprocess
import sys
import tempfile
import importlib.util

import pymupdf

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import anotaciones as A

# lector.pyw no se puede importar con import normal por la extension.
_spec = importlib.util.spec_from_file_location(
    "lector", os.path.join(AQUI, "lector.pyw"))
lector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lector)

fallos = []
hechos = []

# Ningun cuadro de dialogo puede frenar la prueba esperando un clic. Si el
# programa necesita mostrar uno, se anota y se sigue: un error que aparece en un
# cartel es igual de grave que uno que revienta, y asi la prueba lo cuenta.
dialogos = []


def _falso(nombre, devuelve=None):
    def f(*a, **kw):
        dialogos.append("%s: %s" % (nombre, " | ".join(str(x)[:160] for x in a)))
        return devuelve
    return f


lector.messagebox.showerror = _falso("showerror")
lector.messagebox.showwarning = _falso("showwarning")
lector.messagebox.showinfo = _falso("showinfo")
lector.messagebox.askyesno = _falso("askyesno", True)
lector.messagebox.askyesnocancel = _falso("askyesnocancel", True)


def check(condicion, descripcion, detalle=""):
    (hechos if condicion else fallos).append(descripcion + (("  -> " + detalle) if detalle and not condicion else ""))
    print(("  OK   " if condicion else "  FALLA ") + descripcion + (("  -> " + detalle) if detalle else ""))


COLOR_VERDE = (0.18, 0.62, 0.27)


class Evento:
    """Un evento de mouse falso, con lo unico que miran los handlers."""

    def __init__(self, x, y, delta=0, state=0):
        self.x, self.y, self.delta, self.state = x, y, delta, state


def pdf_de_prueba(ruta, paginas=3):
    d = pymupdf.open()
    for i in range(paginas):
        p = d.new_page(width=595, height=842)
        p.insert_text((72, 90), "PAGINA %d DEL MANUAL" % (i + 1), fontsize=20)
        p.insert_text((72, 300), "Parrafo tres punto dos sobre el anticheat", fontsize=11)
        p.insert_text((72, 500), "Segundo parrafo que habla de otra cosa", fontsize=11)
    d.save(ruta)
    d.close()


def main():
    tmp = tempfile.mkdtemp(prefix="autotest_lector_")
    origen = os.path.join(tmp, "manual.pdf")
    pdf_de_prueba(origen)

    print("\n== 1. Abrir el programa y el PDF ==")
    app = lector.App()
    app.update()
    app.abrir_pdf(origen)
    app.update()
    v = app.visor
    check(v is not None, "el visor abrio el PDF")
    v.zoom_ancho()
    app.update()
    check(v.doc.page_count == 3, "lee las 3 paginas")
    check(v.zoom > 0.5, "ajusta el zoom al ancho de la ventana", "zoom=%.2f" % v.zoom)
    check(v.modo == "seleccionar", "arranca en modo Seleccionar (el estado en reposo, como en los editores)")
    check(v.pno == 0, "y abre en la primera pagina", "abrio en la %d" % (v.pno + 1))
    check(v.entrada_pag.get() == "1", "el numero de pagina coincide con lo que se ve",
          repr(v.entrada_pag.get()))

    print("\n== 2. Dibujar un trazo con el mouse ==")
    v.set_modo("dibujar")   # ahora el reposo es Seleccionar: para marcar se elige Dibujar
    # Trazo horizontal a media pagina, en coordenadas de pantalla.
    y_pantalla = 200
    v._click(Evento(120, y_pantalla))
    for x in range(130, 320, 12):
        v._arrastre(Evento(x, y_pantalla))
    v._soltar(Evento(320, y_pantalla))
    app.update()
    marcas0 = v.marcas.get(0, [])
    check(len(marcas0) == 1, "quedo 1 marca en la pagina 1", "hay %d" % len(marcas0))
    if marcas0:
        trazo = marcas0[0]["trazos"][0]
        check(len(trazo) >= 5, "el trazo guardo varios puntos", "%d puntos" % len(trazo))
        # Verificar la conversion pantalla -> PDF con el zoom y el centrado reales.
        esperado_x = (v.canvas.canvasx(120) - v.ox) / v.zoom
        esperado_y = (v.canvas.canvasy(y_pantalla) - v.oy) / v.zoom
        check(abs(trazo[0][0] - esperado_x) < 0.6 and abs(trazo[0][1] - esperado_y) < 0.6,
              "el primer punto cayo en el lugar correcto del PDF",
              "guardado (%.1f, %.1f) esperado (%.1f, %.1f)" % (trazo[0][0], trazo[0][1], esperado_x, esperado_y))
        check(0 <= trazo[0][0] <= v.doc[0].rect.width and 0 <= trazo[0][1] <= v.doc[0].rect.height,
              "el punto cae dentro de la hoja")

    print("\n== 2b. El arrastre llega por los eventos reales de la ventana ==")
    # Los pasos anteriores llaman a los manejadores directamente. Esto en cambio
    # inyecta eventos en la ventana como los manda Windows, asi que comprueba lo
    # que falta: que los bind() esten bien conectados. Si alguien renombra un
    # manejador o se olvida un bind, aca se cae.
    v.marcas.clear()
    v.historial.clear()
    v.render()
    app.update()
    c = v.canvas
    c.event_generate("<ButtonPress-1>", x=140, y=180)
    for x in range(150, 300, 14):
        c.event_generate("<B1-Motion>", x=x, y=180)
    c.event_generate("<ButtonRelease-1>", x=300, y=180)
    app.update()
    check(len(v.marcas.get(0, [])) == 1,
          "arrastrar el mouse sobre la ventana dibuja de verdad",
          "quedaron %d marcas" % len(v.marcas.get(0, [])))

    print("\n== 2c. La rueda lee sin salir del modo dibujar ==")
    v.set_zoom(3.0)          # zoom alto para que la pagina no entre entera
    app.update()
    arriba = c.yview()[0]
    c.event_generate("<MouseWheel>", delta=-120, x=400, y=300)
    app.update()
    check(c.yview()[0] > arriba, "la rueda baja por la pagina",
          "%.3f -> %.3f" % (arriba, c.yview()[0]))
    check(v.modo == "dibujar", "y no cambia la herramienta: se lee y se marca sin alternar")
    marcas_antes_rueda = v.cuenta_marcas()
    check(marcas_antes_rueda == 1, "la rueda no deja marcas")
    v.zoom_pagina()
    app.update()

    print("\n== 2d. Con la hoja entera a la vista, la rueda pasa de pagina ==")
    pagina_antes = v.pno
    c.event_generate("<MouseWheel>", delta=-120, x=400, y=300)
    app.update()
    check(v.pno == pagina_antes + 1, "baja a la pagina siguiente",
          "quedo en %d" % (v.pno + 1))
    c.event_generate("<MouseWheel>", delta=120, x=400, y=300)
    app.update()
    check(v.pno == pagina_antes, "y vuelve a la anterior girando al reves")
    v.marcas.clear()
    v.historial.clear()
    v.render()
    app.update()
    # Rehacer el trazo del paso 2 para que sigan los pasos siguientes.
    v._click(Evento(120, y_pantalla))
    for x in range(130, 320, 12):
        v._arrastre(Evento(x, y_pantalla))
    v._soltar(Evento(320, y_pantalla))
    app.update()

    print("\n== 3. Un clic suelto no deja marcas fantasma ==")
    antes = v.cuenta_marcas()
    v._click(Evento(400, 300))
    v._soltar(Evento(400, 300))
    check(v.cuenta_marcas() == antes, "un clic sin arrastrar no deja nada")

    print("\n== 4. El zoom no mueve las marcas ==")
    punto_antes = v.marcas[0][0]["trazos"][0][0]
    v.set_zoom(v.zoom * 1.6)
    app.update()
    punto_despues = v.marcas[0][0]["trazos"][0][0]
    check(punto_antes == punto_despues, "las coordenadas siguen intactas tras hacer zoom")
    v.zoom_ancho()
    app.update()

    print("\n== 5. Escribir una nota ==")
    v.set_modo("texto")
    v._click(Evento(300, 400))
    app.update()
    check(v._editor is not None, "se abrio el cuadro para escribir")
    v._editor.insert("1.0", "Esto no va.\nRevisar el calculo entero.")
    v._cerrar_editor(confirmar=True)
    app.update()
    notas = [m for m in v.marcas.get(0, []) if m["tipo"] == "texto"]
    check(len(notas) == 1, "quedo la nota escrita")
    if notas:
        check(notas[0]["texto"] == "Esto no va.\nRevisar el calculo entero.",
              "la nota conserva el texto completo, con sus saltos de linea")
    check(v.modo == "seleccionar", "vuelve solo a Seleccionar despues de escribir")

    print("\n== 6. Una nota vacia no ensucia el PDF ==")
    antes = v.cuenta_marcas()
    v.set_modo("texto")
    v._click(Evento(350, 600))
    v._cerrar_editor(confirmar=True)
    check(v.cuenta_marcas() == antes, "una nota sin texto se descarta")

    print("\n== 7. Deshacer ==")
    antes = v.cuenta_marcas()
    v.deshacer()
    app.update()
    check(v.cuenta_marcas() == antes - 1, "Ctrl+Z saca la ultima marca")
    v.deshacer()   # deshace el trazo
    app.update()
    check(v.cuenta_marcas() == antes - 2, "y la anterior tambien")

    print("\n== 8. Marcar en varias paginas ==")
    v.set_modo("dibujar")
    v._click(Evento(150, 250))
    for x in range(160, 300, 14):
        v._arrastre(Evento(x, 250))
    v._soltar(Evento(300, 250))
    v.ir_pagina(2)
    app.update()
    check(v.pno == 2, "cambio a la pagina 3")
    v._click(Evento(150, 300))
    for x in range(160, 300, 14):
        v._arrastre(Evento(x, 320))
    v._soltar(Evento(300, 320))
    v.set_modo("texto")
    v._click(Evento(320, 380))
    app.update()
    v._editor.insert("1.0", "Aca falta el diagrama.")
    v._cerrar_editor(confirmar=True)
    app.update()
    check(len(v.marcas.get(0, [])) == 1 and len(v.marcas.get(2, [])) == 2,
          "las marcas quedan en la pagina donde se hicieron",
          "p1=%d p3=%d" % (len(v.marcas.get(0, [])), len(v.marcas.get(2, []))))

    print("\n== 8b. Una nota a medio escribir no se muda de pagina ==")
    # Si se cambia de pagina con las flechas mientras se escribe, la nota tiene
    # que quedar en la pagina donde se estaba escribiendo, no en la nueva.
    v.ir_pagina(1)
    app.update()
    v.set_modo("texto")
    v._click(Evento(300, 350))
    app.update()
    v._editor.insert("1.0", "nota de la pagina 2")
    v.ir_pagina(2)          # como hacer clic en la flecha ">"
    app.update()
    textos_p2 = [m["texto"] for m in v.marcas.get(1, []) if m["tipo"] == "texto"]
    textos_p3 = [m["texto"] for m in v.marcas.get(2, []) if m["tipo"] == "texto"]
    check("nota de la pagina 2" in textos_p2,
          "la nota quedo en la pagina donde se escribio")
    check("nota de la pagina 2" not in textos_p3,
          "y no se mudo a la pagina siguiente")
    v.ir_pagina(1)
    app.update()
    v.set_modo("borrar")
    for i, m in enumerate(list(v.marcas.get(1, []))):
        if m.get("texto") == "nota de la pagina 2":
            v.marcas[1].pop(i)
            break
    v.render()
    app.update()

    print("\n== 8c. Cancelar una nota mientras se escribe ==")
    v.ir_pagina(0)
    app.update()
    antes = v.cuenta_marcas()
    v.set_modo("texto")
    v._click(Evento(300, 300))
    app.update()
    v._editor.insert("1.0", "esto lo escribi sin querer")
    v.deshacer()            # Ctrl+Z mientras se escribe
    app.update()
    check(v.cuenta_marcas() == antes,
          "Ctrl+Z mientras se escribe cancela la nota y no borra nada mas",
          "habia %d, quedaron %d" % (antes, v.cuenta_marcas()))
    check(v._editor is None, "y cierra el cuadro de texto")

    print("\n== 8d. Saltar a una pagina escribiendo el numero ==")
    v.entrada_pag.delete(0, "end")
    v.entrada_pag.insert(0, "3")
    v._saltar_a_pagina()
    app.update()
    check(v.pno == 2, "escribir 3 y apretar Enter lleva a la pagina 3",
          "quedo en %d" % (v.pno + 1))
    v.entrada_pag.delete(0, "end")
    v.entrada_pag.insert(0, "999")
    v._saltar_a_pagina()
    app.update()
    check(v.pno == v.doc.page_count - 1, "un numero de mas no rompe: va a la ultima")
    v.entrada_pag.delete(0, "end")
    v.entrada_pag.insert(0, "hola")
    v._saltar_a_pagina()
    app.update()
    check(v.pno == v.doc.page_count - 1 and v.entrada_pag.get() == str(v.pno + 1),
          "y si se escribe cualquier cosa, se repone el numero real")
    v.ir_pagina(0)
    app.update()

    print("\n== 8e. Arreglos que salieron de la revision con agentes ==")
    # Este bloque marca y desmarca para probar; se guarda el estado y se repone
    # al final, porque los pasos que siguen cuentan con las marcas de antes.
    copia_marcas = dict((p, list(l)) for p, l in v.marcas.items())
    copia_historial = list(v.historial)
    copia_firma = v.firma_guardada

    # (a) El zoom no puede tirar la lectura al principio de la hoja.
    v.zoom_ancho()
    app.update()
    c.yview_moveto(0.5)
    app.update()
    antes_y = c.yview()[0]
    v.set_zoom(v.zoom * 1.3)
    app.update()
    check(abs(c.yview()[0] - antes_y) < 0.12,
          "al hacer zoom se queda donde se estaba leyendo",
          "%.2f -> %.2f" % (antes_y, c.yview()[0]))
    v.zoom_pagina()
    app.update()

    # (b) Una nota junto al borde derecho tiene que entrar entera en la hoja.
    ancho_hoja = v.doc[v.pno].rect.width
    v.set_modo("texto")
    borde = v._a_canvas(ancho_hoja - 12, 200)
    v._click(Evento(int(borde[0]), int(borde[1] - c.canvasy(0))))
    app.update()
    v._editor.insert("1.0", "nota pegada al borde derecho")
    v._cerrar_editor(confirmar=True)
    app.update()
    nota = [m for m in v.marcas.get(v.pno, []) if m["tipo"] == "texto"][-1]
    check(nota["x"] + A.ANCHO_NOTA <= ancho_hoja + 0.5,
          "una nota junto al borde derecho se corre para entrar entera en la hoja",
          "x=%.0f + %.0f vs hoja %.0f" % (nota["x"], A.ANCHO_NOTA, ancho_hoja))

    # (c) Un temblor de 3 px no puede quedar como marca.
    antes = v.cuenta_marcas()
    v.set_modo("dibujar")
    v._click(Evento(500, 400))
    v._arrastre(Evento(502, 401))
    v._arrastre(Evento(503, 402))
    v._soltar(Evento(503, 402))
    check(v.cuenta_marcas() == antes, "un tiron de pocos pixeles no deja marca")

    # (d) Deshacer hasta volver al estado guardado apaga el "sin guardar".
    v.marcas.clear()
    v.historial.clear()
    v.firma_guardada = v._firma()
    v.render()
    app.update()
    check(not v.sucio, "recien abierto no figura como 'sin guardar'")
    v._click(Evento(150, 250))
    for x in range(160, 300, 14):
        v._arrastre(Evento(x, 250))
    v._soltar(Evento(300, 250))
    app.update()
    check(v.sucio, "al marcar algo si figura como 'sin guardar'")
    v.deshacer()
    app.update()
    check(not v.sucio,
          "y al deshacerlo vuelve a estar limpio, sin pedir guardar lo que ya no cambio")
    # Reponer lo que habia antes de este bloque.
    v.marcas.clear()
    v.marcas.update(copia_marcas)
    v.historial[:] = copia_historial
    v.firma_guardada = copia_firma
    v.ir_pagina(0)
    v.render()
    app.update()

    def trazo(desde_x, y, hasta_x=None, paso=14):
        """Dibuja de verdad, por los manejadores, como lo haria el mouse."""
        hasta_x = hasta_x or (desde_x + 150)
        v._click(Evento(desde_x, y))
        for x in range(desde_x + paso, hasta_x, paso):
            v._arrastre(Evento(x, y))
        v._soltar(Evento(hasta_x, y))
        app.update()

    def a_evento(px, py):
        """Punto del PDF -> evento de mouse, con el scroll y el centrado reales."""
        cx, cy = v._a_canvas(px, py)
        return Evento(int(cx - c.canvasx(0)), int(cy - c.canvasy(0)))

    def empezar_limpio():
        v.ir_pagina(0)
        v.zoom_pagina()
        v.marcas.clear()
        del v.historial[:]
        del v.rehacer_pila[:]
        v._limpiar_seleccion()
        v.render()
        app.update()

    print("\n== 8f. Rehacer (Ctrl+Y) ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    antes = v.cuenta_marcas()
    check(antes == 1, "hay una marca para probar", "hay %d" % antes)
    v.deshacer()
    app.update()
    check(v.cuenta_marcas() == 0, "deshacer saca la marca",
          "quedaron %d" % v.cuenta_marcas())
    v.rehacer()
    app.update()
    check(v.cuenta_marcas() == 1, "y rehacer la devuelve",
          "quedaron %d" % v.cuenta_marcas())
    v.set_modo("dibujar")
    v.deshacer()
    trazo(400, 300)
    check(not v.rehacer_pila, "marcar algo nuevo corta la rama de rehacer")

    print("\n== 8g. Modo Seleccionar: elegir y mover ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    v.set_modo("seleccionar")
    check(v.modo == "seleccionar", "la herramienta existe y se puede elegir")
    objetivo = v.marcas[0][0]
    r = v._bbox(objetivo)
    ev = a_evento((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    v._click_seleccionar(ev)
    app.update()
    check(v.seleccion == [0], "clic encima de una marca la selecciona",
          "seleccion=%s" % v.seleccion)
    check(v.panel.winfo_ismapped(), "y aparece el panel de la derecha")

    x_antes = objetivo["trazos"][0][0][0]
    v._arrastre_seleccionar(Evento(ev.x + 40, ev.y + 25))
    v._soltar_seleccionar(None)
    app.update()
    objetivo = v.marcas[0][0]
    corrimiento = objetivo["trazos"][0][0][0] - x_antes
    check(corrimiento > 5, "arrastrarla la mueve de lugar",
          "se corrio %.1f pt" % corrimiento)
    check(v.sucio, "y eso cuenta como cambio sin guardar")
    v.deshacer()
    app.update()
    check(abs(v.marcas[0][0]["trazos"][0][0][0] - x_antes) < 0.5,
          "y el movimiento se puede deshacer")

    print("\n== 8h. Cambiar color y grosor de lo seleccionado ==")
    v.seleccion = [0]
    v._cambiar_color(COLOR_VERDE)
    app.update()
    check(v.marcas[0][0]["color"] == COLOR_VERDE, "cambia el color del dibujo elegido",
          str(v.marcas[0][0]["color"]))
    v._cambiar_grosor(6.0)
    app.update()
    check(v.marcas[0][0]["grosor"] == 6.0, "y el grosor")
    v.deshacer()
    app.update()
    check(v.marcas[0][0]["grosor"] != 6.0, "el cambio de grosor se deshace")
    v.deshacer()
    app.update()
    check(v.marcas[0][0]["color"] != COLOR_VERDE, "y el de color tambien")

    print("\n== 8i. Unificar varios dibujos en uno ==")
    empezar_limpio()
    v.set_modo("dibujar")
    for y in (200, 240, 280):
        trazo(150, y)
    check(len(v.marcas.get(0, [])) == 3, "hay 3 dibujos sueltos",
          "hay %d" % len(v.marcas.get(0, [])))
    v.set_modo("seleccionar")
    v.seleccion = [0, 1, 2]
    v._unificar()
    app.update()
    check(len(v.marcas[0]) == 1, "unificar los deja como una sola marca",
          "quedaron %d" % len(v.marcas[0]))
    check(len(v.marcas[0][0]["trazos"]) == 3,
          "y esa marca conserva los 3 trazos adentro",
          "%d trazos" % len(v.marcas[0][0]["trazos"]))
    v.deshacer()
    app.update()
    check(len(v.marcas[0]) == 3, "unificar tambien se puede deshacer",
          "quedaron %d" % len(v.marcas[0]))

    print("\n== 8j. Nombre interno de la marca ==")
    v.seleccion = [0]
    v._refrescar_panel()
    app.update()
    check(v.pnl_nombre.get().startswith("dibujo-p01"),
          "propone un nombre legible solo", repr(v.pnl_nombre.get()))
    v.pnl_nombre.delete(0, "end")
    v.pnl_nombre.insert(0, "el titulo esta mal")
    v._renombrar()
    app.update()
    check(v.marcas[0][0].get("nombre") == "el titulo esta mal",
          "se le puede poner el nombre que uno quiera",
          repr(v.marcas[0][0].get("nombre")))

    print("\n== 8k. Seleccionar y copiar texto del documento ==")
    v.set_modo("seleccionar")
    palabras = v._palabras_pagina()
    check(len(palabras) > 0, "el visor ve las palabras del manual",
          "%d palabras" % len(palabras))
    if palabras:
        primera, ultima = palabras[0], palabras[min(3, len(palabras) - 1)]
        v._seleccionar_texto((primera[0] + 1, primera[1] + 1),
                             (ultima[2] - 1, ultima[3] - 1))
        check(len(v._texto_sel) > 0, "arrastrar sobre el texto lo selecciona",
              repr(v._texto_sel)[:60])
        check("PAGINA 1" in v._texto_sel or "MANUAL" in v._texto_sel,
              "y es el texto de verdad del manual", repr(v._texto_sel)[:60])
        v.copiar_texto()
        app.update()
        try:
            pegado = app.clipboard_get()
        except Exception:
            pegado = ""
        check(pegado == v._texto_sel, "Ctrl+C lo deja en el portapapeles",
              repr(pegado)[:60])

    # Los bloques 8f..8k barrieron las marcas para probar en limpio. Se repone
    # lo que esperan los pasos que siguen: una marca en la pagina 1, y en la 3
    # un trazo mas la nota del diagrama.
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    v.ir_pagina(2)
    app.update()
    trazo(150, 320)
    v.set_modo("texto")
    v._click(Evento(320, 380))
    app.update()
    v._editor.insert("1.0", "Aca falta el diagrama.")
    v._cerrar_editor(confirmar=True)
    v.ir_pagina(0)
    v.set_modo("dibujar")
    app.update()

    print("")
    print("== 8l. Nota atada a una frase: se elige DONDE ponerla ==")
    empezar_limpio()
    v.set_modo("seleccionar")
    palabras = v._palabras_pagina()
    primera, ultima = palabras[0], palabras[min(3, len(palabras) - 1)]
    v._seleccionar_texto((primera[0] + 1, primera[1] + 1), (ultima[2] - 1, ultima[3] - 1))
    frase = v._texto_sel
    check(bool(frase), "hay una frase del documento elegida", repr(frase)[:50])

    check(v.comentar_seleccion(), "\"Comentar esta frase\" arranca el pedido")
    app.update()
    check(v.modo == "texto", "deja el programa en modo Texto, esperando el clic",
          "quedo en %s" % v.modo)
    check(v._editor is None, "y todavia no abre ningun cuadro: primero se elige el lugar")
    check(v.ancla_pendiente is not None, "se acuerda de la frase mientras tanto")

    # Ahora si: el clic donde se quiera la nota.
    v._click(Evento(260, 430))
    app.update()
    check(v._editor is not None, "al hacer clic se abre el cuadro para escribir")
    v._editor.insert("1.0", "Esto hay que revisarlo.")
    v._cerrar_editor(confirmar=True)
    app.update()
    notas = [m for m in v.marcas.get(0, []) if m["tipo"] == "texto"]
    check(len(notas) == 1, "quedo la nota donde se hizo clic")
    check(bool(notas[0].get("ancla")), "y quedo atada a la frase elegida antes")
    if notas[0].get("ancla"):
        check(notas[0]["ancla"]["cita"] == frase,
              "la frase guardada es exactamente la que se eligio",
              repr(notas[0]["ancla"]["cita"])[:50])
    check(v.ancla_pendiente is None, "y la frase pendiente se consume, no queda pegada")
    check(v.modo == "seleccionar", "despues vuelve solo a Seleccionar")

    print("")
    print("== 8m. Sin elegir texto, la nota sigue siendo suelta (nada cambia) ==")
    v.set_modo("texto")
    v._click(Evento(200, 560))
    app.update()
    v._editor.insert("1.0", "Nota suelta de toda la vida.")
    v._cerrar_editor(confirmar=True)
    app.update()
    sueltas = [m for m in v.marcas.get(0, []) if m["tipo"] == "texto" and not m.get("ancla")]
    check(len(sueltas) == 1, "la nota sin frase elegida queda suelta, como siempre")

    print("")
    print("== 8m2. Un dibujo tambien se puede atar a una frase ==")
    v.set_modo("seleccionar")
    v._seleccionar_texto((primera[0] + 1, primera[1] + 1), (ultima[2] - 1, ultima[3] - 1))
    check(v.dibujar_sobre_seleccion(), "\"Dibujar sobre esta frase\" arranca el pedido")
    app.update()
    check(v.modo == "dibujar", "deja el programa en modo Dibujar")
    trazo(150, 600)
    dibujos = [m for m in v.marcas.get(0, []) if m["tipo"] == "lapiz"]
    check(len(dibujos) == 1 and bool(dibujos[0].get("ancla")),
          "el dibujo que se hace despues queda atado a esa frase")

    print("")
    print("== 8m3. Escape cancela lo que estaba por atarse ==")
    v.set_modo("seleccionar")
    v._seleccionar_texto((primera[0] + 1, primera[1] + 1), (ultima[2] - 1, ultima[3] - 1))
    v.comentar_seleccion()
    app.update()
    check(v.ancla_pendiente is not None, "hay una frase esperando")
    check(v.cancelar_pendientes(), "Esc la cancela")
    check(v.ancla_pendiente is None, "y ya no queda nada pendiente")

    print("")
    print("== 8m4. Referencia: atar una marca a otra marca ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    trazo(150, 330)
    v.marcas[0][0]["nombre"] = "el-titulo"
    v.set_modo("seleccionar")
    v.seleccion = [1]
    v.elegir_referencia()
    app.update()
    check(v.refiriendo == [1], "queda esperando que se elija la referencia")
    # Clic sobre la otra marca.
    r = v._bbox(v.marcas[0][0])
    ev = a_evento((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    v._click_seleccionar(ev)
    app.update()
    check(v.marcas[0][1].get("ref") == "el-titulo",
          "la marca queda referida a la otra por su nombre",
          repr(v.marcas[0][1].get("ref")))
    check(not v.refiriendo, "y el modo referencia se cierra solo")
    check(v.seleccion == [1], "dejando elegida la marca que se estaba editando")
    v.soltar_ancla()
    app.update()
    check(not v.marcas[0][1].get("ref"), "\"Quitar\" le saca la referencia")

    print("")
    print("== 8n. El ancla sobrevive al guardar ==")
    empezar_limpio()
    v.set_modo("seleccionar")
    v._seleccionar_texto((primera[0] + 1, primera[1] + 1), (ultima[2] - 1, ultima[3] - 1))
    frase = v._texto_sel
    v.comentar_seleccion()
    app.update()
    v._click(Evento(260, 430))
    app.update()
    v._editor.insert("1.0", "Nota atada de prueba.")
    v._cerrar_editor(confirmar=True)
    app.update()
    destino_ancla = os.path.join(tmp, "con-ancla.pdf")
    lector.filedialog.asksaveasfilename = lambda **kw: destino_ancla
    v.guardar()
    app.update()
    # La primera vez sale el cartel con el mensaje para el chat. Es modal (se
    # queda con el mouse): se cierra como lo cerraria una persona, con "Listo".
    check(v.dialogo_guardado is not None, "la primera vez aparece el cartel de guardado")
    if v.dialogo_guardado is not None:
        v.dialogo_guardado.destroy()
        app.update()
    d = pymupdf.open(destino_ancla)
    recargadas = A.cargar(d)
    d.close()
    con_ancla = [m for l in recargadas.values() for m in l if m.get("ancla")]
    check(len(con_ancla) == 1, "al reabrir, la nota sigue atada a su frase",
          "%d con ancla" % len(con_ancla))
    if con_ancla:
        check(con_ancla[0]["ancla"]["cita"] == frase,
              "y la frase es la misma, palabra por palabra")
    check(sum(len(l) for l in recargadas.values()) == 1,
          "el resaltado no aparece como una marca aparte: va dentro de su nota",
          "hay %d marcas" % sum(len(l) for l in recargadas.values()))

    print("")
    print("== 8o. El agente recibe la frase, sin tener que deducirla ==")
    r = subprocess.run([sys.executable, os.path.join(AQUI, "leer_devolucion.py"),
                        destino_ancla, "--solo-marcas", "--png-dir", os.path.join(tmp, "png3")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = r.stdout or ""
    check("NOTA SOBRE UNA FRASE" in salida, "el informe la marca como atada a una frase")
    check(frase[:30] in salida, "y cita la frase del documento", repr(frase[:30]))

    print("")
    print("== 8p. El panel no mueve la hoja al abrirse ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    v.set_modo("seleccionar")
    app.update()
    ancho_antes = v.canvas.winfo_width()
    zoom_antes = v.zoom
    r = v._bbox(v.marcas[0][0])
    v._click_seleccionar(a_evento((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    app.update()
    check(v.panel.winfo_ismapped(), "el panel aparece al elegir")
    check(v.canvas.winfo_width() == ancho_antes,
          "y la hoja NO cambia de ancho: el panel va superpuesto",
          "%d -> %d" % (ancho_antes, v.canvas.winfo_width()))
    check(abs(v.zoom - zoom_antes) < 0.001, "ni cambia el zoom, asi que no salta de lugar")

    print("\n== 8q. Fit to size: el recuadro de la nota se ajusta al texto ==")
    corta = A.rect_nota(100, 100, "ok")
    larga = A.rect_nota(100, 100, "una nota bastante mas larga que la otra para comparar")
    check(corta.width < larga.width, "una nota corta ocupa menos ancho que una larga",
          "corta=%.0f larga=%.0f" % (corta.width, larga.width))
    check(corta.width >= A.ANCHO_MIN_NOTA - 0.5, "pero nunca baja del minimo legible",
          "%.0f" % corta.width)
    check(larga.width <= A.ANCHO_NOTA + 0.5, "ni pasa del ancho maximo", "%.0f" % larga.width)
    parrafo = A.rect_nota(100, 100, "palabra " * 40)
    check(parrafo.width <= A.ANCHO_NOTA + 0.5 and parrafo.height > larga.height,
          "un texto largo se parte en varias lineas en vez de seguir ensanchando")

    print("\n== 8r. El ojito muestra y oculta las marcas sin borrarlas ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    n = v.cuenta_marcas()
    v.toggle_ver_marcas()
    app.update()
    check(not v.ver_marcas and v.cuenta_marcas() == n,
          "apagar el ojito oculta las marcas pero no las borra", "quedan %d" % v.cuenta_marcas())
    v.toggle_ver_marcas()
    app.update()
    check(v.ver_marcas and v.cuenta_marcas() == n, "y volver a encenderlo las trae de vuelta")

    print("\n== 8s. Boton derecho: recuadro por area (estilo RTS) ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250, 300)
    r = v._bbox(v.marcas[0][0])
    v._rts_inicio(a_evento(r.x0 - 8, r.y0 - 8))
    v._rts_mover(a_evento(r.x1 + 8, r.y1 + 8))
    v._rts_soltar(a_evento(r.x1 + 8, r.y1 + 8))
    app.update()
    check(v.modo == "seleccionar", "soltar el recuadro pasa a modo Seleccionar")
    check(v.seleccion == [0], "y agarra la marca que quedo dentro del recuadro",
          "seleccion=%s" % v.seleccion)
    empezar_limpio()
    palabras = v._palabras_pagina()
    pa, pb = palabras[0], palabras[min(3, len(palabras) - 1)]
    v._rts_inicio(a_evento(pa[0] - 2, pa[1] - 2))
    v._rts_soltar(a_evento(pb[2] + 2, pb[3] + 2))
    app.update()
    check(len(v._texto_sel) > 0, "un recuadro sobre un vacio elige el texto del documento",
          repr(v._texto_sel)[:50])

    print("\n== 8t. La manito (ruedita) agarra y suelta la hoja ==")
    empezar_limpio()
    v._pan_inicio(Evento(400, 400))
    check(v._pan is True, "apretar la ruedita agarra la hoja")
    v._pan_mover(Evento(400, 340))
    v._pan_fin(Evento(400, 340))
    check(v._pan is None, "y al soltar la suelta")

    def elegir_frase():
        palabras = v._palabras_pagina()
        pa, pb = palabras[0], palabras[min(3, len(palabras) - 1)]
        v._seleccionar_texto((pa[0] + 1, pa[1] + 1), (pb[2] - 1, pb[3] - 1))
        return v._texto_sel

    class Tecla:
        """Una tecla falsa, con lo unico que mira App._tecla."""

        def __init__(self, keysym, state=0):
            self.keysym, self.state = keysym, state

    print("\n== 8u. Una frase abandonada no se pega a la marca siguiente ==")
    empezar_limpio()
    v.set_modo("seleccionar")
    elegir_frase()
    v.comentar_seleccion()
    v._click(Evento(260, 430))
    app.update()
    v._cerrar_editor(confirmar=True)        # la nota quedo vacia: se abandona
    app.update()
    check(v.ancla_pendiente is None, "cerrar una nota vacia abandona la frase pendiente")
    v.set_modo("texto")
    v._click(Evento(200, 560))
    app.update()
    v._editor.insert("1.0", "nota nueva")
    v._cerrar_editor(confirmar=True)
    app.update()
    nuevas = [m for m in v.marcas.get(0, []) if m.get("texto") == "nota nueva"]
    check(len(nuevas) == 1 and not nuevas[0].get("ancla"), "y la nota siguiente queda suelta")
    v.set_modo("seleccionar")
    elegir_frase()
    v.dibujar_sobre_seleccion()
    v.set_modo("texto")                     # se arrepiente y cambia de herramienta
    check(v.ancla_pendiente is None, "cambiar de herramienta tambien abandona la frase pendiente")
    v.set_modo("seleccionar")

    print("\n== 8v. Una referencia a medio elegir no cruza de pagina ==")
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    v.set_modo("seleccionar")
    v.seleccion = [0]
    v.elegir_referencia()
    v.ir_pagina(1)
    app.update()
    check(not v.refiriendo, "al pasar de pagina se cancela la referencia a medio elegir")
    v.ir_pagina(0)
    app.update()

    print("\n== 8w. Todo cambio cuenta como 'sin guardar' ==")
    empezar_limpio()
    v.set_modo("texto")
    v._click(Evento(260, 430))
    app.update()
    v._editor.insert("1.0", "nota de color")
    v._cerrar_editor(confirmar=True)
    app.update()
    v.firma_guardada = v._firma()
    check(not v.sucio, "recien guardada no figura como 'sin guardar'")
    v.seleccion = [len(v.marcas[0]) - 1]
    v._cambiar_color(COLOR_VERDE)
    check(v.sucio, "cambiar el color de una nota cuenta como cambio")
    v.firma_guardada = v._firma()
    v._refrescar_panel()
    v.pnl_nombre.delete(0, "end")
    v.pnl_nombre.insert(0, "otro-nombre")
    v._renombrar()
    check(v.sucio, "y renombrarla tambien")

    print("\n== 8x. Un circulo no tapa el texto de adentro ==")
    import math
    empezar_limpio()
    cx, cy, radio = 200.0, 300.0, 60.0
    circulo = [(cx + radio * math.cos(a / 30.0 * 2 * math.pi),
                cy + radio * math.sin(a / 30.0 * 2 * math.pi)) for a in range(31)]
    v.marcas.setdefault(0, []).append({"tipo": "lapiz", "trazos": [circulo],
                                       "color": (0.88, 0.19, 0.19), "grosor": 2.0})
    v.render()
    app.update()
    check(v._marca_en((cx, cy)) is None, "un clic en el centro de un circulo no lo agarra")
    check(v._marca_en((cx + radio, cy)) == 0, "un clic sobre el trazo si")

    print("\n== 8y. Con el ojito apagado, las marcas no se tocan ==")
    v.toggle_ver_marcas()
    app.update()
    check(v._marca_en((cx + radio, cy)) is None, "una marca oculta no se puede agarrar")
    v.set_modo("borrar")
    check(v.ver_marcas, "elegir Borrar vuelve a mostrar las marcas")
    v.set_modo("seleccionar")

    print("\n== 8z. Editar una nota atada no le borra la frase; cancelar no la borra ==")
    empezar_limpio()
    v.set_modo("seleccionar")
    frase = elegir_frase()
    v.comentar_seleccion()
    v._click(Evento(260, 430))
    app.update()
    v._editor.insert("1.0", "nota atada")
    v._cerrar_editor(confirmar=True)
    app.update()
    i = next(k for k, m in enumerate(v.marcas[0]) if m.get("texto") == "nota atada")
    v.seleccion = [i]
    v._editar_nota_seleccionada()
    app.update()
    v._editor.delete("1.0", "end")
    v._editor.insert("1.0", "nota atada y editada")
    v._cerrar_editor(confirmar=True)
    app.update()
    editada = [m for m in v.marcas[0] if m.get("texto") == "nota atada y editada"]
    check(len(editada) == 1 and (editada[0].get("ancla") or {}).get("cita") == frase,
          "editar una nota atada conserva su frase")
    n = v.cuenta_marcas()
    v.seleccion = [v.marcas[0].index(editada[0])]
    v._editar_nota_seleccionada()
    app.update()
    v._editor.insert("end", " y algo mas")
    v.deshacer()                            # Ctrl+Z mientras se edita = cancelar
    app.update()
    check(v.cuenta_marcas() == n and any(m.get("texto") == "nota atada y editada"
                                         for m in v.marcas[0]),
          "cancelar la edicion deja la nota como estaba (antes la borraba)")

    print("\n== 8aa. Ancho de la nota con la manija ==")
    empezar_limpio()
    v.set_modo("texto")
    v._click(Evento(120, 430))
    app.update()
    v._editor.insert("1.0", "una nota bastante larga que se parte en varios renglones "
                            "cuando la caja es angosta")
    v._cerrar_editor(confirmar=True)
    app.update()
    i = len(v.marcas[0]) - 1
    mk = v.marcas[0][i]
    antes = len(A.lineas_nota(mk["texto"], mk.get("ancho")))
    v.set_modo("seleccionar")
    v.seleccion = [i]
    v.render()
    app.update()
    v.firma_guardada = v._firma()
    v._empezar_manija(i, "der")
    v._redimensionar((v._pagina().rect.width, mk["y"]))
    v._soltar_seleccionar(None)
    app.update()
    mk = v.marcas[0][i]
    despues = len(A.lineas_nota(mk["texto"], mk.get("ancho")))
    check(despues < antes, "ensanchar la nota con la manija la deja en menos renglones",
          "%d -> %d" % (antes, despues))
    check(v._bbox(mk).x1 <= v._pagina().rect.width + 0.5, "sin salirse de la hoja")
    check(v.sucio, "y cuenta como cambio sin guardar")
    r = A.rect_nota(mk["x"], mk["y"], mk["texto"], mk.get("ancho"))
    mas_ancha = max(A._ancho_texto(l) for l in A.lineas_nota(mk["texto"], mk.get("ancho")))
    check(abs((r.width - 2 * A.PAD_NOTA) - max(mas_ancha, A.ANCHO_MIN_NOTA - 2 * A.PAD_NOTA)) < 0.5,
          "la caja mide justo su renglon mas ancho: sin aire a la derecha")
    v.ancho_automatico()
    check("ancho" not in v.marcas[0][i], "'Ancho automatico' la devuelve al ancho de siempre")

    print("\n== 8ab. En modo Texto, clic sobre una nota la edita ==")
    empezar_limpio()
    v.set_modo("texto")
    v._click(Evento(260, 430))
    app.update()
    v._editor.insert("1.0", "editame")
    v._cerrar_editor(confirmar=True)
    app.update()
    r = v._bbox(v.marcas[0][0])
    v.set_modo("texto")
    v._click(a_evento((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    app.update()
    check(v._editor is not None and v._editor.get("1.0", "end-1c") == "editame",
          "abre esa misma nota para editarla, en vez de otra encima")
    v._cerrar_editor(confirmar=True)
    app.update()
    check(v.cuenta_marcas() == 1, "y no suma una nota de mas")

    print("\n== 8ac. Buscar en el documento ==")
    empezar_limpio()
    v.abrir_busqueda()
    v.entrada_buscar.delete(0, "end")
    v.entrada_buscar.insert(0, "anticheat")
    v.buscar(1)
    app.update()
    check("anticheat" in v._texto_sel, "encuentra el texto y lo deja elegido", repr(v._texto_sel))
    check(v.lbl_buscar.cget("text").startswith("1 de 3"), "y dice cuantos hay",
          v.lbl_buscar.cget("text"))
    v.buscar(1)
    app.update()
    check(v.pno == 1, "Enter pasa al siguiente, en la otra pagina", "pagina %d" % (v.pno + 1))
    v.cerrar_busqueda()
    v.ir_pagina(0)
    app.update()

    print("\n== 8ad. Teclas: Esc, Ctrl y flechas ==")
    empezar_limpio()
    app._tecla(Tecla("Escape"))
    check(app.visor is v, "Esc sin nada elegido NO cierra el documento")
    v.set_modo("dibujar")
    trazo(150, 250)
    v.set_modo("seleccionar")
    v.seleccion = [0]
    x0 = v.marcas[0][0]["trazos"][0][0][0]
    app._tecla(Tecla("Right"))
    check(abs(v.marcas[0][0]["trazos"][0][0][0] - x0 - 1.0) < 0.01,
          "con algo elegido, la flecha lo mueve 1 pt")
    app._tecla(Tecla("Escape"))
    check(v.seleccion == [], "Esc suelta lo elegido")
    app._tecla(Tecla("d", state=0x0004))
    check(v.modo == "seleccionar", "Ctrl+D no cambia de herramienta")

    print("\n== 8ae. El mensaje para el chat trae el Python con su ruta ==")
    msg = lector.mensaje_para_el_chat(os.path.join(tmp, "x.pdf"))
    check('python.exe"' in msg.lower(), "el comando usa la ruta completa de python.exe",
          msg[-160:])

    print("\n== 8af. Barra estandar: Seleccionar primero y la letra subrayada ==")
    empezar_limpio()
    check(list(v.btn_modo) == ["seleccionar", "dibujar", "texto", "borrar"],
          "Seleccionar es la primera herramienta", str(list(v.btn_modo)))
    xs = [v.btn_modo[m].winfo_x() for m in ("seleccionar", "dibujar", "texto", "borrar")]
    check(xs == sorted(xs), "y asi se ven de izquierda a derecha", str(xs))
    check(all(int(b.cget("underline")) == 0 for b in v.btn_modo.values()),
          "cada herramienta tiene subrayada la primera letra")
    for letra, modo in (("d", "dibujar"), ("t", "texto"), ("b", "borrar"), ("s", "seleccionar")):
        app._tecla(Tecla(letra))
        check(v.modo == modo, "la letra %s elige %s" % (letra.upper(), modo))
    app._tecla(Tecla("d", state=0x20000))
    check(v.modo == "dibujar", "Alt + la letra subrayada tambien elige la herramienta")
    v.set_modo("seleccionar")
    lector.idiomas.set_idioma("en", persistir=False)
    check(lector.atajo_de("borrar") == "e", "en ingles, Erase se elige con la E")
    lector.idiomas.set_idioma("es", persistir=False)
    pagina = v.pno
    app._tecla(Tecla("space"))
    check(v.pno == pagina, "la barra espaciadora no hace nada (ni pasa de pagina)")

    print("\n== 8ag. Ocultar marcas: arriba, con estado y accion a la vista ==")
    empezar_limpio()
    check(v.btn_ojo.master is v.barra, "el boton esta en la barra de arriba")
    check(v.btn_ojo.cget("text") == "Ocultar marcas" and v.btn_ojo.cget("relief") == "raised",
          "suelto dice \"Ocultar marcas\"", v.btn_ojo.cget("text"))
    v.toggle_ver_marcas()
    check(v.btn_ojo.cget("text") == "Mostrar marcas" and v.btn_ojo.cget("relief") == "sunken",
          "apretado queda hundido y dice \"Mostrar marcas\"", v.btn_ojo.cget("text"))
    v.toggle_ver_marcas()
    check(v.ver_marcas and v.btn_ojo.cget("text") == "Ocultar marcas", "y vuelve a soltarse")

    print("\n== 8ah. La barra de abajo no dice nada en reposo ==")
    v.set_modo("dibujar")
    trazo(150, 250)
    v.set_modo("seleccionar")
    v.render()
    app.update()
    check(v.pie.cget("text") == "", "sin \"N marca(s)\" ni \"sin guardar\" (lo dice el titulo)",
          repr(v.pie.cget("text")))
    check(app.title().startswith("* "), "el asterisco del titulo avisa que falta guardar",
          app.title())

    print("\n== 8ai. Manijas de la nota: costados = ancho, esquinas = letra ==")
    empezar_limpio()
    v.set_modo("texto")
    v._click(a_evento(20, 300))
    app.update()
    v._editor.insert("1.0", "una nota de prueba con varias palabras para partir")
    v._cerrar_editor(confirmar=True)
    app.update()
    mk = v.marcas[0][0]
    v.set_modo("seleccionar")
    v.seleccion = [0]
    v.render()
    app.update()
    check(sorted(v._manijas(0)) == sorted(["ai", "ad", "bi", "bd", "izq", "der"]),
          "una nota elegida tiene 4 esquinas y 2 costados (arriba y abajo no)")
    antes_r = v._bbox(mk)
    lineas_antes = A.lineas_nota(mk["texto"], mk.get("ancho"), mk.get("cuerpo"))
    v._empezar_manija(0, "bd")
    v._redimensionar((antes_r.x0 + 2 * antes_r.width, antes_r.y0 + 2 * antes_r.height))
    v._soltar_seleccionar(None)
    despues_r = v._bbox(mk)
    check(abs((mk.get("cuerpo") or 0) - 2 * A.CUERPO_NOTA) < 0.3,
          "tirar de una esquina al doble agranda la letra al doble",
          "cuerpo=%s" % mk.get("cuerpo"))
    check(A.lineas_nota(mk["texto"], mk.get("ancho"), mk.get("cuerpo")) == lineas_antes,
          "sin cambiar como se parten los renglones")
    check(abs(despues_r.x0 - antes_r.x0) < 0.5 and abs(despues_r.y0 - antes_r.y0) < 0.5,
          "y la esquina de enfrente queda quieta")
    v.deshacer()
    mk = v.marcas[0][0]
    check(not mk.get("cuerpo"), "Ctrl+Z la devuelve a su letra")
    # Lo mismo, pero con eventos de mouse de verdad sobre la ventana: prueba que
    # la manija se encuentra donde se dibuja y que los bind() la atienden.
    v.seleccion = [0]
    v.render()
    app.update()
    mx, my = v._manijas(0)["bd"]
    ex_, ey_ = int(mx - c.canvasx(0)), int(my - c.canvasy(0))
    c.event_generate("<Motion>", x=ex_, y=ey_)
    check(str(c.cget("cursor")) == "size_nw_se",
          "sobre la esquina, el cursor es la flecha diagonal de estirar", str(c.cget("cursor")))
    c.event_generate("<ButtonPress-1>", x=ex_, y=ey_)
    for k in range(1, 9):
        c.event_generate("<B1-Motion>", x=ex_ + 6 * k, y=ey_ + 3 * k)
    c.event_generate("<ButtonRelease-1>", x=ex_ + 48, y=ey_ + 24)
    app.update()
    mk = v.marcas[0][0]
    check((mk.get("cuerpo") or 0) > A.CUERPO_NOTA,
          "arrastrar la esquina con el mouse agranda la letra", "cuerpo=%s" % mk.get("cuerpo"))
    v.deshacer()
    mk = v.marcas[0][0]
    mk["x"] = 300.0          # al medio de la hoja, con lugar para ensanchar a la izquierda
    v.seleccion = [0]
    v.render()
    derecha = v._bbox(mk).x1
    v._empezar_manija(0, "izq")
    v._redimensionar((v._bbox(mk).x0 - 120, mk["y"]))
    v._soltar_seleccionar(None)
    mk = v.marcas[0][0]
    check(abs(v._bbox(mk).x1 - derecha) < 0.6,
          "tirar del costado izquierdo deja quieto el derecho",
          "%.1f vs %.1f" % (v._bbox(mk).x1, derecha))
    check(bool(mk.get("ancho")), "y cambia el ancho de la nota")
    v.set_modo("dibujar")
    trazo(150, 250)
    v.set_modo("seleccionar")
    v.seleccion = [len(v.marcas[0]) - 1]
    v.render()
    app.update()
    x0c, y0c, _x1c, _y1c = v._caja_en_pantalla(v.marcas[0][-1], len(v.marcas[0]) - 1)
    ex = Evento(int(x0c - 4 - c.canvasx(0)), int(y0c - 4 - c.canvasy(0)))
    check(v._manija_en(ex) is None,
          "un dibujo elegido no tiene manijas (antes tenia cuadraditos que no hacian nada)")

    print("\n== 8aj. Nota con ancho elegido arrastrando ==")
    empezar_limpio()
    v.set_modo("texto")
    v._click(a_evento(60, 400))
    v._arrastre(a_evento(200, 402))
    v._arrastre(a_evento(360, 404))
    v._soltar(a_evento(360, 404))
    app.update()
    v._editor.insert("1.0", "palabra " * 30)
    v._cerrar_editor(confirmar=True)
    app.update()
    mk = v.marcas[0][0]
    esperado = 300.0
    check(abs((mk.get("ancho") or 0) - esperado) < 2,
          "arrastrar con Texto elige el ancho de la nota",
          "ancho=%s esperado=%.0f" % (mk.get("ancho"), esperado))
    check(v._bbox(mk).width <= esperado + 0.5, "y el texto se parte dentro de ese ancho")

    print("\n== 8ak. El borrador borra todo lo que toca al arrastrar ==")
    empezar_limpio()
    v.set_modo("dibujar")
    for x in (100, 200, 300):
        v._click(a_evento(x, 250))
        for y in range(262, 330, 12):
            v._arrastre(a_evento(x, y))
        v._soltar(a_evento(x, 330))
    app.update()
    check(v.cuenta_marcas() == 3, "hay tres trazos verticales")
    v.set_modo("borrar")
    v._click(a_evento(80, 290))
    for x in range(88, 340, 8):
        v._arrastre(a_evento(x, 290))
    v._soltar(a_evento(340, 290))
    app.update()
    check(v.cuenta_marcas() == 0, "una pasada del borrador los borro a los tres",
          "quedan %d" % v.cuenta_marcas())
    v.deshacer()
    check(v.cuenta_marcas() == 3, "y un solo Ctrl+Z los devuelve a los tres")

    print("\n== 8al. Copiar, cortar y pegar marcas ==")
    empezar_limpio()
    v.set_modo("texto")
    v._click(a_evento(100, 400))
    app.update()
    v._editor.insert("1.0", "nota para copiar")
    v._cerrar_editor(confirmar=True)
    v.set_modo("seleccionar")
    v.seleccion = [0]
    v.copiar()
    v.pegar()
    app.update()
    check(v.cuenta_marcas() == 2, "Ctrl+C y Ctrl+V duplican la nota")
    if v.cuenta_marcas() == 2:
        a_, b_ = v.marcas[0]
        check(abs(b_["x"] - a_["x"] - 12) < 0.01 and abs(b_["y"] - a_["y"] - 12) < 0.01,
              "la copia cae corrida un poco, no escondida encima")
        check(v.seleccion == [1], "y queda elegida la copia")
    v.ir_pagina(1)
    v.pegar()
    app.update()
    check(len(v.marcas.get(1, [])) == 1 and abs(v.marcas[1][0]["x"] - v.marcas[0][0]["x"]) < 0.01,
          "en otra pagina se pega en el mismo lugar")
    v.ir_pagina(0)
    v.seleccion = [1]
    v.cortar()
    check(v.cuenta_marcas() == 2, "Ctrl+X saca la marca de la hoja",
          "hay %d en total" % v.cuenta_marcas())
    v.seleccion = [0]
    app._tecla(Tecla("Return"))
    check(v._editor is not None, "Enter con una nota elegida la abre para editarla")
    v._cerrar_editor(confirmar=False)

    print("\n== 8am. Carpeta recordada ==")
    archivo_real = lector._archivo_carpeta
    lector._archivo_carpeta = lambda: os.path.join(tmp, "carpeta.txt")
    otra = os.path.join(tmp, "otra carpeta")
    os.makedirs(otra, exist_ok=True)
    try:
        lector.RECORDAR_CARPETA = True
        app.biblioteca.cambiar_carpeta(otra)
        check(lector.carpeta_recordada() == os.path.normpath(otra),
              "la carpeta elegida queda recordada para la proxima vez")
        with open(os.path.join(tmp, "carpeta.txt"), "w", encoding="utf-8") as f:
            f.write(os.path.join(tmp, "no existe"))
        check(lector.carpeta_recordada() is None,
              "si esa carpeta ya no existe, vuelve a Descargas sin avisar nada")
    finally:
        lector.RECORDAR_CARPETA = False
        lector._archivo_carpeta = archivo_real

    print("\n== 8an. Cursor de mano y ayuda nueva ==")
    check(lector.CURSOR_MANO != "fleur", "el programa trae su cursor de mano (mano.cur)")
    v._pan_inicio(Evento(400, 400))
    check(str(v.canvas.cget("cursor")) == lector.CURSOR_MANO,
          "apretar la ruedita muestra la mano", str(v.canvas.cget("cursor")))
    v._pan_fin(Evento(400, 400))
    import ayuda
    ventana = ayuda.Ventana(app)
    app.update()
    check(len(ventana.pestanas.tabs()) == 2, "la ayuda tiene dos pestanas: pasos y atajos")
    ventana.destroy()
    texto_ayuda = ayuda.como_texto("es")
    check("escritorio" not in texto_ayuda.lower() and "descargas" not in texto_ayuda.lower(),
          "la ayuda no supone donde esta el icono ni en que carpeta estan los PDFs")
    check(len(ayuda.PASOS["es"]) == 5 and len(ayuda.PASOS["en"]) == 5,
          "cinco pasos, en los dos idiomas")

    # Reponer lo que esperan los pasos siguientes.
    empezar_limpio()
    v.set_modo("dibujar")
    trazo(150, 250)
    v.ir_pagina(2)
    app.update()
    trazo(150, 320)
    v.set_modo("texto")
    v._click(Evento(320, 380))
    app.update()
    v._editor.insert("1.0", "Aca falta el diagrama.")
    v._cerrar_editor(confirmar=True)
    v.ir_pagina(0)
    v.set_modo("dibujar")
    app.update()

    print("\n== 9. Borrar una marca con el borrador ==")
    v.ir_pagina(0)
    app.update()
    v.set_modo("borrar")
    marca = v.marcas[0][0]
    r = v._bbox(marca)
    cx, cy = v._a_canvas((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    v._click(Evento(int(cx), int(cy - v.canvas.canvasy(0))))
    app.update()
    check(len(v.marcas.get(0, [])) == 0, "el borrador saco la marca de abajo del cursor",
          "quedan %d" % len(v.marcas.get(0, [])))
    v.deshacer()
    app.update()
    check(len(v.marcas.get(0, [])) == 1, "y Ctrl+Z la devuelve")

    print("\n== 10. Guardar ==")
    destino = os.path.join(tmp, "manual-devolucion.pdf")
    lector.filedialog.asksaveasfilename = lambda **kw: destino
    lector.DialogoGuardado = lambda app_, ruta: None      # no abrir ventanas en el test
    v.set_modo("dibujar")
    esperadas = {p: len(l) for p, l in v.marcas.items() if l}
    # Este visor ya guardo una copia en el paso 8n: Ctrl+S iria a esa. Para
    # elegir otro nombre esta "Guardar como...".
    v.guardar(como=True)
    app.update()
    check(os.path.exists(destino), "el archivo se escribio")
    check(not v.sucio, "el programa deja de marcar 'sin guardar'")
    try:
        portapapeles = app.clipboard_get()
    except Exception:
        portapapeles = ""
    check(destino in portapapeles, "la ruta quedo en el portapapeles para pegar en el chat",
          repr(portapapeles)[:70])
    check("leer_devolucion.py" in portapapeles,
          "y tambien el comando con el que el agente la lee (sirve en un chat nuevo)")
    preguntas = []
    lector.filedialog.asksaveasfilename = lambda **kw: (preguntas.append(kw), destino)[1]
    v.guardar()
    app.update()
    check(not preguntas, "la segunda vez Ctrl+S guarda encima sin preguntar el nombre")
    check(v.ruta_guardado == destino, "y sobre la misma copia de la primera vez")
    check(os.path.basename(destino) in v.pie.cget("text"),
          "avisando abajo donde guardo", v.pie.cget("text"))

    print("\n== 11. Lo guardado es lo que se marco ==")
    d = pymupdf.open(destino)
    recargadas = A.cargar(d)
    reales = {p: len(l) for p, l in recargadas.items() if l}
    check(reales == esperadas, "todas las marcas sobrevivieron al guardado",
          "esperado %s, hay %s" % (esperadas, reales))
    textos_orig = sorted(m["texto"] for l in v.marcas.values() for m in l if m["tipo"] == "texto")
    textos_disco = sorted(m["texto"] for l in recargadas.values() for m in l if m["tipo"] == "texto")
    check(textos_orig == textos_disco, "las notas se leen igual que como se escribieron")
    limpio = A.doc_sin_marcas(destino)
    t = limpio[0].get_text()
    check("PAGINA 1 DEL MANUAL" in t, "el texto del documento sigue intacto (canal 1)")
    check("Esto no va" not in t, "el canal 1 no viene contaminado con las notas")
    limpio.close()
    d.close()

    print("\n== 11b. El color de las notas sobrevive al reabrir ==")
    # El color de la letra vive en /DA, no en los colores del recuadro. Si se
    # leyera del recuadro, la nota volveria en amarillo sobre fondo amarillo:
    # invisible.
    col = os.path.join(tmp, "color.pdf")
    d = pymupdf.open()
    d.new_page().insert_text((72, 100), "hola")
    d.save(col)
    d.close()
    col_dev = os.path.join(tmp, "color-devolucion.pdf")
    A.guardar(col, col_dev,
              {0: [{"tipo": "texto", "x": 100, "y": 200, "texto": "nota roja",
                    "color": (0.88, 0.19, 0.19)}]})
    d = pymupdf.open(col_dev)
    c = A.cargar(d)[0][0]["color"]
    d.close()
    check(abs(c[0] - 0.88) < 0.02 and abs(c[1] - 0.19) < 0.02,
          "la nota vuelve con el color con el que se escribio",
          "volvio %s" % ([round(x, 2) for x in c],))
    check(not (c[0] > 0.9 and c[1] > 0.9),
          "y no con el color del fondo, que la dejaria invisible")

    print("\n== 11d. Guardar: dibujos atados, nombres sin repetir, ancho elegido ==")
    base_g = os.path.join(tmp, "g.pdf")
    d = pymupdf.open()
    for i in range(2):
        d.new_page().insert_text((72, 100), "frase de prueba numero %d" % i, fontsize=12)
    d.save(base_g)
    d.close()
    anc = {"rects": [(72, 88, 200, 104)], "cita": "frase de prueba"}
    marcas_g = {0: [
        {"tipo": "lapiz", "trazos": [[(80, 200), (300, 200)]], "color": (1, 0, 0),
         "grosor": 2, "ancla": anc},
        {"tipo": "texto", "x": 100, "y": 300, "texto": "uno", "color": (0, 0, 0),
         "nombre": "revisar", "ancla": anc},
        {"tipo": "texto", "x": 100, "y": 400, "texto": "dos", "color": (0, 0, 0),
         "nombre": "revisar"},
        {"tipo": "texto", "x": 100, "y": 500, "texto": "palabra " * 30, "color": (0, 0, 0),
         "ancho": 480},
        {"tipo": "texto", "x": 100, "y": 650, "texto": "letra grande", "color": (0, 0, 0),
         "cuerpo": 17.5},
    ]}
    g_dev = os.path.join(tmp, "g-dev.pdf")
    A.guardar(base_g, g_dev, marcas_g)
    d = pymupdf.open(g_dev)
    m = A.cargar(d)[0]
    d.close()
    check(bool(m[0].get("ancla")), "un dibujo atado a una frase vuelve atado al reabrir")
    check(m[1]["nombre"] != m[2]["nombre"], "dos marcas con el mismo nombre quedan distintas",
          "%s / %s" % (m[1]["nombre"], m[2]["nombre"]))
    check(bool(m[1].get("ancla")) and not m[2].get("ancla"),
          "y la frase queda en la que era, no se cruza")
    check(abs(m[3].get("ancho", 0) - 480) < 0.1, "el ancho elegido de una nota se guarda")
    check(abs((m[4].get("cuerpo") or 0) - 17.5) < 0.05,
          "el tamano de letra de una nota se guarda (en el lugar estandar del PDF)")
    check(not m[1].get("cuerpo"), "y una nota comun vuelve sin tamano de mas")
    A.guardar(g_dev, os.path.join(tmp, "g-dev2.pdf"),
              {1: [{"tipo": "texto", "x": 90, "y": 150, "texto": "x", "color": (0, 0, 0)}]})
    d = pymupdf.open(os.path.join(tmp, "g-dev2.pdf"))
    check(len(list(d[0].annots())) == 0,
          "una pagina que quedo sin marcas no arrastra anotaciones viejas")
    d.close()
    deriva = g_dev
    for k in range(4):
        d = pymupdf.open(deriva)
        mm = A.cargar(d)
        d.close()
        nuevo = os.path.join(tmp, "deriva-%d.pdf" % k)
        A.guardar(deriva, nuevo, mm)
        deriva = nuevo
    d = pymupdf.open(deriva)
    x_final = A.cargar(d)[0][1]["x"]
    d.close()
    check(abs(x_final - 100) < 0.05, "guardar y reabrir varias veces no corre las notas",
          "x=%.3f" % x_final)
    check(A.misma_ruta(g_dev, g_dev.upper()),
          "reconoce el mismo archivo aunque cambien las mayusculas")

    print("\n== 11c. Salir con una nota a medio escribir avisa ==")
    v_tmp = app.visor
    v_tmp.set_modo("texto")
    v_tmp._click(Evento(300, 300))
    app.update()
    v_tmp._editor.insert("1.0", "nota que todavia no confirme")
    antes_dialogos = len(dialogos)
    # "Cancelar" en el cartel: ya hay una copia guardada, asi que "Si" la
    # guardaria encima sin preguntar (y cambiaria lo que miden los pasos 12-14).
    lector.messagebox.askyesnocancel = _falso("askyesnocancel", None)
    app._confirmar_descartar()
    lector.messagebox.askyesnocancel = _falso("askyesnocancel", True)
    check(len(dialogos) > antes_dialogos,
          "pregunta antes de tirar una nota a medio escribir")
    v_tmp.deshacer()
    app.update()

    print("\n== 12. Reabrir lo guardado para seguir marcando ==")
    app.abrir_pdf(destino)
    app.update()
    v2 = app.visor
    check(sum(len(l) for l in v2.marcas.values()) == sum(esperadas.values()),
          "al reabrir, las marcas de antes estan y se pueden seguir editando")
    pix = v2.doc[0].get_pixmap(matrix=pymupdf.Matrix(0.4, 0.4), annots=True)
    # El doc del visor no debe traer las marcas dibujadas: las pinta el visor.
    check(len(list(v2.doc[0].annots())) == 0,
          "la pagina se dibuja sin las marcas propias (si no, se verian dobles)")

    print("\n== 13. Guardar dos veces no acumula capas ==")
    check(v2.ruta_guardado == destino,
          "una devolucion reabierta se guarda encima de si misma (Ctrl+S)")
    destino2 = os.path.join(tmp, "otra.pdf")
    lector.filedialog.asksaveasfilename = lambda **kw: destino2
    v2.guardar(como=True)          # "Guardar como..." pregunta siempre
    app.update()
    check(v2.ruta_guardado == destino2, "\"Guardar como...\" pasa a guardar en el nombre nuevo")
    d2 = pymupdf.open(destino2)
    n2 = sum(len(list(d2[i].annots())) for i in range(d2.page_count))
    d2.close()
    check(n2 == sum(esperadas.values()), "no se duplicaron anotaciones", "hay %d" % n2)
    check(abs(os.path.getsize(destino2) - os.path.getsize(destino)) < 20000,
          "el archivo no crece de guardado en guardado",
          "%d vs %d bytes" % (os.path.getsize(destino), os.path.getsize(destino2)))

    print("\n== 14. Guardar encima del mismo archivo que se esta mirando ==")
    preguntas = []
    lector.filedialog.asksaveasfilename = lambda **kw: (preguntas.append(kw), destino2)[1]
    app.abrir_pdf(destino2)
    app.update()
    v3 = app.visor
    antes_dialogos = len(dialogos)
    marcas_antes = v3.cuenta_marcas()
    v3.guardar()
    app.update()
    check(not preguntas, "Ctrl+S sobre una devolucion abierta no pregunta el nombre")
    check(len(dialogos) == antes_dialogos, "guardar encima no tira ningun error",
          "; ".join(dialogos[antes_dialogos:])[:200])
    check(os.path.exists(destino2) and os.path.getsize(destino2) > 1000,
          "sobrescribir el propio archivo no lo rompe")
    check(not os.path.exists(destino2 + ".tmp-lector"), "no queda basura temporal al lado")
    check(v3.doc is not None and v3.doc.page_count > 0,
          "el visor sigue mostrando el PDF despues de sobrescribirlo")
    d3 = pymupdf.open(destino2)
    check(sum(len(l) for l in A.cargar(d3).values()) == marcas_antes,
          "las marcas siguen todas ahi despues de sobrescribir")
    d3.close()
    v3.set_modo("dibujar")
    v3._click(Evento(140, 260))
    for x in range(150, 260, 12):
        v3._arrastre(Evento(x, 260))
    v3._soltar(Evento(260, 260))
    check(v3.cuenta_marcas() == marcas_antes + 1,
          "y se puede seguir marcando sin reabrir nada")

    print("\n== 14b. Un PDF roto no rompe el programa ==")
    roto = os.path.join(tmp, "roto.pdf")
    with open(roto, "wb") as f:
        f.write(b"%PDF-1.4 esto no es un pdf de verdad")
    antes_dialogos = len(dialogos)
    app.abrir_pdf(roto)
    app.update()
    check(len(dialogos) > antes_dialogos, "avisa que no pudo abrirlo, en vez de cerrarse")
    check(app.visor is not None, "sigue en pie con el PDF anterior")

    print("\n== 15. El extractor entiende la devolucion ==")
    r = subprocess.run([sys.executable, os.path.join(AQUI, "leer_devolucion.py"), destino,
                        "--png-dir", os.path.join(tmp, "png")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout or "") + (r.stderr or "")
    check(r.returncode == 0, "el extractor corre sin errores", (r.stderr or "")[:200])
    check("CANAL 1" in salida and "CANAL 2" in salida, "devuelve los dos canales separados")
    # "Esto no va" se deshizo en el paso 7; la nota viva es la de la pagina 3.
    check("Aca falta el diagrama" in salida, "incluye lo que se escribio")
    check("PAGINA 1 DEL MANUAL" in salida, "incluye el texto original del manual")
    check("Parrafo tres punto dos" in salida,
          "ancla cada marca al texto del documento que tiene debajo")
    check(os.path.exists(os.path.join(tmp, "png")) and
          len(os.listdir(os.path.join(tmp, "png"))) >= 2,
          "deja las imagenes de las paginas marcadas")

    print("\n== 15a. Una nota en un hueco no se le atribuye a la seccion de abajo ==")
    # Caso tipico: se escribe en el blanco que queda debajo de un parrafo. Si
    # el informe dijera solo "a la altura de..." podria nombrar el titulo de la
    # seccion siguiente, y el agente terminaria corrigiendo la parte equivocada
    # del manual. Por eso se muestran los tres vecinos.
    hueco = os.path.join(tmp, "hueco.pdf")
    d = pymupdf.open()
    pg = d.new_page(width=595, height=842)
    pg.insert_text((72, 120), "1.1 Marco general", fontsize=14)
    pg.insert_text((72, 150), "El fondo se desplaza con dos capas que se alternan.", fontsize=10)
    pg.insert_text((72, 330), "1.2 Control", fontsize=14)
    pg.insert_text((72, 360), "El mando es una zona rectangular abajo.", fontsize=10)
    d.save(hueco)
    d.close()
    hueco_dev = os.path.join(tmp, "hueco-devolucion.pdf")
    A.guardar(hueco, hueco_dev,
              {0: [{"tipo": "texto", "x": 80, "y": 200,
                    "texto": "Lo de las dos capas no me cierra", "color": (0, 0, 0)}]})
    r = subprocess.run([sys.executable, os.path.join(AQUI, "leer_devolucion.py"),
                        hueco_dev, "--solo-marcas", "--png-dir", os.path.join(tmp, "png2")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    s = r.stdout or ""
    check("justo encima" in s and "dos capas que se alternan" in s,
          "el informe nombra el parrafo que la nota tiene arriba")
    check("hueco en blanco" in s,
          "y dice que la nota cayo en un blanco, en vez de inventar a que se refiere")

    print("\n== 15b. Casos raros que igual pueden aparecer ==")
    # Un PDF bajado de cualquier lado puede traer marcas de Edge o Acrobat, tener
    # el nombre con enes y acentos, o venir con contrasena.
    ajeno = os.path.join(tmp, "conajenas.pdf")
    d = pymupdf.open()
    pg = d.new_page()
    pg.insert_text((72, 100), "texto del documento")
    a = pg.add_highlight_annot(pymupdf.Rect(70, 88, 200, 104))
    a.set_info(title="Edge")
    a.update()
    d.save(ajeno)
    d.close()
    salida_ajeno = os.path.join(tmp, "conajenas-dev.pdf")
    A.guardar(ajeno, salida_ajeno,
              {0: [{"tipo": "lapiz", "trazos": [[(80, 300), (400, 300)]],
                    "color": (0.88, 0.19, 0.19), "grosor": 2}]})
    d = pymupdf.open(salida_ajeno)
    autores = sorted((an.info or {}).get("title", "") for an in d[0].annots())
    check("Edge" in autores, "no pisa las marcas hechas con otro programa", str(autores))
    check(sum(len(v) for v in A.cargar(d).values()) == 1,
          "y al reabrir solo toma las propias, no las ajenas")
    d.close()

    raro = os.path.join(tmp, u"Reseña ñandú v2.pdf")
    d = pymupdf.open()
    d.new_page().insert_text((72, 100), "hola")
    d.save(raro)
    d.close()
    destino_raro = os.path.join(tmp, u"Reseña ñandú v2-devolucion.pdf")
    A.guardar(raro, destino_raro,
              {0: [{"tipo": "texto", "x": 100, "y": 200,
                    "texto": u"acá está la ñ", "color": (0, 0, 0)}]})
    d = pymupdf.open(destino_raro)
    check(A.cargar(d)[0][0]["texto"] == u"acá está la ñ",
          "nombres y notas con enes y acentos se guardan y se leen igual")
    d.close()

    protegido = os.path.join(tmp, "protegido.pdf")
    d = pymupdf.open()
    d.new_page().insert_text((72, 100), "secreto")
    d.save(protegido, encryption=pymupdf.PDF_ENCRYPT_AES_256,
           user_pw="clave123", owner_pw="clave123")
    d.close()
    try:
        A.abrir_para_editar(protegido)
        check(False, "avisa en castellano que el PDF tiene contrasena", "no aviso nada")
    except Exception as e:
        check("contraseña" in str(e), "avisa en castellano que el PDF tiene contrasena",
              str(e)[:80])

    print("\n== 16. Sin dialogos inesperados ==")
    # Los que la propia prueba provoca a proposito no cuentan.
    esperados = ("showerror: No se pudo abrir", "askyesnocancel: Hay marcas sin guardar")
    inesperados = [d for d in dialogos if not d.startswith(esperados)]
    check(not inesperados, "el programa no tuvo que mostrar ningun error por su cuenta",
          " || ".join(inesperados)[:300])

    app.destroy()

    print("\n" + "=" * 70)
    if fallos:
        print("FALLAN %d de %d comprobaciones:" % (len(fallos), len(fallos) + len(hechos)))
        for f in fallos:
            print("   - " + f)
        return 1
    print("TODO BIEN: %d comprobaciones pasadas." % len(hechos))
    print("Carpeta de la prueba: %s" % tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
