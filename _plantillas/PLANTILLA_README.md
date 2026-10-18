# Plantilla APA 7 (`apa_docx.py`)

Módulo de Python que genera informes `.docx` en normas APA 7 (trabajo de
estudiante). Es el formato **por defecto** descrito en el `README.md` de la
raíz, salvo para actividades prácticas/experimentales.

`tareas.py tarea` crea un `generar_documento.py` ya conectado a la plantilla, y
`tareas.py esqueleto` le añade una sección por criterio de la rúbrica.

## Ejemplo completo

```python
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[2] / "_plantillas"))  # materias/<materia>/<tarea>/
from apa_docx import *

SALIDA = AQUI / nombre_entregable("A15_Procedimientos_Almacenados")  # + sufijo del .env

bib = Bibliografia()
bib.agregar("oracle2024", ["Oracle"], 2024, "MySQL 8.4 reference manual",
            url="https://dev.mysql.com/doc/refman/8.4/en/")
bib.agregar("ramos2023", ["Ramos, J.", "Pérez, A."], 2023, "Bases de datos relacionales",
            "Alfaomega")

doc, figura, tabla = nuevo_documento(
    titulo="Procedimientos almacenados",
    materia="Sistemas de Bases de Datos I",
    salida=SALIDA,
    tarea=AQUI,          # docente (README de la materia) y fecha de entrega (TAREA.md)
)

# Introducción: sin encabezado, como pide APA 7.
parrafo(doc, f"Según {bib.cita_narrativa('ramos2023')}, un procedimiento almacenado...")

titulo(doc, "Concepto y ventajas", 1, criterios="C1")
parrafo(doc, f"Se ejecutan en el servidor {bib.cita('oracle2024')}.")

titulo(doc, "Implementación", 1, criterios="C2")
titulo(doc, "Procedimiento con parámetros OUT", 2)
codigo(doc, "CREATE PROCEDURE p1(IN x INT, OUT y INT)\nBEGIN\n  SET y = x * 2;\nEND")
tabla(doc, None, "Procedimientos implementados", ["Nombre", "Parámetros"],
      [("p1", "IN x, OUT y"), ("p2", "IN a")])

titulo(doc, "Evidencia de ejecución", 1, criterios="C3")
figura(doc, None, "Ejecución de p1 en MySQL Workbench", "p1.png", "Captura propia.")

titulo(doc, "Conclusiones", 1)
parrafo(doc, "...")

transversal(doc, "C5")                   # Ortografía y redacción: todo el documento
referencias(doc, bib, criterios="C4")    # Página nueva, solo las fuentes citadas

guardar_documento(doc, SALIDA)
```

## Funciones

| Función | Para qué sirve |
|---|---|
| `nuevo_documento(titulo, materia, salida, ...)` | Crea el documento con estilos APA y portada de estudiante. Devuelve `(doc, figura, tabla)`. Opciones: `tarea=` (carpeta de la tarea: docente y fecha de entrega), `docente=`, `fecha=` (`str` o `date`), `carpeta_capturas=`, `nombre=`, `institucion=`, `carrera=`, `indice=True` (índice tras la portada; APA no lo pide). |
| `titulo(doc, texto, nivel, criterios=None)` | Encabezado APA con estilo de Word *Heading N*. `1` centrado en negrita, `2` a la izquierda en negrita, `3` a la izquierda en negrita y cursiva. `criterios="C1"` o `["C1", "C2"]` marca qué criterios de la rúbrica cubre la sección. |
| `transversal(doc, "C5", ...)` | Criterios que se cumplen en todo el documento (ortografía, formato...). |
| `parrafo(doc, texto, ...)` | Párrafo justificado con sangría y doble espacio. Acepta `negrita`, `cursiva`, `alineacion`, `sangria=False`... |
| `vinieta(doc, texto)` | Punto de lista con viñetas. |
| `codigo(doc, texto)` | Bloque de código/comandos en Courier New, espacio sencillo. |
| `figura(doc, numero, descripcion, archivo, nota)` | Figura APA (rótulo + título en cursiva + imagen + *Nota.*). `numero=None` numera solo. `archivo` es relativo a `capturas/`; si no existe deja `[FALTA LA CAPTURA: ...]`, que `comprobar` detecta. |
| `tabla(doc, numero, descripcion, encabezados, filas)` | Tabla APA con encabezado que se repite entre páginas. `numero=None` numera sola. |
| `Bibliografia()` | Fuentes con `agregar(clave, autores, anio, titulo, fuente, url=, detalles=, tipo=)`. Citas: `cita(clave)` → `(Ramos y Pérez, 2023)`, `cita(clave, "p. 15")`, `cita(c1, c2)`, `cita_narrativa(clave)` → `Ramos y Pérez (2023)`. Con 3 o más autores, *et al.* `tipo="articulo"` pone en cursiva la revista en vez del título. |
| `referencias(doc, bib, criterios=None, entradas=())` | Sección Referencias en página nueva, en orden alfabético y con sangría francesa. Solo incluye las fuentes citadas y avisa de las que no. `entradas` añade referencias escritas a mano. |
| `referencia(doc, texto)` | Una entrada escrita a mano; lo que va entre `*asteriscos*` sale en cursiva. |
| `salto_de_pagina(doc)` | Salto de página. |
| `leer_fuente(ruta)` | Lee un archivo de texto/código completo (útil para un anexo). |
| `guardar_documento(doc, salida)` | Guarda el `.docx` (y rellena el índice si lo hay). |
| `nombre_entregable(base, extension=".docx")` | `"A15_Titulo"` → `"A15_Titulo_<SUFIJO_ARCHIVOS>.docx"`. |
| `fecha_portada(date)`, `fecha_hoy()` | `"25 de octubre de 2026"`. |
| `convertir_a_grises(carpeta)` | **Desaconsejada** (ver abajo). |

Los datos del estudiante (`NOMBRE_ESTUDIANTE`, `INSTITUCION`, `CARRERA`,
`SUFIJO_ARCHIVOS`) salen del `.env` la primera vez que se necesitan;
importar el módulo no exige el `.env`.

## Cómo se conecta con la rúbrica

`criterios="C1"` se guarda en el `.docx` como un marcador invisible en el
encabezado. `tareas.py comprobar` lee el documento generado y, para cada
criterio de `TAREA.md`, busca su marcador, cuenta las palabras, figuras y
tablas de la sección (incluidas sus subsecciones) y las compara con el peso
del criterio. Por eso se pueden cambiar los títulos con libertad, pero no
quitar `criterios=`.

Si una sección no está marcada pero su título se parece al de un criterio, se
toma como cobertura **probable** y se avisa para que se marque.

## Índice

APA 7 no pide índice en trabajos de estudiante. Si el docente lo exige,
`nuevo_documento(..., indice=True)` lo añade tras la portada. Word lo
recalcula, con números de página, al abrir el documento. El PDF de
LibreOffice muestra la lista de encabezados sin números de página.

## Las figuras van a color

**Monocromático es el texto, no las imágenes.** Las figuras se insertan tal
como están y conservan su color original. En una captura o una fotografía el
color casi siempre es información —qué diodo está encendido, de qué color es
un cable, si una advertencia aparece en rojo— y convertirla a grises la
empobrece sin ganar nada.

`convertir_a_grises()` sigue existiendo para los documentos antiguos que ya
dependían de ella, pero **está desaconsejada y no debe usarse en documentos
nuevos**. Reescribe los archivos en el sitio, guardando antes una copia
intacta en la subcarpeta `originales/`.

## Compatibilidad con scripts antiguos

Los `generar_documento.py` creados con la versión anterior siguen funcionando
sin cambios. Lo que cambia en el resultado: los encabezados pasan a ser
estilos *Heading*, la portada sigue el orden APA (la afiliación va en una
línea, "Carrera, Institución") y `referencia()` interpreta `*asteriscos*`
como cursiva. Para que `comprobar` pueda verificarlos, añade `criterios="..."`
a sus `titulo(...)`.

## Cuándo NO usar esta plantilla

Para actividades **prácticas o experimentales**, el formato de entrega se
consulta con el usuario antes de generar el documento (ver el README de la
raíz).
