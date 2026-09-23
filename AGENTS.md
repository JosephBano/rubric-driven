# Instrucciones para agentes de IA

Repositorio de tareas académicas (ver `README.md` para datos del estudiante y el
formato por defecto de los documentos).

## Estructura

```
<materia>/                     carpeta en minúsculas con guiones
  README.md                    reglas propias de la materia + tabla de estado
  <CODIGO>_<Titulo_Corto>/     una carpeta por tarea (A15_..., P2_..., E1_...)
    TAREA.md                   ficha de la tarea: LEER PRIMERO
    enunciado/                 material del docente (PDF, DOCX, rúbrica, archivos base)
    capturas/                  evidencia real (nunca simulada)
    generar_documento.py       script que produce el entregable
    <CODIGO>_<Titulo_Corto>_Bano_Joseph.docx / .pdf   entregables finales
```

Las carpetas se crean con `_plantillas/nuevo.py` (ver `_plantillas/PLANTILLA_README.md`).
Las carpetas antiguas no siguen del todo esta estructura; no reorganizarlas sin pedirlo.

## Cómo resolver una tarea

Cuando el usuario pida "haz la tarea <materia>/<carpeta>" (o similar):

1. Leer `TAREA.md` y **todo** el contenido de `enunciado/`. Si el enunciado es un
   PDF, leerlo completo, incluida la rúbrica.
2. Leer `README.md` de la materia: sus reglas prevalecen sobre las de la raíz.
3. Formato: lo que diga `TAREA.md` > README de la materia > README de la raíz.
   - "por defecto" → APA 7 monocromático con `_plantillas/apa_docx.py`.
   - Práctica/experimental sin formato indicado → **preguntar antes de generar**.
4. Si falta algo que solo el usuario puede aportar (capturas de su equipo, datos
   personales, una decisión de enfoque), preguntar en vez de inventarlo.
5. Generar el documento con un `generar_documento.py` dentro de la carpeta, para
   poder regenerarlo. Nombre de salida: `<CODIGO>_<Titulo_Corto>_Bano_Joseph`.
6. Al terminar: actualizar `Estado:` en `TAREA.md` y la fila en la tabla del
   README de la materia (pendiente → lista / entregada).

## Recordatorios

- Repositorio público: nada de contraseñas, datos de terceros ni capturas con
  información privada.
- Python: reutilizar `arquitectura-computacional/.venv`.
- Conversión a PDF con LibreOffice: usar `TMPDIR` en disco (el tmpfs de `/tmp` se llena).
