# -*- coding: utf-8 -*-
"""Genera el entregable de {codigo} — {titulo}.

Ejecutar desde la raíz del repositorio:
    .venv/bin/python {ruta_script}
    .venv/bin/python _plantillas/tareas.py pdf {ruta_carpeta}

La estructura de secciones debe seguir la rúbrica (ver TAREA.md y enunciado/):
cada criterio evaluado tiene que quedar cubierto por al menos una sección.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[2] / "_plantillas"))  # materias/<materia>/<tarea>/
from apa_docx import *  # noqa: E402,F403

SALIDA = AQUI / nombre_entregable("{base}")

doc, figura, tabla = nuevo_documento(
    titulo="{titulo}",
    materia="{materia_nombre}",
    salida=SALIDA,
)

titulo(doc, "Introducción", 2)
parrafo(doc, "")

titulo(doc, "Desarrollo", 2)
parrafo(doc, "")

titulo(doc, "Conclusiones", 2)
parrafo(doc, "")

titulo(doc, "Referencias", 1)

guardar_documento(doc, SALIDA)
