#!/usr/bin/env python3
"""Crea carpetas de materias y tareas a partir de las plantillas.

Uso:
    python _plantillas/nuevo.py materia <carpeta> "<Nombre de la materia>"
    python _plantillas/nuevo.py tarea <carpeta-materia> <codigo> "<Título>" [--tipo T]

Ejemplos:
    python _plantillas/nuevo.py materia base-datos-2 "Sistemas Gestores de Bases de Datos 2"
    python _plantillas/nuevo.py tarea sgbd1 A15 "Procedimientos almacenados"
    python _plantillas/nuevo.py tarea sis-operativos-redes P5 "Servidor web" --tipo practica
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLAS = Path(__file__).resolve().parent
TIPOS = {
    "actividad": "Actividad (A)",
    "practica": "Práctico-experimental (P)",
    "evaluacion": "Evaluación (E)",
    "otro": "Otro",
}


def slug_titulo(titulo: str) -> str:
    """'Procedimientos almacenados' -> 'Procedimientos_Almacenados' (sin tildes)."""
    sin_tildes = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    palabras = re.findall(r"[A-Za-z0-9]+", sin_tildes)
    return "_".join(p[:1].upper() + p[1:] for p in palabras)


def tipo_por_codigo(codigo: str) -> str:
    return {"A": "actividad", "P": "practica", "E": "evaluacion"}.get(codigo[:1].upper(), "otro")


def nombre_materia(carpeta: Path) -> str:
    readme = carpeta / "README.md"
    if readme.exists():
        for linea in readme.read_text(encoding="utf-8").splitlines():
            if linea.startswith("# "):
                return linea[2:].strip()
    return carpeta.name


def rellenar(plantilla: Path, **valores) -> str:
    texto = plantilla.read_text(encoding="utf-8")
    for clave, valor in valores.items():
        texto = texto.replace("{" + clave + "}", valor)
    return texto


def crear_materia(carpeta: str, nombre: str) -> None:
    destino = RAIZ / carpeta
    if destino.exists():
        sys.exit(f"Ya existe: {destino.relative_to(RAIZ)}")
    destino.mkdir()
    (destino / "README.md").write_text(
        rellenar(PLANTILLAS / "materia" / "README.md", materia_nombre=nombre), encoding="utf-8"
    )
    print(f"Materia creada: {carpeta}/")


def crear_tarea(materia: str, codigo: str, titulo: str, tipo: str | None) -> None:
    carpeta_materia = RAIZ / materia
    if not carpeta_materia.is_dir():
        sys.exit(f"No existe la materia '{materia}'. Créala primero con: nuevo.py materia {materia} \"Nombre\"")
    codigo = codigo.upper()
    tipo = tipo or tipo_por_codigo(codigo)
    nombre = f"{codigo}_{slug_titulo(titulo)}"
    destino = carpeta_materia / nombre
    if destino.exists():
        sys.exit(f"Ya existe: {destino.relative_to(RAIZ)}")

    destino.mkdir()
    (destino / "enunciado").mkdir()
    (destino / "capturas").mkdir()
    (destino / "TAREA.md").write_text(
        rellenar(
            PLANTILLAS / "tarea" / "TAREA.md",
            codigo=codigo,
            titulo=titulo,
            materia_nombre=nombre_materia(carpeta_materia),
            tipo=TIPOS[tipo],
        ),
        encoding="utf-8",
    )

    readme = carpeta_materia / "README.md"
    fila = f"| `{nombre}` | {codigo} — {titulo} | pendiente |\n"
    if readme.exists():
        texto = readme.read_text(encoding="utf-8")
        if "| Carpeta | Entrega | Estado |" in texto:
            readme.write_text(texto.rstrip("\n") + "\n" + fila, encoding="utf-8")

    print(f"Tarea creada: {destino.relative_to(RAIZ)}/")
    print("  1. Deja el PDF/DOCX del docente en enunciado/ (o pega el texto en TAREA.md).")
    print("  2. Completa TAREA.md: fecha, qué se entrega, formato y notas.")
    print(f"  3. Pídele al agente de IA: \"haz la tarea {materia}/{nombre}\".")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="accion", required=True)

    p_materia = sub.add_parser("materia", help="crea la carpeta de una materia")
    p_materia.add_argument("carpeta", help="nombre de carpeta en minúsculas con guiones, p. ej. programacion-web-2")
    p_materia.add_argument("nombre", help="nombre completo de la materia")

    p_tarea = sub.add_parser("tarea", help="crea la carpeta de una tarea dentro de una materia")
    p_tarea.add_argument("materia", help="carpeta de la materia, p. ej. sgbd1")
    p_tarea.add_argument("codigo", help="código del docente: A15, P2, E1...")
    p_tarea.add_argument("titulo", help="título corto de la tarea")
    p_tarea.add_argument("--tipo", choices=TIPOS, help="se deduce de la letra del código si se omite")

    args = parser.parse_args()
    if args.accion == "materia":
        crear_materia(args.carpeta, args.nombre)
    else:
        crear_tarea(args.materia, args.codigo, args.titulo, args.tipo)


if __name__ == "__main__":
    main()
