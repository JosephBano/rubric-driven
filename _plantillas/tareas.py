#!/usr/bin/env python3
"""Herramienta del repositorio: materias, tareas y PDF.

Uso (desde la raíz del repositorio):
    python _plantillas/tareas.py verificar
    python _plantillas/tareas.py materia <carpeta> "<Nombre de la materia>"
    python _plantillas/tareas.py tarea <materia> <codigo> "<Título>" [--tipo T]
    python _plantillas/tareas.py pdf <archivo.docx | carpeta>

Ejemplos:
    python _plantillas/tareas.py materia programacion-web-2 "Programación Web 2"
    python _plantillas/tareas.py tarea sgbd1 A15 "Procedimientos almacenados"
    python _plantillas/tareas.py pdf materias/sgbd1/A15_Procedimientos_Almacenados

Las materias se crean siempre dentro de materias/; <materia> es solo el nombre
de su carpeta (sgbd1), no la ruta.
"""
import argparse
import importlib.util
import os
import re
import resource
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ARCHIVO_ENV, RAIZ, ConfigError, cargar, cargar_o_salir  # noqa: E402

PLANTILLAS = RAIZ / "_plantillas"
MATERIAS = RAIZ / "materias"
TIPOS = {
    "actividad": "Actividad (A)",
    "practica": "Práctico-experimental (P)",
    "evaluacion": "Evaluación (E)",
    "otro": "Otro",
}

# LibreOffice: temporales en disco (no en el tmpfs de /tmp) y tope de 2 GB por
# archivo escrito; un .docx mal formado puede hacer que soffice llene el disco.
LO_TMP = Path.home() / ".cache" / "lo-tmp"
LO_PERFIL = Path.home() / ".cache" / "lo-perfil"
LO_LIMITE_BYTES = 2 * 1024**3
LO_TIMEOUT = 300


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
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


def git(*args, check=True, capturar=False):
    return subprocess.run(
        ["git", *args], cwd=RAIZ, check=check, text=True, capture_output=capturar,
    )


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------
def cmd_verificar(_args) -> None:
    ok = True

    def informe(bien: bool, texto: str) -> None:
        nonlocal ok
        ok &= bien
        print(("  [ok]    " if bien else "  [falta] ") + texto)

    print("Configuración")
    try:
        cfg = cargar()
        informe(True, f".env cargado ({cfg['NOMBRE_ESTUDIANTE']})")
    except ConfigError as e:
        informe(False, str(e).replace("\n", "\n          "))

    print("Python")
    en_venv = Path(sys.prefix).resolve() == (RAIZ / ".venv").resolve()
    informe(en_venv, "ejecutando con .venv de la raíz" if en_venv
            else f"no se está usando .venv (usa .venv/bin/python); intérprete: {sys.executable}")
    for modulo, paquete in (("docx", "python-docx"), ("PIL", "Pillow")):
        informe(importlib.util.find_spec(modulo) is not None, f"{paquete} instalado")

    print("LibreOffice")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    informe(bool(soffice), soffice or "no instalado: sin él no se generan los PDF")

    print("Repositorio público")
    permitidos = (".gitignore", ".env.example", "README.md", "AGENTS.md", "LICENSE",
                  "requirements.txt", "_plantillas/")
    rastreados = git("ls-files", capturar=True).stdout.splitlines()
    fuera = [f for f in rastreados if not f.startswith(permitidos)]
    informe(not fuera, "solo plantillas y documentación en git" if not fuera
            else "archivos de materias en el repo público: " + ", ".join(fuera[:5]))

    sys.exit(0 if ok else 1)


def cmd_materia(args) -> None:
    cargar_o_salir()
    if "/" in args.carpeta or "\\" in args.carpeta:
        sys.exit("Indica solo el nombre de la carpeta (p. ej. sgbd2); se crea dentro de materias/.")
    destino = MATERIAS / args.carpeta
    if destino.exists():
        sys.exit(f"Ya existe: materias/{args.carpeta}/")
    destino.mkdir(parents=True)
    (destino / "README.md").write_text(
        rellenar(PLANTILLAS / "materia" / "README.md", materia_nombre=args.nombre),
        encoding="utf-8",
    )
    print(f"Materia creada: materias/{args.carpeta}/")
    print("  Completa en su README.md el docente, la plataforma y las reglas de entrega.")


def cmd_tarea(args) -> None:
    cargar_o_salir()
    nombre_carpeta = Path(args.materia).name  # admite "sgbd1" o "materias/sgbd1"
    carpeta_materia = MATERIAS / nombre_carpeta
    if not carpeta_materia.is_dir():
        existentes = ", ".join(sorted(p.name for p in MATERIAS.iterdir() if p.is_dir())) if MATERIAS.is_dir() else "ninguna"
        sys.exit(f"No existe la materia '{nombre_carpeta}' en materias/ (hay: {existentes}).\n"
                 f"  Créala con: tareas.py materia {nombre_carpeta} \"Nombre\"")
    codigo = args.codigo.upper()
    tipo = args.tipo or tipo_por_codigo(codigo)
    base = f"{codigo}_{slug_titulo(args.titulo)}"
    destino = carpeta_materia / base
    if destino.exists():
        sys.exit(f"Ya existe: {destino.relative_to(RAIZ)}")

    materia_nombre = nombre_materia(carpeta_materia)
    ruta_carpeta = destino.relative_to(RAIZ).as_posix()
    destino.mkdir()
    (destino / "enunciado").mkdir()
    (destino / "capturas").mkdir()
    (destino / "TAREA.md").write_text(
        rellenar(PLANTILLAS / "tarea" / "TAREA.md", codigo=codigo, titulo=args.titulo,
                 materia_nombre=materia_nombre, tipo=TIPOS[tipo]),
        encoding="utf-8",
    )
    (destino / "generar_documento.py").write_text(
        rellenar(PLANTILLAS / "tarea" / "generar_documento.py", codigo=codigo,
                 titulo=args.titulo, materia_nombre=materia_nombre, base=base,
                 ruta_carpeta=ruta_carpeta, ruta_script=f"{ruta_carpeta}/generar_documento.py"),
        encoding="utf-8",
    )

    readme = carpeta_materia / "README.md"
    if readme.exists():
        texto = readme.read_text(encoding="utf-8")
        if "| Carpeta | Entrega | Estado |" in texto:
            fila = f"| `{base}` | {codigo} — {args.titulo} | pendiente |\n"
            readme.write_text(texto.rstrip("\n") + "\n" + fila, encoding="utf-8")

    print(f"Tarea creada: {ruta_carpeta}/")
    print("  1. Deja el enunciado y la RÚBRICA del docente en enunciado/.")
    print("  2. Completa TAREA.md: fecha, qué se entrega, formato y notas.")
    print(f"  3. Pídele al agente de IA: \"lee AGENTS.md y haz la tarea {ruta_carpeta}\".")


def _limitar_escritura() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (LO_LIMITE_BYTES, LO_LIMITE_BYTES))


def cmd_pdf(args) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("LibreOffice no está instalado. Instálalo (p. ej. `sudo pacman -S libreoffice-fresh`) "
                 "o exporta el PDF a mano desde Word.")
    objetivo = Path(args.ruta).resolve()
    if objetivo.is_dir():
        documentos = sorted(p for p in objetivo.glob("*.docx") if not p.name.startswith("~$"))
    elif objetivo.suffix.lower() == ".docx" and objetivo.exists():
        documentos = [objetivo]
    else:
        sys.exit(f"No es un .docx ni una carpeta: {args.ruta}")
    if not documentos:
        sys.exit(f"No hay archivos .docx en {args.ruta}")

    LO_TMP.mkdir(parents=True, exist_ok=True)
    LO_PERFIL.mkdir(parents=True, exist_ok=True)
    entorno = dict(os.environ, TMPDIR=str(LO_TMP))
    fallos = 0
    for docx in documentos:
        comando = [soffice, f"-env:UserInstallation={LO_PERFIL.as_uri()}", "--headless",
                   "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)]
        try:
            r = subprocess.run(comando, env=entorno, preexec_fn=_limitar_escritura,
                               capture_output=True, text=True, timeout=LO_TIMEOUT)
            pdf = docx.with_suffix(".pdf")
            if r.returncode == 0 and pdf.exists():
                print(f"PDF generado: {pdf.relative_to(RAIZ) if pdf.is_relative_to(RAIZ) else pdf}")
                continue
            print(f"Error al convertir {docx.name}:\n{r.stderr.strip() or r.stdout.strip()}")
        except subprocess.TimeoutExpired:
            print(f"Error: {docx.name} tardó más de {LO_TIMEOUT} s; el .docx probablemente está mal "
                  "formado (p. ej. dos tablas seguidas sin párrafo entre medias).")
            subprocess.run(["pkill", "-f", "soffice"], check=False)
        fallos += 1
    sys.exit(1 if fallos else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="accion", required=True)

    sub.add_parser("verificar", help="comprueba .env, Python, LibreOffice y el repo público")

    p = sub.add_parser("materia", help="crea la carpeta de una materia")
    p.add_argument("carpeta", help="nombre en minúsculas con guiones, p. ej. programacion-web-2")
    p.add_argument("nombre", help="nombre completo de la materia")

    p = sub.add_parser("tarea", help="crea la carpeta de una tarea dentro de una materia")
    p.add_argument("materia", help="carpeta de la materia, p. ej. sgbd1")
    p.add_argument("codigo", help="código del docente: A15, P2, E1...")
    p.add_argument("titulo", help="título corto de la tarea")
    p.add_argument("--tipo", choices=TIPOS, help="se deduce de la letra del código si se omite")

    p = sub.add_parser("pdf", help="convierte .docx a .pdf con LibreOffice")
    p.add_argument("ruta", help="un archivo .docx o una carpeta (convierte todos sus .docx)")

    args = parser.parse_args()
    {
        "verificar": cmd_verificar,
        "materia": cmd_materia,
        "tarea": cmd_tarea,
        "pdf": cmd_pdf,
    }[args.accion](args)


if __name__ == "__main__":
    main()
