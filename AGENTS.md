# Instrucciones para agentes de IA

Repositorio de tareas académicas. Ver `README.md` para la instalación y el
formato por defecto de los documentos.

## Antes de nada

- Debe existir `.env` en la raíz con los datos del estudiante. Si falta, detenerse
  y pedir al usuario que lo cree (`cp .env.example .env`). **Nunca** escribir
  datos personales en archivos versionados ni inventarlos.
- Usar siempre el Python de `.venv/` de la raíz. Si algo falla, empezar por
  `.venv/bin/python _plantillas/tareas.py verificar`.

## Estructura

```
_plantillas/                       el kit: moldes y herramientas. NUNCA guardar tareas aquí
materias/                          todo el contenido, al mismo nivel que _plantillas/
  <materia>/                       carpeta en minúsculas con guiones
    README.md                      ficha: docente, plataforma, formato, reglas + tabla de estado
    <CODIGO>_<Titulo_Corto>/       una carpeta por tarea (A15_..., P2_..., E1_...)
      TAREA.md                     ficha de la tarea: LEER PRIMERO
      enunciado/                   enunciado y rúbrica del docente (PDF, DOCX, archivos base)
      capturas/                    evidencia real (nunca simulada)
      generar_documento.py         script que produce el entregable
      <CODIGO>_<Titulo_Corto>_<SUFIJO_ARCHIVOS>.docx / .pdf   entregables finales
```

Las materias y tareas se crean solo con `_plantillas/tareas.py materia|tarea`,
que las pone en `materias/`; no crear carpetas de materias en otro sitio. Las
tareas antiguas no siguen del todo esta estructura; no reorganizarlas sin pedirlo.

## Cómo resolver una tarea

Cuando el usuario pida "haz la tarea materias/<materia>/<carpeta>" (o similar):

1. Leer `TAREA.md` y **todo** el contenido de `enunciado/`, completo.
2. Leer `README.md` de la materia (docente, formato, nomenclatura, reglas): sus
   reglas prevalecen sobre las de la raíz. Si sus campos están vacíos, se aplica
   el formato por defecto.
3. **Rúbrica.** Localizarla (en `enunciado/` o en `TAREA.md`) y extraer cada
   criterio con su puntaje. El documento se genera a partir de ella:
   - cada criterio debe quedar cubierto por al menos una sección concreta;
   - las secciones y su extensión se reparten según el peso de cada criterio;
   - si no hay rúbrica ni criterios en `TAREA.md`, **preguntar** antes de generar.
4. Formato: lo que diga `TAREA.md` > README de la materia > README de la raíz.
   - "por defecto" → APA 7 con `_plantillas/apa_docx.py`.
   - Práctica/experimental sin formato indicado → **preguntar antes de generar**.
5. Si falta algo que solo el usuario puede aportar (capturas de su equipo, datos
   personales, una decisión de enfoque), preguntar en vez de inventarlo.
6. Escribir el contenido en el `generar_documento.py` de la carpeta (ya conectado
   a la plantilla y con el nombre de salida correcto) y ejecutarlo con
   `.venv/bin/python`. Generar el PDF con `_plantillas/tareas.py pdf <carpeta>`.
7. Verificar contra la rúbrica: rellenar en `TAREA.md` la columna "Dónde se
   cumple" de cada criterio, con la sección del documento que lo cubre. Si
   algún criterio queda sin cubrir, decirlo al usuario.
8. Al terminar: actualizar `Estado:` en `TAREA.md` y la fila en la tabla del
   README de la materia (pendiente → lista / entregada), y recordar al usuario
   ejecutar `_plantillas/tareas.py respaldo`.

## Recordatorios

- El repositorio remoto es público y solo contiene el kit: no añadir excepciones
  al `.gitignore` para materias ni hacer commit de su contenido.
- Convertir a PDF siempre con `tareas.py pdf` y nunca con `soffice` directo:
  un `.docx` mal formado puede hacer que LibreOffice llene `/tmp`.
- Con python-docx, no dejar dos tablas seguidas sin un párrafo entre medias.
