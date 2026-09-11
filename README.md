# Lector PDF

Leer un manual de diseño y marcarlo encima —dibujando y escribiendo— para
devolvérselo a un agente conversacional.

La idea central: **David ve un solo documento marcado; el agente recibe dos cosas
separadas.** Por un lado el texto original del manual, por otro cada marca con la
parte del texto sobre la que cae. Un solo archivo, dos canales.

## Cómo se usa

Doble clic en el acceso directo del escritorio. Se abre mostrando los PDFs de
Descargas, el más nuevo arriba. Se abre uno, se lee y se marca, se guarda, y al
guardar el programa deja en el portapapeles un mensaje listo para pegar en el chat.

**Leer y marcar son la misma postura:** la rueda del mouse siempre lee, arrastrar
siempre dibuja. Nunca hay que ir a la barra de herramientas para alternar entre una
cosa y la otra. Ésa es la decisión de diseño que manda sobre todas las demás.

El instructivo completo está en el botón **"?"** del programa.

## Los archivos

| archivo | qué hace |
|---|---|
| `lector.pyw` | el programa: biblioteca, visor, herramientas de marcado |
| `anotaciones.py` | guardar y leer las marcas dentro del PDF |
| `errores.py` | registro de todos los errores de la sesión |
| `ayuda.py` | el instructivo, en un solo lugar: de acá salen la ventana "?" y el `.txt` |
| `leer_devolucion.py` | **lo corre el agente** para entender la devolución |
| `autotest.py` | 133 comprobaciones · `python autotest.py` |
| `instalar.ps1` | instala en Program Files y rehace los accesos directos |

## Cómo lee el agente una devolución

```
python "C:\Program Files\Mios\LectorPDF\leer_devolucion.py" "ruta\del\pdf-devolucion.pdf"
```

Devuelve el texto original limpio, cada marca con su nombre y el texto sobre el que
cae, y un PNG de cada página marcada. Las imágenes hay que abrirlas: el texto dice
dónde cae cada trazo, pero no si es un círculo, un tachado o una flecha.

## Cómo se guardan las marcas

Como **anotaciones PDF estándar**, no como píxeles quemados sobre la hoja:

- `Ink` para los trazos a mano, `FreeText` para las notas escritas.
- `Underline` tenue para la frase a la que una marca está atada, emparejado con ella
  por el nombre más el sufijo `-ancla`.
- Cada marca lleva un nombre propio en `/NM` (`dibujo-p02-1`), editable, para poder
  hablar de una marca concreta sin tener el documento delante.
- Toda anotación propia va firmada con autor `Devolucion`: así se reconocen al
  reabrir el archivo y no se pisan las de Edge o Acrobat.

Por eso el texto del manual sigue siendo extraíble intacto, y por eso las marcas se
pueden seguir editando después de guardar.

## Requisitos

Python 3.11 con `pymupdf` y `pillow`. El acceso directo apunta al intérprete por
ruta absoluta, a propósito: en esta máquina hubo más de un Python instalado y sólo
uno tenía las librerías.

## Dónde escribe

Nada se escribe junto al programa. El registro de errores va a
`%LOCALAPPDATA%\LectorPDF\errores_de_la_ultima_sesion.txt`, porque Program Files es
de sólo lectura y un registro que no se puede escribir no sirve para nada.
