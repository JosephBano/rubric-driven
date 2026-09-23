# Plantilla APA / monocromática (`apa_docx.py`)

Módulo de Python reutilizable para generar informes `.docx` en normas APA 7,
con el texto monocromático, con el mismo estilo usado en A7, A8 y A14 de
Arquitectura Computacional. Es el formato **por defecto** descrito en
`README.md` de la raíz del repositorio, salvo para actividades
prácticas/experimentales (ver esa excepción en el README).

## Las figuras van a color

**Monocromático es el texto, no las imágenes.** Las figuras se insertan tal
como están y conservan su color original. En una captura o una fotografía el
color casi siempre es información —qué diodo está encendido, de qué color es
un cable, si una advertencia aparece en rojo— y convertirla a grises la
empobrece sin ganar nada.

`convertir_a_grises()` sigue existiendo para los documentos antiguos que ya
dependían de ella, pero **está desaconsejada y no debe usarse en documentos
nuevos**. Reescribe los archivos en el sitio; desde ahora guarda antes una
copia intacta en la subcarpeta `originales/`, para que la conversión sea
reversible. Antes no lo hacía, y por eso las capturas de la Parte 3 del
práctico experimental de Arquitectura Computacional se perdieron en color de
forma definitiva.

## Requisitos

- El `.venv` de la raíz del repositorio, con `requirements.txt` instalado (ver
  README.md de la raíz).
- El archivo `.env` de la raíz con los datos del estudiante. `apa_docx` los lee
  al importarse; si falta, el script termina con un mensaje que explica cómo
  crearlo.

```bash
.venv/bin/python materias/<materia>/<tarea>/generar_documento.py
```

## Uso básico

`tareas.py tarea` ya crea un `generar_documento.py` con este encabezado. La
ruta a la plantilla es relativa, así que funciona en cualquier equipo donde se
clone el repositorio:

```python
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[2] / "_plantillas"))  # materias/<materia>/<tarea>/
from apa_docx import *

CAP = AQUI / "capturas"
SALIDA = AQUI / nombre_entregable("A15_Titulo_Corto")  # añade el sufijo del .env

# Las capturas se insertan tal cual: conservan su color original.

doc, figura, tabla = nuevo_documento(
    titulo="Título del Informe",
    materia="Nombre de la Materia",
    salida=SALIDA,
    carpeta_capturas=CAP,        # opcional; por defecto es "capturas/" junto a SALIDA
    fecha="24 de agosto de 2026",  # opcional; por defecto, la fecha de hoy
)

titulo(doc, "Introducción", 2)
parrafo(doc, "Texto del párrafo, justificado, con sangría de primera línea...")

titulo(doc, "Desarrollo", 2)
titulo(doc, "Subsección", 3)
vinieta(doc, "Punto de una lista con viñetas.")
codigo(doc, "$ comando de ejemplo\n$ otro comando")

figura(doc, 1, "Descripción de la figura en cursiva", "fig1_captura.png",
       "Nota explicativa que aparece debajo, en letra más pequeña.")

tabla(doc, 1, "Descripción de la tabla en cursiva",
      ["Columna A", "Columna B", "Columna C"],
      [("dato1", "dato2", "dato3"), ("dato4", "dato5", "dato6")])

titulo(doc, "Referencias", 1)
referencia(doc, "Autor, A. A. (2026). Título de la obra. Editorial.")

guardar_documento(doc, SALIDA)
```

`nuevo_documento()` ya arma la portada (título, nombre, institución, carrera,
materia, fecha — sin tablas ni logos), aplica Times New Roman 12 a doble
espacio, márgenes de 1 pulgada y numeración de página, y repite el título en
negrita al inicio del cuerpo. Los datos del estudiante salen del `.env`
(`NOMBRE_ESTUDIANTE`, `INSTITUCION`, `CARRERA`); pasar `nombre=`,
`institucion=` o `carrera=` a `nuevo_documento()` solo si hay que
sobreescribirlos para un caso puntual.

## Funciones disponibles

| Función | Para qué sirve |
|---|---|
| `nuevo_documento(...)` | Crea el `Document()`, aplica estilos y arma la portada. Devuelve `(doc, figura, tabla)`. |
| `titulo(doc, texto, nivel)` | Encabezado. `nivel=1` centrado (secciones principales), `2`/`3` alineados a la izquierda (`3` en cursiva). |
| `parrafo(doc, texto, ...)` | Párrafo justificado con sangría, doble espacio. Acepta `negrita`, `cursiva`, `alineacion`, `sangria=False` para portada, etc. |
| `vinieta(doc, texto)` | Punto de lista con viñetas. |
| `codigo(doc, texto)` | Bloque de comandos/código en Courier New, espacio sencillo. |
| `figura(doc, numero, descripcion, archivo, nota)` | Figura en formato APA (rótulo + descripción en cursiva + imagen + Nota). `archivo` es relativo a `carpeta_capturas`. |
| `tabla(doc, numero, descripcion, encabezados, filas)` | Tabla genérica en formato APA con bordes y encabezado sombreado. |
| `referencia(doc, texto)` | Entrada de la lista de referencias con sangría francesa. |
| `convertir_a_grises(carpeta)` | **Desaconsejada.** Convierte las capturas de una carpeta a escala de grises, reescribiéndolas en el sitio (respalda antes en `originales/`). Las figuras van a color: no usar en documentos nuevos. |
| `leer_fuente(ruta)` | Lee un archivo de texto/código completo (útil para volcar código fuente en un Anexo). |
| `guardar_documento(doc, salida)` | Equivale a `doc.save(salida)` con un mensaje de confirmación. |
| `nombre_entregable(base, extension=".docx")` | `"A15_Titulo"` → `"A15_Titulo_<SUFIJO_ARCHIVOS>.docx"`. |
| `fecha_hoy()` | Fecha de hoy en formato de portada: `"23 de septiembre de 2026"`. |

## Cuándo NO usar esta plantilla

Para actividades **prácticas o experimentales**, el formato de entrega se
consulta con el usuario antes de generar el documento (ver README.md de la
raíz). No asumir este estilo APA por defecto en esos casos.

---

# Crear materias y tareas (`tareas.py`)

La referencia completa de comandos (`verificar`, `materia`, `tarea`, `pdf`) está en el README.md de la raíz, y las reglas que sigue el agente
de IA, en `AGENTS.md`.
