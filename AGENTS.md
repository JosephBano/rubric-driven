# Instrucciones para agentes de IA

Repositorio de tareas académicas. Ver `README.md` para la instalación y el
formato por defecto de los documentos.

## Antes de nada

- Debe existir `.env` en la raíz con los datos del estudiante. Si falta, detenerse
  y pedir al usuario que lo cree (`cp .env.example .env`). **Nunca** escribir
  datos personales en archivos versionados ni inventarlos.
- Usar siempre el Python de `.venv/` de la raíz. Si algo falla, empezar por
  `.venv/bin/python _plantillas/tareas.py verificar`.
- Si se modifica la herramienta (`_plantillas/`), ejecutar los tests:
  `.venv/bin/python -m unittest`.

## Estructura

```
_plantillas/                       la herramienta: CLI, plantilla APA y moldes. NUNCA guardar tareas aquí
materias/                          todo el contenido, al mismo nivel que _plantillas/
  <materia>/                       carpeta en minúsculas con guiones
    README.md                      ficha: docente, plataforma, formato, reglas + tabla de estado
    <CODIGO>_<Titulo_Corto>/       una carpeta por tarea (A15_..., P2_..., E1_...)
      TAREA.md                     ficha de la tarea con la rúbrica: LEER PRIMERO
      enunciado/                   enunciado y rúbrica del docente (PDF, DOCX, archivos base)
      capturas/                    evidencia real (nunca simulada)
      generar_documento.py         script que produce el entregable
      <CODIGO>_<Titulo_Corto>_<SUFIJO_ARCHIVOS>.docx / .pdf   entregables finales
```

Las materias y tareas se crean solo con `_plantillas/tareas.py materia|tarea`,
que las pone en `materias/`; no crear carpetas de materias en otro sitio. Las
tareas antiguas no siguen del todo esta estructura; no reorganizarlas sin pedirlo.

En adelante, `tareas` = `.venv/bin/python _plantillas/tareas.py`.

## Cómo resolver una tarea

Cuando el usuario pida "haz la tarea materias/<materia>/<carpeta>" (o similar):

1. Leer `TAREA.md` y **todo** el contenido de `enunciado/`, completo.
2. Leer `README.md` de la materia (docente, formato, nomenclatura, reglas): sus
   reglas prevalecen sobre las de la raíz. Si sus campos están vacíos, se aplica
   el formato por defecto.
3. **Rúbrica.** Debe quedar en la tabla `| ID | Criterio | Puntaje | Dónde se cumple |`
   de `TAREA.md`:
   - si está en un `.docx` de `enunciado/`: `tareas rubrica <tarea> --importar enunciado/<archivo>.docx`
     y revisar que los criterios importados son correctos;
   - si está en PDF o imagen: copiar cada criterio con su puntaje a la tabla;
   - si no hay rúbrica ni criterios, **preguntar** antes de generar.
   `tareas rubrica <tarea>` la muestra con el peso de cada criterio.
4. Formato: lo que diga `TAREA.md` > README de la materia > README de la raíz.
   - "por defecto" → APA 7 con `_plantillas/apa_docx.py`.
   - Práctica/experimental sin formato indicado → **preguntar antes de generar**.
5. Si falta algo que solo el usuario puede aportar (capturas de su equipo, datos
   personales, una decisión de enfoque), preguntar en vez de inventarlo.
6. `tareas esqueleto <tarea>`: escribe en `generar_documento.py` una sección por
   criterio con su extensión orientativa. Escribir el contenido en esas
   secciones **sin quitar `criterios="..."`** de los `titulo(...)`, ni
   `transversal(...)`, ni `criterios=` de `referencias(...)`: son lo que la
   comprobación usa. Si se añade una sección para un criterio, marcarla igual.
   Citar con `bib.cita("clave")` / `bib.cita_narrativa("clave")` tras
   `bib.agregar(...)`; nunca escribir citas a mano sin su referencia.
7. `tareas generar <tarea>`: genera el `.docx`, lo comprueba contra la rúbrica,
   rellena "Dónde se cumple" en `TAREA.md` y genera el PDF. **Corregir todos
   los `[error]`** y revisar los `[aviso]` (secciones poco desarrolladas según
   su peso, extensión, referencias sin citar). Si algún criterio no se puede
   cubrir (p. ej. faltan capturas que solo el usuario puede hacer), decírselo
   al usuario; no rellenarlo con contenido inventado.
8. Al terminar: `tareas marcar <tarea> lista` (actualiza `TAREA.md` y la tabla
   del README de la materia). Solo usar `--forzar` si el usuario lo pide.

## Recordatorios

- El repositorio es público y solo contiene el kit; las tareas viven solo en
  local. No añadir excepciones al `.gitignore` para `materias/` ni hacer commit
  de su contenido.
- Convertir a PDF siempre con `tareas.py pdf` o `generar`, nunca con `soffice` directo:
  un `.docx` mal formado puede hacer que LibreOffice llene `/tmp`.
- Con python-docx, no dejar dos tablas seguidas sin un párrafo entre medias.
