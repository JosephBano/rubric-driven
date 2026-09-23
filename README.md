# istpet-publico

## Propósito

Kit para organizar y generar tareas académicas con ayuda de un agente de IA (Claude, Codex, etc.):

- una estructura fija de carpetas por materia y por tarea, creada con un solo comando;
- una ficha por tarea (`TAREA.md`) y una carpeta `enunciado/` donde se dejan el enunciado y la **rúbrica**;
- instrucciones para el agente ([`AGENTS.md`](AGENTS.md)) que le indican cómo leer la tarea y generar el entregable a partir de la rúbrica;
- una plantilla de Python que produce informes `.docx` en normas APA 7, además de la conversión a `.pdf`.

Este repositorio es **público** y solo contiene el kit. El contenido de las materias queda en local (está en `.gitignore`) y se respalda aparte, en un repositorio **privado** (ver [Respaldo](#respaldo-de-las-materias)).

## Instalación

### Requisitos del sistema

- **Python 3.10 o superior.**
- **Git.**
- **LibreOffice** (recomendado): convierte los `.docx` a `.pdf`. Sin él los `.docx` se generan igual, pero el `.pdf` hay que exportarlo a mano (por ejemplo, desde Word).

### Pasos

```bash
# 1. Clonar e instalar las dependencias de Python en un entorno propio
git clone <url-de-este-repo> materias && cd materias
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2. Cargar tus datos personales (OBLIGATORIO)
cp .env.example .env        # y edítalo con tus datos

# 3. Comprobar que todo está en orden
.venv/bin/python _plantillas/tareas.py verificar
```

> **El `.env` es obligatorio.** Sin él no se puede crear materias ni tareas ni generar documentos: la herramienta se detiene y explica qué falta. El `.env` contiene los datos de la portada (nombre, institución, carrera), el sufijo que llevan los entregables y, opcionalmente, la URL del repositorio privado de respaldo. No se sube al repositorio.

## Uso

Todos los comandos se ejecutan desde la raíz con `.venv/bin/python _plantillas/tareas.py <comando>`.

| Comando | Qué hace |
|---|---|
| `verificar` | Comprueba `.env`, dependencias de Python, LibreOffice y que el repo público no contenga materias. |
| `materia <carpeta> "<Nombre>"` | Crea la carpeta de una materia con su `README.md`. |
| `tarea <materia> <código> "<Título>"` | Crea la carpeta de una tarea (ver abajo). El tipo se deduce de la letra: A = actividad, P = práctica, E = evaluación. |
| `pdf <archivo.docx \| carpeta>` | Convierte a `.pdf` con LibreOffice, con protecciones contra documentos que lo cuelgan. |
| `respaldo ["mensaje"]` | Guarda todas las materias en el repositorio privado de respaldo. |
| `restaurar` | En un equipo nuevo, recupera las materias desde el repositorio privado. |

### Flujo de una tarea

```bash
.venv/bin/python _plantillas/tareas.py tarea sgbd1 A15 "Procedimientos almacenados"
```

```
sgbd1/A15_Procedimientos_Almacenados/
  TAREA.md                 ← ficha: fecha, rúbrica, qué se entrega, formato, notas
  enunciado/               ← enunciado y RÚBRICA del docente (PDF, DOCX...)
  capturas/                ← evidencia real
  generar_documento.py     ← script ya conectado a la plantilla APA
```

1. Deja el enunciado **y la rúbrica** en `enunciado/`. Sin rúbrica, el agente no puede garantizar que el entregable cubra lo que se evalúa: si no la hay, indícalo en `TAREA.md` con los criterios que el docente haya dado.
2. Completa `TAREA.md`.
3. Pide al agente: *"lee AGENTS.md y haz la tarea sgbd1/A15_Procedimientos_Almacenados"*. El agente arma el documento criterio por criterio a partir de la rúbrica y rellena en `TAREA.md` la columna "Dónde se cumple".
4. Genera el PDF: `.venv/bin/python _plantillas/tareas.py pdf sgbd1/A15_Procedimientos_Almacenados`.

### Respaldo de las materias

Las materias no se suben a este repositorio público. `tareas.py respaldo` las guarda en un segundo repositorio git (`.respaldo.git/`, en esta misma carpeta), y si `RESPALDO_REMOTO` está definido en `.env` las sube a ese remoto.

1. Crea un repositorio **privado** vacío en GitHub (p. ej. `materias-privado`).
2. Pon su URL en `.env`: `RESPALDO_REMOTO="git@github.com:usuario/materias-privado.git"`.
3. Ejecuta `.venv/bin/python _plantillas/tareas.py respaldo` cada vez que termines una tarea.

No se respaldan los entornos virtuales, `node_modules`, `.env` ni las carpetas que ya tienen su propio repositorio git.

Para recuperar las materias en otro equipo: instala el kit, pon `RESPALDO_REMOTO` en `.env` y ejecuta `.venv/bin/python _plantillas/tareas.py restaurar`.

## Formato de los documentos y actividades

Salvo que se indique lo contrario (en `TAREA.md` o en el README de la materia), los documentos entregables siguen este estilo por defecto:

- **Normas APA 7.ª edición.**
- **Texto monocromático:** negro, sin colores decorativos. Las figuras conservan su color original, porque en una captura el color suele ser información.
- **Portada sencilla**, sin tablas ni logos: título, nombre del estudiante, institución, carrera, materia y fecha.
- Tipografía **Times New Roman 12 pt**, interlineado doble, márgenes de 1 pulgada.
- Figuras en formato APA (rótulo, descripción en cursiva, imagen, nota explicativa) cuando el trabajo requiere evidencia visual.
- Estructura guiada por la **rúbrica**: cada criterio evaluado queda cubierto por una sección del documento.
- Redacción técnica, clara y directa, sin relleno.
- Toda evidencia (capturas de pantalla, resultados de ejecución) debe ser real y verificada antes de incluirse en el documento; nunca simulada o inventada.

La plantilla [`_plantillas/apa_docx.py`](_plantillas/apa_docx.py) ya implementa este estilo. Ver [`_plantillas/PLANTILLA_README.md`](_plantillas/PLANTILLA_README.md) para el modo de uso.

### Excepción: actividades prácticas/experimentales

Para actividades **prácticas o experimentales** (instalación de software, laboratorios, ejercicios de ejecución en un entorno real, etc.), **no se asume este formato por defecto**. El formato de entrega se indica en `TAREA.md`; si no está, el agente debe preguntarlo antes de generar nada.

## Nota

Este repositorio es **público**: no debe contener información sensible (contraseñas, datos personales, capturas con información privada, etc.). Los datos personales van solo en `.env`, que está en `.gitignore`.
