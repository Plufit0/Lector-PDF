<p align="center">
  <img src="docs/banner.png" alt="Lector PDF" width="820">
</p>

<p align="center">
  <a href="#-english">🇺🇸 English</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="#-español">🇦🇷 Español</a>
</p>

---

## 🇺🇸 English

Read a design manual and mark it up —drawing and writing on top of it— to hand it
back to a conversational agent.

The core idea: **you see a single marked-up document; the agent receives two
separate things.** On one side, the manual's original text; on the other, each
mark together with the piece of text it lands on. One file, two channels.

### How it works

Double-click the desktop shortcut. It opens showing the PDFs in your Downloads
folder, newest first. You open one, read and mark it, save, and on saving the
program leaves a ready-to-paste message on the clipboard for your chat.

**The default tool is Select**, like in editing programs: you can pick, move and
edit what's already marked without pressing a button first. To mark, you choose
**Draw** or **Text**; when you're done, it returns to Select on its own. **The
mouse wheel always scrolls (reads)** in any mode — reading never depends on the
active tool. Pressing the **mouse wheel** grabs the sheet and pans it (the
"hand"). **Right-click** drags a green box to select drawings or text by area.

The full guide is behind the **"?"** button.

### Language

The whole interface is bilingual. An **ES/EN** button in the toolbar switches
between Spanish and English on the spot, without closing the PDF or losing your
marks, and remembers your choice for next time.

### The files

| file | what it does |
|---|---|
| `lector.pyw` | the program: library, viewer, marking tools |
| `idiomas.py` | the language dictionary (Spanish/English) |
| `anotaciones.py` | save and read the marks inside the PDF |
| `ayuda.py` | the guide, in one place: the "?" window and the `.txt` come from here |
| `errores.py` | log of every error in the session |
| `leer_devolucion.py` | **the agent runs this** to understand the returned file |
| `autotest.py` | 144 checks · `python autotest.py` |
| `instalar.ps1` | installs into Program Files and rebuilds the shortcuts |

### How the agent reads a returned file

```
python "C:\Program Files\Mios\LectorPDF\leer_devolucion.py" "path\to\the-returned.pdf"
```

It returns the clean original text, each mark with its name and the text it lands
on, and a PNG of every marked page.

### How the marks are stored

As **standard PDF annotations**, not pixels burned onto the page: `Ink` for
free-hand strokes, `FreeText` for written notes, a faint `Underline` for the
phrase a mark is tied to. Every own annotation is signed with author
`Devolucion`, so they are recognized on reopening and don't clash with Edge or
Acrobat. The manual's text stays fully extractable, and the marks remain editable
after saving.

### Requirements

Python 3.11 with `pymupdf` and `pillow`. The shortcut points to the interpreter
by absolute path on purpose: this machine has more than one Python installed and
only one has the libraries.

---

## 🇦🇷 Español

Leer un manual de diseño y marcarlo encima —dibujando y escribiendo— para
devolvérselo a un agente conversacional.

La idea central: **David ve un solo documento marcado; el agente recibe dos cosas
separadas.** Por un lado el texto original del manual, por otro cada marca con la
parte del texto sobre la que cae. Un solo archivo, dos canales.

### Cómo se usa

Doble clic en el acceso directo del escritorio. Se abre mostrando los PDFs de
Descargas, el más nuevo arriba. Se abre uno, se lee y se marca, se guarda, y al
guardar el programa deja en el portapapeles un mensaje listo para pegar en el chat.

**La herramienta por defecto es Seleccionar**, como en los programas de edición:
se puede elegir, mover y editar lo ya marcado sin apretar un botón antes. Para
marcar se elige **Dibujar** o **Texto**; al terminar, vuelve solo a Seleccionar.
**La rueda del mouse siempre lee (scroll)** en cualquier modo: leer nunca depende
de la herramienta activa. Apretar la **ruedita** agarra la hoja y la arrastra (la
"manito"). El **click derecho** dibuja un recuadro verde para elegir dibujos o
texto por área.

El instructivo completo está en el botón **"?"** del programa.

### Idioma

Toda la interfaz es bilingüe. Un botón **ES/EN** en la barra cambia entre español
e inglés en el momento, sin cerrar el PDF ni perder las marcas, y recuerda tu
elección para la próxima vez.

### Los archivos

| archivo | qué hace |
|---|---|
| `lector.pyw` | el programa: biblioteca, visor, herramientas de marcado |
| `idiomas.py` | el diccionario de idiomas (español/inglés) |
| `anotaciones.py` | guardar y leer las marcas dentro del PDF |
| `ayuda.py` | el instructivo, en un solo lugar: de acá salen la ventana "?" y el `.txt` |
| `errores.py` | registro de todos los errores de la sesión |
| `leer_devolucion.py` | **lo corre el agente** para entender la devolución |
| `autotest.py` | 144 comprobaciones · `python autotest.py` |
| `instalar.ps1` | instala en Program Files y rehace los accesos directos |

### Cómo lee el agente una devolución

```
python "C:\Program Files\Mios\LectorPDF\leer_devolucion.py" "ruta\del\pdf-devolucion.pdf"
```

Devuelve el texto original limpio, cada marca con su nombre y el texto sobre el
que cae, y un PNG de cada página marcada. Las imágenes hay que abrirlas: el texto
dice dónde cae cada trazo, pero no si es un círculo, un tachado o una flecha.

### Cómo se guardan las marcas

Como **anotaciones PDF estándar**, no como píxeles quemados sobre la hoja: `Ink`
para los trazos a mano, `FreeText` para las notas, un `Underline` tenue para la
frase a la que una marca está atada. Toda anotación propia va firmada con autor
`Devolucion`: así se reconocen al reabrir y no se pisan las de Edge o Acrobat. Por
eso el texto del manual sigue siendo extraíble intacto, y las marcas se pueden
seguir editando después de guardar.

### Requisitos

Python 3.11 con `pymupdf` y `pillow`. El acceso directo apunta al intérprete por
ruta absoluta, a propósito: en esta máquina hubo más de un Python instalado y
sólo uno tenía las librerías.

### Dónde escribe

Nada se escribe junto al programa. El registro de errores y el idioma elegido van
a `%LOCALAPPDATA%\LectorPDF`, porque Program Files es de sólo lectura.
</content>
