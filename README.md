# rubric-driven

Herramienta de línea de comandos para preparar informes académicos **a partir de la rúbrica** con la que se van a evaluar, y para comprobar, sobre el `.docx` final, que la cubren.

La idea es sencilla: si el docente califica con una rúbrica, el documento debería estar construido desde ella y no al revés. `rubric-driven`:

1. **Lee la rúbrica**: de la tabla de `TAREA.md` o importada del `.docx` del docente (tablas simples o matrices de niveles).
2. **La convierte en estructura**: una sección por criterio, marcada con su ID, y una extensión orientativa proporcional a su puntaje.
3. **Genera el documento** en APA 7 (`.docx` y `.pdf`): portada de estudiante, encabezados reales de Word, figuras, tablas, citas y lista de referencias.
4. **Lo comprueba** abriendo el `.docx` generado, sin fiarse de lo que diga el script ni el agente:
   - si cada criterio está cubierto;
   - si la extensión de cada sección va acorde con su peso, y la del documento con la que se pide;
   - si queda contenido pendiente (capturas que faltan, `TODO`, secciones vacías);
   - si cada cita tiene su referencia y cada referencia está citada.
5. **Lleva el seguimiento**: tareas pendientes ordenadas por fecha de entrega, con su cobertura.

Está pensada para usarse a mano o con un agente de IA (Claude, Codex...), que sigue las reglas de [`AGENTS.md`](AGENTS.md).

## Ejemplo

```text
$ tareas.py comprobar materias/sgbd1/A15_Procedimientos_Almacenados
Comprobación de A15_Procedimientos_Almacenados
  Documento: A15_Procedimientos_Almacenados_Perez_Ana.docx
  Cuerpo: 358 palabras, 5 secciones, 14 citas, 1 referencias

  Rúbrica
  [ok]    C1  Explica qué es un procedimiento almacenado y sus      4 pts  → Explica qué es... (195 pal.)
  [ok]    C2  Implementa tres procedimientos con parámetros IN      4 pts  → Implementa tres... (28 pal., 1 tabla)
  [ok]    C3  Evidencia de ejecución con capturas                   4 pts  → Evidencia de ejecución con capturas (15 pal.)
  [ok]    C4  Referencias en formato APA                            4 pts  → Referencias
  [ok]    C5  Ortografía y redacción                                4 pts  → todo el documento

  Puntos con sección que los cubre: 20 de 20
  [error] Contenido pendiente en «Evidencia de ejecución con capturas»: [FALTA LA CAPTURA: p1.png]
  [error] Cita sin referencia: Gómez (2019).
  [aviso] C2 poco desarrollado: 28 palabras frente a ~79 según su peso (4 pts).
  [aviso] Extensión corta: 358 palabras frente a ~1200 que pide TAREA.md.
```

## Instalación

Requisitos: **Python 3.10+**, **Git** y, para los PDF, **LibreOffice** (sin él los `.docx` se generan igual y el PDF se exporta a mano desde Word).

```bash
git clone <url-de-este-repo> rubric-driven && cd rubric-driven
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

cp .env.example .env        # tus datos de portada (obligatorio)
.venv/bin/python _plantillas/tareas.py verificar
```

El `.env` lleva los datos de la portada (nombre, institución, carrera) y el sufijo de los entregables. No se sube al repositorio.

> Para no escribir la ruta completa: `alias tareas='.venv/bin/python _plantillas/tareas.py'`. Los ejemplos de abajo usan ese alias.

## Uso

### 1. Crear la materia y la tarea

```bash
tareas materia sgbd1 "Sistemas de Bases de Datos I"     # rellena docente y reglas en su README.md
tareas tarea sgbd1 A15 "Procedimientos almacenados"
```

```
materias/sgbd1/A15_Procedimientos_Almacenados/
  TAREA.md                 ← ficha: fecha, extensión, RÚBRICA, formato, notas
  enunciado/               ← enunciado y rúbrica del docente
  capturas/                ← evidencia real
  generar_documento.py     ← el contenido del documento
```

### 2. Pasar la rúbrica a `TAREA.md`

```bash
tareas rubrica materias/sgbd1/A15_Procedimientos_Almacenados --importar enunciado/rubrica.docx
```

Si la rúbrica viene en PDF o en una imagen, copia los criterios a la tabla a mano (o pídeselo al agente):

```markdown
| ID | Criterio | Puntaje | Dónde se cumple |
|---|---|---|---|
| C1 | Explica qué es un procedimiento almacenado y sus ventajas | 4 | |
| C2 | Implementa tres procedimientos con parámetros IN y OUT | 4 | |
```

Rellena también la fecha de entrega y, si el docente la fija, la extensión (`1500 palabras`, `4-6 páginas`). Sin argumentos, `tareas rubrica <tarea>` muestra la rúbrica con el peso de cada criterio.

### 3. Esqueleto: una sección por criterio

```bash
tareas esqueleto materias/sgbd1/A15_Procedimientos_Almacenados
```

Escribe en `generar_documento.py` algo así:

```python
# C1 · Explica qué es un procedimiento almacenado y sus ventajas · 4 pts (20 %) · ~320 palabras
titulo(doc, 'Explica qué es un procedimiento almacenado y sus ventajas', 1, criterios='C1')
parrafo(doc, "")
...
transversal(doc, 'C5')                    # Ortografía y redacción: todo el documento
referencias(doc, bib, criterios='C4')     # Referencias en formato APA
```

Los títulos se pueden cambiar con libertad: lo que conecta la sección con el criterio es `criterios='C1'`, que queda guardado como marcador invisible en el `.docx`. Los criterios de ortografía, formato o redacción se reconocen como **transversales**; los de referencias se asignan a la sección Referencias. Mientras las secciones estén vacías, el esqueleto se puede regenerar; si ya tienen texto, hace falta `--forzar` (y se guarda una copia `.bak`).

### 4. Escribir, generar y comprobar

```bash
tareas generar materias/sgbd1/A15_Procedimientos_Almacenados
```

Ejecuta `generar_documento.py`, comprueba el `.docx` contra la rúbrica, rellena la columna "Dónde se cumple" de `TAREA.md` y genera el PDF. Termina con error si algún criterio queda sin cubrir o hay contenido pendiente. `tareas comprobar <tarea>` hace solo la comprobación (`--actualizar` para escribir en `TAREA.md`).

### 5. Seguimiento

```bash
tareas estado                 # pendientes por fecha de entrega, con su cobertura
tareas marcar <tarea> lista   # TAREA.md + tabla del README de la materia
```

```text
Entrega      Días  Estado     Materia         Tarea                                 Rúbrica
2026-10-25     +7  pendiente  sgbd1           A15_Procedimientos_Almacenados        5/5 cubiertos, 3 errores
—               —  pendiente  sgbd1           P2_Instalacion_De_PostgreSQL          sin rúbrica
```

`marcar ... lista|entregada` se niega si la comprobación tiene errores (salvo con `--forzar`).

### Referencia de comandos

| Comando | Qué hace |
|---|---|
| `verificar` | Comprueba `.env`, dependencias, LibreOffice y que el repo público no contenga materias. |
| `materia <carpeta> "<Nombre>"` | Crea `materias/<carpeta>/` con su `README.md`. |
| `tarea <materia> <código> "<Título>"` | Crea la carpeta de la tarea. El tipo se deduce de la letra: A = actividad, P = práctica, E = evaluación. |
| `rubrica <tarea> [--importar x.docx]` | Muestra la rúbrica de `TAREA.md` o la importa del `.docx` del docente. |
| `esqueleto <tarea> [--palabras N]` | Escribe en `generar_documento.py` una sección por criterio, con su extensión orientativa. |
| `generar <tarea> [--sin-pdf]` | Genera el `.docx`, lo comprueba, actualiza `TAREA.md` y genera el `.pdf`. |
| `comprobar <tarea> [--actualizar]` | Verifica el `.docx` contra la rúbrica. |
| `pdf <archivo.docx \| carpeta>` | Convierte a PDF con LibreOffice, con límites de disco y tiempo. |
| `estado [<materia>] [--todas]` | Tareas por fecha de entrega con su cobertura. |
| `marcar <tarea> <estado>` | `pendiente`, `lista` o `entregada`, en `TAREA.md` y en el README de la materia. |

## Formato de los documentos

Salvo que `TAREA.md` o el README de la materia digan otra cosa, los documentos siguen **APA 7 (trabajo de estudiante)**:

- **Portada** sin tablas ni logos: título, autor, carrera e institución, materia, docente y fecha de entrega (se toman del `.env`, del README de la materia y de `TAREA.md`).
- **Times New Roman 12**, interlineado doble, márgenes de 1 pulgada y número de página arriba a la derecha.
- **Encabezados APA de nivel 1 a 3** con los estilos de Word (*Heading 1-3*): aparecen en el panel de navegación, en el índice y como marcadores del PDF.
- Introducción sin encabezado, tras el título repetido en negrita.
- **Citas en el texto y referencias** con `Bibliografia`: `(Ramos y Pérez, 2023)`, `Lee et al. (2021)`. La lista sale en página nueva, en orden alfabético, con sangría francesa y solo con las fuentes citadas.
- Figuras y tablas en formato APA, numeradas automáticamente.
- **Texto monocromático.** Las figuras conservan su color original, porque en una captura el color suele ser información.
- Toda evidencia (capturas, resultados) debe ser real; nunca simulada.

Para actividades **prácticas o experimentales** no se asume este formato: se indica en `TAREA.md` o se pregunta.

La referencia de la plantilla está en [`_plantillas/PLANTILLA_README.md`](_plantillas/PLANTILLA_README.md).

## Estructura del repositorio

```
├── README.md, AGENTS.md, LICENSE, requirements.txt, .env.example
├── _plantillas/           ← la herramienta (pública)
│   ├── tareas.py          ← la CLI
│   ├── apa_docx.py        ← generación del .docx en APA 7
│   ├── rubrica.py         ← leer, importar y escribir rúbricas
│   ├── esqueleto.py       ← rúbrica → secciones de generar_documento.py
│   ├── comprobar.py       ← análisis del .docx frente a la rúbrica
│   ├── ficha.py           ← lectura de TAREA.md y README de materias
│   ├── config.py          ← lee el .env
│   ├── materia/, tarea/   ← moldes
├── tests/                 ← python -m unittest
└── materias/              ← TUS TAREAS (solo en local, nunca se suben)
```

`materias/` está en `.gitignore` (lista blanca): nada de lo que haya dentro llega al repositorio, y `verificar` lo comprueba. Si quieres conservar tus tareas, haz tú una copia (disco externo, nube...).

## Desarrollo

```bash
.venv/bin/python -m unittest -v
```

Los tests no tocan tu `.env` ni `materias/`: trabajan sobre una copia temporal del kit. El de PDF se salta si no hay LibreOffice. La CI ejecuta los tests con Python 3.10 y 3.13.

## Uso responsable

La herramienta organiza, da formato y verifica; no sustituye tu trabajo. Muchas instituciones regulan el uso de IA en las entregas: revisa la normativa de tu institución y la de cada docente antes de usar un agente para redactar contenido, y decláralo cuando se pida.

## Licencia

[MIT](LICENSE). El contenido de las materias no forma parte de este repositorio.

Este repositorio es **público**: no debe contener información sensible. Los datos personales van solo en `.env`, que no se sube.
