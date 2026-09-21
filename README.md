<p align="center">
  <img src="docs/banner.png" alt="Lector PDF" width="820">
</p>

<p align="center">
  <a href="#-español">🇦🇷 Español</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="#-english">🇺🇸 English</a>
</p>

---

## 🇦🇷 Español

**Lector PDF** abre cualquier PDF, te deja marcarlo encima con dibujos y notas, y
lo guarda de forma que un agente conversacional (un asistente de IA) entienda
exactamente qué marcaste y sobre qué parte del texto.

Vos ves un solo documento marcado. El agente recibe dos cosas separadas: el
texto original del documento, y cada marca con la frase sobre la que cae.

<p align="center"><img src="docs/captura-es.png" alt="Lector PDF en español" width="900"></p>

### Qué se puede hacer

- **Dibujar** a mano alzada y **escribir notas** encima del PDF.
- **Atar** una nota o un dibujo a una frase concreta, para que no haya dudas de
  a qué se refiere.
- **Mover, copiar, recolorear, renombrar, unir y borrar** lo marcado. Las notas
  se ajustan solas a su texto: sus costados cambian el ancho y sus esquinas el
  tamaño de letra.
- **Ocultar las marcas** un momento para leer el documento limpio.
- **Buscar** texto en el documento y comentar lo encontrado.
- **Guardar** como en cualquier editor: la primera vez elegís el nombre de la
  copia y después `Ctrl+S` guarda encima. Queda en el portapapeles un mensaje
  listo para pegar en el chat, con el comando exacto para que el agente lo lea.
- La lista de PDFs abre en **la última carpeta que usaste**.
- Interfaz en **español e inglés** (botón *English / Español*).

### Atajos principales

| Acción | Atajo |
|---|---|
| Seleccionar / Dibujar / Texto / Borrar (la letra subrayada del botón) | `S` / `D` / `T` / `B` |
| Leer (desplazarse) | rueda del mouse |
| Arrastrar la hoja | apretar la ruedita y mover |
| Elegir por área | clic derecho y arrastrar |
| Menú de lo que hay debajo | clic derecho |
| Zoom hacia el mouse | `Ctrl` + rueda |
| Hoja entera / tamaño real / ancho | `Ctrl+0` / `Ctrl+1` / `Ctrl+2` |
| Buscar | `Ctrl+F`, `Enter` o `F3` para el siguiente |
| Deshacer / Rehacer | `Ctrl+Z` / `Ctrl+Y` |
| Copiar / cortar / pegar marcas | `Ctrl+C` / `Ctrl+X` / `Ctrl+V` |
| Elegir todas las marcas | `Ctrl+A` |
| Editar la nota elegida | doble clic o `Enter` |
| Mover lo elegido | flechas (`Shift` para más) |
| Borrar lo elegido | `Supr` |
| Guardar / Guardar como… | `Ctrl+S` / `Ctrl+Shift+S` |
| Abrir otro PDF / volver a la lista | `Ctrl+O` / `Ctrl+W` |
| Ayuda (pasos y atajos) | `F1` |

Pasando el mouse por cualquier botón aparece qué hace y su atajo.

### Instalación

Requiere **Windows** y **Python 3.11** con dos librerías:

```
python -m pip install pymupdf pillow
```

Después, desde una consola de PowerShell **como administrador**, en la carpeta
del proyecto:

```
powershell -ExecutionPolicy Bypass -File instalar.ps1
```

Copia el programa a `C:\Program Files\Mios\LectorPDF` y crea el acceso directo
*Lector PDF* en el escritorio. Si Python está en otro lugar:
`instalar.ps1 -Python "ruta\a\pythonw.exe"`.

### Cómo lee el agente una devolución

Al guardar, el mensaje que queda en el portapapeles ya trae este comando:

```
"ruta\a\python.exe" "C:\Program Files\Mios\LectorPDF\leer_devolucion.py" "archivo-devolucion.pdf"
```

Devuelve el texto original limpio, cada marca con su nombre y la frase sobre la
que cae, y una imagen de cada página marcada (para ver si un trazo es un
círculo, un tachado o una flecha).

### Cómo se guardan las marcas

Como **anotaciones PDF estándar**, no como píxeles pegados a la hoja: por eso se
ven en cualquier otro lector de PDF, el texto del documento sigue intacto y las
marcas se pueden seguir editando después. El PDF original nunca se modifica:
la primera vez se guarda una copia nueva (`-devolucion`, numerada) y después se
actualiza esa misma copia.

### Archivos

| Archivo | Qué es |
|---|---|
| `lector.pyw` | el programa: lista de PDFs, visor y herramientas |
| `anotaciones.py` | guardar y leer las marcas dentro del PDF |
| `leer_devolucion.py` | el lector de devoluciones que corre el agente |
| `idiomas.py` | todos los textos de la interfaz, en español e inglés |
| `ayuda.py` | la ayuda del botón `?` (F1): pasos y atajos |
| `errores.py` | registro de errores de la sesión |
| `mano.cur` | el cursor de mano para arrastrar la hoja |
| `autotest.py` | pruebas automáticas: `python autotest.py` |
| `instalar.ps1` | instalador |

Nada se escribe junto al programa: el registro de errores, el idioma elegido y
la última carpeta van a `%LOCALAPPDATA%\LectorPDF`.

---

## 🇺🇸 English

**Lector PDF** opens any PDF, lets you mark it up with drawings and notes, and
saves it so that a conversational agent (an AI assistant) understands exactly
what you marked and on which part of the text.

You see a single marked-up document. The agent receives two separate things:
the document's original text, and each mark with the sentence it falls on.

<p align="center"><img src="docs/captura-en.png" alt="Lector PDF in English" width="900"></p>

### What you can do

- **Draw** freehand and **write notes** on top of the PDF.
- **Tie** a note or a drawing to a specific sentence, so there is no doubt
  about what it refers to.
- **Move, copy, recolor, rename, merge and delete** marks. Notes fit their text
  by themselves: their sides change the width and their corners the text size.
- **Hide your marks** for a moment to read the clean document.
- **Find** text in the document and comment on what you found.
- **Save** like in any editor: the first time you choose the copy's name, and
  then `Ctrl+S` saves over it. A ready-to-paste message is left on the
  clipboard, with the exact command the agent needs to read it.
- The PDF list opens in **the last folder you used**.
- Interface in **Spanish and English** (*English / Español* button).

### Main shortcuts

| Action | Shortcut |
|---|---|
| Select / Draw / Text / Erase (the underlined letter on the button) | `S` / `D` / `T` / `E` |
| Read (scroll) | mouse wheel |
| Drag the sheet | press the wheel and move |
| Select by area | right-click and drag |
| Menu for what is under the mouse | right-click |
| Zoom toward the mouse | `Ctrl` + wheel |
| Whole page / actual size / width | `Ctrl+0` / `Ctrl+1` / `Ctrl+2` |
| Find | `Ctrl+F`, `Enter` or `F3` for the next one |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` |
| Copy / cut / paste marks | `Ctrl+C` / `Ctrl+X` / `Ctrl+V` |
| Select all marks | `Ctrl+A` |
| Edit the selected note | double-click or `Enter` |
| Nudge the selection | arrows (`Shift` for more) |
| Delete the selection | `Del` |
| Save / Save as… | `Ctrl+S` / `Ctrl+Shift+S` |
| Open another PDF / back to the list | `Ctrl+O` / `Ctrl+W` |
| Help (steps and shortcuts) | `F1` |

Hovering over any button shows what it does and its shortcut.

### Installation

Requires **Windows** and **Python 3.11** with two libraries:

```
python -m pip install pymupdf pillow
```

Then, from a PowerShell console **as administrator**, in the project folder:

```
powershell -ExecutionPolicy Bypass -File instalar.ps1
```

It copies the program to `C:\Program Files\Mios\LectorPDF` and creates the
*Lector PDF* shortcut on the desktop. If Python lives elsewhere:
`instalar.ps1 -Python "path\to\pythonw.exe"`.

### How the agent reads a returned file

When you save, the message left on the clipboard already includes this command:

```
"path\to\python.exe" "C:\Program Files\Mios\LectorPDF\leer_devolucion.py" "file-devolucion.pdf"
```

It returns the clean original text, each mark with its name and the sentence it
falls on, and an image of every marked page (to see whether a stroke is a
circle, a strikethrough or an arrow).

### How marks are stored

As **standard PDF annotations**, not pixels burned onto the page: that is why
they show up in any other PDF reader, the document's text stays intact, and the
marks can still be edited later. The original PDF is never modified: the first
time a new copy is saved (`-devolucion`, numbered), and after that the same copy
is updated.

### Files

| File | What it is |
|---|---|
| `lector.pyw` | the program: PDF list, viewer and tools |
| `anotaciones.py` | saving and reading marks inside the PDF |
| `leer_devolucion.py` | the returned-file reader the agent runs |
| `idiomas.py` | every interface text, in Spanish and English |
| `ayuda.py` | the help behind the `?` button (F1): steps and shortcuts |
| `errores.py` | session error log |
| `mano.cur` | the hand cursor for dragging the sheet |
| `autotest.py` | automated tests: `python autotest.py` |
| `instalar.ps1` | installer |

Nothing is written next to the program: the error log, the chosen language and
the last folder go to `%LOCALAPPDATA%\LectorPDF`.
