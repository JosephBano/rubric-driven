# -*- coding: utf-8 -*-
"""Genera el entregable de {codigo} — {titulo}.

Ejecutar desde la raíz del repositorio:
    .venv/bin/python _plantillas/tareas.py generar {ruta_carpeta}

Cuando la rúbrica esté en TAREA.md, `tareas.py esqueleto {ruta_carpeta}`
reescribe este archivo con una sección por criterio y la extensión que le
toca según su peso. Cada sección se marca con el ID de su criterio
(criterios="C1") para que `tareas.py comprobar` pueda verificar la cobertura.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[2] / "_plantillas"))  # materias/<materia>/<tarea>/
from apa_docx import *  # noqa: E402,F403

SALIDA = AQUI / nombre_entregable("{base}")

bib = Bibliografia()
# bib.agregar("clave", ["Apellido, A."], 2026, "Título de la obra", "Editorial")
# En el texto: parrafo(doc, f"... {bib.cita('clave')}.")

doc, figura, tabla = nuevo_documento(
    titulo={titulo_py},
    materia={materia_py},
    salida=SALIDA,
    tarea=AQUI,  # docente y fecha de entrega salen de TAREA.md y del README de la materia
)

# --- secciones (tareas.py esqueleto reescribe este bloque) ---
# Introducción: APA 7 la pone sin encabezado, justo después del título.
parrafo(doc, "")

titulo(doc, "Desarrollo", 1)
parrafo(doc, "")

titulo(doc, "Conclusiones", 1)
parrafo(doc, "")
# --- fin de secciones ---

referencias(doc, bib)

guardar_documento(doc, SALIDA)
